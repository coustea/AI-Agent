from visual_tracer import GraphTracer
tracer = GraphTracer()

"""
# shortest_path 算法实现 — domain: graph_structure
Dijkstra 最短路径算法 — 带权有向图
=====================================
核心思想：贪心策略，每次从优先队列中取出当前距离最小的未访问节点，
         对其所有出边执行松弛操作（relaxation）。

时间复杂度：O((V + E) log V)，其中 V 为节点数，E 为边数。
           使用二叉堆（heapq）实现优先队列，每次取最小值 O(log V)，
           每条边最多触发一次松弛入队 O(E log V)，合计 O((V+E) log V)。

空间复杂度：O(V + E)，存储距离表、前驱表和优先队列。

性质：
  1. 仅适用于非负权边（负权边会导致贪心选择失效）。
  2. 每个节点最多被"确定"一次（取出时距离已是最优）。
  3. 优先队列中可能存在同一节点的多个距离副本，通过
     curr_dist > distances[u] 判断跳过已过时条目。
"""

import heapq


def _build_graph_nodes(graph, num_nodes):
    """将图转换为可视化节点列表"""
    nodes = []
    for i in range(num_nodes):
        node_data = {"id": str(i), "label": str(i)}
        node_edges = []
        for v, w in graph.get(i, []):
            node_edges.append({"to": str(v), "label": str(w)})
        node_data["edges"] = node_edges
        nodes.append(node_data)
    return nodes


def dijkstra(graph, source, num_nodes):
    """Dijkstra 最短路径算法，返回距离表和前驱表。

    Args:
        graph: 邻接表，格式 {u: [(v, weight), ...]}
        source: 源节点编号
        num_nodes: 节点总数

    Returns:
        distances: 各节点到源的最短距离（不可达为 inf）
        predecessors: 最短路径前驱表（用于路径重建）
    """
    # 初始化图可视化
    nodes = _build_graph_nodes(graph, num_nodes)
    tracer.init_graph(nodes, line=24)

    distances = {i: float('inf') for i in range(num_nodes)}
    distances[source] = 0

    tracer.visit_node(str(source), line=38)

    predecessors = {i: None for i in range(num_nodes)}

    pq = [(0, source)]

    while pq:
        curr_dist, u = heapq.heappop(pq)

        tracer.move_pointer({"curr": u, "dist": curr_dist}, line=45)
        tracer.visit_node(str(u), line=45)

        if curr_dist > distances[u]:
            continue

        for v, weight in graph.get(u, []):
            tracer.move_pointer({"edge": f"{u}->{v}"}, line=50)
            tracer.visit_node(str(v), line=50)
            new_dist = curr_dist + weight

            if new_dist < distances[v]:
                tracer.highlight(int(str(v)), tone="active", line=53)
                distances[v] = new_dist
                predecessors[v] = u
                heapq.heappush(pq, (new_dist, v))
                tracer.visit_node(str(v), line=56)
                tracer.clear_highlights(line=56)

    tracer.finish(line=62)
    unreachable = [i for i in range(num_nodes) if distances[i] == float('inf')]
    if unreachable:
        pass

    return distances, predecessors


def reconstruct_path(predecessors, source, target):
    """根据前驱表重建从 source 到 target 的最短路径。"""
    if predecessors[target] is None and target != source:
        return []

    path = []
    node = target
    tracer.visit_node(str(node), line=73)
    while node is not None:
        tracer.visit_node(str(node), line=73)
        path.append(node)
        node = predecessors[node]
    path.reverse()
    tracer.finish(line=76)
    return path