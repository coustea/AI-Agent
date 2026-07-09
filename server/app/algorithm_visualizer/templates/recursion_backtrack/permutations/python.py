def permute(nums):
    if not nums:
        return []
    if len(nums) == 1:
        return [nums[:]]
    res = []

    def backtrack(start):
        if start == len(nums):
            res.append(nums[:])
            return
        for i in range(start, len(nums)):
            nums[start], nums[i] = nums[i], nums[start]
            backtrack(start + 1)
            nums[start], nums[i] = nums[i], nums[start]

    backtrack(0)
    return res

def permute_with_dup(nums):
    nums.sort()
    res = []

    def backtrack(path, used):
        if len(path) == len(nums):
            res.append(path[:])
            return
        for i in range(len(nums)):
            if used[i]:
                continue
            if i > 0 and nums[i] == nums[i - 1] and not used[i - 1]:
                continue
            used[i] = True
            path.append(nums[i])
            backtrack(path, used)
            path.pop()
            used[i] = False

    backtrack([], [False] * len(nums))
    return res

def permute_k(nums, k):
    if k <= 0 or k > len(nums):
        return []
    res = []

    def backtrack(start, depth, path):
        if depth == k:
            res.append(path[:])
            return
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, depth + 1, path)
            path.pop()

    backtrack(0, 0, [])
    return res

def next_permutation(nums):
    n = len(nums)
    i = n - 2
    while i >= 0 and nums[i] >= nums[i + 1]:
        i -= 1
    if i >= 0:
        j = n - 1
        while j > i and nums[j] <= nums[i]:
            j -= 1
        nums[i], nums[j] = nums[j], nums[i]
    left, right = i + 1, n - 1
    while left < right:
        nums[left], nums[right] = nums[right], nums[left]
        left += 1
        right -= 1

r1 = permute([1, 2, 3, 4])
assert len(r1) == 24

r2 = permute_with_dup([1, 1, 2])
assert len(r2) == 3

r3 = permute_k([1, 2, 3, 4, 5], 3)
assert len(r3) == 10

arr = [1, 2, 3]
next_permutation(arr)
assert arr == [1, 3, 2]
