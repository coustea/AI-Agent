def bubble_sort_with_bounds(arr):
    """冒泡排序：相邻元素逆序时交换。"""
    nums = list(arr)
    for end in range(len(nums) - 1, 0, -1):
        for index in range(end):
            if nums[index] > nums[index + 1]:
                nums[index], nums[index + 1] = nums[index + 1], nums[index]
    return nums
