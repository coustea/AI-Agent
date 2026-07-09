from visual_tracer import ArrayTracer

tracer = ArrayTracer()

def quick_sort(nums, left, right):
    """快速排序：选取基准值，将数组分为小于和大于基准的两部分，递归排序。
    时间复杂度: 平均 O(n log n)，最坏 O(n²)，空间复杂度: O(log n)，不稳定排序
    优化：三数取中法选取基准，减少最坏情况概率"""

    def median_of_three(l, r):
        """三数取中法：从首、中、尾三个位置选取中值作为基准"""
        mid = (l + r) // 2
        if nums[l] > nums[mid]:
            nums[l], nums[mid] = nums[mid], nums[l]
            tracer.swap(l, mid, line=9)
        if nums[l] > nums[r]:
            nums[l], nums[r] = nums[r], nums[l]
            tracer.swap(l, r, line=11)
        if nums[mid] > nums[r]:
            nums[mid], nums[r] = nums[r], nums[mid]
            tracer.swap(mid, r, line=13)
        nums[mid], nums[l + 1] = nums[l + 1], nums[mid]
        tracer.swap(mid, l + 1, line=15)

    if left >= right:
        return
    if right - left + 1 <= 3:
        insertion_sort_small(nums, left, right)
        return

    median_of_three(left, right)
    pivot = nums[left + 1]
    i, j = left + 1, right
    tracer.move_pointer({"left": left, "right": right, "i": i, "j": j}, line=20)

    while i < j:
        while i < j and nums[j] >= pivot:
            tracer.compare(i, j, line=23)
            j -= 1
            tracer.move_pointer({"left": left, "right": right, "i": i, "j": j}, line=25)
        while i < j and nums[i] <= pivot:
            tracer.compare(i, j, line=26)
            i += 1
            tracer.move_pointer({"left": left, "right": right, "i": i, "j": j}, line=28)
        if i < j:
            nums[i], nums[j] = nums[j], nums[i]
            tracer.swap(i, j, line=30)

    nums[left + 1], nums[i] = nums[i], nums[left + 1]
    tracer.assign(left + 1, nums[left + 1], line=32)
    tracer.assign(i, nums[i], line=33)
    quick_sort(nums, left, i - 1)
    quick_sort(nums, i + 1, right)


def insertion_sort_small(nums, left, right):
    """小规模插入排序：用于快速排序的子问题优化"""
    for i in range(left + 1, right + 1):
        key = nums[i]
        j = i - 1
        while j >= left and key < nums[j]:
            nums[j + 1] = nums[j]
            tracer.assign(j + 1, nums[j + 1], line=42)
            j -= 1
        nums[j + 1] = key
        tracer.assign(j + 1, key, line=45)


arr = [64, 34, 25, 12, 22, 12, 22, 90, 55, 43, 28, 73, 16]
tracer.init_array(arr, line=48)
quick_sort(arr, 0, len(arr) - 1)
for idx in range(len(arr)):
    tracer.mark_sorted(idx, line=51)
tracer.finish(line=52)
tracer.dump()
