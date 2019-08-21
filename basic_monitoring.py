import time
import datetime
import sys
import numpy
import csv
import glob
import argparse
import os
import re


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


def loop(thermo_writer, freq_writer, period):
    start = time.time()
    try:
        while True:
            thermo_writer.add_measure()
            freq_writer.add_measure()
            time.sleep(period)
    except KeyboardInterrupt:
        stop = time.time()
        print('\nMonitored the system for %.2f seconds' % (stop-start))


def main(args):
    parser = argparse.ArgumentParser(description='Periodic frequency and temperature measurements')
    parser.add_argument('--temp_output', type=str, default='/tmp/monitoring_temp.csv',
                        help='Output file for the temperature measures')
    parser.add_argument('--freq_output', type=str, default='/tmp/monitoring_freq.csv',
                        help='Output file for the frequency measures')
    parser.add_argument('--pid_file', type=str, default='/tmp/monitoring_pid',
                        help='File in which the PID of this process will be written')
    parser.add_argument('--period', type=float, default=1,
                        help='Interval of time between each measure')
    args = parser.parse_args(args)
    thermo_writer = Writer(Thermometer(), args.temp_output)
    freq_writer = Writer(CPUFreq(), args.freq_output)
    pid = os.getpid()
    with open(args.pid_file, 'w') as f:
        f.write('%d\n' % pid)
    print('Starting to monitor the system, press Ctrl-C to stop')
    loop(thermo_writer, freq_writer, args.period)


if __name__ == '__main__':
    main(sys.argv[1:])
