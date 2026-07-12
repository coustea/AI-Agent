# combinations 算法实现 — domain: recursion_backtrack
def combination_sum(candidates, target):
    if not candidates or target <= 0:
        return []
    candidates = sorted(candidates)
    res = []

# 定义 backtrack 函数
    def backtrack(start, remain, path):
        if remain == 0:
            res.append(path[:])
            return
        if remain < 0:
            return
        for i in range(start, len(candidates)):
            if candidates[i] > remain:
                break
            path.append(candidates[i])
            backtrack(i, remain - candidates[i], path)
            path.pop()

    backtrack(0, target, [])
    return res

# 定义 combination_sum2 函数
def combination_sum2(candidates, target):
    if not candidates or target <= 0:
        return []
    candidates.sort()
    res = []

# 定义 backtrack 函数
    def backtrack(start, remain, path):
        if remain == 0:
            res.append(path[:])
            return
        if remain < 0:
            return
        for i in range(start, len(candidates)):
            if i > start and candidates[i] == candidates[i - 1]:
                continue
            if candidates[i] > remain:
                break
            path.append(candidates[i])
            backtrack(i + 1, remain - candidates[i], path)
            path.pop()

    backtrack(0, target, [])
    return res

# 定义 combination_sum_k 函数
def combination_sum_k(k, n):
    res = []

# 定义 backtrack 函数
    def backtrack(start, remain, path, depth):
        if depth == k and remain == 0:
            res.append(path[:])
            return
        if depth >= k or remain <= 0:
            return
        for i in range(start, 10):
            path.append(i)
            backtrack(i + 1, remain - i, path, depth + 1)
            path.pop()

    backtrack(1, n, [], 0)
    return res
