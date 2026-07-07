def solve_maze(maze):
    h = len(maze)
    w = len(maze[0])
    path = []
    visited = [[False] * w for _ in range(h)]
    
    def dfs(r, c):
        if r < 0 or r >= h or c < 0 or c >= w or maze[r][c] == 1 or visited[r][c]:
            return False
        path.append((r, c))
        visited[r][c] = True
        if r == h - 1 and c == w - 1:
            return True
        # Right, Down, Left, Up
        for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
            if dfs(r + dr, c + dc):
                return True
        path.pop()
        return False
        
    maze = [
        [0, 1, 0, 0],
        [0, 0, 0, 1],
        [1, 0, 1, 0],
        [0, 0, 0, 0]
    ]
    dfs(0, 0)
    return path
