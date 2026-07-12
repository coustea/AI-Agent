def radix_sort(arr):
    if not arr:
        return arr
    max_val = max(arr)
    if max_val < 0:
        raise ValueError("radix sort does not support negative numbers")
    exp = 1
    while max_val // exp > 0:
        arr = counting_sort_by_digit(arr, exp)
        exp *= 10
    return arr

# 定义 counting_sort_by_digit 函数
def counting_sort_by_digit(arr, exp):
    n = len(arr)
    output = [0] * n
    count = [0] * 10
    for i in range(n):
        digit = (arr[i] // exp) % 10
        count[digit] += 1
    for i in range(1, 10):
        count[i] += count[i - 1]
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
    while max_val > 0:
        digits += 1
        max_val //= 10
    return digits
