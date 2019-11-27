#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <x86intrin.h>
#include <math.h>
#include <string.h>
#include <stdint.h>
#include "util.h"

typedef double number;

void measure_call(FILE *f, unsigned long long inner_loop, long id, number tab[6]) {
    timestamp_t start = get_time();
    for(unsigned long long i = 0; i < inner_loop; i++) {
        tab[0] += tab[1]*tab[2];
        tab[3] += tab[4]*tab[5];
        tab[0] += tab[1]*tab[2];
        tab[3] += tab[4]*tab[5];
        tab[0] += tab[1]*tab[2];
        tab[3] += tab[4]*tab[5];
        tab[0] += tab[1]*tab[2];
        tab[3] += tab[4]*tab[5];
        tab[0] += tab[1]*tab[2];
        tab[3] += tab[4]*tab[5];
        tab[0] += tab[1]*tab[2];
        tab[3] += tab[4]*tab[5];
        tab[0] += tab[1]*tab[2];
        tab[3] += tab[4]*tab[5];
        tab[0] += tab[1]*tab[2];
        tab[3] += tab[4]*tab[5];
    }
    timestamp_t stop = get_time();
    unsigned long long duration = compute_duration(start, stop);
    char human_timestamp[50];
    assert(timespec2str(human_timestamp, sizeof(human_timestamp), &start) == 0);
    fprintf(f, "%s,%llu,%li\n", human_timestamp, duration, id);
}

int main(int argc, char *argv[]) {
    if(argc != 6) {
        fprintf(stderr, "Syntax: %s <filename> <mode> <outer_loop> <inner_loop> <ID>\n", argv[0]);
        exit(1);
    }
    char *end;
    unsigned long long outer_loop = strtoull(argv[3], &end, 10);
    unsigned long long inner_loop = strtoull(argv[4], &end, 10);
    long id = strtol(argv[5], &end, 10);
    FILE *f = fopen(argv[1], "w");
    char *mode = argv[2];
    if(!f) {
        perror("fopen");
        exit(1);
    }

    number tab[6];
    if(strcmp("random", mode) == 0) {
        for(int i = 0; i < 6; i++) {
            tab[i] = (double)rand()/(double)(RAND_MAX);
        }
    }
    else if(strcmp("equal", mode) == 0) {
        double value = (double)rand()/(double)(RAND_MAX);
        for(int i = 0; i < 6; i++) {
            tab[i] = value;
        }
    }
    else if(strcmp("adversarial", mode) == 0) {
        unsigned long long mask_1, mask_2;
        // the mantisse of the 1st mask is the bit sequence 0b010101... (i.e. 0x555...)
        // the mantisse of the 2nd mask is the bit sequence 0b101010... (i.e. 0xAAA...)
        // for both masks, the exponent is 0x3EF, to have a floating point number not "too large" nor "too small"
        // the sign is 0 (i.e. positive number)
        mask_1 = 0x3EF5555555555555;
        mask_2 = 0x3EFAAAAAAAAAAAAA;
        for(int i = 0; i < 3; i++) {
            tab[i] = *((double*)&mask_1);
        }
        for(int i = 3; i < 6; i++) {
            tab[i] = *((double*)&mask_2);
        }
    }
    else {
        fprintf(stderr, "Error, unknown mode '%s', must be 'random', 'equal' or 'adversarial'\n", mode);
        exit(1);
    }

    printf("%e %e\n", tab[0], tab[3]);
    for(unsigned long long i = 0; i < outer_loop; i++) {
        measure_call(f, inner_loop, id, tab);
    }
    printf("%e %e\n", tab[0], tab[3]);
    assert(isfinite(tab[0]));
    assert(isfinite(tab[3]));

    fclose(f);
    return 0;
}
