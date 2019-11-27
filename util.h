#ifndef __UTIL_H__
#define __UTIL_H__

#include <stdlib.h>
#include <time.h>

typedef struct timespec timestamp_t;

/*
 * Return the current timestamp.
 */
timestamp_t get_time(void);

/*
 * Return the time (in nano-seconds) between two timestamps.
 */
unsigned long long compute_duration(timestamp_t start, timestamp_t stop);

/*
 * Write a human-readable date-time in the buffer according to the given timestamp.
 */
int timespec2str(char *buf, uint len, timestamp_t *ts);

#endif
