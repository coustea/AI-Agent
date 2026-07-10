# recursion_fib 算法实现 — domain: recursion_backtrack
def fib_naive(n):
    if n <= 1:
        return n
    return fib_naive(n - 1) + fib_naive(n - 2)

# 定义 fib_memo 函数
def fib_memo(n, memo=None):
    if memo is None:
        memo = {0: 0, 1: 1}
    if n in memo:
        return memo[n]
    memo[n] = fib_memo(n - 1, memo) + fib_memo(n - 2, memo)
    return memo[n]

# 定义 fib_tabulation 函数
def fib_tabulation(n):
    if n <= 1:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]

# 定义 fib_optimized 函数
def fib_optimized(n):
    if n <= 1:
        return n
    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr
    return curr

# 定义 fib_matrix 函数
def fib_matrix(n):
# 定义 mat_mul 函数
    def mat_mul(A, B):
        return [
            [A[0][0]*B[0][0] + A[0][1]*B[1][0], A[0][0]*B[0][1] + A[0][1]*B[1][1]],
            [A[1][0]*B[0][0] + A[1][1]*B[1][0], A[1][0]*B[0][1] + A[1][1]*B[1][1]],
        ]
# 定义 mat_pow 函数
    def mat_pow(M, n):
        result = [[1, 0], [0, 1]]
        while n > 0:
            if n & 1:
                result = mat_mul(result, M)
            M = mat_mul(M, M)
            n >>= 1
        return result
    if n <= 1:
        return n
    M = [[1, 1], [1, 0]]
    return mat_pow(M, n - 1)[0][0]

for n in [10, 20, 30]:
    r1 = fib_memo(n)
    r2 = fib_tabulation(n)
    r3 = fib_optimized(n)
    r4 = fib_matrix(n)
    assert r1 == r2 == r3 == r4

dp_table = [fib_tabulation(i) for i in range(15)]
