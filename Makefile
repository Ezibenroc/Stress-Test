test_flips:
	gcc -lm -O2 util.c test_flips.c -o test_flips

test:
	gcc -lblas -O2 util.c test.c -o test

clean:
	rm -f test_flips test
