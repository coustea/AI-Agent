from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def merge_sort(arr):
    tracer.init_array(arr, line=1)
    if len(arr) <= 1:
        tracer.finish(line=2)
        return arr
    mid = len(arr) // 2
    tracer.move_pointer({"mid": mid}, line=4)
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    result = merge(left, right)
    return result

# 定义 merge 函数
def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        tracer.compare(i, j, line=13)
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    tracer.init_array(result, line=20)
    tracer.finish(line=21)
    return result

# 定义 merge_sort_inplace 函数
def merge_sort_inplace(arr, temp, left, right):
    tracer.init_array(arr, line=24)
    if left >= right:
        tracer.finish(line=25)
        return
    mid = (left + right) // 2
    tracer.move_pointer({"mid": mid}, line=27)
    merge_sort_inplace(arr, temp, left, mid)
    merge_sort_inplace(arr, temp, mid + 1, right)
    merge_inplace(arr, temp, left, mid, right)

# 定义 merge_inplace 函数
def merge_inplace(arr, temp, left, mid, right):
    for k in range(left, right + 1):
        temp[k] = arr[k]
    i, j = left, mid + 1
    tracer.move_pointer({"i": i, "j": j}, line=37)
    for k in range(left, right + 1):
        if i > mid:
            arr[k] = temp[j]
            tracer.assign(k, temp[j], line=40)
            j += 1
        elif j > right:
            arr[k] = temp[i]
            tracer.assign(k, temp[i], line=43)
            i += 1
        elif temp[i] <= temp[j]:
            tracer.compare(i, j, line=45)
            arr[k] = temp[i]
            tracer.assign(k, temp[i], line=46)
            i += 1
        else:
            tracer.compare(i, j, line=48)
            arr[k] = temp[j]
            tracer.assign(k, temp[j], line=49)
            j += 1
    tracer.finish(line=50)

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
        tracer.init_array(left + right, line=65)
        while i < len(left) and j < len(right):
            tracer.compare(i, j, line=68)
            if left[i] <= right[j]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                inv += len(left) - i
                j += 1
        result.extend(left[i:])
        result.extend(right[j:])
        tracer.finish(line=75)
        return result, inv

    _, inversions = sort_count(arr)
    return inversions

# 定义 merge_sort_wrapper 函数
def merge_sort_wrapper(arr):
    temp = [0] * len(arr)
    merge_sort_inplace(arr, temp, 0, len(arr) - 1)
    tracer.finish(line=86)
    return arr
