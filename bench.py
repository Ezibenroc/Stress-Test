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


def run(tmpfile, nb_calls, size, core):
    numactl_str = 'numactl --physcpubind=%d --localalloc' % core
    cmd = '%s ./%s %s %d %d %d' % (numactl_str, EXEC_NAME, tmpfile, nb_calls, size, core)
    print(cmd)
    return Popen(cmd.split(), stdout=PIPE, stderr=PIPE)


def run_all(filename, nb_calls, size, cores):
    compile_exec()
    assert len(set(cores)) == len(cores)
    tmpfiles = ['/tmp/bench_%d.csv' % c for c in cores]
    processes = [run(f, nb_calls, size, c) for f, c in zip(tmpfiles, cores)]
    for proc in processes:
        stdout, stderr = proc.communicate()
        sys.stdout.write(stdout.decode())
        sys.stderr.write(stderr.decode())
    with open(filename, 'w') as f:
        f.write('start,end,duration,nb_cycles,core_id\n')
        for tmp in tmpfiles:
            with open(tmp) as f2:
                for line in f2:
                    f.write(line)


def main(args):
    parser = argparse.ArgumentParser(description='Stress test with performance and frequency measurements')
    parser.add_argument('--output', type=str, default='/tmp/stress_perf.csv',
                        help='Output file for the measure')
    parser.add_argument('--nb_calls', type=int, default=100,
                        help='Number of calls to perform')
    parser.add_argument('--size', type=int, default=1000000000,
                        help='Problem size (number of iterations for the loop)')
    parser.add_argument('--cores', type=int, default=[1], nargs='+',
                        help='Cores on which to run the test')
    args = parser.parse_args(args)
    run_all(args.output, args.nb_calls, args.size, args.cores)


if __name__ == '__main__':
    main(sys.argv[1:])
