#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <time.h>
#include <assert.h>
#include <string.h>
#include <x86intrin.h>

typedef struct timespec timestamp_t;

timestamp_t get_time(){
    struct timespec tp;
    clock_gettime (CLOCK_REALTIME, &tp);
    return tp;
}

unsigned long long compute_duration(timestamp_t start, timestamp_t stop) {
    unsigned long long start_u = (start.tv_sec * 1000000000 + start.tv_nsec);
    unsigned long long stop_u  = (stop.tv_sec  * 1000000000 + stop.tv_nsec);
    return stop_u - start_u;
}

int timespec2str(char *buf, uint len, timestamp_t *ts) {
    // Taken from https://stackoverflow.com/a/14746954/4110059
    int ret;
    struct tm t;

    tzset();
    if (localtime_r(&(ts->tv_sec), &t) == NULL)
        return 1;

    ret = strftime(buf, len, "%F %T", &t);
    if (ret == 0)
        return 2;
    len -= ret - 1;

    ret = snprintf(&buf[strlen(buf)], len, ".%09ld", ts->tv_nsec);
    if (ret >= len)
        return 3;

    return 0;
}

void measure_call(FILE *f, unsigned long long size) {
    timestamp_t start = get_time();
    unsigned long long start_cycle = __rdtsc();
    for(unsigned long long i=0; i < size; i++);
    unsigned long long stop_cycle = __rdtsc();
    timestamp_t stop = get_time();
    unsigned long long nb_cycles = stop_cycle-start_cycle;
    unsigned long long duration = compute_duration(start, stop);
    char start_date[50], stop_date[50];
    assert(timespec2str(start_date, sizeof(start_date), &start) == 0);
    assert(timespec2str(stop_date, sizeof(stop_date), &start) == 0);
    fprintf(f, "%s,%s,%llu,%llu,%e\n", start_date, stop_date, duration, nb_cycles, ((double)nb_cycles)/duration);
}

int main(int argc, char *argv[]) {
    if(argc != 4) {
        fprintf(stderr, "Syntax: %s <filename> <nb_calls> <size>\n", argv[0]);
        exit(1);
    }
    char *end;
    unsigned long long nb_calls = strtoull(argv[2], &end, 10);
    unsigned long long size = strtoull(argv[3], &end, 10);
    FILE *f = fopen(argv[1], "w");
    if(!f) {
        perror("fopen");
        exit(1);
    }
    for(unsigned long long i = 0; i < nb_calls; i++) {
        measure_call(f, size);
    }
    fclose(f);
    return 0;
}
