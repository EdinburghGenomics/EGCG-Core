from os.path import join
from tests import TestEGCG
from egcg_core.config import Configuration, EnvConfiguration


class TestConfiguration(TestEGCG):
    def setUp(self):
        self.cfg = Configuration(self.etc_config)

    def test_find_config_file(self):
        existing_cfg_file = self.etc_config
        non_existing_cfg_file = join(self.etc, 'non_existent.yaml')
        assert self.cfg._find_config_file((non_existing_cfg_file, existing_cfg_file)) == existing_cfg_file

        self.cfg.content = None
        self.cfg._find_config_file((non_existing_cfg_file,))
        assert self.cfg.content is None

    def test_load_config_file(self):
        original_content = self.cfg.content
        self.cfg.content = None
        self.cfg.load_config_file(self.etc_config)
        assert self.cfg.content == original_content

    def test_get(self):
        assert self.cfg.get('nonexistent_thing') is None
        assert self.cfg.get('nonexistent_thing', 'a_default') == 'a_default'
        assert self.cfg.get('default').get('executor').get('job_execution') == 'local'

    def test_query(self):
        assert self.cfg.query('default', 'executor', 'job_execution') == 'local'
        assert self.cfg.query('default', 'nonexistent_thing') is None

    def test_contains(self):
        assert 'default' in self.cfg


class TestEnvConfiguration(TestConfiguration):
    def setUp(self):
        self.cfg = EnvConfiguration(self.etc_config)

    def test_get(self):
        assert self.cfg.get('executor').get('job_execution') == 'local'

    def test_query(self):
        assert self.cfg.query('logging', 'handlers', 'nonexistent_handler') is None
        assert self.cfg.query('logging', 'datefmt') == '%Y-%b-%d %H:%M:%S'

    def test_merge_dicts(self):
        default_dict = {
            'this': {
                'another': [2, 3, 4],
                'more': {
                    'thing': 'thang'
                }
            },
            'that': 'a_thing',
            'other': {
                'another': [2, '3', 4],
                'more': {
                    'thing': 'thang'
                }
            }
        }
        override_dict = {
            'that': 'another_thing',
            'another': 4,
            'more': 5,
            'other': {
                'another': [8, 9, 10],
                'more': {'thung': 'theng'}
            }
        }
        merged_dict = self.cfg._merge_dicts(default_dict, override_dict)

        assert dict(merged_dict) == {
            'this': {
                'another': [2, 3, 4],
                'more': {
                    'thing': 'thang'
                }
            },
            'that': 'another_thing',
            'other': {
                'another': [8, 9, 10],
                'more': {
                    'thing': 'thang',
                    'thung': 'theng'
                }
            },
            'another': 4,
            'more': 5
        }

        assert dict(self.cfg._merge_dicts(default_dict, default_dict)) == default_dict

    def test_contains(self):
        assert 'rest_api' in self.cfg
