def quick_select(nums, k):
    def partition(left, right, pivot_idx):
        pivot = nums[pivot_idx]
        # Move pivot to end
        nums[pivot_idx], nums[right] = nums[right], nums[pivot_idx]
        store_idx = left
        for i in range(left, right):
            if nums[i] < pivot:
                nums[store_idx], nums[i] = nums[i], nums[store_idx]
                store_idx += 1
        # Move pivot to its final place
        nums[right], nums[store_idx] = nums[store_idx], nums[right]
        return store_idx
        
    def select(left, right, k_smallest):
        if left == right:
            return nums[left]
        pivot_idx = left
        pivot_idx = partition(left, right, pivot_idx)
        if k_smallest == pivot_idx:
            return nums[k_smallest]
        elif k_smallest < pivot_idx:
            return select(left, pivot_idx - 1, k_smallest)
        else:
            return select(pivot_idx + 1, right, k_smallest)
            
    return select(0, len(nums) - 1, len(nums) - k)

quick_select([3, 2, 1, 5, 6, 4], 2)
