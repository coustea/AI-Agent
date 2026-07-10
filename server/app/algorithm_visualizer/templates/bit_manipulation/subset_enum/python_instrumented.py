from visual_tracer import ArrayTracer

tracer = ArrayTracer()

# 定义 enumerate_subsets 函数
def enumerate_subsets(n):
    subsets = []
# 循环遍历处理
    for mask in range(1 << n):
        subset = []
# 循环遍历处理
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
    tracer.init_array(nums, line=20)
    n = len(nums)
    results = []
# 循环遍历处理
    for mask in range(1 << n):
        subset = []
        total = 0
# 循环遍历处理
        for i in range(n):
            if mask & (1 << i):
                tracer.compare(i, i, line=27)
                subset.append(nums[i])
                total += nums[i]
        if total == target:
            results.append(subset)
    tracer.finish(line=33)
    return results

# 定义 count_subsets_with_sum 函数
def count_subsets_with_sum(nums, target):
    n = len(nums)
    count = 0
# 循环遍历处理
    for mask in range(1 << n):
        total = 0
# 循环遍历处理
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
