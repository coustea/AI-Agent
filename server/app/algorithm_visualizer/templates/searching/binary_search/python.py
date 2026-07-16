def binary_search(arr, target):
    """二分查找：每次根据中点缩小有序区间。"""
    left, right = 0, len(arr) - 1
    while left <= right:
        middle = (left + right) // 2
        if arr[middle] == target:
            return middle
        if arr[middle] < target:
            left = middle + 1
        else:
            right = middle - 1
    return -1
