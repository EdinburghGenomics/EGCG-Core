import os
import pytest
import shutil
import subprocess
from unittest.mock import patch, Mock
from tests import TestEGCG
from egcg_core.executor import Executor, StreamExecutor, ArrayExecutor, PBSExecutor, SlurmExecutor
from egcg_core.executor.cluster_executor import ClusterExecutor, running_executors, stop_running_jobs
from egcg_core.exceptions import EGCGError

get_stdout = 'egcg_core.executor.cluster_executor.ClusterExecutor._get_stdout'
sleep = 'egcg_core.executor.cluster_executor.sleep'


class TestExecutor(TestEGCG):
    executor_cls = Executor

    def execute(self, *args, **kwargs):
        e = self.executor_cls(*args, **kwargs)
        e.start()
        return e.join()

    def test_cmd(self):
        assert self.execute('ls ' + os.path.dirname(self.assets_path)) == 0

    def test_dodgy_cmd(self):
        assert self.execute('dodgy_cmd') == 127  # command not found

    def test_script(self):
        assert self.execute(os.path.join(self.assets_path, 'countdown.sh')) == 0

    def test_dodgy_script(self):
        # same exit status as the running script
        assert self.execute('%s dodgy' % os.path.join(self.assets_path, 'countdown.sh')) == 13

    def test_internal_error(self):
        with patch.object(self.executor_cls, 'info', side_effect=ValueError('Something went wrong')):
            with pytest.raises(EGCGError) as err:
                self.execute('ls')

            assert 'Command failed: ls' in str(err)

    def test_process(self):
        e = self.executor_cls('ls ' + os.path.dirname(self.assets_path))
        assert e.proc is None
        proc = e._process()
        assert proc is e.proc and isinstance(e.proc, subprocess.Popen)

    def test_bash_syntax(self):
        with patch.object(self.executor_cls, 'info') as mocked_info:
            assert self.execute('ls -lh %s | grep __init__' % os.path.dirname(self.assets_path)) == 0

        assert '__init__.py' in mocked_info.call_args_list[1][0][0]


class TestStreamExecutor(TestExecutor):
    executor_cls = StreamExecutor


class TestArrayExecutor(TestExecutor):
    executor_cls = ArrayExecutor

    def execute(self, *args, **kwargs):
        return super().execute(args, stream=True, **kwargs)

    def test_cmd(self):
        e = self.executor_cls(['ls', 'ls -lh', 'pwd'], stream=True)
        e.start()
        assert e.join() == 0
        assert e.exit_statuses == [0, 0, 0]

    def test_dodgy_cmd(self):
        e = self.executor_cls(['ls', 'non_existent_cmd', 'pwd'], stream=True)
        for s in e.executors:
            s.error = Mock()

        e.error = Mock()
        e.start()
        assert e.join() == 127
        assert e.exit_statuses == [
            0,  # ls
            127,  # command not found
            0  # pwd
        ]

    def test_internal_error(self):
        with patch.object(StreamExecutor, 'info', side_effect=ValueError('Something went wrong')):
            with pytest.raises(EGCGError) as err:
                self.execute('ls')

            assert 'Commands failed' in str(err)

    def test_process(self):
        e = self.executor_cls(['ls ' + os.path.dirname(self.assets_path)], stream=True)
        assert e.proc is None
        proc = e._process()
        assert proc is e.proc and isinstance(e.proc, subprocess.Popen)

    def test_bash_syntax(self):
        with patch.object(StreamExecutor, 'info') as mocked_info:
            assert self.execute('ls -lh %s | grep __init__' % os.path.dirname(self.assets_path)) == 0

        assert '__init__.py' in mocked_info.call_args_list[1][0][0]


