from unittest.mock import patch

import os

from egcg_core.archive_management import archive_states, release_file_from_lustre, ArchivingError, \
    register_for_archiving, recall_from_tape, archive_directory
from tests import TestEGCG


class TestArchiveManagement(TestEGCG):

    def test_archive_states(self):

        with patch('egcg_core.archive_management._get_stdout',
                   return_value='testfile: (0x0000000d) released exists archived, archive_id:1'):
            assert archive_states('testfile') == ['released', 'exists', 'archived']

        with patch('egcg_core.archive_management._get_stdout',
                   return_value='testfile: (0x00000009) exists archived, archive_id:1'):
            assert archive_states('testfile') == ['exists', 'archived']

        with patch('egcg_core.archive_management._get_stdout',
                   return_value='testfile: (0x00000001) exists, archive_id:1'):
            assert archive_states('testfile') == ['exists']

        with patch('egcg_core.archive_management._get_stdout',
                   return_value='testfile: (0x00000000)'):
            assert archive_states('testfile') == []

    def test_release_file_from_lustre(self):
        with patch('egcg_core.archive_management._get_stdout',
                   side_effect=[
                       'testfile: (0x00000009) exists archived, archive_id:1',
                       '',
                       'testfile: (0x0000000d) released exists archived, archive_id:1'
                   ]) as get_stdout:
            assert release_file_from_lustre('testfile')
            assert get_stdout.call_count == 3
            assert get_stdout.call_args_list[1][0] == ('lfs hsm_release testfile',)

        with patch('egcg_core.archive_management._get_stdout',
                   side_effect=[
                       'testfile: (0x0000000d) released exists archived, archive_id:1',
                   ]) as get_stdout:
            assert release_file_from_lustre('testfile')
            assert get_stdout.call_count == 1

        with patch('egcg_core.archive_management._get_stdout',
                   side_effect=[
                       'testfile: (0x00000009) exists, archive_id:1',
                   ]) as get_stdout:
            self.assertRaises(ArchivingError, release_file_from_lustre, 'testfile')
            assert get_stdout.call_count == 1

    def test_register_for_archiving(self):
        with patch('egcg_core.archive_management._get_stdout',
                   side_effect=[
                       'testfile: (0x00000001)',
                       '',
                       'testfile: (0x00000009) exists, archive_id:1',
                    ]) as get_stdout:
            assert register_for_archiving('testfile')
            assert get_stdout.call_count == 3
            assert get_stdout.call_args_list[1][0] == ('lfs hsm_archive testfile',)

        with patch('egcg_core.archive_management._get_stdout',
                   side_effect=[
                       'testfile: (0x00000001) exists, archive_id:1',
                   ]) as get_stdout:
            assert register_for_archiving('testfile')
            assert get_stdout.call_count == 1

        with patch('egcg_core.archive_management._get_stdout',
                   side_effect=[
                       'testfile: (0x00000001)',
                       '',
                       'testfile: (0x00000001)',
                    ]) as get_stdout:
            self.assertRaises(ArchivingError, register_for_archiving, 'testfile', True)
            assert get_stdout.call_count == 3
            assert get_stdout.call_args_list[1][0] == ('lfs hsm_archive testfile',)

    def test_recall_from_tape(self):
        with patch('egcg_core.archive_management._get_stdout',
                   side_effect=[
                       'testfile: (0x0000000d) released exists archived, archive_id:1',
                       '',
                   ]) as get_stdout:
            assert recall_from_tape('testfile')
            assert get_stdout.call_count == 2
            assert get_stdout.call_args_list[1][0] == ('lfs hsm_restore testfile',)

    def test_archive_directory(self):
        with patch('egcg_core.archive_management.register_for_archiving') as register:
            assert archive_directory(os.path.join(self.assets_path, 'fastqs'))
            assert register.call_count == 6
