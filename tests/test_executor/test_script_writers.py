from os import makedirs
from os.path import join
import shutil
from egcg_core.executor import script_writers
from tests import TestEGCG

working_dir = join(TestEGCG.assets_path, 'test_script_writer_wd')


class TestScriptWriter(TestEGCG):
    writer_cls = script_writers.ScriptWriter
    array_index = 'JOB_INDEX'
    exp_header = [
            '#!/bin/bash\n',
            '# job name: a_job_name',
            '# cpus: 1',
            '# mem: 2gb',
            '# queue: a_job_queue',
            '# log file: ' + join(working_dir, 'a_job_name.log'),
            '# walltime: 3',
            '# job array: 1-3',
            '',
            'cd ' + working_dir
        ]

    def setUp(self):
        self.exp_cmds = [
            '',
            'some',
            'preliminary',
            'cmds',
            'case $%s in' % self.array_index,
            '1) this\n;;',
            '2) that\n;;',
            '3) other\n;;',
            '*) echo "Unexpected %s: $%s"' % (self.array_index, self.array_index),
            'esac'
        ]

        makedirs(working_dir, exist_ok=True)
        self.script_writer = self.writer_cls(
            'a_job_name',
            working_dir,
            'a_job_queue',
            cpus=1,
            mem=2,
            walltime='3'
        )
        assert self.script_writer.lines == []

    def tearDown(self):
        shutil.rmtree(working_dir)

    def test_init(self):
        w = self.script_writer
        assert w.script_name == join(working_dir, 'a_job_name') + w.suffix
        assert w.log_commands is True
        assert w.log_file == join(working_dir, 'a_job_name.log')

    def test_register_cmd(self):
        self.script_writer.register_cmd('a_cmd', log_file='a_log_file')
        assert self.script_writer.lines == ['a_cmd > a_log_file 2>&1']

    def test_register_cmds(self):
        self.script_writer.register_cmds('this', 'that', parallel=False)
        assert self.script_writer.lines == ['this', 'that']

    def test_add_job_array(self):
        self.script_writer.add_job_array('this', 'that', 'other')
        assert self.script_writer.lines == [
            'case $%s in' % self.array_index,
            '1) this > ' + join(working_dir, 'a_job_name.log1') + ' 2>&1\n;;',
            '2) that > ' + join(working_dir, 'a_job_name.log2') + ' 2>&1\n;;',
            '3) other > ' + join(working_dir, 'a_job_name.log3') + ' 2>&1\n;;',
            '*) echo "Unexpected %s: $%s"' % (self.array_index, self.array_index),
            'esac'
        ]

    def test_save(self):
        self.script_writer.add_line('a_line')
        self.script_writer.save()
        assert 'a_line\n' in open(self.script_writer.script_name, 'r').readlines()

    def test_trim_field(self):
        s = script_writers.PBSWriter('a_job_name_too_long_for_pbs', 'a_working_dir', 'a_job_queue')
        assert s.cluster_config['job_name'] == 'a_job_name_too_'

    def test(self):
        self.script_writer.log_commands = False
        self.script_writer.register_cmds('some', 'preliminary', 'cmds', parallel=False)
        self.script_writer.register_cmds('this', 'that', 'other', parallel=True)
        self.script_writer.add_header()

        obs = self.script_writer.lines
        exp = self.exp_header + self.exp_cmds
        assert obs == exp


class TestPBSWriter(TestScriptWriter):
    writer_cls = script_writers.PBSWriter
    array_index = 'PBS_ARRAY_INDEX'
    exp_header = [
        '#!/bin/bash\n',
        '#PBS -N a_job_name',
        '#PBS -l ncpus=1,mem=2gb',
        '#PBS -q a_job_queue',
        '#PBS -j oe',
        '#PBS -o ' + join(working_dir, 'a_job_name.log'),
        '#PBS -l walltime=3:00:00',
        '#PBS -J 1-3',
        '',
        'cd ' + working_dir
    ]


class TestSlurmWriter(TestScriptWriter):
    writer_cls = script_writers.SlurmWriter
    array_index = 'SLURM_ARRAY_TASK_ID'
    exp_header = [
        '#!/bin/bash\n',
        '#SBATCH --job-name="a_job_name"',
        '#SBATCH --cpus-per-task=1',
        '#SBATCH --mem=2g',
        '#SBATCH --partition=a_job_queue',
        '#SBATCH --output=' + join(working_dir, 'a_job_name.log'),
        '#SBATCH --time=3:00:00',
        '#SBATCH --array=1-3',
        '',
        'cd ' + working_dir
    ]
