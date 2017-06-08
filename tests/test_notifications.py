from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate
from os.path import join, abspath, dirname

import os
import pytest
from unittest.mock import Mock, patch
from smtplib import SMTPException
from email.mime.text import MIMEText
from egcg_core.notifications import NotificationCentre, EmailNotification, send_email, AsanaNotification
from egcg_core.exceptions import EGCGError
from egcg_core.notifications.log import LogNotification
from tests import TestEGCG


class FakeSMTP(Mock):
    def __init__(self, host, port):
        super().__init__()
        self.mailhost, self.port = host, port

    @staticmethod
    def send_message(msg, reporter, recipients):
        if 'dodgy' in str(msg):
            raise SMTPException('Oh noes!')
        else:
            pass

    @staticmethod
    def quit():
        pass


class TestNotificationCentre(TestEGCG):
    def setUp(self):
        self.notification_centre = NotificationCentre('a_name')

    def test_config_init(self):
        e = self.notification_centre.subscribers['email']
        assert e.sender == 'this'
        assert e.recipients == ['that', 'other']
        assert e.mailhost == 'localhost'
        assert e.port == 1337
        assert e.strict is True

        a = self.notification_centre.subscribers['asana']
        assert a.workspace_id == 1337
        assert a.project_id == 1338

    def test_notify(self):
        self.notification_centre.subscribers = {'asana': Mock(), 'email': Mock()}
        self.notification_centre.notify_all('a message')
        for name, s in self.notification_centre.subscribers.items():
            s.notify.assert_called_with('a message')


class TestLogNotification(TestEGCG):
    def setUp(self):
        self.notification_log = join(self.assets_path, 'LogNotification.log')
        self.ntf = LogNotification('log_notification', self.notification_log)

    def tearDown(self):
        os.remove(self.notification_log)

    def test_notify(self):
        self.ntf.notify('message')
        with open(self.notification_log) as open_file:
            assert '[log_notification] message' in open_file.read()

    def _test_notify_with_attachements(self, attachments):
        attachment = join(self.assets_path, 'test_to_upload.txt')
        self.ntf.notify('message', attachments=attachments)
        with open(self.notification_log) as open_file:
            data = open_file.read().split('\n')
            assert '[log_notification] message' in data[0]
            assert '[log_notification] Attachment: %s' % attachment in data[1]

    def test_notify_with_attachement(self):
        self._test_notify_with_attachements([join(self.assets_path, 'test_to_upload.txt')])

    def test_notify_with_attachements(self):
        self._test_notify_with_attachements(join(self.assets_path, 'test_to_upload.txt'))


