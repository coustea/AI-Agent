def combination_sum(candidates, target):
    res = []
    path = []
    def backtrack(start, remain):
        if remain == 0:
            res.append(path[:])
            return
        if remain < 0:
            return
        for i in range(start, len(candidates)):
            path.append(candidates[i])
            backtrack(i, remain - candidates[i])
            path.pop()
    backtrack(0, target)
    return res

combination_sum([2, 3, 6, 7], 7)
