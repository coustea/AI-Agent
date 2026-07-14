from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def quick_sort(nums, left, right):
    """快速排序：选取基准值，将数组分为小于和大于基准的两部分，递归排序。
    时间复杂度: 平均 O(n log n)，最坏 O(n²)，空间复杂度: O(log n)，不稳定排序
    优化：三数取中法选取基准，减少最坏情况概率"""

    def median_of_three(l, r):
        """三数取中法：从首、中、尾三个位置选取中值作为基准"""
        mid = (l + r) // 2
        # 将三个位置的中值放到 l 位置
        tracer.compare(l, mid, line=10)
        if nums[l] > nums[mid]:
            nums[l], nums[mid] = nums[mid], nums[l]
            tracer.swap(l, mid, line=11)
        tracer.compare(l, r, line=12)
        if nums[l] > nums[r]:
            nums[l], nums[r] = nums[r], nums[l]
            tracer.swap(l, r, line=13)
        tracer.compare(mid, r, line=14)
        if nums[mid] > nums[r]:
            nums[mid], nums[r] = nums[r], nums[mid]
            tracer.swap(mid, r, line=15)
        # 中值在 mid 位置，交换到 left+1 位置作为基准
        nums[mid], nums[l + 1] = nums[l + 1], nums[mid]
        tracer.swap(mid, l + 1, line=17)

    def _quick_sort(left, right):
        if left >= right:
            if 0 <= left < len(nums):
                tracer.mark_sorted(left, line=20)
            return
        if right - left + 1 <= 3:
            insertion_sort_small(nums, left, right)
            for i in range(left, right + 1):
                tracer.mark_sorted(i, line=23)
            return

        median_of_three(left, right)
        pivot = nums[left + 1]
        i, j = left + 1, right

        while i < j:
            while i < j and nums[j] >= pivot:
                tracer.move_pointer({"j": j}, line=30)
                j -= 1
            while i < j and nums[i] <= pivot:
                tracer.move_pointer({"i": i}, line=32)
                i += 1
            if i < j:
                tracer.compare(i, j, line=34)
                nums[i], nums[j] = nums[j], nums[i]
                tracer.swap(i, j, line=35)

        nums[left + 1], nums[i] = nums[i], nums[left + 1]
        tracer.swap(left + 1, i, line=37)
        tracer.mark_sorted(i, line=37)
        _quick_sort(left, i - 1)
        _quick_sort(i + 1, right)

    tracer.init_array(nums, line=1)
    _quick_sort(left, right)
    tracer.finish(line=39)


def insertion_sort_small(nums, left, right):
    """小规模插入排序：用于快速排序的子问题优化"""
    for i in range(left + 1, right + 1):
        key = nums[i]
        j = i - 1
        tracer.move_pointer({"i": i}, line=44)
        while j >= left and key < nums[j]:
            tracer.compare(j, j + 1, line=47)
            nums[j + 1] = nums[j]
            tracer.assign(j + 1, nums[j], line=48)
            j -= 1
        nums[j + 1] = key
        tracer.assign(j + 1, key, line=50)
