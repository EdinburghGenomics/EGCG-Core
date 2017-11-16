import jinja2
import smtplib
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.utils import COMMASPACE
from time import sleep
from os.path import basename

from egcg_core.app_logging import AppLogger
from egcg_core.exceptions import EGCGError
from .notification import Notification


class EmailSender(AppLogger):

    def __init__(self, subject, mailhost, port, sender, recipients, email_template=None):
        self.subject = subject
        self.mailhost = mailhost
        self.port = port
        self.sender = sender
        self.recipients = recipients
        self.email_template = email_template

    def send_email(self, **kwargs):
        email = self._build_email(**kwargs)
        success = self._try_send(email)
        if not success:
            err_msg = 'Failed to send message with following args: ' + str(kwargs)
            raise EGCGError(err_msg)

    def _try_send(self, msg, retries=3):
        """
        Prepare a MIMEText message from body and diagnostics, and try to send a set number of times.
        :param int retries: Which retry we're currently on
        :return: True if a message is sucessfully sent, otherwise False
        """
        try:
            self._connect_and_send(msg)
            return True
        except (smtplib.SMTPException, TimeoutError) as e:
            retries -= 1
            self.warning('Encountered a %s exception. %s retries remaining', str(e), retries)
            if retries:
                sleep(2)
                return self._try_send(msg, retries)

            return False

    def _build_email(self, **kwargs):
        """
        Create a MIMEMultipart email which can contain:
        MIMEText formated from plain text of Jinja templated html.
        MIMEApplication containing attachments
        :param str body: The main body of the email to send
        """
        if self.email_template:
            content = jinja2.Template(open(self.email_template).read())
            text = MIMEText(content.render(**kwargs), 'html')
        elif 'text_message' in kwargs:
            text = MIMEText(kwargs.get('text_message'))
        else:
            raise EGCGError('EmailSender needs either a text_message or an email template')
        if 'attachments' in kwargs and kwargs['attachments']:
            if isinstance(kwargs['attachments'], str):
                kwargs['attachments'] = [kwargs['attachments']]
            msg = MIMEMultipart()
            msg.attach(text)
            for f in kwargs.get('attachments') or []:
                with open(f, "rb") as fil:
                    part = MIMEApplication(
                        fil.read(),
                        Name=basename(f)
                    )
                    part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
                    msg.attach(part)
        else:
            msg = text

        msg['Subject'] = self.subject
        msg['From'] = self.sender
        msg['To'] = COMMASPACE.join(self.recipients)
        return msg

    def _connect_and_send(self, msg):
        connection = smtplib.SMTP(self.mailhost, self.port)
        connection.send_message(msg, self.sender, self.recipients)
        connection.quit()


class EmailNotification(Notification):
    translation_map = {' ': '&nbsp', '\n': '<br/>'}

    def __init__(self, name, mailhost, port, sender, recipients, strict=False, email_template=None):
        super().__init__(name)
        self.email_sender = EmailSender(name, mailhost, port, sender, recipients, email_template)
        self.strict = strict
        self.email_template = email_template

    def notify(self, msg, attachments=None):
        try:
            if self.email_template:
                self.email_sender.send_email(body=self._prepare_string(msg), attachments=attachment)
            else:
                self.email_sender.send_email(body=msg, attachments=attachments)
        except EGCGError:
            err_msg = 'Failed to send message: ' + str(msg)
            if self.strict:
                raise EGCGError(err_msg)
            else:
                self.critical(err_msg)

    @classmethod
    def _prepare_string(cls, msg):
        for k in cls.translation_map:
            msg = msg.replace(k, cls.translation_map[k])
        return msg


def send_email(msg, mailhost, port, sender, recipients, subject, attachments=None):
    EmailSender(
        subject,
        mailhost,
        port,
        sender,
        recipients,
    ).send_email(text_message=msg, attachments=attachments)

def send_html_email(mailhost, port, sender, recipients, subject, email_template, attachments=None, **kwargs):
    EmailSender(
        subject,
        mailhost,
        port,
        sender,
        recipients,
        email_template=email_template
    ).send_email(attachments=attachments, **kwargs)

