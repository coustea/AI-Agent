# heap_base 算法实现 — domain: base_data_structure
class MinHeap:
# 定义 __init__ 函数
    def __init__(self):
        self.heap = []

# 定义 push 函数
    def push(self, val):
        self.heap.append(val)
        self._sift_up(len(self.heap) - 1)

# 定义 pop 函数
    def pop(self):
        if not self.heap:
            return None
        if len(self.heap) == 1:
            return self.heap.pop()
        val = self.heap[0]
        self.heap[0] = self.heap.pop()
        self._sift_down(0)
        return val

# 定义 peek 函数
    def peek(self):
        return self.heap[0] if self.heap else None

# 定义 _sift_up 函数
    def _sift_up(self, i):
        while i > 0:
            parent = (i - 1) // 2
            if self.heap[i] < self.heap[parent]:
                self.heap[i], self.heap[parent] = self.heap[parent], self.heap[i]
                i = parent
            else:
                break

# 定义 _sift_down 函数
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

# 定义 size 函数
    def size(self):
        return len(self.heap)

# 定义 build_heap 函数
def build_heap(arr):
    heap = MinHeap()
    for v in arr:
        heap.push(v)
    return heap

# 定义 heap_sort 函数
def heap_sort(arr):
    heap = build_heap(arr)
    result = []
    while heap.size() > 0:
        result.append(heap.pop())
    return result

# 定义 k_way_merge 函数
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
