# sleep for 10s and work for 10s

import time
import math

from AbstractHandler import AbstractHandler

class handler4(AbstractHandler):
    def run(self):
        print("run")
    
    def stop(self):
        print("stop")
    
    def load_data(self):
        print("load_data")
    
    def ready(self):
        print("ready")
    
    def exception(self):
        print("exception")
    
    def exit(self):
        print("exit")

def is_prime(n):
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(math.sqrt(n)) + 1, 2):
        if n % i == 0:
            return False
    return True

def work(n):
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
    print("Sleeping for 10s")
    time.sleep(10)
    print("Worked for 10s")
    start = time.time()
    while(time.time()-start < 10):
        work(100000)

if __name__ == "__main__":
    main()
    