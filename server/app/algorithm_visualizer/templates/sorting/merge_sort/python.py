def merge_sort_wrapper(arr):
    """归并排序：递归拆分，再合并两个有序数组。"""
    nums = list(arr)

    def merge_sort(values):
        if len(values) <= 1:
            return values
        middle = len(values) // 2
        left = merge_sort(values[:middle])
        right = merge_sort(values[middle:])
        merged = []
        while left and right:
            if left[0] <= right[0]:
                merged.append(left.pop(0))
            else:
                merged.append(right.pop(0))
        return merged + left + right

    nums[:] = merge_sort(nums)
    return nums
