from egcg_core.app_logging import AppLogger
from egcg_core.config import cfg
from .asana import AsanaNotification
from .email import EmailNotification, EmailSender, send_email, send_html_email, send_plain_text_email
from .log import LogNotification


class NotificationCentre(AppLogger):
    ntf_aliases = {
        'log': LogNotification,
        'email': EmailNotification,
        'asana': AsanaNotification
    }

    def __init__(self, name):
        self.name = name
        self.subscribers = {}

        for s in cfg.get('notifications', {}):
            if s in self.ntf_aliases:
                self.debug('Configuring notification for: ' + s)
                config = cfg['notifications'][s]
                self.subscribers[s] = self.ntf_aliases[s](name=self.name, **config)
            else:
                self.warning("Bad notification config '%s' - this will be ignored", s)

    def notify(self, msg, subs):
        for s in subs:
            if s in self.subscribers:
                self.subscribers[s].notify(msg)
            else:
                self.debug('Tried to notify by %s, but no configuration present', s)

    def notify_all(self, msg):
        for s in self.subscribers.values():
            s.notify(msg)
