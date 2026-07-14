from visual_tracer import ArrayTracer
tracer = ArrayTracer()

# permutations 算法实现 — domain: recursion_backtrack
def permute(nums):
    tracer.init_array(nums, line=1)
    if not nums:
        tracer.finish(line=3)
        return []
    if len(nums) == 1:
        tracer.mark_sorted(0, line=5)
        tracer.finish(line=5)
        return [nums[:]]
    res = []

# 定义 backtrack 函数
    def backtrack(start):
        tracer.move_pointer({"start": start}, line=10)
        if start == len(nums):
            for i in range(len(nums)):
                tracer.mark_sorted(i, line=12)
            res.append(nums[:])
            return
        for i in range(start, len(nums)):
            tracer.move_pointer({"i": i}, line=14)
            tracer.swap(start, i, line=15)
            nums[start], nums[i] = nums[i], nums[start]
            backtrack(start + 1)
            tracer.swap(start, i, line=17)
            nums[start], nums[i] = nums[i], nums[start]

    backtrack(0)
    tracer.finish(line=19)
    return res

# 定义 permute_with_dup 函数
def permute_with_dup(nums):
    tracer.init_array(sorted(nums), line=22)
    nums.sort()
    res = []

# 定义 backtrack 函数
    def backtrack(path, used):
        tracer.move_pointer({"depth": len(path)}, line=28)
        if len(path) == len(nums):
            for i in range(len(nums)):
                tracer.mark_sorted(i, line=30)
            res.append(path[:])
            return
        for i in range(len(nums)):
            tracer.move_pointer({"i": i}, line=32)
            if used[i]:
                tracer.highlight(i, tone="danger", line=34)
                tracer.clear_highlights(line=34)
                continue
            if i > 0 and nums[i] == nums[i - 1] and not used[i - 1]:
                tracer.highlight(i, tone="danger", line=35)
                tracer.clear_highlights(line=35)
                continue
            tracer.highlight(i, tone="active", line=37)
            used[i] = True
            path.append(nums[i])
            tracer.assign(i, len(path), line=38)
            backtrack(path, used)
            path.pop()
            used[i] = False
            tracer.clear_highlights(line=41)

    backtrack([], [False] * len(nums))
    tracer.finish(line=43)
    return res

# 定义 permute_k 函数
def permute_k(nums, k):
    tracer.init_array(nums, line=46)
    if k <= 0 or k > len(nums):
        tracer.finish(line=48)
        return []
    res = []

# 定义 backtrack 函数
    def backtrack(start, depth, path):
        tracer.move_pointer({"depth": depth}, line=53)
        if depth == k:
            for i in range(len(path)):
                tracer.mark_sorted(i, line=55)
            res.append(path[:])
            return
        for i in range(start, len(nums)):
            tracer.move_pointer({"i": i}, line=57)
            path.append(nums[i])
            backtrack(i + 1, depth + 1, path)
            path.pop()

    backtrack(0, 0, [])
    tracer.finish(line=62)
    return res

# 定义 next_permutation 函数
def next_permutation(nums):
    tracer.init_array(nums, line=65)
    n = len(nums)
    i = n - 2
    tracer.move_pointer({"i": i}, line=67)
    while i >= 0 and nums[i] >= nums[i + 1]:
        tracer.compare(i, i + 1, line=69)
        i -= 1
        tracer.move_pointer({"i": i}, line=69)
    if i >= 0:
        j = n - 1
        tracer.move_pointer({"j": j}, line=71)
        while j > i and nums[j] <= nums[i]:
            tracer.compare(i, j, line=73)
            j -= 1
            tracer.move_pointer({"j": j}, line=73)
        tracer.swap(i, j, line=75)
        nums[i], nums[j] = nums[j], nums[i]
    left, right = i + 1, n - 1
    while left < right:
        tracer.swap(left, right, line=78)
        nums[left], nums[right] = nums[right], nums[left]
        left += 1
        right -= 1
    for i in range(n):
        tracer.mark_sorted(i, line=80)
    tracer.finish(line=80)