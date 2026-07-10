from visual_tracer import ArrayTracer

tracer = ArrayTracer()

# 定义 radix_sort 函数
def radix_sort(arr):
    if not arr:
        return arr
    tracer.init_array(arr, line=1)
    max_val = max(arr)
    if max_val < 0:
        raise ValueError("radix sort does not support negative numbers")
    exp = 1
# 循环条件判断
    while max_val // exp > 0:
        arr = counting_sort_by_digit(arr, exp)
# 循环遍历处理
        for i in range(len(arr)):
            tracer.assign(i, arr[i], line=9)
        exp *= 10
    tracer.finish(line=12)
    return arr

# 定义 counting_sort_by_digit 函数
def counting_sort_by_digit(arr, exp):
    n = len(arr)
    output = [0] * n
    count = [0] * 10
# 循环遍历处理
    for i in range(n):
        digit = (arr[i] // exp) % 10
        count[digit] += 1
# 循环遍历处理
    for i in range(1, 10):
        count[i] += count[i - 1]
# 循环遍历处理
    for i in range(n - 1, -1, -1):
        digit = (arr[i] // exp) % 10
        output[count[digit] - 1] = arr[i]
        count[digit] -= 1
    return output

# 定义 radix_sort_with_negatives 函数
def radix_sort_with_negatives(arr):
    if not arr:
        return arr
    neg = [-x for x in arr if x < 0]
    pos = [x for x in arr if x >= 0]
    if neg:
        neg = radix_sort(neg)
        neg = [-x for x in reversed(neg)]
    if pos:
        pos = radix_sort(pos)
    return neg + pos

# 定义 max_digit_count 函数
def max_digit_count(arr):
    if not arr:
        return 0
    max_val = max(abs(x) for x in arr)
    digits = 0
# 循环条件判断
    while max_val > 0:
        digits += 1
        max_val //= 10
    return digits

datasets = [
    [170, 45, 75, 90, 802, 24, 2, 66, 503, 31, 7, 128, 999, 4, 567],
    [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9],
    [100, 200, 300, 400, 500, 600, 700, 800, 900],
]

radix_sort(datasets[0][:])
# 循环遍历处理
for data in datasets[1:]:
    r1 = radix_sort(data[:])
    assert r1 == sorted(data)

mixed = [-5, 3, -1, 7, -8, 2, 0, -3, 9, -2, 4, -7, 1, -4, 6]
r2 = radix_sort_with_negatives(mixed[:])
assert r2 == sorted(mixed)
tracer.dump()
