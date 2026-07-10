from visual_tracer import DpTableTracer

tracer = DpTableTracer()

# 定义 fibonacci 函数
def fibonacci(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 0
    if n == 1:
        return 1
    headers = ["i"] + [str(i) for i in range(n + 1)]
    tracer.init_table(headers, rows=1, cols=n + 1, fill_value=0, line=4)
    dp = [0] * (n + 1)
    dp[0] = 0
    tracer.set_value(0, 0, 0, line=9)
    dp[1] = 1
    tracer.set_value(0, 1, 1, line=11)
# 循环遍历处理
    for i in range(2, n + 1):
        tracer.highlight(0, i - 1, tone="dep", line=13)
        tracer.highlight(0, i - 2, tone="dep", line=13)
        dp[i] = dp[i - 1] + dp[i - 2]
        tracer.highlight(0, i, tone="active", line=15)
        tracer.set_value(0, i, dp[i], line=15)
        tracer.clear_highlights(line=16)
    tracer.finish(line=18)
    return dp[n]

# 定义 fibonacci_optimized 函数
def fibonacci_optimized(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 0
    if n == 1:
        return 1
    prev2, prev1 = 0, 1
# 循环遍历处理
    for i in range(2, n + 1):
        curr = prev1 + prev2
        prev2, prev1 = prev1, curr
    return prev1

# 定义 fibonacci_matrix 函数
def fibonacci_matrix(n):
# 定义 mat_mul 函数
    def mat_mul(A, B):
        return [
            [A[0][0] * B[0][0] + A[0][1] * B[1][0], A[0][0] * B[0][1] + A[0][1] * B[1][1]],
            [A[1][0] * B[0][0] + A[1][1] * B[1][0], A[1][0] * B[0][1] + A[1][1] * B[1][1]],
        ]

# 定义 mat_pow 函数
    def mat_pow(M, p):
        result = [[1, 0], [0, 1]]
# 循环条件判断
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

# 定义 fibonacci_range 函数
def fibonacci_range(start, end):
    dp = [0, 1]
# 循环遍历处理
    for i in range(2, end + 1):
        dp.append(dp[-1] + dp[-2])
    return dp[start:end + 1]

fibonacci(12)
# 循环遍历处理
for n in [0, 1, 5, 10, 15, 20]:
    r1 = fibonacci_optimized(n)
    r2 = fibonacci_matrix(n)
    assert r1 == r2

fib_range = fibonacci_range(0, 12)
assert len(fib_range) == 13
tracer.dump()
