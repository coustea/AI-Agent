# heap_tree 算法实现 — domain: tree_structure
def max_heapify(arr, n, i):
    """下沉调整 (sift down) — 维护最大堆性质
    比较节点 i 与其左右子节点，将最大值交换到父位置
    递归调整被交换的子树，时间复杂度: O(log n)"""
    largest = i
    left = 2 * i + 1
    right = 2 * i + 2
    if left < n and arr[left] > arr[largest]:
        largest = left
    if right < n and arr[right] > arr[largest]:
        largest = right
    if largest != i:
        arr[i], arr[largest] = arr[largest], arr[i]
        max_heapify(arr, n, largest)


def build_max_heap(arr):
    """自底向上建堆 — 从最后一个非叶子节点开始逐个下沉
    最后非叶子节点索引: n//2 - 1
    时间复杂度: O(n)，而非直觉的 O(n log n)"""
    n = len(arr)
    if n <= 1:
        return
    for i in range(n // 2 - 1, -1, -1):
        max_heapify(arr, n, i)


def heap_push(arr, val):
    """向最大堆中插入元素 — 上浮调整 (sift up)
    新元素加到末尾，逐步与父节点比较并交换
    时间复杂度: O(log n)"""
    arr.append(val)
    i = len(arr) - 1
    while i > 0:
        parent = (i - 1) // 2
        if arr[i] > arr[parent]:
            arr[i], arr[parent] = arr[parent], arr[i]
            i = parent
        else:
            break


def heap_pop(arr):
    """提取最大值 — 交换根与末尾，删除末尾，下沉调整根
    时间复杂度: O(log n)"""
    if not arr:
        return None
    if len(arr) == 1:
        return arr.pop()
    max_val = arr[0]
    arr[0] = arr.pop()
    max_heapify(arr, len(arr), 0)
    return max_val


def heap_sort(arr):
    """堆排序 — 建堆后逐个提取最大值放到末尾
    原地排序，时间复杂度: O(n log n)，空间复杂度: O(1)
    不稳定排序"""
    n = len(arr)
    if n <= 1:
        return arr
    build_max_heap(arr)
    for i in range(n - 1, 0, -1):
        arr[0], arr[i] = arr[i], arr[0]
        max_heapify(arr, i, 0)
    return arr


data = [4, 10, 3, 5, 15, 2, 8, 12, 1, 6]

heap = list(data)
build_max_heap(heap)

heap_push(heap, 20)
heap_push(heap, 9)

max1 = heap_pop(heap)
max2 = heap_pop(heap)

sorted_arr = heap_sort(list(data))
