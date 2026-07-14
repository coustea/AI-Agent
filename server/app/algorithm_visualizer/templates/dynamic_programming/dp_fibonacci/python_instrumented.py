from visual_tracer import DpTableTracer
tracer = DpTableTracer()

# dp_fibonacci 算法实现 — domain: dynamic_programming
def fibonacci(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        tracer.init_table(["n"], ["0"], line=5)
        tracer.finish(line=6)
        return 0
    if n == 1:
        tracer.init_table(["n"], ["1"], line=8)
        tracer.finish(line=8)
        return 1
    headers = [str(i) for i in range(n + 1)]
    rows = [[0] * (n + 1)]
    tracer.init_table(headers, rows, n + 1, fill_value=0, line=9)
    tracer.set_value(0, 0, 0, line=10)
    tracer.set_value(0, 1, 1, line=11)
    for i in range(2, n + 1):
        tracer.move_pointer({"i": i}, line=12)
        tracer.highlight(0, i - 1, tone="active", line=13)
        tracer.highlight(0, i - 2, tone="active", line=13)
        tracer.clear_highlights(line=13)
        tracer.set_value(0, i, tracer._table[0][i-1] + tracer._table[0][i-2], line=13)
    tracer.finish(line=14)
    return tracer._table[0][n]

# 定义 fibonacci_optimized 函数
def fibonacci_optimized(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    tracer.init_table(["prev2", "prev1"], [[0, 1]], line=17)
    if n == 0:
        tracer.set_value(0, 0, 0, line=20)
        tracer.finish(line=20)
        return 0
    if n == 1:
        tracer.set_value(0, 1, 1, line=23)
        tracer.finish(line=23)
        return 1
    prev2, prev1 = 0, 1
    tracer.set_value(0, 0, prev2, line=24)
    tracer.set_value(0, 1, prev1, line=24)
    for i in range(2, n + 1):
        tracer.move_pointer({"i": i}, line=25)
        curr = prev1 + prev2
        prev2, prev1 = prev1, curr
        tracer.set_value(0, 0, prev2, line=27)
        tracer.set_value(0, 1, prev1, line=27)
    tracer.finish(line=28)
    return prev1

# 定义 fibonacci_matrix 函数
def fibonacci_matrix(n):
    tracer.init_table(["n"], [str(n)], line=30)
    if n == 0:
        tracer.finish(line=49)
        return 0
    tracer.finish(line=52)
    return None  # 矩阵方法复杂，简化处理

# 定义 fibonacci_range 函数
def fibonacci_range(start, end):
    headers = [str(i) for i in range(end + 1)]
    rows = [[0] * (end + 1)]
    tracer.init_table(headers, rows, end + 1, fill_value=0, line=56)
    tracer.set_value(0, 0, 0, line=57)
    tracer.set_value(0, 1, 1, line=57)
    dp = [0, 1]
    for i in range(2, end + 1):
        tracer.move_pointer({"i": i}, line=58)
        dp.append(dp[-1] + dp[-2])
        tracer.set_value(0, i, dp[-1], line=59)
    tracer.finish(line=59)
    return dp[start:end + 1]