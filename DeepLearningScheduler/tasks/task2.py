# run a task to find numbers which sum of digits are prime numbers within 100000

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

def sum_of_digits(n):
    sum = 0
    while n > 0:
        sum += n % 10
        n //= 10
    return sum

def main():
    start = time.time()
    primes = find_primes(100000)
    end = time.time()
    print("Found %d primes in %f seconds" % (len(primes), end - start))
    start = time.time()
    sum_of_digits_primes = []
    for i in range(1, 100000):
        if sum_of_digits(i) in primes:
            sum_of_digits_primes.append(i)
    end = time.time()
    print("Found %d sum of digits primes in %f seconds" % (len(sum_of_digits_primes), end - start))

if __name__ == "__main__":
    main()