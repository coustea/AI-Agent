from visual_tracer import ArrayTracer

tracer = ArrayTracer()

def fibonacci_search(arr, target):
    n = len(arr)
    if n == 0:
        return -1
    fib = [0, 1]
    while fib[-1] < n:
        fib.append(fib[-1] + fib[-2])
    k = len(fib) - 1
    padded = arr + [arr[-1]] * (fib[k] - n)
    tracer.init_array(arr, line=4)
    offset = -1
    tracer.move_pointer({"offset": -1, "k": k}, line=10)
    while fib[k] > 1:
        i = min(offset + fib[k - 2], n - 1)
        tracer.move_pointer({"offset": offset, "i": i, "k": k}, line=13)
        tracer.compare(i, i, line=14)
        if padded[i] < target:
            k = k - 1
            offset = i
            tracer.move_pointer({"offset": offset, "i": i, "k": k}, line=17)
        elif padded[i] > target:
            k = k - 2
            tracer.move_pointer({"offset": offset, "k": k}, line=20)
        else:
            tracer.finish(line=22)
            return i
    if fib[k - 1] and padded[offset + 1] == target:
        tracer.finish(line=24)
        return offset + 1
    tracer.finish(line=26)
    return -1

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
fibonacci_search(data, 27)
fibonacci_search(data, 3)
fibonacci_search(data, 51)
fibonacci_search(data, 99)

data_dup = [2, 5, 5, 5, 8, 8, 12, 12, 12, 12, 15, 20]
fibonacci_search_range(data_dup, 5)
fibonacci_search_range(data_dup, 12)
fibonacci_search_range(data_dup, 99)

build_fibonacci_sequence(15)
tracer.dump()
