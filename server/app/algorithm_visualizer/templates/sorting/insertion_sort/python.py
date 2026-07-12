def binary_insertion_sort(arr):
    n = len(arr)
    for i in range(1, n):
        key = arr[i]
        lo, hi = 0, i
        while lo < hi:
            mid = (lo + hi) // 2
            if arr[mid] <= key:
                lo = mid + 1
            else:
                hi = mid
        for j in range(i, lo, -1):
            arr[j] = arr[j - 1]
        arr[lo] = key
    return arr

# 定义 insertion_sort 函数
def insertion_sort(arr):
    n = len(arr)
    for i in range(1, n):
        key = arr[i]
        j = i - 1
        while j >= 0 and key < arr[j]:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr

# 定义 shell_insertion 函数
def shell_insertion(arr, gap):
    n = len(arr)
    for i in range(gap, n):
        key = arr[i]
        j = i
        while j >= gap and arr[j - gap] > key:
            arr[j] = arr[j - gap]
            j -= gap
        arr[j] = key
    return arr
