#include <stdio.h>
#include <string.h>
#include "util.h"

timestamp_t get_time(void){
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
