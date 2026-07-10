from visual_tracer import ArrayTracer

tracer = ArrayTracer()

# 定义 partition 函数
def partition(arr, lo, hi):
    tracer.init_array(arr, line=1)
    pivot = arr[hi]
    i = lo
# 循环遍历处理
    for j in range(lo, hi):
        tracer.compare(j, hi, line=5)
        if arr[j] <= pivot:
            arr[i], arr[j] = arr[j], arr[i]
            tracer.swap(i, j, line=8)
            i += 1
    arr[i], arr[hi] = arr[hi], arr[i]
    tracer.swap(i, hi, line=11)
    tracer.finish(line=12)
    return i

# 定义 three_way_partition 函数
def three_way_partition(arr, lo, hi):
    pivot = arr[lo]
    lt, i, gt = lo, lo, hi
# 循环条件判断
    while i <= gt:
        if arr[i] < pivot:
            arr[lt], arr[i] = arr[i], arr[lt]
            lt += 1
            i += 1
        elif arr[i] > pivot:
            arr[gt], arr[i] = arr[i], arr[gt]
            gt -= 1
        else:
            i += 1
    return lt, gt

# 定义 quickselect 函数
def quickselect(arr, k):
    lo, hi = 0, len(arr) - 1
# 循环条件判断
    while lo <= hi:
        if lo == hi:
            return arr[lo]
        pivot_idx = partition(arr, lo, hi)
        if k == pivot_idx:
            return arr[k]
        elif k < pivot_idx:
            hi = pivot_idx - 1
        else:
            lo = pivot_idx + 1
    return arr[lo]

# 定义 find_median 函数
def find_median(arr):
    n = len(arr)
    if n % 2 == 1:
        return quickselect(arr[:], n // 2)
    return (quickselect(arr[:], n // 2 - 1) + quickselect(arr[:], n // 2)) / 2

arr = [89, 45, 23, 78, 12, 56, 91, 34, 67, 3, 88, 15, 72, 41, 60]
pivot_idx = partition(arr[:], 0, len(arr) - 1)

arr2 = [5, 3, 8, 3, 9, 3, 2, 3, 7]
lt, gt = three_way_partition(arr2, 0, len(arr2) - 1)

kth = quickselect([89, 45, 23, 78, 12, 56, 91, 34, 67, 3], 4)

median = find_median([89, 45, 23, 78, 12, 56, 91, 34, 67])
tracer.dump()
