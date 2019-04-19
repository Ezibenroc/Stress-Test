import sys
import argparse
from subprocess import Popen, PIPE


EXEC_NAME = 'test'


def compile_exec():
    cmd = 'gcc %s.c -o %s -Wall' % (EXEC_NAME, EXEC_NAME)
    print(cmd)
    proc = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()
    sys.stdout.write(stdout.decode())
    sys.stderr.write(stderr.decode())


class WrongPattern(Exception):
    pass


def run(file_pattern, nb_calls, size, core):
    numactl_str = 'numactl --physcpubind=%d --localalloc' % core
    try:
        filename = file_pattern % core
    except TypeError:
        raise WrongPattern()
    cmd = '%s ./%s %s %d %d' % (numactl_str, EXEC_NAME, filename, nb_calls, size)
    print(cmd)
    return Popen(cmd.split(), stdout=PIPE, stderr=PIPE)


def run_all(file_pattern, nb_calls, size, cores):
    processes = [run(file_pattern, nb_calls, size, c) for c in cores]
    for proc in processes:
        stdout, stderr = proc.communicate()
        sys.stdout.write(stdout.decode())
        sys.stderr.write(stderr.decode())


def main(args):
    parser = argparse.ArgumentParser(description='Stress test with performance and frequency measurements')
    parser.add_argument('--output_pattern', type=str, default='/tmp/stress_%d.csv',
                        help='Output file for the measures, must contain a "%d"')
    parser.add_argument('--nb_calls', type=int, default=100,
                        help='Number of calls to perform')
    parser.add_argument('--size', type=int, default=1000000000,
                        help='Problem size (number of iterations for the loop)')
    parser.add_argument('--cores', type=int, default=[1], nargs='+',
                        help='Cores on which to run the test')
    args = parser.parse_args(args)
    compile_exec()
    try:
        run_all(args.output_pattern, args.nb_calls, args.size, args.cores)
    except WrongPattern:
        parser.error('The file pattern must contain one (and only one) "%d"')


if __name__ == '__main__':
    main(sys.argv[1:])
