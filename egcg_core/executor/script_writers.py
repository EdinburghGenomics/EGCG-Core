from os.path import join
from egcg_core.app_logging import AppLogger
from egcg_core.exceptions import EGCGError


class ScriptWriter(AppLogger):
    """
    Writes a basic job submission script. Subclassed by PBSWriter. Initialises with self.lines as an empty
    list, which is appended by self.write_line. This list is then saved line by line to self.script_file by
    self.save.
    """
    header = (
        '#!/bin/bash\n',
        '# job name: {job_name}',
        '# cpus: {cpus}',
        '# mem: {mem}gb',
        '# queue: {job_queue}',
        '# log file: {log_file}'
    )
    walltime_header = '# walltime: {walltime}'
    array_header = '# job array: 1-{jobs}'
    suffix = '.sh'
    array_index = 'JOB_INDEX'

    def __init__(self, job_name, working_dir, job_queue, log_commands=True, **cluster_config):
        """
        :param str job_name: Desired full path to the pbs script to write
        """
        self.script_name = join(working_dir, job_name + self.suffix)
        self.log_commands = log_commands
        self.working_dir = working_dir
        self.log_file = join(self.working_dir, job_name + '.log')
        self.info('Writing job "%s" in %s', job_name, working_dir)
        self.lines = []
        self.array_jobs_written = 0
        self.cluster_config = dict(cluster_config, job_name=job_name, log_file=self.log_file, job_queue=job_queue)

    def register_cmd(self, cmd, log_file=None):
        if log_file:
            cmd += ' > %s 2>&1' % log_file
        self.add_line(cmd)

    def register_cmds(self, *cmds, parallel):
        if parallel:
            self.add_job_array(*cmds)
        else:
            self.lines.extend(list(cmds))

    def add_job_array(self, *cmds):
        if self.array_jobs_written != 0:
            raise EGCGError('Already written a job array - can only have one per script')

        if len(cmds) == 1:
            self.register_cmd(cmds[0])
        else:
            self._start_array()
            for idx, cmd in enumerate(cmds):
                self._register_array_cmd(
                    idx + 1,
                    cmd,
                    log_file=self.log_file + str(idx + 1) if self.log_commands else None
                )
            self._finish_array()

        self.array_jobs_written += len(cmds)

    def _register_array_cmd(self, idx, cmd, log_file=None):
        """
        :param int idx: The index of the job, i.e. which number the job has in the array
        :param str cmd: The command to write
        """
        line = str(idx) + ') ' + cmd
        if log_file:
            line += ' > ' + log_file + ' 2>&1'
        line += '\n' + ';;'
        self.add_line(line)

    def add_line(self, line):
        self.lines.append(line)

    def _start_array(self):
        self.add_line('case $%s in' % self.array_index)

    def _finish_array(self):
        self.add_line('*) echo "Unexpected %s: $%s"' % (self.array_index, self.array_index))
        self.add_line('esac')

    def line_break(self):
        self.lines.append('')

    def save(self):
        """Save self.lines to self.script_name."""
        with open(self.script_name, 'w') as f:
            f.write('\n'.join(self.lines) + '\n')

    def add_header(self):
        """Write a header for a given resource manager. If multiple jobs, split them into a job array."""
        header_mapping = dict(self.cluster_config, log_file=self.log_file, jobs=str(self.array_jobs_written))
        header_lines = list(self.header)

        if self.cluster_config.get('walltime'):
            header_lines.append(self.walltime_header)

        if self.array_jobs_written > 1:
            header_lines.append(self.array_header)

        header_lines.extend(['', 'cd ' + self.working_dir, ''])  # prepend the formatted header
        self.lines = [l.format(**header_mapping) for l in header_lines] + self.lines


class SlurmWriter(ScriptWriter):
    """Writes a Bash script runnable on Slurm"""
    suffix = '.slurm'
    array_index = 'SLURM_ARRAY_TASK_ID'

    header = (
        '#!/bin/bash\n',
        '#SBATCH --job-name="{job_name}"',
        '#SBATCH --cpus-per-task={cpus}',
        '#SBATCH --mem={mem}g',
        '#SBATCH --partition={job_queue}',
        '#SBATCH --output={log_file}'
    )
    walltime_header = '#SBATCH --time={walltime}:00:00'
    array_header = '#SBATCH --array=1-{jobs}'


class PBSWriter(ScriptWriter):
    """Writes a Bash script runnable on PBS"""
    suffix = '.pbs'
    array_index = 'PBS_ARRAY_INDEX'

    header = (
        '#!/bin/bash\n',
        '#PBS -N {job_name}',
        '#PBS -l ncpus={cpus},mem={mem}gb',
        '#PBS -q {job_queue}',
        '#PBS -j oe',
        '#PBS -o {log_file}'
    )
    walltime_header = '#PBS -l walltime={walltime}:00:00'
    array_header = '#PBS -J 1-{jobs}'

    def __init__(self, job_name, working_dir, job_queue, log_commands=True, **cluster_config):
        super().__init__(job_name, working_dir, job_queue, log_commands, **cluster_config)
        if len(self.cluster_config['job_name']) > 15:  # job names longer than 15 chars break PBS
            self.cluster_config['job_name'] = self.cluster_config['job_name'][:15]
