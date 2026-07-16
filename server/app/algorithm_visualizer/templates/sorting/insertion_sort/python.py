def insertion_sort(arr):
    """插入排序：将当前元素插入左侧有序区间。"""
    nums = list(arr)
    for index in range(1, len(nums)):
        value = nums[index]
        position = index - 1
        while position >= 0 and nums[position] > value:
            nums[position + 1] = nums[position]
            position -= 1
        nums[position + 1] = value
    return nums
