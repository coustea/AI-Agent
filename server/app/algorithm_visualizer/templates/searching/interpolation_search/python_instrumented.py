from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def interpolation_search(arr, target):
    tracer.init_array(arr, line=1)
    if not arr:
        tracer.finish(line=2)
        return -1
    low, high = 0, len(arr) - 1
    while low <= high and target >= arr[low] and target <= arr[high]:
        tracer.move_pointer({"low": low, "high": high}, line=5)
        if low == high:
            tracer.compare(low, low, line=7)
            if arr[low] == target:
                tracer.mark_sorted(low, line=8)
                tracer.finish(line=8)
                return low
            tracer.finish(line=9)
            return -1
        pos = low + (target - arr[low]) * (high - low) // (arr[high] - arr[low])
        pos = max(low, min(pos, high))
        tracer.move_pointer({"pos": pos}, line=11)
        tracer.compare(pos, pos, line=12)
        if arr[pos] == target:
            tracer.mark_sorted(pos, line=13)
            tracer.finish(line=13)
            return pos
        if arr[pos] < target:
            low = pos + 1
        else:
            high = pos - 1
    tracer.finish(line=18)
    return -1

# 定义 interpolation_search_all 函数
def interpolation_search_all(arr, target):
    tracer.init_array(arr, line=20)
    idx = interpolation_search(arr, target)
    if idx == -1:
        tracer.finish(line=24)
        return []
    result = [idx]
    tracer.mark_sorted(idx, line=26)
    left = idx - 1
    while left >= 0 and arr[left] == target:
        tracer.move_pointer({"left": left}, line=27)
        result.append(left)
        tracer.mark_sorted(left, line=28)
        left -= 1
    right = idx + 1
    while right < len(arr) and arr[right] == target:
        tracer.move_pointer({"right": right}, line=30)
        result.append(right)
        tracer.mark_sorted(right, line=31)
        right += 1
    tracer.finish(line=33)
    return sorted(result)

# 定义 interpolation_insert_pos 函数
def interpolation_insert_pos(arr, target):
    tracer.init_array(arr, line=36)
    if not arr:
        tracer.finish(line=39)
        return 0
    low, high = 0, len(arr) - 1
    if target <= arr[low]:
        tracer.move_pointer({"insert": low}, line=42)
        tracer.finish(line=42)
        return low
    if target > arr[high]:
        tracer.move_pointer({"insert": high + 1}, line=44)
        tracer.finish(line=44)
        return high + 1
    while low <= high and target >= arr[low] and target <= arr[high]:
        tracer.move_pointer({"low": low, "high": high}, line=45)
        if low == high:
            tracer.finish(line=47)
            return low + (1 if arr[low] < target else 0)
        pos = low + (target - arr[low]) * (high - low) // (arr[high] - arr[low])
        pos = max(low, min(pos, high))
        tracer.move_pointer({"pos": pos}, line=49)
        if arr[pos] < target:
            low = pos + 1
        else:
            high = pos - 1
    tracer.finish(line=54)
    return low
