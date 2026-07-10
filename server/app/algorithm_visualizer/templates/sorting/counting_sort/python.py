def counting_sort(arr):
    if not arr:
        return arr
    min_val = min(arr)
    max_val = max(arr)
    range_val = max_val - min_val + 1
    count = [0] * range_val
    for x in arr:
        count[x - min_val] += 1
    for i in range(1, len(count)):
        count[i] += count[i - 1]
    output = [0] * len(arr)
    for i in range(len(arr) - 1, -1, -1):
        val = arr[i]
        output[count[val - min_val] - 1] = val
        count[val - min_val] -= 1
    for i in range(len(arr)):
        arr[i] = output[i]
    return arr

# 定义 counting_sort_unstable 函数
def counting_sort_unstable(arr):
    if not arr:
        return arr
    min_val = min(arr)
    max_val = max(arr)
    range_val = max_val - min_val + 1
    count = [0] * range_val
    for x in arr:
        count[x - min_val] += 1
    result = []
    for i in range(range_val):
        result.extend([i + min_val] * count[i])
    return result

# 定义 frequency_count 函数
def frequency_count(arr):
    if not arr:
        return {}
    min_val = min(arr)
    max_val = max(arr)
    freq = {}
    for x in arr:
        freq[x] = freq.get(x, 0) + 1
    return freq

datasets = [
    [4, -2, 2, 8, 3, 3, 1, -5, 7, 3, 0, 6, -1, 9, -3, 5, 2, 8, -4, 1],
    [10, 10, 10, 5, 5, 5, 1, 1, 1, 8, 8, 8, 3, 3, 3],
    [0, -1, 1, -2, 2, -3, 3, -4, 4, -5, 5, -6, 6, -7, 7],
]

for data in datasets:
    r1 = counting_sort(data[:])
    r2 = counting_sort_unstable(data[:])
    assert r1 == r2 == sorted(data)
    freq = frequency_count(data)
