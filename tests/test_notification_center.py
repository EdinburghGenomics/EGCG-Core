import pytest
from unittest.mock import Mock, patch
from smtplib import SMTPException
from egcg_core.notifications import NotificationCentre
from egcg_core.notifications import EmailNotification, AsanaNotification
from egcg_core.exceptions import EGCGError
from tests import TestEGCG

patched_get = patch('egcg_core.rest_communication.get_documents', return_value=[{'run_id': 'test_dataset'}])


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


class TestNotificationCenter(TestEGCG):
    def setUp(self):
        self.notification_center = NotificationCentre('a_name')
        self.notification_center.setup_subscribers(Mock(), Mock())

    def test_notify(self):
        self.notification_center.notify('a message')
        for s in self.notification_center.subscribers:
            s.notify.assert_called_with('a message')


class TestEmailNotification(TestEGCG):
    def setUp(self):
        self.email_ntf = EmailNotification('a_name')

    def test_retries(self):
        with patch('smtplib.SMTP', new=FakeSMTP), patch('egcg_core.notifications.email_notification.sleep'):
            assert self.email_ntf._try_send(self.email_ntf._prepare_message('this is a test')) is True
            assert self.email_ntf._try_send(self.email_ntf._prepare_message('dodgy')) is False

            with pytest.raises(EGCGError) as e:
                self.email_ntf.notify('dodgy')
                assert 'Failed to send message: dodgy' in str(e)


class TestAsanaNotification(TestEGCG):
    def setUp(self):
        self.ntf = AsanaNotification('another_name')
        self.ntf.client = Mock(
            tasks=Mock(
                find_all=Mock(return_value=[{'name': 'this'}]),
                create_in_workspace=Mock(return_value={'id': 1337}),
                find_by_id=Mock(return_value={'name': 'this', 'id': 1337})
            )
        )

    def test_task(self):
        assert self.ntf._task is None
        assert self.ntf.task == {'id': 1337, 'name': 'this'}
        self.ntf.client.tasks.find_by_id.assert_called_with(1337)

    def test_add_comment(self):
        self.ntf.notify('a comment')
        self.ntf.client.tasks.add_comment.assert_called_with(1337, text='a comment')

    def test_get_entity(self):
        collection = [{'name': 'this'}, {'name': 'that'}]
        assert self.ntf._get_entity(collection, 'that') == {'name': 'that'}
        assert self.ntf._get_entity(collection, 'other') is None

    def test_create_task(self):
        assert self.ntf._create_task() == {'id': 1337}
        self.ntf.client.tasks.create_in_workspace.assert_called_with(1337, self.ntf.task_template)
