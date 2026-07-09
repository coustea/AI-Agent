def subsets(nums):
    if not nums:
        return [[]]
    res = []

    def backtrack(start, path):
        res.append(path[:])
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()

    backtrack(0, [])
    return res

def subsets_with_dup(nums):
    nums.sort()
    res = []

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

def subset_sum(nums, target):
    res = []

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

r1 = subsets([1, 2, 3, 4, 5])
assert len(r1) == 32

r2 = subsets_with_dup([1, 2, 2, 3])
assert len(r2) == 12

r3 = subsets_bitmask([1, 2, 3])
assert len(r3) == 8

r4 = subset_sum([3, 1, 4, 2, 5, 6], 6)
for s in r4:
    assert sum(s) == 6
