def max_subarray_sum(arr, k):
    if len(arr) < k:
        return 0
    
    # Init first window sum
    window_sum = sum(arr[:k])
    max_sum = window_sum
    
    # Slide window
    for i in range(len(arr) - k):
        window_sum = window_sum - arr[i] + arr[i + k]
        max_sum = max(max_sum, window_sum)
    return max_sum

max_subarray_sum([1, 4, 2, 10, 2, 3, 1, 0, 20], 4)
