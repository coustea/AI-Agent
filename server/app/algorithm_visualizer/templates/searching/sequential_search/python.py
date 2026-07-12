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
