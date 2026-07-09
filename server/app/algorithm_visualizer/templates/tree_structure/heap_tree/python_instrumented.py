from visual_tracer import TreeTracer

tracer = TreeTracer()


def build_heap_nodes(arr):
    n = len(arr)
    nodes = []
    for i in range(n):
        nodes.append({"id": f"node-{i}", "label": str(arr[i]), "children": []})
    for i in range(n):
        left = 2 * i + 1
        right = 2 * i + 2
        if left < n:
            nodes[i]["children"].append(f"node-{left}")
        if right < n:
            nodes[i]["children"].append(f"node-{right}")
    return nodes


data = [4, 10, 3, 5, 15, 2, 8, 12, 1, 6]
heap = list(data)

nodes = build_heap_nodes(heap)
tracer.init_tree(nodes, line=62)

def max_heapify(arr, n, i):
    largest = i
    left = 2 * i + 1
    right = 2 * i + 2
    tracer.visit_node(f"node-{i}", line=7)
    if left < n and arr[left] > arr[largest]:
        largest = left
    if right < n and arr[right] > arr[largest]:
        largest = right
    if largest != i:
        arr[i], arr[largest] = arr[largest], arr[i]
        for idx in range(n):
            nodes[idx]["label"] = str(arr[idx])
        tracer.visit_node(f"node-{largest}", line=16)
        max_heapify(arr, n, largest)

def build_max_heap(arr):
    n = len(arr)
    if n <= 1:
        return
    for i in range(n // 2 - 1, -1, -1):
        max_heapify(arr, n, i)

build_max_heap(heap)

tracer.finish(line=65)
tracer.dump()
