def quick_sort(nums, left, right):
    """快速排序：按枢轴分区后递归处理两侧。"""
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

    quick_sort(nums, left, j)
    quick_sort(nums, i, right)
    return nums
