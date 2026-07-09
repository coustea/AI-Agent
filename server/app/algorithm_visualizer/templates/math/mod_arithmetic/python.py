def mod_add(a, b, m):
    return (a % m + b % m) % m

def mod_mul(a, b, m):
    return (a % m * b % m) % m

def mod_pow(base, exp, m):
    result = 1
    base %= m
    while exp > 0:
        if exp & 1:
            result = result * base % m
        exp >>= 1
        base = base * base % m
    return result

def mod_inverse(a, m):
    g, x, _ = extended_gcd(a, m)
    return x % m if g == 1 else None

def extended_gcd(a, b):
    if b == 0:
        return a, 1, 0
    g, x1, y1 = extended_gcd(b, a % b)
    return g, y1, x1 - (a // b) * y1

def crt(remainders, moduli):
    m = 1
    for mi in moduli:
        m *= mi
    x = 0
    for ri, mi in zip(remainders, moduli):
        Mi = m // mi
        yi = mod_inverse(Mi, mi)
        x = (x + ri * Mi * yi) % m
    return x

m = 1000000007
vals = [mod_add(123456, 789012, m), mod_mul(12345, 67890, m), mod_pow(2, 100, m)]
inv = mod_inverse(3, m)
crt_result = crt([2, 3, 2], [3, 5, 7])
