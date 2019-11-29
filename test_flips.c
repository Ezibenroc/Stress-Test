#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <x86intrin.h>
#include <math.h>
#include <string.h>
#include <stdint.h>
#include "util.h"

#ifdef AVX2
typedef __m256d number;
#else
typedef double number;
#endif

/*
 * Return 0b000...01...1, with n ones at the end.
 */
uint64_t __get_mask(unsigned n) {
    if(n == 0)
        return 0;
    assert(n >= 0 && n < 64);
    uint64_t mask = 1;
    return (mask << n) - 1;
}

/*
 * Return 0b000...01...10...0.
 * The bits at positions [start, stop] are equal to 1, the others to 0 (start is the lower order).
 */
uint64_t get_mask(unsigned start, unsigned stop) {
    assert(0 <= start && start <= stop && stop < 64);
    uint64_t ones = __get_mask(stop);
    uint64_t zeroes = ~__get_mask(start);
    return ones & zeroes;
}

/*
 * Apply the given mask to a double.
 */
double apply_mask(double x, uint64_t mask) {
    uint64_t *tmp = (uint64_t*)&x;
    (*tmp) |= mask;
    return *((double*)tmp);
}

void __print_bits(uint64_t n, unsigned i) {
    if(i == 64)
        return;
    __print_bits(n / 2, i+1);
    if(n % 2)
        printf("1");
    else
        printf("0");
}

void print_bits(uint64_t n) {
    printf("0b");
    __print_bits(n, 0);
    printf("\n");
}

void print_bits_f(double x) {
    uint64_t *tmp = (uint64_t*)&x;
    print_bits(*tmp);
}

number measure_call(FILE *f, unsigned long long inner_loop, long id, number tab[4]) {
#ifdef AVX2
    number x0, x1, x2, x3, x4, x5, x6, x7, x8, x9, xA, xB = _mm256_set1_pd(0);
#else
    number x0, x1, x2, x3, x4, x5, x6, x7, x8, x9, xA, xB = 0;
#endif
    timestamp_t start = get_time();
    for(unsigned long long i = 0; i < inner_loop; i++) {
#ifdef AVX2
        x0 = _mm256_fmadd_pd(tab[0], tab[1], x0);
        x1 = _mm256_fmadd_pd(tab[2], tab[3], x1);
        x2 = _mm256_fmadd_pd(tab[0], tab[1], x2);
        x3 = _mm256_fmadd_pd(tab[2], tab[3], x3);
        x4 = _mm256_fmadd_pd(tab[0], tab[1], x4);
        x5 = _mm256_fmadd_pd(tab[2], tab[3], x5);
        x6 = _mm256_fmadd_pd(tab[0], tab[1], x6);
        x7 = _mm256_fmadd_pd(tab[2], tab[3], x7);
        x8 = _mm256_fmadd_pd(tab[0], tab[1], x8);
        x9 = _mm256_fmadd_pd(tab[2], tab[3], x9);
        xA = _mm256_fmadd_pd(tab[0], tab[1], xA);
        xB = _mm256_fmadd_pd(tab[2], tab[3], xB);
#else
        x0 += tab[0] * tab[1];
        x1 += tab[2] * tab[3];
        x2 += tab[0] * tab[1];
        x3 += tab[2] * tab[3];
        x4 += tab[0] * tab[1];
        x5 += tab[2] * tab[3];
        x6 += tab[0] * tab[1];
        x7 += tab[2] * tab[3];
        x8 += tab[0] * tab[1];
        x9 += tab[2] * tab[3];
        xA += tab[0] * tab[1];
        xB += tab[2] * tab[3];
#endif
    }
    timestamp_t stop = get_time();
    unsigned long long duration = compute_duration(start, stop);
    char human_timestamp[50];
    assert(timespec2str(human_timestamp, sizeof(human_timestamp), &start) == 0);
    fprintf(f, "%s,%llu,%li\n", human_timestamp, duration, id);
    number result;
#ifdef AVX2
    x0 = _mm256_add_pd(x0, x1);
    x0 = _mm256_add_pd(x0, x2);
    x0 = _mm256_add_pd(x0, x3);
    x0 = _mm256_add_pd(x0, x4);
    x0 = _mm256_add_pd(x0, x5);
    x0 = _mm256_add_pd(x0, x6);
    x0 = _mm256_add_pd(x0, x7);
    x0 = _mm256_add_pd(x0, x8);
    x0 = _mm256_add_pd(x0, x9);
    x0 = _mm256_add_pd(x0, xA);
    x0 = _mm256_add_pd(x0, xB);
    result = x0;
#else
    result = x0 + x1 + x2 + x3 + x4 + x5;
    result+= x6 + x7 + x8 + x9 + xA + xB;
#endif
    return result;
}

int main(int argc, char *argv[]) {
#ifdef AVX2
    printf("Using AVX2 mode\n");
#else
    printf("Using scalar mode\n");
#endif
    if(argc != 6) {
        fprintf(stderr, "Syntax: %s <filename> <mask_size> <outer_loop> <inner_loop> <ID>\n", argv[0]);
        exit(1);
    }
    char *end;
    unsigned long long outer_loop = strtoull(argv[3], &end, 10);
    unsigned long long inner_loop = strtoull(argv[4], &end, 10);
    long id = strtol(argv[5], &end, 10);
    FILE *f = fopen(argv[1], "w");
    unsigned mask_size = strtoul(argv[2], &end, 10);
    if(!f) {
        perror("fopen");
        exit(1);
    }

    number tab[4];
    double *tab_alias = (double*) tab;
#ifdef AVX2
    int tab_limit = 4*4;
#else
    int tab_limit = 4;
#endif
    unsigned long long val_1, val_2;
    uint64_t mask = get_mask(0, mask_size);
    // the mantisse of the 1st mask is the bit sequence 0b010101... (i.e. 0x555...)
    // the mantisse of the 2nd mask is the bit sequence 0b101010... (i.e. 0xAAA...)
    // for both masks, the exponent is 0x3EF, to have a floating point number not "too large" nor "too small"
    // the sign is 0 (i.e. positive number)
    val_1 = 0x3EF5555555555555 | mask;
    val_2 = 0x3EFAAAAAAAAAAAAA | mask;
    for(int i = 0; i < tab_limit/2; i++) {
        tab_alias[i] = *((double*)&val_1);
    }
    for(int i = tab_limit/2; i < tab_limit; i++) {
        tab_alias[i] = *((double*)&val_2);
    }
    print_bits_f(tab_alias[0]);
    print_bits_f(tab_alias[2]);

    printf("%e %e\n", tab_alias[0], tab_alias[3]);
    for(unsigned long long i = 0; i < outer_loop; i++) {
        measure_call(f, inner_loop, id, tab);
    }

    fclose(f);
    return 0;
}