class TestClusterExecutor(TestEGCG):
    script = os.path.join(TestEGCG.assets_path, 'countdown.sh')
    executor_cls = ClusterExecutor

    def setUp(self):
        self.working_dir = os.path.join(self.assets_path, 'a_working_dir')
        os.makedirs(self.working_dir, exist_ok=True)
        self.executor = self.executor_cls(self.script, job_name='test_job', working_dir=self.working_dir)

    def tearDown(self):
        shutil.rmtree(self.working_dir)

    def test_get_writer(self):
        w = self.executor.writer  # default args
        assert w.cluster_config == {
            'job_name': 'test_job',
            'job_queue': 'a_job_queue',
            'cpus': 1,
            'mem': 2,
            'walltime': None,
            'log_file': w.log_file
        }

        w = self.executor._get_writer('test_job_2', self.working_dir, 'another_job_queue', 2, 4, 1, False)
        assert w.cluster_config == {
            'job_name': 'test_job_2',
            'job_queue': 'another_job_queue',
            'cpus': 2,
            'mem': 4,
            'walltime': 1,
            'log_file': w.log_file
        }

    def test_get_stdout(self):
        popen = 'egcg_core.executor.executor.subprocess.Popen'
        with patch(popen, return_value=Mock(wait=Mock(return_value=None))) as p:
            assert self.executor._get_stdout('ls -d ' + self.assets_path).endswith('tests/assets')
            p.assert_called_with(['ls', '-d', self.assets_path], stdout=-1, stderr=-1)

    def test_run_and_retry(self):
        with patch(get_stdout, side_effect=[None, None, self.assets_path]) as p, patch(sleep):
            assert self.executor._run_and_retry('ls -d ' + self.assets_path).endswith('tests/assets')
            assert p.call_count == 3

    def test_dodgy_cmd(self):
        with pytest.raises(EGCGError) as err, patch(get_stdout, return_value=None), patch(sleep):
            self.executor.cmds = [os.path.join(self.assets_path, 'non_existent_script.sh')]
            self.executor.start()

        assert str(err).endswith('Job submission failed')

    def test_join(self):
        patched_job_finished = patch.object(self.executor_cls, '_job_finished', return_value=True)
        patched_exit_code = patch.object(self.executor_cls, '_job_exit_code', return_value=0)
        self.executor.finished_statuses = 'FXM'
        with patched_job_finished, patched_exit_code, patch(sleep):
            assert self.executor.join() == 0

    def test_job_cancellation(self):
        with patch.object(self.executor_cls, '_submit_job'),\
             patch.object(self.executor_cls, '_job_finished', return_value=True),\
             patch.object(self.executor_cls, 'write_script'),\
             patch.object(self.executor_cls, '_job_exit_code', return_value=9),\
             patch.object(self.executor_cls, 'cancel_job'), patch(sleep):

            self.executor.job_id = 'test_job'
            self.executor.start()
            assert running_executors == {'test_job': self.executor}
            stop_running_jobs()
            assert running_executors == {}


class TestPBSExecutor(TestClusterExecutor):
    executor_cls = PBSExecutor

    def test_qstat(self):
        fake_report = ('Job id            Name             User              Time Use S Queue\n'
                       '----------------  ---------------- ----------------  -------- - -------\n'
                       '1337[].server     a_job_name       a_user            0        B a_queue\n'
                       '1338.server       another_job_name another_user      00:00:00 R a_queue\n')
        with patch(get_stdout, return_value=fake_report) as p:
            assert self.executor._qstat() == [
                '1337[].server     a_job_name       a_user            0        B a_queue',
                '1338.server       another_job_name another_user      00:00:00 R a_queue'
            ]
            p.assert_called_with('qstat -xt None')

    def test_job_status(self):
        qstat = 'egcg_core.executor.cluster_executor.PBSExecutor._qstat'
        fake_report = ['1337.server   a_job   a_user   10:00:00   R    q']
        with patch(qstat, return_value=fake_report):
            assert self.executor._job_statuses() == {'R'}

    def test_job_finished(self):
        job_statuses = 'egcg_core.executor.cluster_executor.PBSExecutor._job_statuses'
        with patch(job_statuses, return_value={'F', 'M', 'X', 'B'}):
            assert not self.executor._job_finished()
        with patch(job_statuses, return_value={'F', 'F', 'M', 'X'}):
            assert self.executor._job_finished()


class TestSlurmExecutor(TestClusterExecutor):
    executor_cls = SlurmExecutor

    def test_sacct(self):
        with patch(get_stdout, return_value=' COMPLETED  0:0 \n COMPLETED  0:0\n FAILED 1:0') as p:
            assert self.executor._sacct('State,ExitCode') == {'COMPLETED  0:0', 'FAILED 1:0'}
            p.assert_called_with('sacct -nX -j None -o State,ExitCode')

    def test_squeue(self):
        with patch(get_stdout, return_value='RUNNING\nRUNNING\nRUNNING') as p:
            assert self.executor._squeue() == {'RUNNING'}
            p.assert_called_with('squeue -h -j None -o %T')

    def test_job_finished(self):
        sacct = 'egcg_core.executor.cluster_executor.SlurmExecutor._sacct'
        patched_squeue = patch('egcg_core.executor.cluster_executor.SlurmExecutor._squeue', return_value='')
        with patch(sacct, return_value=['RUNNING']), patched_squeue:
            assert not self.executor._job_finished()
        with patch(sacct, return_value=['COMPLETED']), patched_squeue:
            assert self.executor._job_finished()

    def test_job_exit_code(self):
        sacct = 'egcg_core.executor.cluster_executor.SlurmExecutor._sacct'
        with patch(sacct, return_value=['CANCELLED 0:0']):
            assert self.executor._job_exit_code() == 9
        with patch(sacct, return_value=['COMPLETED 0:x']):
            assert self.executor._job_exit_code() == 0
