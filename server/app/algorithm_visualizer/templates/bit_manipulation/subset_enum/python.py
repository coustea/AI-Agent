def get_subsets_bitmask(nums):
    n = len(nums)
    subsets = []
    for mask in range(1 << n):
        subset = []
        for i in range(n):
            if mask & (1 << i):
                subset.append(nums[i])
        subsets.append(subset)
    return subsets

get_subsets_bitmask([1, 2, 3])
