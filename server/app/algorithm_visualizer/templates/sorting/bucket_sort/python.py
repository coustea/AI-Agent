# bucket_sort 算法实现 — domain: sorting
def insertion_sort_for_buckets(bucket):
    for i in range(1, len(bucket)):
        key = bucket[i]
        j = i - 1
        while j >= 0 and bucket[j] > key:
            bucket[j + 1] = bucket[j]
            j -= 1
        bucket[j + 1] = key
    return bucket

# 定义 bucket_sort 函数
def bucket_sort(arr):
    if not arr:
        return arr
    min_val, max_val = min(arr), max(arr)
    if min_val == max_val:
        return arr
    n = len(arr)
    num_buckets = max(1, n // 3)
    bucket_range = (max_val - min_val) / num_buckets
    buckets = [[] for _ in range(num_buckets)]
    for x in arr:
        idx = int((x - min_val) / bucket_range)
        if idx == num_buckets:
            idx -= 1
        buckets[idx].append(x)
    result = []
    for b in buckets:
        if b:
            insertion_sort_for_buckets(b)
            result.extend(b)
    return result

# 定义 bucket_sort_with_negatives 函数
def bucket_sort_with_negatives(arr):
    if not arr:
        return arr
    neg = [-x for x in arr if x < 0]
    pos = [x for x in arr if x >= 0]
    if neg:
        neg = [-x for x in reversed(bucket_sort(neg))]
    if pos:
        pos = bucket_sort(pos)
    return neg + pos

# 定义 bucket_sort_custom_buckets 函数
def bucket_sort_custom_buckets(arr, num_buckets):
    if not arr:
        return arr
    min_val, max_val = min(arr), max(arr)
    if min_val == max_val:
        return arr
    bucket_range = (max_val - min_val) / num_buckets
    buckets = [[] for _ in range(num_buckets)]
    for x in arr:
        idx = int((x - min_val) / bucket_range)
        if idx == num_buckets:
            idx -= 1
        buckets[idx].append(x)
    result = []
    for b in buckets:
        if b:
            insertion_sort_for_buckets(b)
            result.extend(b)
    return result
