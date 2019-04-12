import time
import datetime
import os
import sys
import numpy
import csv
import argparse


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


class Thermometer:
    header = ['sensor_id', 'temperature']

    def __init__(self):
        self.temp_files = []
        main_dir = '/sys/class/thermal/'
        for dirname in os.listdir(main_dir):
            if dirname.startswith('thermal_zone'):
                self.temp_files.append(os.path.join(main_dir, dirname, 'temp'))

    def get_values(self):
        temperatures = []
        for i, filename in enumerate(self.temp_files):
            with open(filename) as f:
                lines = f.readlines()
                assert len(lines) == 1
                temp = int(lines[0])
                temperatures.append([i, temp / 1000])  # temperatures in millidegree Celcius
        return temperatures


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


def loop(blas_writer, thermo_writer, nb_calls, nb_runs, nb_sleeps, sleep_time):
    thermo_writer.add_measure()
    for run in range(nb_runs):
        for call in range(nb_calls):
            blas_writer.add_measure()
            thermo_writer.add_measure()
        for sleep in range(nb_sleeps):
            time.sleep(sleep_time)
            thermo_writer.add_measure()


def main(args):
    parser = argparse.ArgumentParser(description='Stress test with performance and temperature measurements')
    parser.add_argument('--size', type=int, default=4096,
                        help='Problem size (rank of the matrix) to use in the tests')
    parser.add_argument('--perf_output', type=str, default='/tmp/stress_perf.csv',
                        help='Output file for the performance measures')
    parser.add_argument('--temp_output', type=str, default='/tmp/stress_temp.csv',
                        help='Output file for the temperature measures')
    parser.add_argument('--nb_calls', type=int, default=10,
                        help='Number of consecutive calls in a run')
    parser.add_argument('--nb_runs', type=int, default=10,
                        help='Number of runs to perform')
    parser.add_argument('--nb_sleeps', type=int, default=100,
                        help='Number of sleeps to perform between each run')
    parser.add_argument('--sleep_time', type=float, default=1,
                        help='Duration of a sleep')
    args = parser.parse_args(args)
    blas_writer = Writer(BLAS(args.size), args.perf_output)
    thermo_writer = Writer(Thermometer(), args.temp_output)
    loop(blas_writer, thermo_writer, args.nb_calls, args.nb_runs, args.nb_sleeps, args.sleep_time)


if __name__ == '__main__':
    main(sys.argv[1:])
