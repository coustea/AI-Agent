def sequential_search(arr, target):
    for i, val in enumerate(arr):
        if val == target:
            return i
    return -1

# 定义 sentinel_search 函数
def sentinel_search(arr, target):
    last = arr[-1]
    arr[-1] = target
    i = 0
    while arr[i] != target:
        i += 1
    arr[-1] = last
    if i < len(arr) - 1 or last == target:
        return i
    return -1

# 定义 multi_key_search 函数
def multi_key_search(arr, keys):
    results = {}
    for key in keys:
        indices = [i for i, v in enumerate(arr) if v == key]
        results[key] = indices
    return results

# 定义 search_with_count 函数
def search_with_count(arr, target):
    comparisons = 0
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

for arr, target in datasets:
    r1 = sequential_search(arr, target)
    r2 = sentinel_search(arr[:], target)
    assert r1 == r2

arr = [23, 45, 12, 67, 34, 89, 56, 12, 78, 12]
multi = multi_key_search(arr, [12, 45, 99])

idx, comps = search_with_count([10, 20, 30, 40, 50], 30)
