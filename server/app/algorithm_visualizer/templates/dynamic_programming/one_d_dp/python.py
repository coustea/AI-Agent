# one_d_dp 算法实现 — domain: dynamic_programming
def climb_stairs(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 1
    if n == 1:
        return 1
    dp = [0] * (n + 1)
    dp[0] = 1
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]

# 定义 climb_stairs_k 函数
def climb_stairs_k(n, k):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 1
    dp = [0] * (n + 1)
    dp[0] = 1
    for i in range(1, n + 1):
        for j in range(1, k + 1):
            if i - j >= 0:
                dp[i] += dp[i - j]
    return dp[n]

# 定义 climb_stairs_cost 函数
def climb_stairs_cost(cost):
    n = len(cost)
    if n == 0:
        return 0
    if n == 1:
        return cost[0]
    dp = [0] * n
    dp[0] = cost[0]
    dp[1] = cost[1]
    for i in range(2, n):
        dp[i] = cost[i] + min(dp[i - 1], dp[i - 2])
    return min(dp[n - 1], dp[n - 2])

# 定义 climb_stairs_min_cost 函数
def climb_stairs_min_cost(cost):
    n = len(cost)
    dp = [0] * (n + 1)
    for i in range(2, n + 1):
        dp[i] = min(dp[i - 1] + cost[i - 1], dp[i - 2] + cost[i - 2])
    return dp[n]

assert climb_stairs(10) == 89
assert climb_stairs(0) == 1
assert climb_stairs(1) == 1
assert climb_stairs(5) == 8

assert climb_stairs_k(10, 2) == 89
assert climb_stairs_k(10, 3) == 274

cost = [10, 15, 20, 5, 30, 10, 25, 15, 20, 8]
r1 = climb_stairs_cost(cost)
r2 = climb_stairs_min_cost(cost)
assert r1 >= 0
assert r2 >= 0
