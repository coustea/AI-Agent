from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def binary_insertion_sort(arr):
    tracer.init_array(arr, line=1)
    n = len(arr)
    for i in range(1, n):
        key = arr[i]
        tracer.move_pointer({"i": i}, line=4)
        lo, hi = 0, i
        while lo < hi:
            mid = (lo + hi) // 2
            tracer.compare(mid, i, line=7)
            if arr[mid] <= key:
                lo = mid + 1
            else:
                hi = mid
        for j in range(i, lo, -1):
            arr[j] = arr[j - 1]
            tracer.assign(j, arr[j - 1], line=12)
        arr[lo] = key
        tracer.assign(lo, key, line=14)
    for i in range(n):
        tracer.mark_sorted(i, line=15)
    tracer.finish(line=15)
    return arr

# 定义 insertion_sort 函数
def insertion_sort(arr):
    tracer.init_array(arr, line=17)
    n = len(arr)
    for i in range(1, n):
        key = arr[i]
        tracer.move_pointer({"i": i}, line=20)
        j = i - 1
        while j >= 0 and key < arr[j]:
            tracer.compare(j, j + 1, line=23)
            arr[j + 1] = arr[j]
            tracer.assign(j + 1, arr[j], line=24)
            j -= 1
        arr[j + 1] = key
        tracer.assign(j + 1, key, line=26)
    for i in range(n):
        tracer.mark_sorted(i, line=27)
    tracer.finish(line=27)
    return arr

# 定义 shell_insertion 函数
def shell_insertion(arr, gap):
    tracer.init_array(arr, line=29)
    n = len(arr)
    for i in range(gap, n):
        key = arr[i]
        tracer.move_pointer({"i": i}, line=32)
        j = i
        while j >= gap and arr[j - gap] > key:
            tracer.compare(j - gap, j, line=35)
            arr[j] = arr[j - gap]
            tracer.assign(j, arr[j - gap], line=36)
            j -= gap
        arr[j] = key
        tracer.assign(j, key, line=38)
    tracer.finish(line=39)
    return arr
