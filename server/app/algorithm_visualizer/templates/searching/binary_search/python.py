def binary_search(arr, target):
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1

# 定义 lower_bound 函数
def lower_bound(arr, target):
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo

# 定义 upper_bound 函数
def upper_bound(arr, target):
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] <= target:
            lo = mid + 1
        else:
            hi = mid
    return lo

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

arr = [1, 3, 5, 5, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25]
idx = binary_search(arr, 7)
lb = lower_bound(arr, 5)
ub = upper_bound(arr, 5)
count = ub - lb

rotated = [15, 17, 19, 21, 23, 25, 1, 3, 5, 7, 9, 11, 13]
r = search_rotated(rotated, 5)
r2 = search_rotated(rotated, 14)
