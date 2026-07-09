from visual_tracer import ArrayTracer

tracer = ArrayTracer()

def max_subarray_sum(arr, k):
    n = len(arr)
    if n < k or k <= 0:
        return None
    window_sum = sum(arr[:k])
    max_sum = window_sum
    max_start = 0
    tracer.init_array(arr, line=4)
    tracer.move_pointer({"start": 0, "end": k - 1}, line=9)
    for i in range(n - k):
        window_sum = window_sum - arr[i] + arr[i + k]
        if window_sum > max_sum:
            max_sum = window_sum
            max_start = i + 1
        tracer.move_pointer({"start": i + 1, "end": i + k}, line=15)
    tracer.finish(line=17)
    return max_sum, max_start

def min_subarray_sum(arr, k):
    n = len(arr)
    if n < k or k <= 0:
        return None
    window_sum = sum(arr[:k])
    min_sum = window_sum
    for i in range(n - k):
        window_sum = window_sum - arr[i] + arr[i + k]
        if window_sum < min_sum:
            min_sum = window_sum
    return min_sum

def max_subarray_sum_variable(arr):
    if not arr:
        return 0
    max_sum = arr[0]
    current_sum = arr[0]
    start = 0
    best_start, best_end = 0, 0
    for i in range(1, len(arr)):
        if current_sum < 0:
            current_sum = arr[i]
            start = i
        else:
            current_sum += arr[i]
        if current_sum > max_sum:
            max_sum = current_sum
            best_start, best_end = start, i
    return max_sum, best_start, best_end

def longest_substring_k_distinct(arr, k):
    if k <= 0:
        return 0
    count = {}
    left = 0
    max_len = 0
    for right in range(len(arr)):
        count[arr[right]] = count.get(arr[right], 0) + 1
        while len(count) > k:
            count[arr[left]] -= 1
            if count[arr[left]] == 0:
                del count[arr[left]]
            left += 1
        max_len = max(max_len, right - left + 1)
    return max_len

data = [3, 1, -2, 5, 4, -1, 2, 8, -3, 6, 2, 1, 4, -2, 7]
max_subarray_sum(data, 5)
min_subarray_sum(data, 5)
max_subarray_sum_variable(data)

chars = ['a', 'b', 'a', 'c', 'b', 'a', 'd', 'c', 'a', 'b']
longest_substring_k_distinct(chars, 2)
tracer.dump()
