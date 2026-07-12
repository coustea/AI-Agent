# knapsack_dp 算法实现 — domain: dynamic_programming
def knapsack(weights, values, capacity):
    if not weights or capacity <= 0:
        return 0, [], []
    n = len(weights)
    if n != len(values):
        raise ValueError("weights and values must have same length")
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(1, capacity + 1):
            if weights[i - 1] <= w:
                dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - weights[i - 1]] + values[i - 1])
            else:
                dp[i][w] = dp[i - 1][w]
    selected = []
    w = capacity
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            selected.append(i - 1)
            w -= weights[i - 1]
    selected.reverse()
    return dp[n][capacity], dp, selected

# 定义 knapsack_optimized 函数
def knapsack_optimized(weights, values, capacity):
    if not weights or capacity <= 0:
        return 0
    n = len(weights)
    dp = [0] * (capacity + 1)
    for i in range(n):
        for w in range(capacity, weights[i] - 1, -1):
            dp[w] = max(dp[w], dp[w - weights[i]] + values[i])
    return dp[capacity]

# 定义 knapsack_unbounded 函数
def knapsack_unbounded(weights, values, capacity):
    if not weights or capacity <= 0:
        return 0
    dp = [0] * (capacity + 1)
    for w in range(1, capacity + 1):
        for i in range(len(weights)):
            if weights[i] <= w:
                dp[w] = max(dp[w], dp[w - weights[i]] + values[i])
    return dp[capacity]

# 定义 knapsack_fractional 函数
def knapsack_fractional(items, capacity):
    items = sorted(items, key=lambda x: x[1] / x[0], reverse=True)
    total_value = 0.0
    remaining = capacity
    for weight, value in items:
        if remaining >= weight:
            total_value += value
            remaining -= weight
        else:
            total_value += value * (remaining / weight)
            break
    return total_value
