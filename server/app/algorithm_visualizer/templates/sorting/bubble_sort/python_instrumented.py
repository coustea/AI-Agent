from visual_tracer import ArrayTracer
tracer = ArrayTracer()

# bubble_sort 算法实现 — domain: sorting
def cocktail_sort(arr):
    n = len(arr)
    tracer.init_array(arr, line=3)
    start, end = 0, n - 1
    swapped = True
    while swapped:
        swapped = False
        for i in range(start, end):
            tracer.compare(i, i + 1, line=8)
            if arr[i] > arr[i + 1]:
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                tracer.swap(i, i + 1, line=10)
                swapped = True
        if not swapped:
            break
        tracer.mark_sorted(end, line=14)
        end -= 1
        swapped = False
        for i in range(end, start, -1):
            tracer.compare(i, i - 1, line=18)
            if arr[i] < arr[i - 1]:
                arr[i], arr[i - 1] = arr[i - 1], arr[i]
                tracer.swap(i, i - 1, line=20)
                swapped = True
        tracer.mark_sorted(start, line=22)
        start += 1
    for i in range(n):
        tracer.mark_sorted(i, line=24)
    tracer.finish(line=25)
    return arr

# 定义 bubble_sort_with_bounds 函数
def bubble_sort_with_bounds(arr):
    n = len(arr)
    tracer.init_array(arr, line=28)
    lo, hi = 0, n - 1
    while lo < hi:
        last_swap = lo
        for i in range(lo, hi):
            tracer.compare(i, i + 1, line=32)
            if arr[i] > arr[i + 1]:
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                tracer.swap(i, i + 1, line=34)
                last_swap = i
        tracer.mark_sorted(hi, line=36)
        hi = last_swap
        last_swap = hi
        for i in range(hi, lo, -1):
            tracer.compare(i, i - 1, line=39)
            if arr[i] < arr[i - 1]:
                arr[i], arr[i - 1] = arr[i - 1], arr[i]
                tracer.swap(i, i - 1, line=41)
                last_swap = i
        tracer.mark_sorted(lo, line=43)
        lo = last_swap
    for i in range(n):
        tracer.mark_sorted(i, line=45)
    tracer.finish(line=46)
    return arr

# 定义 is_sorted 函数
def is_sorted(arr):
    return all(arr[i] <= arr[i + 1] for i in range(len(arr) - 1))