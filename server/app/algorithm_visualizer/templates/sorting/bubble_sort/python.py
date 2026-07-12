# bubble_sort 算法实现 — domain: sorting
def cocktail_sort(arr):
    n = len(arr)
    start, end = 0, n - 1
    swapped = True
    while swapped:
        swapped = False
        for i in range(start, end):
            if arr[i] > arr[i + 1]:
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                swapped = True
        if not swapped:
            break
        end -= 1
        swapped = False
        for i in range(end, start, -1):
            if arr[i] < arr[i - 1]:
                arr[i], arr[i - 1] = arr[i - 1], arr[i]
                swapped = True
        start += 1
    return arr

# 定义 bubble_sort_with_bounds 函数
def bubble_sort_with_bounds(arr):
    n = len(arr)
    lo, hi = 0, n - 1
    while lo < hi:
        last_swap = lo
        for i in range(lo, hi):
            if arr[i] > arr[i + 1]:
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                last_swap = i
        hi = last_swap
        last_swap = hi
        for i in range(hi, lo, -1):
            if arr[i] < arr[i - 1]:
                arr[i], arr[i - 1] = arr[i - 1], arr[i]
                last_swap = i
        lo = last_swap
    return arr

# 定义 is_sorted 函数
def is_sorted(arr):
    return all(arr[i] <= arr[i + 1] for i in range(len(arr) - 1))
