from visual_tracer import ArrayTracer
tracer = ArrayTracer()

# prime_sieve 算法实现 — domain: math
def sieve_of_eratosthenes(n):
    tracer.init_array(list(range(n + 1)), line=2)
    is_prime = [True] * (n + 1)
    tracer.assign(0, False, line=4)
    tracer.assign(1, False, line=4)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(n ** 0.5) + 1):
        tracer.move_pointer({"i": i}, line=6)
        if is_prime[i]:
            tracer.highlight(i, tone="active", line=7)
            for j in range(i * i, n + 1, i):
                tracer.move_pointer({"mark": j}, line=8)
                is_prime[j] = False
                tracer.assign(j, False, line=8)
                tracer.highlight(j, tone="danger", line=8)
            tracer.clear_highlights(line=8)
    primes = [i for i in range(n + 1) if is_prime[i]]
    for p in primes:
        tracer.mark_sorted(p, line=9)
    tracer.finish(line=9)
    return primes

# 定义 linear_sieve 函数
def linear_sieve(n):
    tracer.init_array(list(range(n + 1)), line=11)
    is_prime = [True] * (n + 1)
    primes = []
    tracer.assign(0, False, line=15)
    tracer.assign(1, False, line=15)
    is_prime[0] = is_prime[1] = False
    for i in range(2, n + 1):
        tracer.move_pointer({"i": i}, line=16)
        if is_prime[i]:
            primes.append(i)
            tracer.highlight(i, tone="active", line=18)
            tracer.mark_sorted(i, line=18)
        for p in primes:
            tracer.move_pointer({"p": p}, line=19)
            if i * p > n:
                break
            is_prime[i * p] = False
            tracer.assign(i * p, False, line=22)
            tracer.highlight(i * p, tone="danger", line=22)
            if i % p == 0:
                tracer.clear_highlights(line=23)
                break
        tracer.clear_highlights(line=23)
    tracer.finish(line=25)
    return primes

# 定义 count_primes 函数
def count_primes(n):
    primes = sieve_of_eratosthenes(n)
    return len(primes)

# 定义 is_prime_check 函数
def is_prime_check(n):
    tracer.init_array([n], line=32)
    if n < 2:
        tracer.finish(line=34)
        return False
    if n < 4:
        tracer.finish(line=36)
        return True
    tracer.move_pointer({"check": n}, line=37)
    if n % 2 == 0 or n % 3 == 0:
        tracer.highlight(0, tone="danger", line=38)
        tracer.finish(line=38)
        return False
    i = 5
    while i * i <= n:
        tracer.move_pointer({"i": i}, line=40)
        if n % i == 0 or n % (i + 2) == 0:
            tracer.highlight(0, tone="danger", line=41)
            tracer.finish(line=41)
            return False
        i += 6
    tracer.highlight(0, tone="success", line=43)
    tracer.finish(line=43)
    return True