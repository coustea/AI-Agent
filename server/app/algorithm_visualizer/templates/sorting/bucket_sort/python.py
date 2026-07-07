def bucket_sort(arr):
    if not arr:
        return arr
    num_buckets = 5
    min_val, max_val = min(arr), max(arr)
    bucket_range = (max_val - min_val) / num_buckets
    if bucket_range == 0:
        return arr
    buckets = [[] for _ in range(num_buckets)]
    
    for x in arr:
        idx = int((x - min_val) / bucket_range)
        if idx == num_buckets:
            idx -= 1
        buckets[idx].append(x)
        
    result = []
    for b in buckets:
        b.sort()
        result.extend(b)
    return result

bucket_sort([29, 25, 3, 49, 9, 37, 21, 43])
