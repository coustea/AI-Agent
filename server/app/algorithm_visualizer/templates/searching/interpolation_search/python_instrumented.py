from visual_tracer import ArrayTracer

tracer = ArrayTracer()

# 定义 interpolation_search 函数
def interpolation_search(arr, target):
    if not arr:
        return -1
    low, high = 0, len(arr) - 1
    tracer.init_array(arr, line=4)
    tracer.move_pointer({"low": low, "high": high}, line=6)
# 循环条件判断
    while low <= high and target >= arr[low] and target <= arr[high]:
        if low == high:
            tracer.compare(low, low, line=9)
            if arr[low] == target:
                tracer.finish(line=11)
                return low
            tracer.finish(line=13)
            return -1
        pos = low + (target - arr[low]) * (high - low) // (arr[high] - arr[low])
        pos = max(low, min(pos, high))
        tracer.move_pointer({"low": low, "high": high, "pos": pos}, line=15)
        tracer.compare(pos, pos, line=16)
        if arr[pos] == target:
            tracer.finish(line=18)
            return pos
        if arr[pos] < target:
            low = pos + 1
            tracer.move_pointer({"low": low, "high": high}, line=21)
        else:
            high = pos - 1
            tracer.move_pointer({"low": low, "high": high}, line=24)
    tracer.finish(line=26)
    return -1

# 定义 interpolation_search_all 函数
def interpolation_search_all(arr, target):
    idx = interpolation_search(arr, target)
    if idx == -1:
        return []
    result = [idx]
    left = idx - 1
# 循环条件判断
    while left >= 0 and arr[left] == target:
        result.append(left)
        left -= 1
    right = idx + 1
# 循环条件判断
    while right < len(arr) and arr[right] == target:
        result.append(right)
        right += 1
    return sorted(result)

# 定义 interpolation_insert_pos 函数
def interpolation_insert_pos(arr, target):
    if not arr:
        return 0
    low, high = 0, len(arr) - 1
    if target <= arr[low]:
        return low
    if target > arr[high]:
        return high + 1
# 循环条件判断
    while low <= high and target >= arr[low] and target <= arr[high]:
        if low == high:
            return low + (1 if arr[low] < target else 0)
        pos = low + (target - arr[low]) * (high - low) // (arr[high] - arr[low])
        pos = max(low, min(pos, high))
        if arr[pos] < target:
            low = pos + 1
        else:
            high = pos - 1
    return low

data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150]
interpolation_search(data, 70)
interpolation_search(data, 10)
interpolation_search(data, 150)
interpolation_search(data, 99)

data_dup = [5, 10, 10, 10, 20, 20, 30, 30, 30, 30, 40, 50]
interpolation_search_all(data_dup, 10)
interpolation_search_all(data_dup, 30)
interpolation_search_all(data_dup, 25)

interpolation_insert_pos(data, 55)
interpolation_insert_pos(data, 5)
interpolation_insert_pos(data, 200)
tracer.dump()
