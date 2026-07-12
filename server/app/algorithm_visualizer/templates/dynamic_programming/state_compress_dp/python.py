# state_compress_dp 算法实现 — domain: dynamic_programming
def tsp(dist):
    if not dist or not dist[0]:
        return 0
    n = len(dist)
    if n == 1:
        return 0
    if n == 2:
        return dist[0][1] + dist[1][0]
    memo = {}

# 定义 solve 函数
    def solve(mask, pos):
        if mask == (1 << n) - 1:
            return dist[pos][0]
        state = (mask, pos)
        if state in memo:
            return memo[state]
        ans = float('inf')
        for nxt in range(n):
            if not (mask & (1 << nxt)):
                sub = solve(mask | (1 << nxt), nxt)
                val = dist[pos][nxt] + sub
                if val < ans:
                    ans = val
        memo[state] = ans
        return ans

    result = solve(1, 0)
    path = [0]
    mask = 1
    pos = 0
    while mask != (1 << n) - 1:
        best_nxt = -1
        best_val = float('inf')
        for nxt in range(n):
            if not (mask & (1 << nxt)):
                val = dist[pos][nxt] + memo.get((mask | (1 << nxt), nxt), float('inf'))
                if val < best_val:
                    best_val = val
                    best_nxt = nxt
        if best_nxt == -1:
            break
        path.append(best_nxt)
        mask |= (1 << best_nxt)
        pos = best_nxt
    path.append(0)
    return result, path

# 定义 tsp_with_pruning 函数
def tsp_with_pruning(dist):
    n = len(dist)
    if n <= 1:
        return 0, [0]
    best = float('inf')
    best_path = []
    visited = [False] * n
    visited[0] = True

# 定义 dfs 函数
    def dfs(pos, count, cost, path):
        nonlocal best, best_path
        if cost >= best:
            return
        if count == n:
            total = cost + dist[pos][0]
            if total < best:
                best = total
                best_path = path[:] + [0]
            return
        for nxt in range(n):
            if not visited[nxt]:
                visited[nxt] = True
                path.append(nxt)
                dfs(nxt, count + 1, cost + dist[pos][nxt], path)
                path.pop()
                visited[nxt] = False

    dfs(0, 1, 0, [0])
    return best, best_path

# 定义 tsp_nearest_neighbor 函数
def tsp_nearest_neighbor(dist):
    n = len(dist)
    if n <= 1:
        return 0, [0]
    visited = [False] * n
    path = [0]
    visited[0] = True
    total = 0
    pos = 0
    for _ in range(n - 1):
        best_nxt = -1
        best_dist = float('inf')
        for nxt in range(n):
            if not visited[nxt] and dist[pos][nxt] < best_dist:
                best_dist = dist[pos][nxt]
                best_nxt = nxt
        visited[best_nxt] = True
        path.append(best_nxt)
        total += best_dist
        pos = best_nxt
    total += dist[pos][0]
    path.append(0)
    return total, path
