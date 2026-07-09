from visual_tracer import ArrayTracer

tracer = ArrayTracer()

def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    tracer.init_array(left + [0] * len(right), line=14)
    while i < len(left) and j < len(right):
        tracer.compare(i, len(left) + j - 1 if j > 0 else i, line=16)
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    tracer.finish(line=24)
    return result

def count_inversions(arr):
    if len(arr) <= 1:
        return arr, 0
    mid = len(arr) // 2
    left, inv_l = count_inversions(arr[:mid])
    right, inv_r = count_inversions(arr[mid:])
    merged, inv_m = merge_count(left, right)
    return merged, inv_l + inv_r + inv_m

def merge_count(left, right):
    result = []
    i = j = inv = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            inv += len(left) - i
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result, inv

def merge_k_sorted(arrays):
    import heapq
    heap = []
    for arr_idx, arr in enumerate(arrays):
        if arr:
            heapq.heappush(heap, (arr[0], arr_idx, 0))
    result = []
    while heap:
        val, arr_idx, elem_idx = heapq.heappop(heap)
        result.append(val)
        if elem_idx + 1 < len(arrays[arr_idx]):
            heapq.heappush(heap, (arrays[arr_idx][elem_idx + 1], arr_idx, elem_idx + 1))
    return result

data = [89, 45, 23, 78, 12, 56, 91, 34, 67, 3, 88, 15, 72, 41, 60]
sorted_data = merge_sort(data)

_, inv = count_inversions([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5])

arrays = [[1, 4, 7], [2, 5, 8], [3, 6, 9, 10]]
merged = merge_k_sorted(arrays)
tracer.dump()
