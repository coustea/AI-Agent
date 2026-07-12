def heap_sort(arr):
    n = len(arr)
    if n <= 1:
        return arr
    for i in range(n // 2 - 1, -1, -1):
        heapify(arr, n, i)
    for i in range(n - 1, 0, -1):
        arr[0], arr[i] = arr[i], arr[0]
        heapify(arr, i, 0)
    return arr

# 定义 heapify 函数
def heapify(arr, n, i):
    largest = i
    left = 2 * i + 1
    right = 2 * i + 2
    if left < n and arr[left] > arr[largest]:
        largest = left
    if right < n and arr[right] > arr[largest]:
        largest = right
    if largest != i:
        arr[i], arr[largest] = arr[largest], arr[i]
        heapify(arr, n, largest)

# 定义 heap_sort_min 函数
def heap_sort_min(arr):
    n = len(arr)
    if n <= 1:
        return arr
    for i in range(n // 2 - 1, -1, -1):
        heapify_min(arr, n, i)
    result = []
    for i in range(n - 1, -1, -1):
        result.append(arr[0])
        arr[0] = arr[i]
        heapify_min(arr, i, 0)
    return result

# 定义 heapify_min 函数
def heapify_min(arr, n, i):
    smallest = i
    left = 2 * i + 1
    right = 2 * i + 2
    if left < n and arr[left] < arr[smallest]:
        smallest = left
    if right < n and arr[right] < arr[smallest]:
        smallest = right
    if smallest != i:
        arr[i], arr[smallest] = arr[smallest], arr[i]
        heapify_min(arr, n, smallest)

# 定义 kth_largest 函数
def kth_largest(arr, k):
    n = len(arr)
    for i in range(n // 2 - 1, -1, -1):
        heapify(arr, n, i)
    for i in range(k - 1):
        arr[0], arr[n - 1 - i] = arr[n - 1 - i], arr[0]
        heapify(arr, n - 1 - i, 0)
    return arr[0]
