def subsets(nums):
    if not nums:
        return [[]]
    res = []

# 定义 backtrack 函数
    def backtrack(start, path):
        res.append(path[:])
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()

    backtrack(0, [])
    return res

# 定义 subsets_with_dup 函数
def subsets_with_dup(nums):
    nums.sort()
    res = []

# 定义 backtrack 函数
    def backtrack(start, path):
        res.append(path[:])
        for i in range(start, len(nums)):
            if i > start and nums[i] == nums[i - 1]:
                continue
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()

    backtrack(0, [])
    return res

# 定义 subsets_bitmask 函数
def subsets_bitmask(nums):
    n = len(nums)
    res = []
    for mask in range(1 << n):
        subset = []
        for i in range(n):
            if mask & (1 << i):
                subset.append(nums[i])
        res.append(subset)
    return res

# 定义 subset_sum 函数
def subset_sum(nums, target):
    res = []

# 定义 backtrack 函数
    def backtrack(start, remain, path):
        if remain == 0:
            res.append(path[:])
            return
        if remain < 0:
            return
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, remain - nums[i], path)
            path.pop()

    backtrack(0, target, [])
    return res
