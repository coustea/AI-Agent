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
