# subset_enum 算法实现 — domain: bit_manipulation
def enumerate_subsets(n):
    subsets = []
    for mask in range(1 << n):
        subset = []
        for i in range(n):
            if mask & (1 << i):
                subset.append(i)
        subsets.append(subset)
    return subsets

# 定义 gray_code 函数
def gray_code(n):
    if n == 0:
        return [0]
    smaller = gray_code(n - 1)
    return smaller + [x | (1 << (n - 1)) for x in reversed(smaller)]

# 定义 subset_sum 函数
def subset_sum(nums, target):
    n = len(nums)
    results = []
    for mask in range(1 << n):
        subset = []
        total = 0
        for i in range(n):
            if mask & (1 << i):
                subset.append(nums[i])
                total += nums[i]
        if total == target:
            results.append(subset)
    return results

# 定义 count_subsets_with_sum 函数
def count_subsets_with_sum(nums, target):
    n = len(nums)
    count = 0
    for mask in range(1 << n):
        total = 0
        for i in range(n):
            if mask & (1 << i):
                total += nums[i]
        if total == target:
            count += 1
    return count
