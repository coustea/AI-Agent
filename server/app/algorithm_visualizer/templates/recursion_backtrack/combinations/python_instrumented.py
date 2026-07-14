from visual_tracer import ArrayTracer
tracer = ArrayTracer()

# combinations 算法实现 — domain: recursion_backtrack
def combination_sum(candidates, target):
    tracer.init_array(sorted(candidates), line=1)
    if not candidates or target <= 0:
        tracer.finish(line=3)
        return []
    candidates = sorted(candidates)
    res = []

# 定义 backtrack 函数
    def backtrack(start, remain, path):
        tracer.move_pointer({"remain": remain}, line=9)
        if remain == 0:
            for i in range(len(path)):
                tracer.mark_sorted(i, line=11)
            res.append(path[:])
            return
        if remain < 0:
            tracer.highlight(0, tone="danger", line=14)
            tracer.clear_highlights(line=14)
            return
        for i in range(start, len(candidates)):
            tracer.move_pointer({"i": i}, line=15)
            if candidates[i] > remain:
                tracer.highlight(i, tone="danger", line=17)
                tracer.clear_highlights(line=17)
                break
            tracer.highlight(i, tone="active", line=18)
            path.append(candidates[i])
            backtrack(i, remain - candidates[i], path)
            path.pop()
            tracer.clear_highlights(line=20)

    backtrack(0, target, [])
    tracer.finish(line=22)
    return res

# 定义 combination_sum2 函数
def combination_sum2(candidates, target):
    tracer.init_array(sorted(candidates), line=25)
    if not candidates or target <= 0:
        tracer.finish(line=27)
        return []
    candidates.sort()
    res = []

# 定义 backtrack 函数
    def backtrack(start, remain, path):
        tracer.move_pointer({"remain": remain}, line=33)
        if remain == 0:
            for i in range(len(path)):
                tracer.mark_sorted(i, line=35)
            res.append(path[:])
            return
        if remain < 0:
            return
        for i in range(start, len(candidates)):
            tracer.move_pointer({"i": i}, line=39)
            if i > start and candidates[i] == candidates[i - 1]:
                tracer.highlight(i, tone="danger", line=40)
                tracer.clear_highlights(line=40)
                continue
            if candidates[i] > remain:
                tracer.highlight(i, tone="danger", line=43)
                tracer.clear_highlights(line=43)
                break
            tracer.highlight(i, tone="active", line=44)
            path.append(candidates[i])
            backtrack(i + 1, remain - candidates[i], path)
            path.pop()
            tracer.clear_highlights(line=46)

    backtrack(0, target, [])
    tracer.finish(line=48)
    return res

# 定义 combination_sum_k 函数
def combination_sum_k(k, n):
    res = []
    tracer.init_array(list(range(1, 10)), line=52)

# 定义 backtrack 函数
    def backtrack(start, remain, path, depth):
        tracer.move_pointer({"depth": depth, "remain": remain}, line=56)
        if depth == k and remain == 0:
            for i in range(len(path)):
                tracer.mark_sorted(i, line=58)
            res.append(path[:])
            return
        if depth >= k or remain <= 0:
            tracer.highlight(0, tone="danger", line=60)
            tracer.clear_highlights(line=60)
            return
        for i in range(start, 10):
            tracer.move_pointer({"i": i}, line=62)
            tracer.highlight(i - 1, tone="active", line=63)
            path.append(i)
            backtrack(i + 1, remain - i, path, depth + 1)
            path.pop()
            tracer.clear_highlights(line=65)

    backtrack(1, n, [], 0)
    tracer.finish(line=67)
    return res