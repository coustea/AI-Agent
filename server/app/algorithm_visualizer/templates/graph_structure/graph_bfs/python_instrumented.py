from visual_tracer import GraphTracer

tracer = GraphTracer()

graph = {
    0: [1, 2, 3],
    1: [0, 4],
    2: [0, 4, 5],
    3: [0, 5],
    4: [1, 2, 6],
    5: [2, 3, 6],
    6: [4, 5],
    7: []
}

labels = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E", 5: "F", 6: "G", 7: "H"}

nodes = []
for node_id in sorted(graph.keys()):
    node_edges = [{"to": str(neighbor)} for neighbor in graph[node_id]]
    nodes.append({"id": str(node_id), "label": labels[node_id], "edges": node_edges})
tracer.init_graph(nodes, line=28)


def bfs(graph, start, visited, distance, parent):
    """BFS 核心函数 —— 对应 python.py 第 44 行"""
    visited.add(start)
    distance[start] = 0
    parent[start] = -1
    tracer.visit_node(str(start), line=46)

    queue = [start]
    order = []

    while queue:
        node = queue.pop(0)
        order.append(node)
        tracer.visit_node(str(node), line=55)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                distance[neighbor] = distance[node] + 1
                parent[neighbor] = node
                queue.append(neighbor)
                tracer.visit_node(str(neighbor), line=62)

    return order


def bfs_all_components(graph):
    """对图执行完整 BFS，处理所有连通分量 —— 对应 python.py 第 72 行"""
    visited = set()
    distance = {}
    parent = {}
    components = []

    for node in graph:
        if node not in visited:
            component = bfs(graph, node, visited, distance, parent)
            components.append(component)

    return components, distance, parent


components, distance, parent = bfs_all_components(graph)

print(f"连通分量数量: {len(components)}")
for i, comp in enumerate(components):
    labels_str = ", ".join(labels[n] for n in comp)
    print(f"  分量 {i + 1}: [{labels_str}] (节点编号: {comp})")

print("\n节点距离与前驱信息:")
for node in sorted(graph.keys()):
    p = labels.get(parent[node], "无") if parent.get(node) is not None else "无"
    if parent.get(node) == -1:
        p = "无（起始节点）"
    print(f"  节点 {labels[node]}({node}): 距离={distance[node]}, 前驱={p}")

print("\nBFS 层级结构（按距离分组）:")
max_dist = max(distance.values())
for d in range(max_dist + 1):
    level_nodes = [n for n in sorted(graph.keys()) if distance[n] == d]
    labels_str = ", ".join(labels[n] for n in level_nodes)
    print(f"  距离 {d}: [{labels_str}]")

tracer.finish(line=91)
tracer.dump()
