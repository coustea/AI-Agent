# difference_array 算法实现 — domain: linear_structure
def range_updates(arr, updates):
    n = len(arr)
    if n == 0:
        return []
    if not updates:
        return list(arr)
    diff = [0] * (n + 1)
    diff[0] = arr[0]
    for i in range(1, n):
        diff[i] = arr[i] - arr[i - 1]
    for l, r, val in updates:
        if l < 0 or r >= n or l > r:
            continue
        diff[l] += val
        diff[r + 1] -= val
    result = [0] * n
    result[0] = diff[0]
    for i in range(1, n):
        result[i] = result[i - 1] + diff[i]
    return result

# 定义 range_updates_with_query 函数
def range_updates_with_query(arr, updates, queries):
    n = len(arr)
    if n == 0:
        return []
    diff = [0] * (n + 1)
    diff[0] = arr[0]
    for i in range(1, n):
        diff[i] = arr[i] - arr[i - 1]
    for l, r, val in updates:
        if l < 0 or r >= n or l > r:
            continue
        diff[l] += val
        diff[r + 1] -= val
    result_arr = [0] * n
    result_arr[0] = diff[0]
    for i in range(1, n):
        result_arr[i] = result_arr[i - 1] + diff[i]
    return [result_arr[q] for q in queries if 0 <= q < n]

# 定义 range_add_and_range_sum 函数
def range_add_and_range_sum(arr, updates, queries):
    n = len(arr)
    result = range_updates(arr, updates)
    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i + 1] = prefix[i] + result[i]
    results = []
    for l, r in queries:
        if 0 <= l <= r < n:
            results.append(prefix[r + 1] - prefix[l])
    return results

# 定义 apply_and_verify 函数
def apply_and_verify(arr, updates):
    result = range_updates(arr, updates)
    brute = list(arr)
    for l, r, val in updates:
        for i in range(l, r + 1):
            if 0 <= i < len(brute):
                brute[i] += val
    return result == brute
