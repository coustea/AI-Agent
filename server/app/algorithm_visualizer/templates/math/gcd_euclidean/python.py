# gcd_euclidean 算法实现 — domain: math
def extended_gcd(a, b):
    if b == 0:
        return a, 1, 0
    g, x1, y1 = extended_gcd(b, a % b)
    return g, y1, x1 - (a // b) * y1

# 定义 gcd 函数
def gcd(a, b):
    while b != 0:
        a, b = b, a % b
    return a

# 定义 lcm 函数
def lcm(a, b):
    return abs(a * b) // gcd(a, b) if a and b else 0

# 定义 mod_inverse 函数
def mod_inverse(a, m):
    g, x, _ = extended_gcd(a % m, m)
    return x % m if g == 1 else None

# 定义 are_coprime 函数
def are_coprime(a, b):
    return gcd(a, b) == 1
