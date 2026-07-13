from visual_tracer import ArrayTracer
tracer = ArrayTracer()

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
    tracer.init_array(arr, line=12)
    if not arr:
        tracer.finish(line=14)
        return arr
    min_val, max_val = min(arr), max(arr)
    if min_val == max_val:
        for i in range(len(arr)):
            tracer.assign(i, arr[i], line=18)
            tracer.mark_sorted(i, line=18)
        tracer.finish(line=19)
        return arr
    n = len(arr)
    num_buckets = max(1, n // 3)
    bucket_range = (max_val - min_val) / num_buckets
    buckets = [[] for _ in range(num_buckets)]

    for x in arr:
        tracer.move_pointer({"val": x}, line=23)
        idx = int((x - min_val) / bucket_range)
        if idx == num_buckets:
            idx -= 1
        buckets[idx].append(x)

    result = []
    for b_idx, b in enumerate(buckets):
        tracer.move_pointer({"bucket": b_idx}, line=29)
        if b:
            insertion_sort_for_buckets(b)
            result.extend(b)

    tracer.init_array(result, line=35)
    for i, v in enumerate(result):
        tracer.assign(i, v, line=36)
        tracer.mark_sorted(i, line=37)
    tracer.finish(line=38)
    return result
