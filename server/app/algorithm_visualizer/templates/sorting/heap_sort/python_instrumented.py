from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def heap_sort(arr):
    tracer.init_array(arr, line=1)
    n = len(arr)
    if n <= 1:
        tracer.finish(line=3)
        return arr
    # 建堆阶段
    for i in range(n // 2 - 1, -1, -1):
        tracer.move_pointer({"build": i}, line=5)
        heapify(arr, n, i)
    # 排序阶段
    for i in range(n - 1, 0, -1):
        tracer.swap(0, i, line=8)
        arr[0], arr[i] = arr[i], arr[0]
        tracer.mark_sorted(i, line=8)
        heapify(arr, i, 0)
    tracer.mark_sorted(0, line=10)
    tracer.finish(line=10)
    return arr

# 定义 heapify 函数
def heapify(arr, n, i):
    largest = i
    left = 2 * i + 1
    right = 2 * i + 2
    tracer.move_pointer({"node": i}, line=14)
    if left < n:
        tracer.compare(left, largest, line=17)
        if arr[left] > arr[largest]:
            largest = left
    if right < n:
        tracer.compare(right, largest, line=19)
        if arr[right] > arr[largest]:
            largest = right
    if largest != i:
        tracer.swap(i, largest, line=22)
        arr[i], arr[largest] = arr[largest], arr[i]
        heapify(arr, n, largest)

# 定义 heap_sort_min 函数
def heap_sort_min(arr):
    tracer.init_array(arr, line=25)
    n = len(arr)
    if n <= 1:
        tracer.finish(line=28)
        return arr
    for i in range(n // 2 - 1, -1, -1):
        tracer.move_pointer({"build": i}, line=30)
        heapify_min(arr, n, i)
    result = []
    for i in range(n - 1, -1, -1):
        result.append(arr[0])
        tracer.mark_sorted(0, line=34)
        arr[0] = arr[i]
        heapify_min(arr, i, 0)
    tracer.finish(line=36)
    return result

# 定义 heapify_min 函数
def heapify_min(arr, n, i):
    smallest = i
    left = 2 * i + 1
    right = 2 * i + 2
    tracer.move_pointer({"node": i}, line=40)
    if left < n:
        tracer.compare(left, smallest, line=44)
        if arr[left] < arr[smallest]:
            smallest = left
    if right < n:
        tracer.compare(right, smallest, line=46)
        if arr[right] < arr[smallest]:
            smallest = right
    if smallest != i:
        tracer.swap(i, smallest, line=49)
        arr[i], arr[smallest] = arr[smallest], arr[i]
        heapify_min(arr, n, smallest)

# 定义 kth_largest 函数
def kth_largest(arr, k):
    tracer.init_array(arr, line=52)
    n = len(arr)
    for i in range(n // 2 - 1, -1, -1):
        heapify(arr, n, i)
    for i in range(k - 1):
        tracer.swap(0, n - 1 - i, line=58)
        arr[0], arr[n - 1 - i] = arr[n - 1 - i], arr[0]
        heapify(arr, n - 1 - i, 0)
    tracer.mark_sorted(0, line=60)
    tracer.finish(line=60)
    return arr[0]
