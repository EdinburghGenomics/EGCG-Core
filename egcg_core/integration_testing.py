import json
import requests
from time import sleep
from unittest import TestCase
from egcg_core import config, rest_communication
from subprocess import check_output

cfg = config.Configuration()


class WrappedFunc:
    """For wrapping unittest.TestCase's assert methods, logging details of the assertion carried out."""
    def __init__(self, assert_func):
        self.assert_func = assert_func

    def __call__(self, check_name, *args, **kwargs):
        if not isinstance(check_name, str):
            raise NameError('Incorrect call - check_name required')

        msg = "'%s' using %s with args: %s" % (check_name, self.assert_func.__name__, args)
        if kwargs:
            msg += ', with kwargs: %s' % kwargs

        try:
            self.assert_func(*args, **kwargs)
            self.log(msg + ' - success')
        except AssertionError:
            self.log(msg + ' - failed')
            raise

    @staticmethod
    def log(msg):
        with open('checks.log', 'a') as f:
            f.write(msg + '\n')


class IntegrationTest(TestCase):
    """Contains some common functionality for patching, and quality-oriented assertion logging."""
    patches = ()

    def __init__(self, *args):
        super().__init__(*args)

        # need separate TestCase with non-wrapped assert methods, because some of them call each other
        self.asserter = TestCase()
        for attrname in dir(self.asserter):
            if attrname.startswith('assert'):
                attr = getattr(self.asserter, attrname)
                if callable(attr):
                    setattr(self, attrname, WrappedFunc(attr))

    def setUp(self):
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()


class ReportingAppIntegrationTest(IntegrationTest):
    """
    Sets up a Reporting-App Docker image before each test, and stops/removes it after. Captures the image's IP address
    and uses that to patch egcg_core.rest_communication.default.
    """
    container_id = None
    container_ip = None
    container_port = None

    def setUp(self):
        super().setUp()

        self.container_id = check_output(
            ['docker', 'run', '-d', cfg['reporting_app']['image_name'],
             cfg.query('reporting_app', 'branch', ret_default='master')]
        ).decode()
        assert self.container_id
        container_info = json.loads(check_output(['docker', 'inspect', self.container_id]).decode())[0]
        # for now, assume the container is running on the main 'bridge' network
        self.container_ip = container_info['NetworkSettings']['Networks']['bridge']['IPAddress']
        self.container_port = list(container_info['Config']['ExposedPorts'])[0].rstrip('/tcp')
        container_url = 'http://' + self.container_ip + ':' + self.container_port + '/api/0.1'
        rest_communication.default._baseurl = container_url
        assert rest_communication.default._auth, "Need to specify authentication credentials in the tested app's config"

        self._ping(container_url)

    def tearDown(self):
        super().tearDown()

        assert self.container_id
        check_output(['docker', 'stop', self.container_id])
        check_output(['docker', 'rm', self.container_id])
        self.container_id = self.container_ip = self.container_port = None

    def _ping(self, url, retries=36):
        try:
            requests.get(url, timeout=2)
            return True
        except requests.exceptions.ConnectionError:
            if retries > 0:
                sleep(5)
                return self._ping(url, retries - 1)
            else:
                raise
