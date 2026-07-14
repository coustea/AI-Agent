from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def fibonacci_search(arr, target):
    tracer.init_array(arr, line=1)
    n = len(arr)
    if n == 0:
        tracer.finish(line=3)
        return -1
    fib = [0, 1]
    tracer.init_array(fib, line=5)
    while fib[-1] < n:
        fib.append(fib[-1] + fib[-2])
        tracer.init_array(fib, line=7)
    k = len(fib) - 1
    padded = arr + [arr[-1]] * (fib[k] - n)
    offset = -1

    while fib[k] > 1:
        i = min(offset + fib[k - 2], n - 1)
        tracer.move_pointer({"i": i, "offset": offset}, line=12)
        tracer.compare(i, i, line=13)
        if padded[i] < target:
            k = k - 1
            offset = i
        elif padded[i] > target:
            k = k - 2
        else:
            tracer.mark_sorted(i, line=19)
            tracer.finish(line=19)
            return i

    tracer.move_pointer({"check": offset + 1}, line=20)
    if fib[k - 1] and padded[offset + 1] == target:
        tracer.mark_sorted(offset + 1, line=21)
        tracer.finish(line=21)
        return offset + 1
    tracer.finish(line=22)
    return -1

# 定义 fibonacci_search_range 函数
def fibonacci_search_range(arr, target):
    tracer.init_array(arr, line=24)
    idx = fibonacci_search(arr, target)
    if idx == -1:
        tracer.finish(line=28)
        return -1, -1
    left = idx
    while left > 0 and arr[left - 1] == target:
        tracer.move_pointer({"left": left}, line=30)
        left -= 1
    right = idx
    while right < len(arr) - 1 and arr[right + 1] == target:
        tracer.move_pointer({"right": right}, line=33)
        right += 1
    for i in range(left, right + 1):
        tracer.mark_sorted(i, line=35)
    tracer.finish(line=35)
    return left, right

# 定义 build_fibonacci_sequence 函数
def build_fibonacci_sequence(n):
    if n <= 0:
        tracer.init_array([0], line=38)
        tracer.finish(line=39)
        return [0]
    if n == 1:
        tracer.init_array([0, 1], line=41)
        tracer.finish(line=42)
        return [0, 1]
    fib = [0, 1]
    tracer.init_array(fib, line=43)
    for i in range(2, n + 1):
        fib.append(fib[-1] + fib[-2])
        tracer.init_array(fib, line=45)
    tracer.finish(line=45)
    return fib
