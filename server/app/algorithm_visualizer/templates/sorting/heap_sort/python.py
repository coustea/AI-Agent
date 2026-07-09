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

def kth_largest(arr, k):
    n = len(arr)
    for i in range(n // 2 - 1, -1, -1):
        heapify(arr, n, i)
    for i in range(k - 1):
        arr[0], arr[n - 1 - i] = arr[n - 1 - i], arr[0]
        heapify(arr, n - 1 - i, 0)
    return arr[0]

datasets = [
    [89, 45, 23, 78, 12, 56, 91, 34, 67, 3, 88, 15, 72, 41, 60],
    [5, -3, 8, -1, 0, 7, -4, 2, 9, -6, 1, -8, 3, -2, 6],
    [42, 42, 17, 17, 63, 63, 8, 8, 91, 91, 25, 25, 56, 56, 34],
]

for data in datasets:
    r1 = heap_sort(data[:])
    assert r1 == sorted(data)
    r2 = heap_sort_min(data[:])
    assert r2 == sorted(data)
    k3 = kth_largest(data[:], 3)
    expected3 = sorted(data, reverse=True)[2]
    assert k3 == expected3
