def partition(arr, lo, hi):
    pivot = arr[hi]
    i = lo
    for j in range(lo, hi):
        if arr[j] <= pivot:
            arr[i], arr[j] = arr[j], arr[i]
            i += 1
    arr[i], arr[hi] = arr[hi], arr[i]
    return i

def three_way_partition(arr, lo, hi):
    pivot = arr[lo]
    lt, i, gt = lo, lo, hi
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

def quickselect(arr, k):
    lo, hi = 0, len(arr) - 1
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
