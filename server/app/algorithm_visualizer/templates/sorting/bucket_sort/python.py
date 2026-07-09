def insertion_sort_for_buckets(bucket):
    for i in range(1, len(bucket)):
        key = bucket[i]
        j = i - 1
        while j >= 0 and bucket[j] > key:
            bucket[j + 1] = bucket[j]
            j -= 1
        bucket[j + 1] = key
    return bucket

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

datasets = [
    [29, 25, 3, 49, 9, 37, 21, 43, 88, 15, 66, 52, 71, 34, 18],
    [0.5, 0.2, 0.8, 0.1, 0.9, 0.3, 0.7, 0.4, 0.6, 0.15, 0.85, 0.45],
    [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
]

for data in datasets:
    r1 = bucket_sort(data[:])
    assert r1 == sorted(data)

for nb in [3, 5, 7, 10]:
    r2 = bucket_sort_custom_buckets(datasets[0][:], nb)
    assert r2 == sorted(datasets[0])
