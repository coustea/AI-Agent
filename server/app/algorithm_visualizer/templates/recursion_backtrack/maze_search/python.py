# maze_search 算法实现 — domain: recursion_backtrack
def solve_maze(maze):
    if not maze or not maze[0]:
        return []
    h = len(maze)
    w = len(maze[0])
    if maze[0][0] == 1 or maze[h - 1][w - 1] == 1:
        return []
    path = []
    visited = [[False] * w for _ in range(h)]

# 定义 dfs 函数
    def dfs(r, c):
        if r < 0 or r >= h or c < 0 or c >= w:
            return False
        if maze[r][c] == 1 or visited[r][c]:
            return False
        path.append((r, c))
        visited[r][c] = True
        if r == h - 1 and c == w - 1:
            return True
        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            if dfs(r + dr, c + dc):
                return True
        path.pop()
        return False

    if dfs(0, 0):
        return path
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
    while queue:
        r, c, dist = queue.popleft()
        if r == h - 1 and c == w - 1:
            return dist
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
path = solve_maze(maze)
assert len(path) > 0

all_paths = solve_maze_all_paths(maze)
assert len(all_paths) >= 1

shortest = shortest_path_length(maze)
assert shortest > 0
assert shortest <= len(path) - 1
