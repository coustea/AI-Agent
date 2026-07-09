def pascals_triangle(n):
    triangle = []
    for i in range(n):
        row = [1] * (i + 1)
        for j in range(1, i):
            row[j] = triangle[i - 1][j - 1] + triangle[i - 1][j]
        triangle.append(row)
    return triangle

def nCr(n, r):
    if r < 0 or r > n:
        return 0
    if r == 0 or r == n:
        return 1
    r = min(r, n - r)
    result = 1
    for i in range(r):
        result = result * (n - i) // (i + 1)
    return result

def nCr_mod(n, r, p):
    if r < 0 or r > n:
        return 0
    fact = [1] * (n + 1)
    for i in range(1, n + 1):
        fact[i] = fact[i - 1] * i % p
    inv_fact = [1] * (n + 1)
    inv_fact[n] = pow(fact[n], p - 2, p)
    for i in range(n - 1, -1, -1):
        inv_fact[i] = inv_fact[i + 1] * (i + 1) % p
    return fact[n] * inv_fact[r] % p * inv_fact[n - r] % p

def lucas_theorem(n, r, p):
    if r == 0:
        return 1
    return nCr_mod(n % p, r % p, p) * lucas_theorem(n // p, r // p, p) % p

triangle = pascals_triangle(8)
combos = [nCr(10, 3), nCr(20, 10), nCr(15, 7), nCr(100, 50)]
mod_results = [nCr_mod(n, r, 1000000007) for n, r in [(10, 3), (20, 10), (15, 7)]]
lucas = lucas_theorem(100, 50, 13)
