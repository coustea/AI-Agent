from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def radix_sort(arr):
    tracer.init_array(arr, line=1)
    if not arr:
        tracer.finish(line=2)
        return arr
    max_val = max(arr)
    if max_val < 0:
        raise ValueError("radix sort does not support negative numbers")
    exp = 1
    while max_val // exp > 0:
        tracer.move_pointer({"exp": exp}, line=8)
        arr = counting_sort_by_digit(arr, exp)
        tracer.init_array(arr, line=9)
        exp *= 10
    for i in range(len(arr)):
        tracer.mark_sorted(i, line=11)
    tracer.finish(line=11)
    return arr

# 定义 counting_sort_by_digit 函数
def counting_sort_by_digit(arr, exp):
    n = len(arr)
    output = [0] * n
    count = [0] * 10
    tracer.init_array(count, line=17)

    for i in range(n):
        tracer.move_pointer({"i": i}, line=18)
        digit = (arr[i] // exp) % 10
        count[digit] += 1
        tracer.assign(digit, count[digit], line=20)

    for i in range(1, 10):
        count[i] += count[i - 1]
        tracer.assign(i, count[i], line=22)

    for i in range(n - 1, -1, -1):
        tracer.move_pointer({"i": i}, line=23)
        digit = (arr[i] // exp) % 10
        output[count[digit] - 1] = arr[i]
        count[digit] -= 1

    return output

# 定义 radix_sort_with_negatives 函数
def radix_sort_with_negatives(arr):
    tracer.init_array(arr, line=29)
    if not arr:
        tracer.finish(line=31)
        return arr
    neg = [-x for x in arr if x < 0]
    pos = [x for x in arr if x >= 0]
    if neg:
        neg = radix_sort(neg)
        neg = [-x for x in reversed(neg)]
    if pos:
        pos = radix_sort(pos)
    result = neg + pos
    tracer.init_array(result, line=40)
    for i in range(len(result)):
        tracer.mark_sorted(i, line=40)
    tracer.finish(line=40)
    return result

# 定义 max_digit_count 函数
def max_digit_count(arr):
    tracer.init_array(arr, line=42)
    if not arr:
        tracer.finish(line=45)
        return 0
    max_val = max(abs(x) for x in arr)
    digits = 0
    while max_val > 0:
        tracer.move_pointer({"digits": digits}, line=48)
        digits += 1
        max_val //= 10
    tracer.finish(line=50)
    return digits
