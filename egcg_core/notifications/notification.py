from egcg_core.app_logging import AppLogger


class Notification(AppLogger):
    def __init__(self, name):
        self.name = name

    def _notify(self, msg):
        raise NotImplementedError

    def notify(self, msg):
        self._notify(self.preprocess(msg))

    def preprocess(self, msg):
        return msg
