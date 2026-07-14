def merge_sort_wrapper(arr):
    """归并排序：按区间宽度逐轮合并相邻有序段。"""
    nums = list(arr)
    width = 1
    while width < len(nums):
        for left in range(0, len(nums), width * 2):
            middle = min(left + width, len(nums))
            right = min(left + width * 2, len(nums))
            left_values = nums[left:middle]
            right_values = nums[middle:right]
            left_index = 0
            right_index = 0
            merged = []
            while left_index < len(left_values) and right_index < len(right_values):
                if left_values[left_index] <= right_values[right_index]:
                    merged.append(left_values[left_index])
                    left_index += 1
                else:
                    merged.append(right_values[right_index])
                    right_index += 1
            merged.extend(left_values[left_index:])
            merged.extend(right_values[right_index:])
            nums[left:right] = merged
        width *= 2
    return nums
