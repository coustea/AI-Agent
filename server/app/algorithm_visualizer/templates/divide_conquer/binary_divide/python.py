def binary_search_divide(arr, low, high, target):
    if low > high:
        return -1
    mid = (low + high) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] > target:
        return binary_search_divide(arr, low, mid - 1, target)
    else:
        return binary_search_divide(arr, mid + 1, high, target)

binary_search_divide([1, 2, 3, 5, 8], 0, 4, 5)
