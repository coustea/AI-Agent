def quick_sort(nums, left, right):
    if left >= right:
        return
    i, j = left, right
    pivot = nums[left]
    while i < j:
        while i < j and nums[j] >= pivot:
            j -= 1
        while i < j and nums[i] <= pivot:
            i += 1
        if i < j:
            nums[i], nums[j] = nums[j], nums[i]
    nums[left] = nums[i]
    nums[i] = pivot
    quick_sort(nums, left, i - 1)
    quick_sort(nums, i + 1, right)

arr = [6, 1, 8, 3, 9, 2, 5, 7, 4]
quick_sort(arr, 0, len(arr) - 1)