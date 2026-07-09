from visual_tracer import ArrayTracer

tracer = ArrayTracer()

def enumerate_subsets(n):
    subsets = []
    for mask in range(1 << n):
        subset = []
        for i in range(n):
            if mask & (1 << i):
                subset.append(i)
        subsets.append(subset)
    return subsets

def gray_code(n):
    if n == 0:
        return [0]
    smaller = gray_code(n - 1)
    return smaller + [x | (1 << (n - 1)) for x in reversed(smaller)]

def subset_sum(nums, target):
    tracer.init_array(nums, line=20)
    n = len(nums)
    results = []
    for mask in range(1 << n):
        subset = []
        total = 0
        for i in range(n):
            if mask & (1 << i):
                tracer.compare(i, i, line=27)
                subset.append(nums[i])
                total += nums[i]
        if total == target:
            results.append(subset)
    tracer.finish(line=33)
    return results

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

nums = [3, 1, 4, 2, 5]
subsets = enumerate_subsets(len(nums))
gc = gray_code(4)
sums = subset_sum(nums, 7)
count = count_subsets_with_sum(nums, 7)
tracer.dump()
