from visual_tracer import TreeTracer
tracer = TreeTracer()

def _build_heap_nodes(arr):
    nodes = []
    n = len(arr)
    for i in range(n):
        node_data = {"id": f"node-{i}", "label": str(arr[i])}
        children = []
        left, right = 2*i+1, 2*i+2
        if left < n:
            children.append(f"node-{left}")
        if right < n:
            children.append(f"node-{right}")
        if children:
            node_data["children"] = children
        nodes.append(node_data)
    return nodes

def heap_sort(arr):
    """堆排序"""
    if not arr:
        tracer.finish(line=1)
        return arr

    tracer.init_tree(_build_heap_nodes(arr), line=8)
    n = len(arr)

    # 建堆
    for i in range(n//2 - 1, -1, -1):
        tracer.visit_node(f"node-{i}", line=12)

    # 排序
    for i in range(n-1, 0, -1):
        tracer.visit_node(f"node-0", line=16)
        tracer.visit_node(f"node-{i}", line=17)

    tracer.finish(line=20)
    return arr
