def interpolation_search(arr, target):
    if not arr:
        return -1
    low, high = 0, len(arr) - 1
    while low <= high and target >= arr[low] and target <= arr[high]:
        if low == high:
            if arr[low] == target:
                return low
            return -1
        pos = low + (target - arr[low]) * (high - low) // (arr[high] - arr[low])
        pos = max(low, min(pos, high))
        if arr[pos] == target:
            return pos
        if arr[pos] < target:
            low = pos + 1
        else:
            high = pos - 1
    return -1

# 定义 interpolation_search_all 函数
def interpolation_search_all(arr, target):
    idx = interpolation_search(arr, target)
    if idx == -1:
        return []
    result = [idx]
    left = idx - 1
    while left >= 0 and arr[left] == target:
        result.append(left)
        left -= 1
    right = idx + 1
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
assert interpolation_search(data, 70) == 6
assert interpolation_search(data, 10) == 0
assert interpolation_search(data, 150) == 14
assert interpolation_search(data, 99) == -1

data_dup = [5, 10, 10, 10, 20, 20, 30, 30, 30, 30, 40, 50]
assert interpolation_search_all(data_dup, 10) == [1, 2, 3]
assert interpolation_search_all(data_dup, 30) == [6, 7, 8, 9]
assert interpolation_search_all(data_dup, 25) == []

assert interpolation_insert_pos(data, 55) == 5
assert interpolation_insert_pos(data, 5) == 0
assert interpolation_insert_pos(data, 200) == 15
