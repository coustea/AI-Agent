from visual_tracer import GraphTracer
import heapq

tracer = GraphTracer()

def dijkstra(graph, source, num_nodes):
    """Dijkstra 最短路径算法，返回距离表和前驱表。"""

    labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    nodes = []
    for node_id in range(num_nodes):
        node_edges = [{"to": str(v), "weight": w} for v, w in graph.get(node_id, [])]
        nodes.append({"id": str(node_id), "label": labels[node_id], "edges": node_edges})
    tracer.init_graph(nodes, line=38)

    distances = {i: float('inf') for i in range(num_nodes)}
    distances[source] = 0
    predecessors = {i: None for i in range(num_nodes)}

    pq = [(0, source)]
    tracer.visit_node(str(source), line=39)

    while pq:
        curr_dist, u = heapq.heappop(pq)

        if curr_dist > distances[u]:
            continue

        tracer.visit_node(str(u), line=51)

        for v, weight in graph.get(u, []):
            new_dist = curr_dist + weight

            if new_dist < distances[v]:
                distances[v] = new_dist
                predecessors[v] = u
                heapq.heappush(pq, (new_dist, v))
                tracer.visit_node(str(v), line=64)

    unreachable = [i for i in range(num_nodes) if distances[i] == float('inf')]
    if unreachable:
        print(f"不可达节点: {unreachable}")

    tracer.finish(line=74)
    return distances, predecessors


def reconstruct_path(predecessors, source, target):
    """根据前驱表重建从 source 到 target 的最短路径。"""
    if predecessors[target] is None and target != source:
        return []

    path = []
    node = target
    while node is not None:
        path.append(node)
        node = predecessors[node]
    path.reverse()
    return path


graph = {
    0: [(1, 2), (2, 6)],
    1: [(3, 5)],
    2: [(3, 2), (4, 3)],
    3: [(5, 1)],
    4: [(5, 4), (6, 2)],
    5: [(6, 3)],
    6: [],
}

distances, predecessors = dijkstra(graph, 0, 7)

labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
print("最短距离:")
for i in range(7):
    d = distances[i]
    d_str = str(d) if d != float('inf') else "∞"
    print(f"  {labels[i]}({i}): {d_str}")

print("\n最短路径:")
for i in range(7):
    path = reconstruct_path(predecessors, 0, i)
    if path:
        path_str = " -> ".join(f"{labels[n]}({n})" for n in path)
        print(f"  A(0) -> {labels[i]}({i}): {path_str}, 距离={distances[i]}")
    else:
        print(f"  A(0) -> {labels[i]}({i}): 不可达")

tracer.dump()
