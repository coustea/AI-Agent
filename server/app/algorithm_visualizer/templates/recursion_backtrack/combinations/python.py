def combination_sum(candidates, target):
    if not candidates or target <= 0:
        return []
    candidates = sorted(candidates)
    res = []

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

def combination_sum2(candidates, target):
    if not candidates or target <= 0:
        return []
    candidates.sort()
    res = []

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

def combination_sum_k(k, n):
    res = []

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

r1 = combination_sum([2, 3, 5, 7], 8)
assert len(r1) >= 1
for c in r1:
    assert sum(c) == 8

r2 = combination_sum2([10, 1, 2, 7, 6, 1, 5], 8)
for c in r2:
    assert sum(c) == 8

r3 = combination_sum_k(3, 7)
for c in r3:
    assert len(c) == 3 and sum(c) == 7
