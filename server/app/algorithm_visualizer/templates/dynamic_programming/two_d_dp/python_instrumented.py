from visual_tracer import DpTableTracer

tracer = DpTableTracer()

# 定义 min_path_sum 函数
def min_path_sum(grid):
    if not grid or not grid[0]:
        return 0, [], []
    m, n = len(grid), len(grid[0])
    row_headers = [f"r{i}" for i in range(m)]
    col_headers = ["dp"] + [f"c{j}" for j in range(n)]
    headers = col_headers
    tracer.init_table(headers, rows=m, cols=n, fill_value=0, line=4)
    dp = [[0] * n for _ in range(m)]
    dp[0][0] = grid[0][0]
    tracer.set_value(0, 0, dp[0][0], line=9)
# 循环遍历处理
    for i in range(1, m):
        tracer.highlight(i - 1, 0, tone="dep", line=11)
        dp[i][0] = dp[i - 1][0] + grid[i][0]
        tracer.highlight(i, 0, tone="active", line=12)
        tracer.set_value(i, 0, dp[i][0], line=12)
        tracer.clear_highlights(line=13)
# 循环遍历处理
    for j in range(1, n):
        tracer.highlight(0, j - 1, tone="dep", line=15)
        dp[0][j] = dp[0][j - 1] + grid[0][j]
        tracer.highlight(0, j, tone="active", line=16)
        tracer.set_value(0, j, dp[0][j], line=16)
        tracer.clear_highlights(line=17)
# 循环遍历处理
    for i in range(1, m):
# 循环遍历处理
        for j in range(1, n):
            tracer.highlight(i - 1, j, tone="dep", line=19)
            tracer.highlight(i, j - 1, tone="dep", line=19)
            dp[i][j] = min(dp[i - 1][j], dp[i][j - 1]) + grid[i][j]
            tracer.highlight(i, j, tone="active", line=21)
            tracer.set_value(i, j, dp[i][j], line=21)
            tracer.clear_highlights(line=22)
    path = []
    i, j = m - 1, n - 1
# 循环条件判断
    while i > 0 or j > 0:
        path.append((i, j))
        if i == 0:
            j -= 1
        elif j == 0:
            i -= 1
        elif dp[i - 1][j] <= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    path.append((0, 0))
    path.reverse()
    tracer.finish(line=35)
    return dp[m - 1][n - 1], dp, path

# 定义 max_path_sum 函数
def max_path_sum(grid):
    if not grid or not grid[0]:
        return 0
    m, n = len(grid), len(grid[0])
    dp = [[0] * n for _ in range(m)]
    dp[0][0] = grid[0][0]
# 循环遍历处理
    for i in range(1, m):
        dp[i][0] = dp[i - 1][0] + grid[i][0]
# 循环遍历处理
    for j in range(1, n):
        dp[0][j] = dp[0][j - 1] + grid[0][j]
# 循环遍历处理
    for i in range(1, m):
# 循环遍历处理
        for j in range(1, n):
            dp[i][j] = max(dp[i - 1][j], dp[i][j - 1]) + grid[i][j]
    return dp[m - 1][n - 1]

# 定义 unique_paths 函数
def unique_paths(m, n):
    dp = [[0] * n for _ in range(m)]
# 循环遍历处理
    for i in range(m):
        dp[i][0] = 1
# 循环遍历处理
    for j in range(n):
        dp[0][j] = 1
# 循环遍历处理
    for i in range(1, m):
# 循环遍历处理
        for j in range(1, n):
            dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
    return dp[m - 1][n - 1]

# 定义 unique_paths_with_obstacles 函数
def unique_paths_with_obstacles(obstacle_grid):
    m, n = len(obstacle_grid), len(obstacle_grid[0])
    dp = [[0] * n for _ in range(m)]
    dp[0][0] = 1 if obstacle_grid[0][0] == 0 else 0
# 循环遍历处理
    for i in range(1, m):
        dp[i][0] = dp[i - 1][0] if obstacle_grid[i][0] == 0 else 0
# 循环遍历处理
    for j in range(1, n):
        dp[0][j] = dp[0][j - 1] if obstacle_grid[0][j] == 0 else 0
# 循环遍历处理
    for i in range(1, m):
# 循环遍历处理
        for j in range(1, n):
            if obstacle_grid[i][j] == 0:
                dp[i][j] = dp[i - 1][j] + dp[i][j - 1]
            else:
                dp[i][j] = 0
    return dp[m - 1][n - 1]

grid = [
    [1, 3, 5, 9, 2, 1],
    [2, 1, 3, 4, 8, 3],
    [5, 2, 6, 7, 1, 4],
    [3, 4, 1, 2, 3, 5],
    [2, 1, 4, 1, 2, 1]
]
result, dp_table, path = min_path_sum(grid)
max_path_sum(grid)
unique_paths(3, 7)

obstacle_grid = [
    [0, 0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 1, 0, 0, 1],
    [0, 0, 0, 0, 0, 0]
]
unique_paths_with_obstacles(obstacle_grid)
tracer.dump()
