def tsp(dist):
    n = len(dist)
    memo = {}
    
    def solve(mask, pos):
        if mask == (1 << n) - 1:
            return dist[pos][0]
        state = (mask, pos)
        if state in memo:
            return memo[state]
            
        ans = float('inf')
        for nxt in range(n):
            if not (mask & (1 << nxt)):
                ans = min(ans, dist[pos][nxt] + solve(mask | (1 << nxt), nxt))
        memo[state] = ans
        return ans
        
    dist = [
        [0, 10, 15, 20],
        [10, 0, 35, 25],
        [15, 35, 0, 30],
        [20, 25, 30, 0]
    ]
    return solve(1, 0)
