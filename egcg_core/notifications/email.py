from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, COMMASPACE

import jinja2
import smtplib
from time import sleep
from email.mime.text import MIMEText

from os.path import basename

from egcg_core.exceptions import EGCGError
from .notification import Notification


class EmailNotification(Notification):
    translation_map = {' ': '&nbsp', '\n': '<br/>'}

    def __init__(self, name, mailhost, port, sender, recipients, strict=False, email_template=None):
        super().__init__(name)
        self.mailhost = mailhost
        self.port = port
        self.sender = sender
        self.recipients = recipients
        self.email_template = email_template
        self.strict = strict

    def notify(self, msg, attachment=None):
        email = self.build_email(msg, attachment)
        success = self._try_send(email)
        if not success:
            err_msg = 'Failed to send message: ' + str(msg)
            if self.strict:
                raise EGCGError(err_msg)
            else:
                self.critical(err_msg)

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

    def build_email(self, body, attachments=None):
        """
        Create a MIMEMultipart email which can contain:
        MIMEText formated from plain text of Jinja templated html.
        MIMEApplication containing attachments
        :param str body: The main body of the email to send
        """

        if self.email_template:
            content = jinja2.Template(open(self.email_template).read())
            text = MIMEText(content.render(title=self.name, body=self._prepare_string(body)), 'html')
        else:
            text = MIMEText(body)
        if attachments:
            if isinstance(attachments, str):
                attachments = [attachments]
            msg = MIMEMultipart()
            msg.attach(text)
        else:
            msg = text

        for f in attachments or []:
            with open(f, "rb") as fil:
                part = MIMEApplication(
                    fil.read(),
                    Name=basename(f)
                )
                part['Content-Disposition'] = 'attachment; filename="%s"' % basename(f)
                msg.attach(part)

        msg['Subject'] = self.name
        msg['From'] = self.sender
        msg['To'] = COMMASPACE.join(self.recipients)
        return msg

    @classmethod
    def _prepare_string(cls, msg):
        for k in cls.translation_map:
            msg = msg.replace(k, cls.translation_map[k])
        return msg

    def _connect_and_send(self, msg):
        connection = smtplib.SMTP(self.mailhost, self.port)
        connection.send_message(msg, self.sender, self.recipients)
        connection.quit()


def send_email(msg, mailhost, port, sender, recipients, subject, email_template=None, strict=False, attachments=None):
    EmailNotification(
        subject,
        mailhost,
        port,
        sender,
        recipients,
        strict=strict,
        email_template=email_template
    ).notify(msg, attachments)
