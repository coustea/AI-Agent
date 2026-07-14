def knapsack(weights, values, capacity):
    """0/1 背包：每件物品只有选与不选两种状态转移。"""
    dp = [[0] * (capacity + 1) for _ in range(len(weights) + 1)]
    for index, weight in enumerate(weights, start=1):
        value = values[index - 1]
        for current_capacity in range(capacity + 1):
            dp[index][current_capacity] = dp[index - 1][current_capacity]
            if current_capacity >= weight:
                dp[index][current_capacity] = max(
                    dp[index][current_capacity],
                    dp[index - 1][current_capacity - weight] + value,
                )
    return dp
