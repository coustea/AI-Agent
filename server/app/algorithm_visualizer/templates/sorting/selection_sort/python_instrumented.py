from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def bidirectional_selection_sort(arr):
    tracer.init_array(arr, line=1)
    n = len(arr)
    lo, hi = 0, n - 1
    while lo < hi:
        min_idx, max_idx = lo, lo
        tracer.move_pointer({"lo": lo, "hi": hi}, line=5)
        for i in range(lo, hi + 1):
            tracer.compare(i, min_idx, line=7)
            if arr[i] < arr[min_idx]:
                min_idx = i
            tracer.compare(i, max_idx, line=9)
            if arr[i] > arr[max_idx]:
                max_idx = i
        if min_idx != lo:
            tracer.swap(min_idx, lo, line=11)
            arr[lo], arr[min_idx] = arr[min_idx], arr[lo]
        if max_idx == lo:
            max_idx = min_idx
        if max_idx != hi:
            tracer.swap(max_idx, hi, line=15)
            arr[hi], arr[max_idx] = arr[max_idx], arr[hi]
        tracer.mark_sorted(lo, line=17)
        tracer.mark_sorted(hi, line=17)
        lo += 1
        hi -= 1
    for i in range(n):
        tracer.mark_sorted(i, line=18)
    tracer.finish(line=19)
    return arr

# 定义 selection_sort 函数
def selection_sort(arr):
    tracer.init_array(arr, line=21)
    n = len(arr)
    for i in range(n):
        min_idx = i
        tracer.move_pointer({"i": i}, line=24)
        for j in range(i + 1, n):
            tracer.compare(j, min_idx, line=26)
            if arr[j] < arr[min_idx]:
                min_idx = j
        if min_idx != i:
            tracer.swap(min_idx, i, line=29)
            arr[i], arr[min_idx] = arr[min_idx], arr[i]
        tracer.mark_sorted(i, line=30)
    tracer.finish(line=31)
    return arr

# 定义 count_inversions 函数
def count_inversions(arr):
# 定义 merge_count 函数
    def merge_count(left, right):
        result = []
        i = j = inv = 0
        tracer.init_array(left + right, line=36)
        while i < len(left) and j < len(right):
            tracer.compare(i, j, line=39)
            if left[i] <= right[j]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                inv += len(left) - i
                j += 1
        result.extend(left[i:])
        result.extend(right[j:])
        tracer.finish(line=45)
        return result, inv

# 定义 sort_count 函数
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
