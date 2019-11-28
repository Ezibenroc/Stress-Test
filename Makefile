test_flips: test_flips.c util.c
	gcc -lm -O2 $^ -o $@

test: test.c util.c
	gcc -lblas -O2 $^ -o $@

clean:
	rm -f test_flips test
