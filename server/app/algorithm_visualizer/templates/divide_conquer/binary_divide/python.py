# binary_divide 算法实现 — domain: divide_conquer
def binary_search_first(arr, target):
    lo, hi = 0, len(arr) - 1
    result = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            result = mid
            hi = mid - 1
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return result

# 定义 binary_search_last 函数
def binary_search_last(arr, target):
    lo, hi = 0, len(arr) - 1
    result = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            result = mid
            lo = mid + 1
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return result

# 定义 sqrt_binary 函数
def sqrt_binary(n, precision=1e-7):
    if n < 0:
        return None
    lo, hi = 0, max(1, n)
    while hi - lo > precision:
        mid = (lo + hi) / 2
        if mid * mid < n:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

# 定义 search_rotated 函数
def search_rotated(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        if arr[lo] <= arr[mid]:
            if arr[lo] <= target < arr[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:
            if arr[mid] < target <= arr[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1

arr = [1, 2, 3, 4, 5, 5, 5, 6, 7, 8, 9, 10]
first = binary_search_first(arr, 5)
last = binary_search_last(arr, 5)

sqrt_2 = sqrt_binary(2)
sqrt_10 = sqrt_binary(10)

rotated = [4, 5, 6, 7, 0, 1, 2]
idx = search_rotated(rotated, 0)
idx2 = search_rotated(rotated, 3)
