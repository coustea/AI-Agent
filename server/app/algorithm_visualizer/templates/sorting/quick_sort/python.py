def quick_sort(arr):
    """快速排序：按枢轴分区后递归处理两侧。"""
    return _quick_sort(list(arr), 0, len(arr) - 1)


def _quick_sort(nums, left, right):
    if left >= right:
        return nums

    pivot = nums[(left + right) // 2]
    i, j = left, right
    while i <= j:
        while nums[i] < pivot:
            i += 1
        while nums[j] > pivot:
            j -= 1
        if i <= j:
            nums[i], nums[j] = nums[j], nums[i]
            i += 1
            j -= 1

    _quick_sort(nums, left, j)
    _quick_sort(nums, i, right)
    return nums
