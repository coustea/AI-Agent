# merge_divide 算法实现 — domain: divide_conquer
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

# 定义 merge 函数
def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

# 定义 count_inversions 函数
def count_inversions(arr):
    if len(arr) <= 1:
        return arr, 0
    mid = len(arr) // 2
    left, inv_l = count_inversions(arr[:mid])
    right, inv_r = count_inversions(arr[mid:])
    merged, inv_m = merge_count(left, right)
    return merged, inv_l + inv_r + inv_m

# 定义 merge_count 函数
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

# 定义 merge_k_sorted 函数
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
