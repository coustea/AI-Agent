from visual_tracer import DpTableTracer

tracer = DpTableTracer()

def climb_stairs(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 1
    if n == 1:
        return 1
    headers = ["step"] + [str(i) for i in range(n + 1)]
    tracer.init_table(headers, rows=1, cols=n + 1, fill_value=0, line=4)
    dp = [0] * (n + 1)
    dp[0] = 1
    tracer.set_value(0, 0, 1, line=9)
    dp[1] = 1
    tracer.set_value(0, 1, 1, line=11)
    for i in range(2, n + 1):
        tracer.highlight(0, i - 1, tone="dep", line=13)
        tracer.highlight(0, i - 2, tone="dep", line=13)
        dp[i] = dp[i - 1] + dp[i - 2]
        tracer.highlight(0, i, tone="active", line=15)
        tracer.set_value(0, i, dp[i], line=15)
        tracer.clear_highlights(line=16)
    tracer.finish(line=18)
    return dp[n]

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

def climb_stairs_min_cost(cost):
    n = len(cost)
    dp = [0] * (n + 1)
    for i in range(2, n + 1):
        dp[i] = min(dp[i - 1] + cost[i - 1], dp[i - 2] + cost[i - 2])
    return dp[n]

climb_stairs(10)

climb_stairs_k(10, 2)
climb_stairs_k(10, 3)

cost = [10, 15, 20, 5, 30, 10, 25, 15, 20, 8]
climb_stairs_cost(cost)
climb_stairs_min_cost(cost)
tracer.dump()
