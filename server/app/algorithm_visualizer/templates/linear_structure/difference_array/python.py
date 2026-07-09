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

def apply_and_verify(arr, updates):
    result = range_updates(arr, updates)
    brute = list(arr)
    for l, r, val in updates:
        for i in range(l, r + 1):
            if 0 <= i < len(brute):
                brute[i] += val
    return result == brute

data = [3, 7, 2, 9, 5, 1, 8, 4, 6, 10, 3, 12, 2, 5, 8]
updates = [(1, 5, 3), (3, 8, -2), (0, 10, 4), (6, 11, 1)]
result = range_updates(data, updates)
assert apply_and_verify(data, updates)

queries = [2, 5, 9]
point_results = range_updates_with_query(data, updates, queries)
assert len(point_results) == 3
