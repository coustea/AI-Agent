from visual_tracer import ArrayTracer

tracer = ArrayTracer()

class MinHeap:
    def __init__(self):
        self.heap = []

    def push(self, val):
        self.heap.append(val)
        self._sift_up(len(self.heap) - 1)

    def pop(self):
        if not self.heap:
            return None
        if len(self.heap) == 1:
            return self.heap.pop()
        val = self.heap[0]
        self.heap[0] = self.heap.pop()
        self._sift_down(0)
        return val

    def peek(self):
        return self.heap[0] if self.heap else None

    def _sift_up(self, i):
        tracer.init_array(self.heap, line=16)
        while i > 0:
            parent = (i - 1) // 2
            tracer.compare(i, parent, line=19)
            if self.heap[i] < self.heap[parent]:
                self.heap[i], self.heap[parent] = self.heap[parent], self.heap[i]
                tracer.swap(i, parent, line=22)
                i = parent
            else:
                break
        tracer.finish(line=26)

    def _sift_down(self, i):
        n = len(self.heap)
        while True:
            smallest = i
            left = 2 * i + 1
            right = 2 * i + 2
            if left < n and self.heap[left] < self.heap[smallest]:
                smallest = left
            if right < n and self.heap[right] < self.heap[smallest]:
                smallest = right
            if smallest == i:
                break
            self.heap[i], self.heap[smallest] = self.heap[smallest], self.heap[i]
            i = smallest

    def size(self):
        return len(self.heap)

def build_heap(arr):
    heap = MinHeap()
    for v in arr:
        heap.push(v)
    return heap

def heap_sort(arr):
    heap = build_heap(arr)
    result = []
    while heap.size() > 0:
        result.append(heap.pop())
    return result

def k_way_merge(arrays):
    import heapq
    heap = []
    for arr_idx, arr in enumerate(arrays):
        if arr:
            heapq.heappush(heap, (arr[0], arr_idx, 0))
    result = []
    while heap:
        val, arr_idx, elem_idx = heapq.heappop(heap)
        result.append(val)
        if elem_idx + 1 < len(arrays[arr_idx]):
            heapq.heappush(heap, (arrays[arr_idx][elem_idx + 1], arr_idx, elem_idx + 1))
    return result

data = [89, 45, 23, 78, 12, 56, 91, 34, 67, 3]
heap = build_heap(data)
sorted_data = heap_sort(data)
assert sorted_data == sorted(data)

arrays = [[1, 4, 7, 10], [2, 5, 8, 11], [3, 6, 9, 12]]
merged = k_way_merge(arrays)
assert merged == list(range(1, 13))
tracer.dump()
