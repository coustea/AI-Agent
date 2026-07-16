def selection_sort(arr):
    """选择排序：每轮把未排序区间的最小值放到起点。"""
    nums = list(arr)
    for start in range(len(nums) - 1):
        minimum = start
        for index in range(start + 1, len(nums)):
            if nums[index] < nums[minimum]:
                minimum = index
        nums[start], nums[minimum] = nums[minimum], nums[start]
    return nums
