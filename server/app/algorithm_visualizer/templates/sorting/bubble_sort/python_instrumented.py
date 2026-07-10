from visual_tracer import ArrayTracer

tracer = ArrayTracer()

# 定义 cocktail_sort 函数
def cocktail_sort(arr):
    n = len(arr)
    start, end = 0, n - 1
    swapped = True
# 循环条件判断
    while swapped:
        swapped = False
# 循环遍历处理
        for i in range(start, end):
            tracer.compare(i, i + 1, line=6)
            if arr[i] > arr[i + 1]:
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                tracer.swap(i, i + 1, line=8)
                swapped = True
        if not swapped:
            break
        end -= 1
        swapped = False
# 循环遍历处理
        for i in range(end, start, -1):
            tracer.compare(i, i - 1, line=15)
            if arr[i] < arr[i - 1]:
                arr[i], arr[i - 1] = arr[i - 1], arr[i]
                tracer.swap(i, i - 1, line=17)
                swapped = True
        start += 1
    return arr

# 定义 bubble_sort_with_bounds 函数
def bubble_sort_with_bounds(arr):
    n = len(arr)
    lo, hi = 0, n - 1
    tracer.init_array(arr, line=23)
# 循环条件判断
    while lo < hi:
        last_swap = lo
# 循环遍历处理
        for i in range(lo, hi):
            tracer.compare(i, i + 1, line=27)
            if arr[i] > arr[i + 1]:
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                tracer.swap(i, i + 1, line=29)
                last_swap = i
        hi = last_swap
        tracer.move_pointer({"lo": lo, "hi": hi}, line=32)
        last_swap = hi
# 循环遍历处理
        for i in range(hi, lo, -1):
            tracer.compare(i, i - 1, line=35)
            if arr[i] < arr[i - 1]:
                arr[i], arr[i - 1] = arr[i - 1], arr[i]
                tracer.swap(i, i - 1, line=37)
                last_swap = i
        lo = last_swap
        tracer.move_pointer({"lo": lo, "hi": hi}, line=40)
    tracer.finish(line=41)
    return arr

# 定义 is_sorted 函数
def is_sorted(arr):
    return all(arr[i] <= arr[i + 1] for i in range(len(arr) - 1))

datasets = [
    [89, 45, 23, 78, 12, 56, 91, 34, 67, 3, 88, 15, 72, 41, 60],
    [5, -3, 8, -1, 0, 7, -4, 2, 9, -6, 1, -8, 3, -2, 6],
    [42, 42, 17, 17, 63, 63, 8, 8, 91, 91, 25, 25, 56, 56, 34],
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
]

# 循环遍历处理
for data in datasets:
    result = bubble_sort_with_bounds(data[:])
    assert is_sorted(result)
tracer.dump()
