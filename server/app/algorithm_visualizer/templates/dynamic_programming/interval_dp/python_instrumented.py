from visual_tracer import DpTableTracer

tracer = DpTableTracer()

def longest_palindrome_subseq(s):
    if not s:
        return 0, [], ""
    n = len(s)
    if n == 1:
        return 1, [[1]], s
    headers = ["dp"] + [f"{s[j]}(j={j})" for j in range(n)]
    tracer.init_table(headers, rows=n, cols=n, fill_value=0, line=4)
    dp = [[0] * n for _ in range(n)]
    for i in range(n):
        dp[i][i] = 1
        tracer.highlight(i, i, tone="active", line=9)
        tracer.set_value(i, i, 1, line=9)
        tracer.clear_highlights(line=10)
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            if s[i] == s[j]:
                if length == 2:
                    dp[i][j] = 2
                else:
                    tracer.highlight(i + 1, j - 1, tone="dep", line=17)
                    dp[i][j] = dp[i + 1][j - 1] + 2
                tracer.highlight(i, j, tone="active", line=19)
                tracer.set_value(i, j, dp[i][j], line=19)
            else:
                tracer.highlight(i + 1, j, tone="dep", line=21)
                tracer.highlight(i, j - 1, tone="dep", line=21)
                dp[i][j] = max(dp[i + 1][j], dp[i][j - 1])
                tracer.highlight(i, j, tone="active", line=23)
                tracer.set_value(i, j, dp[i][j], line=23)
            tracer.clear_highlights(line=25)
    def reconstruct(i, j):
        if i > j:
            return ""
        if i == j:
            return s[i]
        if s[i] == s[j]:
            return s[i] + reconstruct(i + 1, j - 1) + s[j]
        elif dp[i + 1][j] > dp[i][j - 1]:
            return reconstruct(i + 1, j)
        else:
            return reconstruct(i, j - 1)
    lps = reconstruct(0, n - 1)
    tracer.finish(line=38)
    return dp[0][n - 1], dp, lps

def matrix_chain_order(dims):
    n = len(dims) - 1
    if n <= 0:
        return 0, []
    dp = [[0] * n for _ in range(n)]
    split = [[0] * n for _ in range(n)]
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            dp[i][j] = float('inf')
            for k in range(i, j):
                cost = dp[i][k] + dp[k + 1][j] + dims[i] * dims[k + 1] * dims[j + 1]
                if cost < dp[i][j]:
                    dp[i][j] = cost
                    split[i][j] = k
    return dp[0][n - 1], dp

def longest_palindrome_substring(s):
    if not s:
        return 0, ""
    n = len(s)
    dp = [[False] * n for _ in range(n)]
    max_len = 1
    start = 0
    for i in range(n):
        dp[i][i] = True
    for length in range(2, n + 1):
        for i in range(n - length + 1):
            j = i + length - 1
            if s[i] == s[j]:
                if length == 2 or dp[i + 1][j - 1]:
                    dp[i][j] = True
                    if length > max_len:
                        max_len = length
                        start = i
    return max_len, s[start:start + max_len]

s1 = "bbbababb"
result1, dp1, lps1 = longest_palindrome_subseq(s1)

dims = [10, 30, 5, 60, 15, 20, 25]
min_cost, dp2 = matrix_chain_order(dims)

s2 = "babad"
max_len, substr = longest_palindrome_substring(s2)
tracer.dump()
