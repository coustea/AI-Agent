from visual_tracer import ArrayTracer

tracer = ArrayTracer()

def bidirectional_selection_sort(arr):
    n = len(arr)
    lo, hi = 0, n - 1
    tracer.init_array(arr, line=3)
    while lo < hi:
        min_idx, max_idx = lo, lo
        for i in range(lo, hi + 1):
            tracer.compare(i, min_idx, line=7)
            if arr[i] < arr[min_idx]:
                min_idx = i
            tracer.compare(i, max_idx, line=9)
            if arr[i] > arr[max_idx]:
                max_idx = i
        if min_idx != lo:
            arr[lo], arr[min_idx] = arr[min_idx], arr[lo]
            tracer.swap(lo, min_idx, line=13)
        if max_idx == lo:
            max_idx = min_idx
        if max_idx != hi:
            arr[hi], arr[max_idx] = arr[max_idx], arr[hi]
            tracer.swap(hi, max_idx, line=17)
        tracer.mark_sorted(lo, line=18)
        tracer.mark_sorted(hi, line=19)
        lo += 1
        hi -= 1
    if lo == hi:
        tracer.mark_sorted(lo, line=22)
    tracer.finish(line=23)
    return arr

def selection_sort(arr):
    n = len(arr)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            if arr[j] < arr[min_idx]:
                min_idx = j
        if min_idx != i:
            arr[i], arr[min_idx] = arr[min_idx], arr[i]
    return arr

def count_inversions(arr):
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

    def sort_count(arr):
        if len(arr) <= 1:
            return arr, 0
        mid = len(arr) // 2
        left, inv_l = sort_count(arr[:mid])
        right, inv_r = sort_count(arr[mid:])
        merged, inv_m = merge_count(left, right)
        return merged, inv_l + inv_r + inv_m

    _, inversions = sort_count(arr)
    return inversions

datasets = [
    [89, 45, 23, 78, 12, 56, 91, 34, 67, 3, 88, 15, 72, 41, 60],
    [5, -3, 8, -1, 0, 7, -4, 2, 9, -6, 1, -8, 3, -2, 6],
    [42, 42, 17, 17, 63, 63, 8, 8, 91, 91, 25, 25, 56, 56, 34],
]

for data in datasets:
    result = bidirectional_selection_sort(data[:])
    inv = count_inversions(data[:])
tracer.dump()
