from visual_tracer import TreeTracer
tracer = TreeTracer()

def _build_tree_nodes(arr):
    nodes = []
    n = len(arr)
    for i in range(n):
        if arr[i] is not None:
            node_data = {"id": f"node-{i}", "label": str(arr[i])}
            children = []
            left, right = 2*i+1, 2*i+2
            if left < n and arr[left] is not None:
                children.append(f"node-{left}")
            if right < n and arr[right] is not None:
                children.append(f"node-{right}")
            if children:
                node_data["children"] = children
            nodes.append(node_data)
    return nodes

def max_depth(arr):
    """二叉树最大深度"""
    if not arr:
        tracer.finish(line=1)
        return 0

    tracer.init_tree(_build_tree_nodes(arr), line=8)

    def dfs(i):
        if i >= len(arr) or arr[i] is None:
            return 0
        tracer.visit_node(f"node-{i}", line=12)
        return 1 + max(dfs(2*i+1), dfs(2*i+2))

    result = dfs(0)
    tracer.finish(line=15)
    return result
