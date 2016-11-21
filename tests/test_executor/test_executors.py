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
    def _get_executor(self, cmd):
        return Executor(cmd)

    def test_cmd(self):
        e = self._get_executor('ls ' + os.path.join(self.assets_path, '..'))
        exit_status = e.join()
        assert exit_status == 0

    def test_dodgy_cmd(self):
        with pytest.raises(EGCGError) as err:
            e = self._get_executor('dodgy_cmd')
            e.join()
            assert 'Command failed: \'dodgy_cmd\'' in str(err)

    def test_process(self):
        e = self._get_executor('ls ' + os.path.join(self.assets_path, '..'))
        assert e.proc is None
        proc = e._process()
        assert proc is e.proc and isinstance(e.proc, subprocess.Popen)


class TestStreamExecutor(TestExecutor):
    def _get_executor(self, cmd):
        return StreamExecutor(cmd)

    def test_cmd(self):
        e = self._get_executor(os.path.join(self.assets_path, 'countdown.sh'))
        e.start()
        assert e.join() == 0

    def test_dodgy_command(self):
        e = self._get_executor(os.path.join(self.assets_path, 'countdown.sh') + ' dodgy')
        e.start()
        assert e.join() == 13  # same exit status as the running script

    def test_dodgy_cmd(self):
        with pytest.raises(EGCGError) as err:
            e = self._get_executor('dodgy_cmd')
            e.start()
            e.join()
            assert 'self.proc command failed: \'dodgy_cmd\'' in str(err)


class TestArrayExecutor(TestExecutor):
    def _get_executor(self, cmds):
        return ArrayExecutor(cmds, stream=True)

    def test_cmd(self):
        e = self._get_executor(['ls', 'ls -lh', 'pwd'])
        e.start()
        assert e.join() == 0
        assert e.exit_statuses == [0, 0, 0]

    def test_dodgy_cmd(self):
        e = self._get_executor(['ls', 'non_existent_cmd', 'pwd'])
        e.start()
        with pytest.raises(EGCGError) as err:
            e.join()
            assert 'Commands failed' in str(err)


class TestClusterExecutor(TestEGCG):
    @property
    def script(self):
        return os.path.join(self.assets_path, 'countdown.sh')

    def setUp(self):
        os.makedirs(os.path.join(self.assets_path, 'a_run_id'), exist_ok=True)
        self.executor = self._get_executor(self.script)
        self.ppath = 'egcg_core.executor.cluster_executor.' + self.executor.__class__.__name__

    def tearDown(self):
        shutil.rmtree(os.path.join(self.assets_path, 'a_run_id'))

    def _get_executor(self, cmd):
        return ClusterExecutor(
            cmd,
            job_name='test_job',
            working_dir=os.path.join(self.assets_path, 'a_run_id')
        )

    def test_get_stdout(self):
        popen = 'egcg_core.executor.executor.subprocess.Popen'
        with patch(popen, return_value=Mock(wait=Mock(return_value=None))) as p:
            assert self.executor._get_stdout('ls -d ' + self.assets_path).endswith('tests/assets')
            p.assert_called_with(['ls', '-d', self.assets_path], stdout=-1, stderr=-1)

    def test_dodgy_cmd(self):
        with pytest.raises(EGCGError) as err, patch(get_stdout, return_value=None):
            ex = self._get_executor(os.path.join(self.assets_path, 'non_existent_script.sh'))
            ex.start()
            assert str(err) == 'Job submission failed'

    def test_join(self):
        job_finished = self.ppath + '._job_finished'
        exit_code = self.ppath + '._job_exit_code'
        self.executor.finished_statuses = 'FXM'
        with patch(job_finished, return_value=True), patch(exit_code, return_value=0), patch(sleep):
            assert self.executor.join() == 0

    def test_job_cancellation(self):
        with patch(self.ppath + '._submit_job'), patch(self.ppath + '._job_finished', return_value=True),\
             patch(self.ppath + '.write_script'), patch(self.ppath + '._job_exit_code', return_value=9),\
             patch(self.ppath + '.cancel_job'), patch(sleep):

            self.executor.job_id = 'test_job'
            self.executor.start()
            assert running_executors == {'test_job': self.executor}
            stop_running_jobs()
            assert running_executors == {}


class TestPBSExecutor(TestClusterExecutor):
    def _get_executor(self, cmd):
        return PBSExecutor(
            cmd,
            job_name='test_job',
            working_dir=os.path.join(self.assets_path, 'a_run_id')
        )

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
    def _get_executor(self, cmd):
        return SlurmExecutor(
            cmd,
            job_name='test_job',
            working_dir=os.path.join(self.assets_path, 'a_run_id')
        )

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
