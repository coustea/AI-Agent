def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

# 定义 merge 函数
def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

# 定义 merge_sort_inplace 函数
def merge_sort_inplace(arr, temp, left, right):
    if left >= right:
        return
    mid = (left + right) // 2
    merge_sort_inplace(arr, temp, left, mid)
    merge_sort_inplace(arr, temp, mid + 1, right)
    merge_inplace(arr, temp, left, mid, right)

# 定义 merge_inplace 函数
def merge_inplace(arr, temp, left, mid, right):
    for k in range(left, right + 1):
        temp[k] = arr[k]
    i, j = left, mid + 1
    for k in range(left, right + 1):
        if i > mid:
            arr[k] = temp[j]
            j += 1
        elif j > right:
            arr[k] = temp[i]
            i += 1
        elif temp[i] <= temp[j]:
            arr[k] = temp[i]
            i += 1
        else:
            arr[k] = temp[j]
            j += 1

# 定义 count_inversions 函数
def count_inversions(arr):
# 定义 sort_count 函数
    def sort_count(arr):
        if len(arr) <= 1:
            return arr, 0
        mid = len(arr) // 2
        left, inv_l = sort_count(arr[:mid])
        right, inv_r = sort_count(arr[mid:])
        merged, inv_m = merge_count(left, right)
        return merged, inv_l + inv_r + inv_m

# 定义 merge_count 函数
    def merge_count(left, right):
        result = []
        i = j = inv = 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                inv += len(left) - i
                j += 1
        result.extend(left[i:])
        result.extend(right[j:])
        return result, inv

    _, inversions = sort_count(arr)
    return inversions

datasets = [
    [89, 45, 23, 78, 12, 56, 91, 34, 67, 3, 88, 15, 72, 41, 60],
    [5, -3, 8, -1, 0, 7, -4, 2, 9, -6, 1, -8, 3, -2, 6],
    [42, 42, 17, 17, 63, 63, 8, 8, 91, 91, 25, 25, 56, 56, 34],
    [99, 88, 77, 66, 55, 44, 33, 22, 11, 1, 2, 3, 4, 5, 6, 7],
]

for data in datasets:
    r1 = merge_sort(data[:])
    temp = [0] * len(data)
    arr_copy = data[:]
    merge_sort_inplace(arr_copy, temp, 0, len(arr_copy) - 1)
    assert r1 == arr_copy == sorted(data)
    inv = count_inversions(data[:])
