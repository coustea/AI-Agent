from visual_tracer import DpTableTracer

tracer = DpTableTracer()

# 定义 solve_maze 函数
def solve_maze(maze):
    if not maze or not maze[0]:
        return []
    h = len(maze)
    w = len(maze[0])
    if maze[0][0] == 1 or maze[h - 1][w - 1] == 1:
        return []
    path = []
    visited = [[False] * w for _ in range(h)]
    headers = [str(c) for c in range(w)]
    tracer.init_table(headers, rows=h, cols=w, fill_value="", line=4)
# 循环遍历处理
    for r in range(h):
# 循环遍历处理
        for c in range(w):
            if maze[r][c] == 1:
                tracer.set_value(r, c, "X", line=8)
# 定义 dfs 函数
    def dfs(r, c):
        if r < 0 or r >= h or c < 0 or c >= w:
            return False
        if maze[r][c] == 1 or visited[r][c]:
            tracer.highlight(r, c, tone="conflict", line=14)
            tracer.clear_highlights(line=15)
            return False
        path.append((r, c))
        visited[r][c] = True
        tracer.set_value(r, c, "O", line=19)
        tracer.highlight(r, c, tone="active", line=20)
        if r == h - 1 and c == w - 1:
            tracer.set_value(r, c, "E", line=23)
            tracer.finish(line=24)
            return True
# 循环遍历处理
        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            if dfs(r + dr, c + dc):
                return True
        path.pop()
        tracer.set_value(r, c, "-", line=32)
        tracer.clear_highlights(line=33)
        return False
    if dfs(0, 0):
        return path
    tracer.finish(line=37)
    return []

# 定义 solve_maze_all_paths 函数
def solve_maze_all_paths(maze):
    if not maze or not maze[0]:
        return []
    h = len(maze)
    w = len(maze[0])
    if maze[0][0] == 1 or maze[h - 1][w - 1] == 1:
        return []
    all_paths = []
    visited = [[False] * w for _ in range(h)]
# 定义 dfs 函数
    def dfs(r, c, path):
        if r < 0 or r >= h or c < 0 or c >= w:
            return
        if maze[r][c] == 1 or visited[r][c]:
            return
        path.append((r, c))
        visited[r][c] = True
        if r == h - 1 and c == w - 1:
            all_paths.append(path[:])
        else:
# 循环遍历处理
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                dfs(r + dr, c + dc, path)
        path.pop()
        visited[r][c] = False
    dfs(0, 0, [])
    return all_paths

# 定义 shortest_path_length 函数
def shortest_path_length(maze):
    if not maze or not maze[0]:
        return -1
    h = len(maze)
    w = len(maze[0])
    if maze[0][0] == 1 or maze[h - 1][w - 1] == 1:
        return -1
    from collections import deque
    queue = deque([(0, 0, 0)])
    visited = [[False] * w for _ in range(h)]
    visited[0][0] = True
# 循环条件判断
    while queue:
        r, c, dist = queue.popleft()
        if r == h - 1 and c == w - 1:
            return dist
# 循环遍历处理
        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and maze[nr][nc] == 0 and not visited[nr][nc]:
                visited[nr][nc] = True
                queue.append((nr, nc, dist + 1))
    return -1

maze = [
    [0, 1, 0, 0, 0, 1, 0],
    [0, 0, 0, 1, 0, 0, 0],
    [1, 0, 1, 0, 0, 1, 0],
    [0, 0, 0, 0, 1, 0, 0],
    [0, 1, 1, 0, 0, 0, 1],
    [0, 0, 0, 1, 0, 0, 0],
    [0, 1, 0, 0, 1, 0, 0]
]
solve_maze(maze)
solve_maze_all_paths(maze)
shortest_path_length(maze)
tracer.dump()