class TestEmailNotification(TestEGCG):
    def setUp(self):
        self.ntf = EmailNotification(
            'a_subject', 'localhost', 1337, 'a_sender', ['some', 'recipients'], strict=True,
            email_template=join(dirname(dirname(abspath(__file__))), 'etc', 'email_notification.html')
        )

    @patch('egcg_core.notifications.EmailNotification._logger')
    def test_retries(self, mocked_logger):
        with patch('smtplib.SMTP', new=FakeSMTP), patch('egcg_core.notifications.email.sleep'):
            assert self.ntf._try_send(self.ntf.build_email('this is a test')) is True
            assert self.ntf._try_send(self.ntf.build_email('dodgy')) is False
            for i in range(3):
                mocked_logger.warning.assert_any_call(
                    'Encountered a %s exception. %s retries remaining', 'Oh noes!', i
                )

            with pytest.raises(EGCGError) as e:
                self.ntf.notify('dodgy')
                assert 'Failed to send message: dodgy' in str(e)

    def test_build_email(self):
        exp_msg = (
            '<!DOCTYPE html>\n'
            '<html lang="en">\n'
            '<head>\n'
            '    <meta charset="UTF-8">\n'
            '    <style>\n'
            '        table, th, td {\n'
            '            border: 1px solid black;\n'
            '            border-collapse: collapse;\n'
            '        }\n'
            '    </style>\n'
            '</head>\n'
            '<body>\n'
            '    <h2>a_subject</h2>\n'
            '    <p>a&nbspmessage</p>\n'
            '</body>\n'
            '</html>'
        )

        exp = MIMEText(exp_msg, 'html')
        exp['Subject'] = 'a_subject'
        exp['From'] = 'a_sender'
        exp['To'] = 'some, recipients'
        obs = self.ntf.build_email('a message')
        assert str(obs) == str(exp)

    def test_build_email_plain_text(self):
        self.ntf.email_template = None
        exp = MIMEText('a message')
        exp['Subject'] = 'a_subject'
        exp['From'] = 'a_sender'
        exp['To'] = 'some, recipients'
        obs = self.ntf.build_email('a message')
        assert str(obs) == str(exp)

    def _test_build_email_attachments(self, attachements):
        attachment = join(self.assets_path, 'test_to_upload.txt')
        self.ntf.email_template = None
        exp = MIMEMultipart()
        exp['Subject'] = 'a_subject'
        exp['From'] = 'a_sender'
        exp['To'] = 'some, recipients'
        obs = self.ntf.build_email('a message', attachments=attachements)
        payload = obs.get_payload()
        assert len(payload) == 2
        assert str(payload[0]) == str(MIMEText('a message'))
        with open(attachment, 'rb') as open_file:
            part = MIMEApplication(
                open_file.read(),
                Name='test_to_upload.txt'
            )
            part['Content-Disposition'] = 'attachment; filename="test_to_upload.txt"'
            assert str(payload[1]) == str(part)

    def test_build_email_attachments(self):
        attachment = join(self.assets_path, 'test_to_upload.txt')
        self._test_build_email_attachments([attachment])

    def test_build_email_attachment(self):
        attachment = join(self.assets_path, 'test_to_upload.txt')
        self._test_build_email_attachments(attachment)


@patch('egcg_core.notifications.EmailNotification._try_send')
def test_send_email(mocked_send):
    send_email('a message', 'localhost', 1337, 'a_sender', ['some', 'recipients'], 'a subject')
    exp = MIMEText('a message')
    exp['Subject'] = 'a subject'
    exp['From'] = 'a_sender'
    exp['To'] = 'some, recipients'
    assert str(mocked_send.call_args[0][0]) == str(exp)


class TestAsanaNotification(TestEGCG):
    def setUp(self):
        self.ntf = AsanaNotification(
            'another_name',
            workspace_id=1337,
            project_id=1338,
            access_token='an_access_token'
        )
        self.ntf.client = Mock(
            tasks=Mock(
                find_all=Mock(return_value=[{'name': 'this'}]),
                create_in_workspace=Mock(return_value={'id': 1337}),
                find_by_id=Mock(return_value={'name': 'this', 'id': 1337})
            )
        )

    def test_task(self):
        assert self.ntf.task == {'id': 1337, 'name': 'this'}
        self.ntf.client.tasks.find_by_id.assert_called_with(1337)

    def test_add_comment(self):
        self.ntf.notify('a comment')
        self.ntf.client.tasks.add_comment.assert_called_with(1337, text='a comment')

    def _test_add_comment_with_attachments(self, attachments):
        self.ntf.notify('a comment', attachments=[join(self.assets_path, 'test_to_upload.txt')])
        self.ntf.client.tasks.add_comment.assert_called_with(1337, text='a comment')
        self.ntf.client.attachments.create_on_task.assert_called_with(
            file_content=b'test content',
            file_name='test_to_upload.txt',
            task_id=1337
        )

    def test_add_comment_with_attachments(self):
        self._test_add_comment_with_attachments([join(self.assets_path, 'test_to_upload.txt')])

    def test_add_comment_with_attachment(self):
        self._test_add_comment_with_attachments(join(self.assets_path, 'test_to_upload.txt'))

    def test_get_entity(self):
        collection = [{'name': 'this'}, {'name': 'that'}]
        assert self.ntf._get_entity(collection, 'that') == {'name': 'that'}
        assert self.ntf._get_entity(collection, 'other') is None

    def test_create_task(self):
        assert self.ntf._create_task() == {'id': 1337}
        self.ntf.client.tasks.create_in_workspace.assert_called_with(1337, self.ntf.task_template)
