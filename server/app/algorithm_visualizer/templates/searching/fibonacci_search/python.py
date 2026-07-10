def fibonacci_search(arr, target):
    n = len(arr)
    if n == 0:
        return -1
    fib = [0, 1]
    while fib[-1] < n:
        fib.append(fib[-1] + fib[-2])
    k = len(fib) - 1
    padded = arr + [arr[-1]] * (fib[k] - n)
    offset = -1
    while fib[k] > 1:
        i = min(offset + fib[k - 2], n - 1)
        if padded[i] < target:
            k = k - 1
            offset = i
        elif padded[i] > target:
            k = k - 2
        else:
            return i
    if fib[k - 1] and padded[offset + 1] == target:
        return offset + 1
    return -1

# 定义 fibonacci_search_range 函数
def fibonacci_search_range(arr, target):
    idx = fibonacci_search(arr, target)
    if idx == -1:
        return -1, -1
    left = idx
    while left > 0 and arr[left - 1] == target:
        left -= 1
    right = idx
    while right < len(arr) - 1 and arr[right + 1] == target:
        right += 1
    return left, right

# 定义 build_fibonacci_sequence 函数
def build_fibonacci_sequence(n):
    if n <= 0:
        return [0]
    if n == 1:
        return [0, 1]
    fib = [0, 1]
    for i in range(2, n + 1):
        fib.append(fib[-1] + fib[-2])
    return fib

data = [3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51]
assert fibonacci_search(data, 27) == 6
assert fibonacci_search(data, 3) == 0
assert fibonacci_search(data, 51) == 12
assert fibonacci_search(data, 99) == -1

data_dup = [2, 5, 5, 5, 8, 8, 12, 12, 12, 12, 15, 20]
assert fibonacci_search_range(data_dup, 5) == (1, 3)
assert fibonacci_search_range(data_dup, 12) == (6, 9)
assert fibonacci_search_range(data_dup, 99) == (-1, -1)

fib_seq = build_fibonacci_sequence(15)
assert len(fib_seq) == 16
