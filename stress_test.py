import time
import datetime
import sys
import numpy
import csv
import glob
import argparse
import os
import re
from subprocess import Popen, PIPE


class BLAS:
    header = ['duration', 'gflops']

    def __init__(self, matrix_rank):
        self.matrix_A = self.get_random_matrix(matrix_rank)
        self.matrix_B = self.get_random_matrix(matrix_rank)
        self.matrix_rank = matrix_rank

    @staticmethod
    def get_random_matrix(matrix_rank):
        return numpy.matrix(numpy.random.rand(matrix_rank, matrix_rank))

    def compute(self):
        start = time.time()
        self.matrix_A * self.matrix_B
        duration = time.time() - start
        return duration

    def get_values(self):
        duration = self.compute()
        gflops = 2*self.matrix_rank**3/duration * 1e-9
        return [[duration, gflops]]


class FileWatcher:
    header = ['id', 'value']

    def __init__(self, prefix, name, suffix):
        '''
        Suppose files of the form prefix/name42/suffix
        '''
        self.files = {}
        regex = re.compile('^%s(?P<id>\\d+)$' % name)
        for dirname in os.listdir(prefix):
            match = regex.match(dirname)
            if match:
                new_id = int(match.group('id'))
                self.files[new_id] = os.path.join(prefix, dirname, suffix)

    def get_values(self):
        values = []
        for i, filename in self.files.items():
            with open(filename) as f:
                lines = f.readlines()
                assert len(lines) == 1
                values.append((i, int(lines[0])))
        return values


class Thermometer(FileWatcher):
    header = ['sensor_id', 'temperature']

    def __init__(self):
        super().__init__('/sys/class/thermal', 'thermal_zone', 'temp')

    def get_values(self):
        temperatures = super().get_values()
        return [[i, temp/1000] for i, temp in temperatures]  # temperature in millidegree Celcius


class CPUFreq(FileWatcher):
    header = ['core_id', 'frequency']

    def __init__(self):
        super().__init__('/sys/devices/system/cpu', 'cpu', 'cpufreq/scaling_cur_freq')

    def get_values(self):
        frequencies = super().get_values()
        return [[i, freq*1000] for i, freq in frequencies]  # frequency in kilo Hertz


class Writer:
    def __init__(self, subject, filename):
        self.subject = subject
        self.filename = filename
        self.file = open(filename, 'w')
        self.writer = csv.writer(self.file)
        self.writer.writerow(['start', 'stop'] + self.subject.header)

    def add_measure(self):
        start = self.get_timestamp()
        lines = self.subject.get_values()
        stop = self.get_timestamp()
        for line in lines:
            self.writer.writerow([start, stop] + line)
        self.file.flush()

    @staticmethod
    def get_timestamp():
        return str(datetime.datetime.now())


def loop_blas(blas_writer, thermo_writer, nb_calls, nb_runs, nb_sleeps, sleep_time):
    thermo_writer.add_measure()
    for run in range(nb_runs):
        for call in range(nb_calls):
            blas_writer.add_measure()
            thermo_writer.add_measure()
        for sleep in range(nb_sleeps):
            time.sleep(sleep_time)
            thermo_writer.add_measure()


def loop_cmd(thermo_writer, freq_writer, cmd, nb_runs, nb_sleeps, sleep_time):
    thermo_writer.add_measure()
    freq_writer.add_measure()
    for run in range(nb_runs):
        print('%s | %s' % (Writer.get_timestamp(), cmd))
        proc = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        while proc.poll() is None:
            time.sleep(sleep_time)
            thermo_writer.add_measure()
            freq_writer.add_measure()
        stdout, stderr = proc.communicate()
        sys.stdout.write(stdout.decode())
        sys.stderr.write(stderr.decode())
        if proc.returncode != 0:
            sys.exit(proc.returncode)
        for sleep in range(nb_sleeps):
            time.sleep(sleep_time)
            thermo_writer.add_measure()
            freq_writer.add_measure()


def main(args):
    parser = argparse.ArgumentParser(description='Stress test with performance, frequency and temperature measurements')
    parser.add_argument('--temp_output', type=str, default='/tmp/stress_temp.csv',
                        help='Output file for the temperature measures')
    parser.add_argument('--nb_runs', type=int, default=10,
                        help='Number of runs to perform')
    parser.add_argument('--nb_sleeps', type=int, default=100,
                        help='Number of sleeps to perform between each run')
    parser.add_argument('--sleep_time', type=float, default=1,
                        help='Duration of a sleep')
    sp = parser.add_subparsers(dest='mode')
    sp.required = True
    sp_blas = sp.add_parser('blas', help='Compute a matrix matrix product.')
    sp_blas.add_argument('--size', type=int, default=4096,
                         help='Problem size (rank of the matrix) to use in the tests')
    sp_blas.add_argument('--perf_output', type=str, default='/tmp/stress_perf.csv',
                         help='Output file for the performance measures')
    sp_blas.add_argument('--nb_calls', type=int, default=10,
                         help='Number of consecutive calls in a run')
    sp_cmd = sp.add_parser('command', help='Run a command given as argument.')
    sp_cmd.add_argument('cmd', type=str, help='Command to run')
    sp_cmd.add_argument('--freq_output', type=str, default='/tmp/stress_freq.csv',
                        help='Output file for the frequency measures')
    args = parser.parse_args(args)
    thermo_writer = Writer(Thermometer(), args.temp_output)
    if args.mode == 'blas':
        blas_writer = Writer(BLAS(args.size), args.perf_output)
        loop_blas(blas_writer, thermo_writer, args.nb_calls, args.nb_runs, args.nb_sleeps, args.sleep_time)
    if args.mode == 'command':
        freq_writer = Writer(CPUFreq(), args.freq_output)
        loop_cmd(thermo_writer, freq_writer, args.cmd, args.nb_runs, args.nb_sleeps, args.sleep_time)


if __name__ == '__main__':
    main(sys.argv[1:])
