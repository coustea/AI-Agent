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
