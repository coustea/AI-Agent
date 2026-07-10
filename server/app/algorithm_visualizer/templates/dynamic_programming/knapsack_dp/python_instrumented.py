from visual_tracer import DpTableTracer

tracer = DpTableTracer()

# 定义 knapsack 函数
def knapsack(weights, values, capacity):
    if not weights or capacity <= 0:
        return 0, [], []
    n = len(weights)
    if n != len(values):
        raise ValueError("weights and values must have same length")
    headers = ["dp"] + [f"w{j}" for j in range(capacity + 1)]
    tracer.init_table(headers, rows=n + 1, cols=capacity + 1, fill_value=0, line=4)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
# 循环遍历处理
    for i in range(1, n + 1):
# 循环遍历处理
        for w in range(1, capacity + 1):
            if weights[i - 1] <= w:
                tracer.highlight(i - 1, w, tone="dep", line=10)
                tracer.highlight(i - 1, w - weights[i - 1], tone="dep", line=10)
                dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - weights[i - 1]] + values[i - 1])
                tracer.highlight(i, w, tone="active", line=12)
                tracer.set_value(i, w, dp[i][w], line=12)
            else:
                tracer.highlight(i - 1, w, tone="dep", line=14)
                dp[i][w] = dp[i - 1][w]
                tracer.highlight(i, w, tone="active", line=15)
                tracer.set_value(i, w, dp[i][w], line=15)
            tracer.clear_highlights(line=16)
    selected = []
    w = capacity
# 循环遍历处理
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            selected.append(i - 1)
            w -= weights[i - 1]
    selected.reverse()
    tracer.finish(line=24)
    return dp[n][capacity], dp, selected

# 定义 knapsack_optimized 函数
def knapsack_optimized(weights, values, capacity):
    if not weights or capacity <= 0:
        return 0
    n = len(weights)
    dp = [0] * (capacity + 1)
# 循环遍历处理
    for i in range(n):
# 循环遍历处理
        for w in range(capacity, weights[i] - 1, -1):
            dp[w] = max(dp[w], dp[w - weights[i]] + values[i])
    return dp[capacity]

# 定义 knapsack_unbounded 函数
def knapsack_unbounded(weights, values, capacity):
    if not weights or capacity <= 0:
        return 0
    dp = [0] * (capacity + 1)
# 循环遍历处理
    for w in range(1, capacity + 1):
# 循环遍历处理
        for i in range(len(weights)):
            if weights[i] <= w:
                dp[w] = max(dp[w], dp[w - weights[i]] + values[i])
    return dp[capacity]

# 定义 knapsack_fractional 函数
def knapsack_fractional(items, capacity):
    items = sorted(items, key=lambda x: x[1] / x[0], reverse=True)
    total_value = 0.0
    remaining = capacity
# 循环遍历处理
    for weight, value in items:
        if remaining >= weight:
            total_value += value
            remaining -= weight
        else:
            total_value += value * (remaining / weight)
            break
    return total_value

weights = [2, 3, 4, 5, 6, 7, 8]
values = [3, 5, 6, 8, 10, 11, 14]
capacity = 15

result, dp_table, selected = knapsack(weights, values, capacity)
r2 = knapsack_optimized(weights, values, capacity)
assert result == r2

r3 = knapsack_unbounded(weights, values, capacity)
assert r3 >= result

items = [(2, 3), (3, 5), (4, 6), (5, 8), (6, 10), (7, 11), (8, 14)]
r4 = knapsack_fractional(items, capacity)
assert r4 >= result
tracer.dump()
