from visual_tracer import DpTableTracer
tracer = DpTableTracer()

# two_d_dp 算法实现 — domain: dynamic_programming
def min_path_sum(grid):
    if not grid or not grid[0]:
        tracer.finish(line=3)
        return 0, [], []
    m, n = len(grid), len(grid[0])

    headers = [str(j) for j in range(n)]
    rows = [[0] * n for _ in range(m)]
    tracer.init_table(headers, rows, m, n, fill_value=0, line=6)

    dp = [[0] * n for _ in range(m)]
    dp[0][0] = grid[0][0]
    tracer.set_value(0, 0, dp[0][0], line=7)

    for i in range(1, m):
        tracer.move_pointer({"i": i}, line=8)
        tracer.highlight(i - 1, 0, tone="active", line=9)
        dp[i][0] = dp[i - 1][0] + grid[i][0]
        tracer.set_value(i, 0, dp[i][0], line=9)
        tracer.clear_highlights(line=9)

    for j in range(1, n):
        tracer.move_pointer({"j": j}, line=10)
        tracer.highlight(0, j - 1, tone="active", line=11)
        dp[0][j] = dp[0][j - 1] + grid[0][j]
        tracer.set_value(0, j, dp[0][j], line=11)
        tracer.clear_highlights(line=11)

    for i in range(1, m):
        tracer.move_pointer({"i": i}, line=12)
        for j in range(1, n):
            tracer.move_pointer({"j": j}, line=13)
            tracer.highlight(i - 1, j, tone="active", line=14)
            tracer.highlight(i, j - 1, tone="active", line=14)
            dp[i][j] = min(dp[i - 1][j], dp[i][j - 1]) + grid[i][j]
            tracer.set_value(i, j, dp[i][j], line=14)
            tracer.clear_highlights(line=14)

    # 回溯路径
    path = []
    i, j = m - 1, n - 1
    tracer.highlight(i, j, tone="success", line=17)
    while i > 0 or j > 0:
        path.append((i, j))
        tracer.highlight(i, j, tone="success", line=18)
        if i == 0:
            j -= 1
        elif j == 0:
            i -= 1
        elif dp[i - 1][j] <= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    path.append((0, 0))
    tracer.highlight(0, 0, tone="success", line=28)
    path.reverse()
    tracer.clear_highlights(line=28)
    tracer.finish(line=29)
    return dp[m - 1][n - 1], dp, path

# 定义 max_path_sum 函数
def max_path_sum(grid):
    if not grid or not grid[0]:
        tracer.finish(line=33)
        return 0
    m, n = len(grid), len(grid[0])

    headers = [str(j) for j in range(n)]
    tracer.init_table(headers, [[0] * n for _ in range(m)], m, n, fill_value=0, line=36)

    dp = [[0] * n for _ in range(m)]
    dp[0][0] = grid[0][0]
    tracer.set_value(0, 0, dp[0][0], line=37)

    for i in range(1, m):
        dp[i][0] = dp[i - 1][0] + grid[i][0]
        tracer.set_value(i, 0, dp[i][0], line=39)

    for j in range(1, n):
        dp[0][j] = dp[0][j - 1] + grid[0][j]
        tracer.set_value(0, j, dp[0][j], line=41)

    for i in range(1, m):
        for j in range(1, n):
            tracer.highlight(i - 1, j, tone="active", line=44)
            tracer.highlight(i, j - 1, tone="active", line=44)
            dp[i][j] = max(dp[i - 1][j], dp[i][j - 1]) + grid[i][j]
            tracer.set_value(i, j, dp[i][j], line=44)
            tracer.clear_highlights(line=44)

    tracer.finish(line=45)
    return dp[m - 1][n - 1]

# 定义 unique_paths 函数
def unique_paths(m, n):
    headers = [str(j) for j in range(n)]
    tracer.init_table(headers, [[0] * n for _ in range(m)], m, n, fill_value=0, line=49)

    dp = [[0] * n for _ in range(m)]
    for i in range(m):
        tracer.move_pointer({"i": i}, line=50)
        dp[i][0] = 1
        tracer.set_value(i, 0, 1, line=51)
    for j in range(n):
        tracer.move_pointer({"j": j}, line=52)
        dp[0][j] = 1
        tracer.set_value(0, j, 1, line=53)

    for i in range(1, m):
        for j in range(1, n):
            tracer.highlight(i - 1, j, tone="active", line=56)
            tracer.highlight(i, j - 1, tone="active", line=56)
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
            tracer.set_value(i, j, dp[i][j], line=56)
            tracer.clear_highlights(line=56)

    tracer.finish(line=57)
    return dp[m - 1][n - 1]

# 定义 unique_paths_with_obstacles 函数
def unique_paths_with_obstacles(obstacle_grid):
    m, n = len(obstacle_grid), len(obstacle_grid[0])
    headers = [str(j) for j in range(n)]
    tracer.init_table(headers, [[0] * n for _ in range(m)], m, n, fill_value=0, line=62)

    dp = [[0] * n for _ in range(m)]
    dp[0][0] = 1 if obstacle_grid[0][0] == 0 else 0
    tracer.set_value(0, 0, dp[0][0], line=63)

    for i in range(1, m):
        dp[i][0] = dp[i - 1][0] if obstacle_grid[i][0] == 0 else 0
        tracer.set_value(i, 0, dp[i][0], line=65)
        if obstacle_grid[i][0] == 1:
            tracer.highlight(i, 0, tone="danger", line=65)

    for j in range(1, n):
        dp[0][j] = dp[0][j - 1] if obstacle_grid[0][j] == 0 else 0
        tracer.set_value(0, j, dp[0][j], line=67)
        if obstacle_grid[0][j] == 1:
            tracer.highlight(0, j, tone="danger", line=67)

    tracer.clear_highlights(line=67)

    for i in range(1, m):
        for j in range(1, n):
            if obstacle_grid[i][j] == 0:
                tracer.highlight(i - 1, j, tone="active", line=71)
                tracer.highlight(i, j - 1, tone="active", line=71)
                dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
                tracer.set_value(i, j, dp[i][j], line=71)
            else:
                dp[i][j] = 0
                tracer.set_value(i, j, 0, line=73)
                tracer.highlight(i, j, tone="danger", line=73)
            tracer.clear_highlights(line=73)

    tracer.finish(line=74)
    return dp[m - 1][n - 1]