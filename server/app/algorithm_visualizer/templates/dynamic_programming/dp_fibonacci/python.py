def fibonacci(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 0
    if n == 1:
        return 1
    dp = [0] * (n + 1)
    dp[0] = 0
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]

def fibonacci_optimized(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 0
    if n == 1:
        return 1
    prev2, prev1 = 0, 1
    for i in range(2, n + 1):
        curr = prev1 + prev2
        prev2, prev1 = prev1, curr
    return prev1

def fibonacci_matrix(n):
    def mat_mul(A, B):
        return [
            [A[0][0] * B[0][0] + A[0][1] * B[1][0], A[0][0] * B[0][1] + A[0][1] * B[1][1]],
            [A[1][0] * B[0][0] + A[1][1] * B[1][0], A[1][0] * B[0][1] + A[1][1] * B[1][1]],
        ]

    def mat_pow(M, p):
        result = [[1, 0], [0, 1]]
        while p > 0:
            if p % 2 == 1:
                result = mat_mul(result, M)
            M = mat_mul(M, M)
            p //= 2
        return result

    if n == 0:
        return 0
    base = [[1, 1], [1, 0]]
    result = mat_pow(base, n - 1)
    return result[0][0]

def fibonacci_range(start, end):
    dp = [0, 1]
    for i in range(2, end + 1):
        dp.append(dp[-1] + dp[-2])
    return dp[start:end + 1]

for n in [0, 1, 5, 10, 15, 20]:
    r1 = fibonacci(n)
    r2 = fibonacci_optimized(n)
    r3 = fibonacci_matrix(n)
    assert r1 == r2 == r3

fib_range = fibonacci_range(0, 12)
assert len(fib_range) == 13
assert fib_range[10] == 55
