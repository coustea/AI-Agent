from visual_tracer import DpTableTracer
tracer = DpTableTracer()

# knapsack_dp 算法实现 — domain: dynamic_programming
def knapsack(weights, values, capacity):
    if not weights or capacity <= 0:
        tracer.finish(line=3)
        return 0, [], []
    n = len(weights)
    if n != len(values):
        raise ValueError("weights and values must have same length")

    # 初始化 DP 表
    headers = [str(w) for w in range(capacity + 1)]
    rows = [[0] * (capacity + 1) for _ in range(n + 1)]
    tracer.init_table(headers, rows, n + 1, capacity + 1, fill_value=0, line=8)

    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        tracer.move_pointer({"i": i}, line=9)
        for w in range(1, capacity + 1):
            tracer.move_pointer({"w": w}, line=10)
            tracer.highlight(i - 1, w, tone="active", line=11)
            if weights[i - 1] <= w:
                tracer.highlight(i - 1, w - weights[i - 1], tone="active", line=12)
                dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - weights[i - 1]] + values[i - 1])
                tracer.set_value(i, w, dp[i][w], line=12)
            else:
                dp[i][w] = dp[i - 1][w]
                tracer.set_value(i, w, dp[i][w], line=14)
            tracer.clear_highlights(line=14)

    selected = []
    w = capacity
    for i in range(n, 0, -1):
        tracer.move_pointer({"backtrack": i}, line=17)
        tracer.highlight(i, w, tone="success", line=18)
        if dp[i][w] != dp[i - 1][w]:
            selected.append(i - 1)
            w -= weights[i - 1]
        tracer.clear_highlights(line=20)
    selected.reverse()

    tracer.finish(line=22)
    return dp[n][capacity], dp, selected

# 定义 knapsack_optimized 函数
def knapsack_optimized(weights, values, capacity):
    if not weights or capacity <= 0:
        tracer.finish(line=24)
        return 0
    n = len(weights)
    headers = [str(w) for w in range(capacity + 1)]
    tracer.init_table(headers, [[0] * (capacity + 1)], capacity + 1, fill_value=0, line=29)

    dp = [0] * (capacity + 1)
    for i in range(n):
        tracer.move_pointer({"item": i}, line=30)
        for w in range(capacity, weights[i] - 1, -1):
            tracer.move_pointer({"w": w}, line=31)
            tracer.highlight(0, w - weights[i], tone="active", line=32)
            dp[w] = max(dp[w], dp[w - weights[i]] + values[i])
            tracer.set_value(0, w, dp[w], line=32)
            tracer.clear_highlights(line=32)

    tracer.finish(line=33)
    return dp[capacity]

# 定义 knapsack_unbounded 函数
def knapsack_unbounded(weights, values, capacity):
    if not weights or capacity <= 0:
        tracer.finish(line=35)
        return 0
    headers = [str(w) for w in range(capacity + 1)]
    tracer.init_table(headers, [[0] * (capacity + 1)], capacity + 1, fill_value=0, line=39)

    dp = [0] * (capacity + 1)
    for w in range(1, capacity + 1):
        tracer.move_pointer({"w": w}, line=40)
        for i in range(len(weights)):
            if weights[i] <= w:
                tracer.highlight(0, w - weights[i], tone="active", line=42)
                dp[w] = max(dp[w], dp[w - weights[i]] + values[i])
                tracer.set_value(0, w, dp[w], line=43)
                tracer.clear_highlights(line=43)

    tracer.finish(line=44)
    return dp[capacity]

# 定义 knapsack_fractional 函数
def knapsack_fractional(items, capacity):
    tracer.init_table(["weight", "value"], [[str(w), str(v)] for w, v in items], line=47)
    items = sorted(items, key=lambda x: x[1] / x[0], reverse=True)
    total_value = 0.0
    remaining = capacity
    for weight, value in items:
        tracer.move_pointer({"item": items.index((weight, value)) if (weight, value) in items else 0}, line=51)
        tracer.highlight(0, items.index((weight, value)) if (weight, value) in items else 0, tone="active", line=52)
        if remaining >= weight:
            total_value += value
            remaining -= weight
        else:
            total_value += value * (remaining / weight)
            break
        tracer.clear_highlights(line=55)
    tracer.finish(line=58)
    return total_value