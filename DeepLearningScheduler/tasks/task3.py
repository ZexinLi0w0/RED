# run a task to find numbers which mod one of primes smaller than this number are prime number within 100000

import time
import math

def is_prime(n):
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True

def find_primes(n):
    primes = []
    i = 2
    while len(primes) < n:
        if is_prime(i):
            primes.append(i)
        i += 1
    return primes

def main():
    start = time.time()
    primes = find_primes(100000)
    end = time.time()
    print("Found %d primes in %f seconds" % (len(primes), end - start))
    start = time.time()
    mod_primes = []
    for i in range(1, 100000):
        for j in primes:
            if i % j == 0 and is_prime(i):
                mod_primes.append(i)
                break
    end = time.time()
    print("Found %d mod primes in %f seconds" % (len(mod_primes), end - start))

if __name__ == "__main__":
    main()