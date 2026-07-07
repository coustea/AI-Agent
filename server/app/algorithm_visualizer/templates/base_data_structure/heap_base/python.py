def heap_operations():
    # Minimum heap simulation
    heap = []
    
    def push(val):
        heap.append(val)
        up(len(heap) - 1)
        
    def up(i):
        while i > 0:
            parent = (i - 1) // 2
            if heap[i] < heap[parent]:
                heap[i], heap[parent] = heap[parent], heap[i]
                i = parent
            else:
                break
                
    push(5)
    push(3)
    push(8)
    push(1)
    push(2)
    return heap

heap_operations()
