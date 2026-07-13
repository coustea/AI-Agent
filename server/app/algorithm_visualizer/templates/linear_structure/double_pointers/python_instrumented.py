from visual_tracer import ArrayTracer
tracer = ArrayTracer()

# double_pointers 算法实现 — domain: linear_structure
def two_sum_sorted(arr, target):
    tracer.init_array(arr, line=2)
    n = len(arr)
    if n < 2:
        tracer.finish(line=5)
        return None
    left = 0
    right = n - 1
    tracer.move_pointer({"left": left, "right": right}, line=8)
    while left < right:
        tracer.move_pointer({"left": left, "right": right}, line=9)
        tracer.highlight(left, tone="active", line=9)
        tracer.highlight(right, tone="active", line=9)
        current_sum = arr[left] + arr[right]
        if current_sum == target:
            tracer.mark_sorted(left, line=11)
            tracer.mark_sorted(right, line=11)
            tracer.finish(line=11)
            return (left, right)
        elif current_sum < target:
            tracer.highlight(left, tone="danger", line=13)
            left += 1
        else:
            tracer.highlight(right, tone="danger", line=15)
            right -= 1
        tracer.clear_highlights(line=15)
    tracer.finish(line=16)
    return None

# 定义 two_sum_all_pairs 函数
def two_sum_all_pairs(arr, target):
    tracer.init_array(arr, line=18)
    n = len(arr)
    if n < 2:
        tracer.finish(line=21)
        return []
    left = 0
    right = n - 1
    pairs = []
    tracer.move_pointer({"left": left, "right": right}, line=25)
    while left < right:
        tracer.move_pointer({"left": left, "right": right}, line=26)
        tracer.highlight(left, tone="active", line=26)
        tracer.highlight(right, tone="active", line=26)
        current_sum = arr[left] + arr[right]
        if current_sum == target:
            tracer.mark_sorted(left, line=29)
            tracer.mark_sorted(right, line=29)
            pairs.append((left, right))
            left += 1
            right -= 1
        elif current_sum < target:
            tracer.highlight(left, tone="danger", line=33)
            left += 1
        else:
            tracer.highlight(right, tone="danger", line=35)
            right -= 1
        tracer.clear_highlights(line=35)
    tracer.finish(line=36)
    return pairs

# 定义 reverse_in_range 函数
def reverse_in_range(arr, start, end):
    tracer.init_array(arr, line=38)
    if start < 0 or end >= len(arr) or start >= end:
        tracer.finish(line=40)
        return arr
    left = start
    right = end
    tracer.move_pointer({"left": left, "right": right}, line=43)
    while left < right:
        tracer.move_pointer({"left": left, "right": right}, line=44)
        tracer.highlight(left, tone="active", line=45)
        tracer.highlight(right, tone="active", line=45)
        tracer.swap(left, right, line=45)
        arr[left], arr[right] = arr[right], arr[left]
        left += 1
        right -= 1
        tracer.clear_highlights(line=47)
    tracer.finish(line=48)
    return arr

# 定义 three_sum_sorted 函数
def three_sum_sorted(arr, target):
    tracer.init_array(arr, line=50)
    n = len(arr)
    if n < 3:
        tracer.finish(line=53)
        return []
    result = []
    for i in range(n - 2):
        tracer.move_pointer({"i": i}, line=56)
        if i > 0 and arr[i] == arr[i - 1]:
            tracer.highlight(i, tone="danger", line=57)
            tracer.clear_highlights(line=57)
            continue
        left, right = i + 1, n - 1
        tracer.move_pointer({"left": left, "right": right}, line=59)
        while left < right:
            tracer.highlight(left, tone="active", line=61)
            tracer.highlight(right, tone="active", line=61)
            s = arr[i] + arr[left] + arr[right]
            if s == target:
                tracer.mark_sorted(i, line=63)
                tracer.mark_sorted(left, line=63)
                tracer.mark_sorted(right, line=63)
                result.append((arr[i], arr[left], arr[right]))
                left += 1
                right -= 1
                while left < right and arr[left] == arr[left - 1]:
                    tracer.highlight(left, tone="danger", line=66)
                    left += 1
                    tracer.clear_highlights(line=66)
                while left < right and arr[right] == arr[right + 1]:
                    tracer.highlight(right, tone="danger", line=69)
                    right -= 1
                    tracer.clear_highlights(line=69)
            elif s < target:
                tracer.highlight(left, tone="danger", line=71)
                left += 1
                tracer.clear_highlights(line=71)
            else:
                tracer.highlight(right, tone="danger", line=73)
                right -= 1
                tracer.clear_highlights(line=73)
    tracer.finish(line=74)
    return result

# 定义 remove_duplicates_sorted 函数
def remove_duplicates_sorted(arr):
    tracer.init_array(arr, line=76)
    if not arr:
        tracer.finish(line=78)
        return []
    slow = 0
    tracer.move_pointer({"slow": slow}, line=80)
    for fast in range(1, len(arr)):
        tracer.move_pointer({"fast": fast}, line=81)
        tracer.highlight(fast, tone="active", line=81)
        if arr[fast] != arr[slow]:
            slow += 1
            arr[slow] = arr[fast]
            tracer.assign(slow, arr[fast], line=84)
        tracer.clear_highlights(line=84)
    for i in range(slow + 1):
        tracer.mark_sorted(i, line=85)
    tracer.finish(line=85)
    return arr[:slow + 1]

# 定义 reverse_array 函数
def reverse_array(arr):
    return reverse_in_range(arr, 0, len(arr) - 1)
