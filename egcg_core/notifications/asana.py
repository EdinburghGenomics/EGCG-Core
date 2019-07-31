import asana
from cached_property import cached_property
from os.path import basename
from .notification import Notification


class AsanaNotification(Notification):
    def __init__(self, name, workspace_id, project_id, access_token, task_description=None):
        super().__init__(name)
        self.task_id = self.name
        self.workspace_id = workspace_id
        self.project_id = project_id
        self.client = asana.Client.access_token(access_token)
        self.task_template = {'name': name, 'projects': [self.project_id]}
        if task_description:
            self.task_template['notes'] = task_description

    def notify(self, msg, attachments=None):
        self.client.tasks.add_comment(self.task['gid'], text=msg)
        self.client.tasks.update(self.task['gid'], completed=False)

        if attachments:
            if isinstance(attachments, str):
                attachments = [attachments]

        for attachment in attachments or []:
            with open(attachment, 'rb') as fil:
                content = fil.read()

                # can't use self.client.attachments.create_on_task here - results in TypeError
                self.client.request(
                    'post',
                    '/tasks/%s/attachments' % self.task['gid'],
                    files=[('file', (basename(attachment), content, None))],
                )

    @cached_property
    def task(self):
        tasks = list(self.client.tasks.find_all(project=self.project_id))
        task_ent = self._get_entity(tasks, self.task_id)
        if task_ent is None:
            task_ent = self._create_task()
        return self.client.tasks.find_by_id(task_ent['gid'])

    @staticmethod
    def _get_entity(collection, name):
        for e in collection:
            if e['name'] == name:
                return e

    def _create_task(self):
        return self.client.tasks.create_in_workspace(self.workspace_id, self.task_template)
