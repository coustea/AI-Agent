from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def subsets(nums):
    tracer.init_array(nums, line=1)
    if not nums:
        tracer.finish(line=3)
        return [[]]
    res = []

# 定义 backtrack 函数
    def backtrack(start, path):
        tracer.move_pointer({"start": start}, line=7)
        for i in range(len(path)):
            tracer.mark_sorted(i, line=8)
        res.append(path[:])
        for i in range(start, len(nums)):
            tracer.move_pointer({"i": i}, line=9)
            tracer.highlight(i, tone="active", line=10)
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
            tracer.clear_highlights(line=12)

    backtrack(0, [])
    tracer.finish(line=14)
    return res

# 定义 subsets_with_dup 函数
def subsets_with_dup(nums):
    tracer.init_array(sorted(nums), line=17)
    nums.sort()
    res = []

# 定义 backtrack 函数
    def backtrack(start, path):
        tracer.move_pointer({"start": start}, line=23)
        for i in range(len(path)):
            tracer.mark_sorted(i, line=24)
        res.append(path[:])
        for i in range(start, len(nums)):
            tracer.move_pointer({"i": i}, line=25)
            if i > start and nums[i] == nums[i - 1]:
                tracer.highlight(i, tone="danger", line=26)
                tracer.clear_highlights(line=26)
                continue
            tracer.highlight(i, tone="active", line=28)
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
            tracer.clear_highlights(line=30)

    backtrack(0, [])
    tracer.finish(line=32)
    return res

# 定义 subsets_bitmask 函数
def subsets_bitmask(nums):
    tracer.init_array(nums, line=35)
    n = len(nums)
    res = []
    for mask in range(1 << n):
        tracer.move_pointer({"mask": mask}, line=39)
        subset = []
        for i in range(n):
            if mask & (1 << i):
                tracer.highlight(i, tone="active", line=42)
                subset.append(nums[i])
        tracer.clear_highlights(line=43)
        res.append(subset)
    tracer.finish(line=44)
    return res

# 定义 subset_sum 函数
def subset_sum(nums, target):
    tracer.init_array(nums, line=47)
    res = []

# 定义 backtrack 函数
    def backtrack(start, remain, path):
        tracer.move_pointer({"remain": remain}, line=52)
        if remain == 0:
            for i in range(len(path)):
                tracer.mark_sorted(i, line=54)
            res.append(path[:])
            return
        if remain < 0:
            tracer.highlight(0, tone="danger", line=56)
            tracer.clear_highlights(line=56)
            return
        for i in range(start, len(nums)):
            tracer.move_pointer({"i": i}, line=58)
            tracer.highlight(i, tone="active", line=59)
            path.append(nums[i])
            backtrack(i + 1, remain - nums[i], path)
            path.pop()
            tracer.clear_highlights(line=61)

    backtrack(0, target, [])
    tracer.finish(line=63)
    return res