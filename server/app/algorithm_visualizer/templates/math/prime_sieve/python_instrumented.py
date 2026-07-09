from visual_tracer import ArrayTracer

tracer = ArrayTracer()

def sieve_of_eratosthenes(n):
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    tracer.init_array(list(range(n + 1)), line=3)
    for i in range(2, int(n ** 0.5) + 1):
        if is_prime[i]:
            for j in range(i * i, n + 1, i):
                is_prime[j] = False
                tracer.assign(j, 0, line=9)
    tracer.finish(line=11)
    return [i for i in range(n + 1) if is_prime[i]]

def linear_sieve(n):
    is_prime = [True] * (n + 1)
    primes = []
    is_prime[0] = is_prime[1] = False
    for i in range(2, n + 1):
        if is_prime[i]:
            primes.append(i)
        for p in primes:
            if i * p > n:
                break
            is_prime[i * p] = False
            if i % p == 0:
                break
    return primes

def count_primes(n):
    return len(sieve_of_eratosthenes(n))

def is_prime_check(n):
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True

primes_100 = sieve_of_eratosthenes(100)
primes_linear_100 = linear_sieve(100)
assert primes_100 == primes_linear_100

count_1000 = count_primes(1000)

checks = [2, 3, 4, 17, 25, 97, 100, 101, 997, 1000]
for n in checks:
    r = is_prime_check(n)
tracer.dump()
