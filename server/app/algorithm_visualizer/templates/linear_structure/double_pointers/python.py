# double_pointers 算法实现 — domain: linear_structure
def two_sum_sorted(arr, target):
    n = len(arr)
    if n < 2:
        return None
    left = 0
    right = n - 1
    while left < right:
        current_sum = arr[left] + arr[right]
        if current_sum == target:
            return (left, right)
        elif current_sum < target:
            left += 1
        else:
            right -= 1
    return None

# 定义 two_sum_all_pairs 函数
def two_sum_all_pairs(arr, target):
    n = len(arr)
    if n < 2:
        return []
    left = 0
    right = n - 1
    pairs = []
    while left < right:
        current_sum = arr[left] + arr[right]
        if current_sum == target:
            pairs.append((left, right))
            left += 1
            right -= 1
        elif current_sum < target:
            left += 1
        else:
            right -= 1
    return pairs

# 定义 reverse_in_range 函数
def reverse_in_range(arr, start, end):
    if start < 0 or end >= len(arr) or start >= end:
        return arr
    left = start
    right = end
    while left < right:
        arr[left], arr[right] = arr[right], arr[left]
        left += 1
        right -= 1
    return arr

# 定义 three_sum_sorted 函数
def three_sum_sorted(arr, target):
    n = len(arr)
    if n < 3:
        return []
    result = []
    for i in range(n - 2):
        if i > 0 and arr[i] == arr[i - 1]:
            continue
        left, right = i + 1, n - 1
        while left < right:
            s = arr[i] + arr[left] + arr[right]
            if s == target:
                result.append((arr[i], arr[left], arr[right]))
                left += 1
                right -= 1
                while left < right and arr[left] == arr[left - 1]:
                    left += 1
                while left < right and arr[right] == arr[right + 1]:
                    right -= 1
            elif s < target:
                left += 1
            else:
                right -= 1
    return result

# 定义 remove_duplicates_sorted 函数
def remove_duplicates_sorted(arr):
    if not arr:
        return []
    slow = 0
    for fast in range(1, len(arr)):
        if arr[fast] != arr[slow]:
            slow += 1
            arr[slow] = arr[fast]
    return arr[:slow + 1]

data = [-4, -1, 0, 3, 5, 9, 12, 15, 18, 20, 23, 27]
assert two_sum_sorted(data, 30) is not None
assert two_sum_sorted(data, 100) is None

pairs = two_sum_all_pairs(data, 23)
assert len(pairs) >= 1

assert reverse_in_range(data[:], 2, 9)[2] == data[9]

triplets = three_sum_sorted(data, 14)
assert isinstance(triplets, list)

dup_data = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]
assert remove_duplicates_sorted(dup_data) == [1, 2, 3, 4, 5]
