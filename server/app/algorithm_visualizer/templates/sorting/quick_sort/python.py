def quick_sort(nums, left, right):
    """快速排序：选取基准值，将数组分为小于和大于基准的两部分，递归排序。
    时间复杂度: 平均 O(n log n)，最坏 O(n²)，空间复杂度: O(log n)，不稳定排序
    优化：三数取中法选取基准，减少最坏情况概率"""

    def median_of_three(l, r):
        """三数取中法：从首、中、尾三个位置选取中值作为基准"""
        mid = (l + r) // 2
        # 将三个位置的中值放到 l 位置
        if nums[l] > nums[mid]:
            nums[l], nums[mid] = nums[mid], nums[l]
        if nums[l] > nums[r]:
            nums[l], nums[r] = nums[r], nums[l]
        if nums[mid] > nums[r]:
            nums[mid], nums[r] = nums[r], nums[mid]
        # 中值在 mid 位置，交换到 left+1 位置作为基准
        nums[mid], nums[l + 1] = nums[l + 1], nums[mid]

    if left >= right:  # 递归终止条件
        return
    if right - left + 1 <= 3:  # 小规模直接插入排序更高效
        insertion_sort_small(nums, left, right)
        return

    median_of_three(left, right)  # 三数取中选取基准
    pivot = nums[left + 1]  # 基准值
    i, j = left + 1, right  # 从 left+1 和 right 开始扫描

    while i < j:
        while i < j and nums[j] >= pivot:  # 从右向左找小于基准的元素
            j -= 1
        while i < j and nums[i] <= pivot:  # 从左向右找大于基准的元素
            i += 1
        if i < j:
            nums[i], nums[j] = nums[j], nums[i]  # 交换不符合条件的元素

    nums[left + 1], nums[i] = nums[i], nums[left + 1]  # 基准归位
    quick_sort(nums, left, i - 1)   # 递归排序左半部分
    quick_sort(nums, i + 1, right)  # 递归排序右半部分


def insertion_sort_small(nums, left, right):
    """小规模插入排序：用于快速排序的子问题优化"""
    for i in range(left + 1, right + 1):
        key = nums[i]
        j = i - 1
        while j >= left and key < nums[j]:
            nums[j + 1] = nums[j]
            j -= 1
        nums[j + 1] = key


# 测试数据：12个元素，包含重复值
arr = [64, 34, 25, 12, 22, 11, 90, 55, 43, 28, 73, 16]
quick_sort(arr, 0, len(arr) - 1)
