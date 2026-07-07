def heap_sort(arr):
    n = len(arr)
    
    def heapify(n, i):
        largest = i
        l = 2 * i + 1
        r = 2 * i + 2
        if l < n and arr[l] > arr[largest]:
            largest = l
        if r < n and arr[r] > arr[largest]:
            largest = r
        if largest != i:
            arr[i], arr[largest] = arr[largest], arr[i]
            heapify(n, largest)
            
    # Build max heap
    for i in range(n // 2 - 1, -1, -1):
        heapify(n, i)
        
    # Extract elements
    for i in range(n - 1, 0, -1):
        arr[i], arr[0] = arr[0], arr[i]
        heapify(i, 0)
    return arr

heap_sort([4, 10, 3, 5, 1, 2])
