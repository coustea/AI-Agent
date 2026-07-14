from visual_tracer import ArrayTracer
tracer = ArrayTracer()

# sliding_window 算法实现 — domain: linear_structure
def max_subarray_sum(arr, k):
    tracer.init_array(arr, line=2)
    n = len(arr)
    if n < k or k <= 0:
        tracer.finish(line=5)
        return None
    window_sum = sum(arr[:k])
    tracer.move_pointer({"window": f"[0:{k}]"}, line=7)
    for i in range(k):
        tracer.highlight(i, tone="active", line=7)
    tracer.clear_highlights(line=7)
    max_sum = window_sum
    max_start = 0
    tracer.mark_sorted(0, line=9)
    for i in range(n - k):
        tracer.move_pointer({"slide": i}, line=10)
        tracer.highlight(i, tone="danger", line=10)
        tracer.highlight(i + k, tone="active", line=10)
        window_sum = window_sum - arr[i] + arr[i + k]
        if window_sum > max_sum:
            max_sum = window_sum
            max_start = i + 1
            tracer.clear_highlights(line=13)
            for j in range(max_start, max_start + k):
                tracer.mark_sorted(j, line=13)
        else:
            tracer.clear_highlights(line=13)
    tracer.finish(line=14)
    return max_sum, max_start

# 定义 min_subarray_sum 函数
def min_subarray_sum(arr, k):
    tracer.init_array(arr, line=16)
    n = len(arr)
    if n < k or k <= 0:
        tracer.finish(line=19)
        return None
    window_sum = sum(arr[:k])
    tracer.move_pointer({"window": f"[0:{k}]"}, line=21)
    for i in range(k):
        tracer.highlight(i, tone="active", line=21)
    min_sum = window_sum
    tracer.clear_highlights(line=21)
    for i in range(n - k):
        tracer.move_pointer({"slide": i}, line=24)
        tracer.highlight(i, tone="danger", line=24)
        tracer.highlight(i + k, tone="active", line=24)
        window_sum = window_sum - arr[i] + arr[i + k]
        if window_sum < min_sum:
            min_sum = window_sum
        tracer.clear_highlights(line=26)
    tracer.finish(line=27)
    return min_sum

# 定义 max_subarray_sum_variable 函数
def max_subarray_sum_variable(arr):
    tracer.init_array(arr, line=29)
    if not arr:
        tracer.finish(line=31)
        return 0
    max_sum = arr[0]
    current_sum = arr[0]
    start = 0
    best_start, best_end = 0, 0
    tracer.move_pointer({"current": 0}, line=34)
    for i in range(1, len(arr)):
        tracer.move_pointer({"i": i}, line=37)
        if current_sum < 0:
            tracer.highlight(i - 1, tone="danger", line=38)
            current_sum = arr[i]
            start = i
            tracer.clear_highlights(line=40)
        else:
            tracer.highlight(i - 1, tone="active", line=42)
            current_sum += arr[i]
            tracer.clear_highlights(line=42)
        tracer.highlight(i, tone="active", line=44)
        if current_sum > max_sum:
            max_sum = current_sum
            best_start, best_end = start, i
            for j in range(best_start, best_end + 1):
                tracer.mark_sorted(j, line=45)
        tracer.clear_highlights(line=45)
    tracer.finish(line=46)
    return max_sum, best_start, best_end

# 定义 longest_substring_k_distinct 函数
def longest_substring_k_distinct(arr, k):
    tracer.init_array(arr, line=48)
    if k <= 0:
        tracer.finish(line=50)
        return 0
    count = {}
    left = 0
    max_len = 0
    tracer.move_pointer({"left": 0, "right": 0}, line=54)
    for right in range(len(arr)):
        tracer.move_pointer({"right": right}, line=55)
        tracer.highlight(right, tone="active", line=56)
        count[arr[right]] = count.get(arr[right], 0) + 1
        while len(count) > k:
            tracer.move_pointer({"shrink": left}, line=58)
            tracer.highlight(left, tone="danger", line=59)
            count[arr[left]] -= 1
            if count[arr[left]] == 0:
                del count[arr[left]]
            left += 1
            tracer.clear_highlights(line=62)
        tracer.clear_highlights(line=62)
        max_len = max(max_len, right - left + 1)
    tracer.finish(line=63)
    return max_len