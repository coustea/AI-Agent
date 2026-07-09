def quick_pow(base, exp):
    result = 1
    while exp > 0:
        if exp & 1:
            result *= base
        exp >>= 1
        base *= base
    return result

def mod_pow(base, exp, m):
    result = 1
    base %= m
    while exp > 0:
        if exp & 1:
            result = result * base % m
        exp >>= 1
        base = base * base % m
    return result

def mat_mul(A, B, m=None):
    n = len(A)
    C = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                C[i][j] += A[i][k] * B[k][j]
            if m:
                C[i][j] %= m
    return C

def mat_pow(M, exp, m=None):
    n = len(M)
    result = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    while exp > 0:
        if exp & 1:
            result = mat_mul(result, M, m)
        exp >>= 1
        M = mat_mul(M, M, m)
    return result

def fib_matrix(n, m=None):
    if n <= 1:
        return n
    M = [[1, 1], [1, 0]]
    result = mat_pow(M, n - 1, m)
    return result[0][0] if not m else result[0][0] % m

tests = [quick_pow(2, 10), quick_pow(3, 7), mod_pow(2, 100, 1000000007)]
fib_tests = [fib_matrix(i) for i in range(15)]
fib_mod = [fib_matrix(i, 1000000007) for i in [50, 100, 500, 1000]]
