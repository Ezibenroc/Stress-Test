# Call as follows to enable AVX2
# make CFLAGS="-DAVX2"

test_flips: test_flips.c util.c
	gcc -march=native -lm -O2 $(CFLAGS) $^ -o $@

test: test.c util.c
	gcc -lblas -O2 $^ -o $@

clean:
	rm -f test_flips test
