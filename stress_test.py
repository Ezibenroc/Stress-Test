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
from basic_monitoring import FileWatcher, Thermometer, CPUFreq, Writer


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


class Loop:
    EXEC_NAME = 'test'
    NUMA = True  # set to False to disable thread pinning

    def __init__(self, filename, nb_calls, size, cores, freq_writer, thermo_writer, nb_runs, nb_sleeps, sleep_time):
        assert len(set(cores)) == len(cores)
        self.filename = filename
        with open(filename, 'w') as f:
            f.write('start,stop,duration,nb_cycles,core_id,gflops\n')
        self.nb_calls = nb_calls
        self.size = size
        self.cores = cores
        self.freq_writer = freq_writer
        self.thermo_writer = thermo_writer
        self.nb_runs = nb_runs
        self.nb_sleeps = nb_sleeps
        self.sleep_time = sleep_time
        self.compile_exec()

    @classmethod
    def compile_exec(cls):
        cmd = 'gcc -lblas %s.c -o %s -Wall' % (cls.EXEC_NAME, cls.EXEC_NAME)
        print(cmd)
        proc = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()
        sys.stdout.write(stdout.decode())
        sys.stderr.write(stderr.decode())

    @classmethod
    def run(cls, tmpfile, nb_calls, size, core):
        numactl_str = 'numactl --physcpubind=%d --localalloc' % core if cls.NUMA else ''
        os.environ['OMP_NUM_THREADS'] = '1'
        cmd = '%s ./%s %s %d %d %d' % (numactl_str, cls.EXEC_NAME, tmpfile, nb_calls, size, core)
        print(cmd)
        return Popen(cmd.split(), stdout=PIPE, stderr=PIPE)

    def run_cores(self):
        self.thermo_writer.add_measure()
        self.freq_writer.add_measure()
        tmpfiles = ['/tmp/bench_%d.csv' % c for c in self.cores]
        processes = [self.run(f, self.nb_calls, self.size, c) for f, c in zip(tmpfiles, self.cores)]
        while processes[0].poll() is None:
            time.sleep(self.sleep_time)
            self.thermo_writer.add_measure()
            self.freq_writer.add_measure()
        for proc in processes:
            stdout, stderr = proc.communicate()
            sys.stdout.write(stdout.decode())
            sys.stderr.write(stderr.decode())
        with open(self.filename, 'a') as f:
            for tmp in tmpfiles:
                with open(tmp) as f2:
                    for line in f2:
                        f.write(line)

    def run_all(self):
        for run in range(self.nb_runs):
            self.run_cores()
            for sleep in range(self.nb_sleeps):
                time.sleep(self.sleep_time)
                self.thermo_writer.add_measure()
                self.freq_writer.add_measure()


def main(args):
    parser = argparse.ArgumentParser(description='Stress test with performance, frequency and temperature measurements')
    parser.add_argument('--temp_output', type=str, default='/tmp/stress_temp.csv',
                        help='Output file for the temperature measures')
    parser.add_argument('--nb_runs', type=int, default=10,
                        help='Number of runs to perform')
    parser.add_argument('--nb_calls', type=int, default=10,
                        help='Number of consecutive calls in a run')
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
    sp_cmd = sp.add_parser('command', help='Run a command given as argument.')
    sp_cmd.add_argument('cmd', type=str, help='Command to run')
    sp_cmd.add_argument('--freq_output', type=str, default='/tmp/stress_freq.csv',
                        help='Output file for the frequency measures')
    sp_loop = sp.add_parser('loop', help='Run an (empty) for loop')
    sp_loop.add_argument('--size', type=int, default=1000000000,
                         help='Number of iterations to perform')
    sp_loop.add_argument('--perf_output', type=str, default='/tmp/stress_perf.csv',
                         help='Output file for the performance measures')
    sp_loop.add_argument('--freq_output', type=str, default='/tmp/stress_freq.csv',
                         help='Output file for the frequency measures')
    sp_loop.add_argument('--cores', type=int, default=[1], nargs='+',
                         help='Cores on which to run the test')
    args = parser.parse_args(args)
    thermo_writer = Writer(Thermometer(), args.temp_output)
    if args.mode == 'blas':
        blas_writer = Writer(BLAS(args.size), args.perf_output)
        loop_blas(blas_writer, thermo_writer, args.nb_calls, args.nb_runs, args.nb_sleeps, args.sleep_time)
    if args.mode == 'command':
        freq_writer = Writer(CPUFreq(), args.freq_output)
        loop_cmd(thermo_writer, freq_writer, args.cmd, args.nb_runs, args.nb_sleeps, args.sleep_time)
    if args.mode == 'loop':
        freq_writer = Writer(CPUFreq(), args.freq_output)
        Loop(args.perf_output, args.nb_calls, args.size, args.cores, freq_writer, thermo_writer, args.nb_runs,
             args.nb_sleeps, args.sleep_time).run_all()


if __name__ == '__main__':
    main(sys.argv[1:])
