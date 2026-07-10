from visual_tracer import ArrayTracer

tracer = ArrayTracer()

# 定义 sequential_search 函数
def sequential_search(arr, target):
    tracer.init_array(arr, line=1)
# 循环遍历处理
    for i, val in enumerate(arr):
        tracer.move_pointer({"i": i}, line=4)
        tracer.compare(i, i, line=5)
        if val == target:
            tracer.finish(line=7)
            return i
    tracer.finish(line=9)
    return -1

# 定义 sentinel_search 函数
def sentinel_search(arr, target):
    last = arr[-1]
    arr[-1] = target
    i = 0
# 循环条件判断
    while arr[i] != target:
        i += 1
    arr[-1] = last
    if i < len(arr) - 1 or last == target:
        return i
    return -1

# 定义 multi_key_search 函数
def multi_key_search(arr, keys):
    results = {}
# 循环遍历处理
    for key in keys:
        indices = [i for i, v in enumerate(arr) if v == key]
        results[key] = indices
    return results

# 定义 search_with_count 函数
def search_with_count(arr, target):
    comparisons = 0
# 循环遍历处理
    for i, val in enumerate(arr):
        comparisons += 1
        if val == target:
            return i, comparisons
    return -1, comparisons

datasets = [
    ([23, 45, 12, 67, 34, 89, 56, 1, 78, 43, 91, 15, 60, 3, 88], 67),
    ([5, -3, 8, -1, 0, 7, -4, 2, 9, -6, 1, -8], -4),
    ([42, 42, 17, 17, 63, 63, 8, 8, 91, 91], 63),
]

# 循环遍历处理
for arr, target in datasets:
    r1 = sequential_search(arr, target)
    r2 = sentinel_search(arr[:], target)
    assert r1 == r2

arr = [23, 45, 12, 67, 34, 89, 56, 12, 78, 12]
multi = multi_key_search(arr, [12, 45, 99])

idx, comps = search_with_count([10, 20, 30, 40, 50], 30)
tracer.dump()
