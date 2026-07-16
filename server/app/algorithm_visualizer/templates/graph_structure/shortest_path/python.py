import heapq


def _build_weighted_graph(num_nodes, edges):
    """从节点数和加权边列表构建有向图邻接表。"""
    graph = {i: [] for i in range(num_nodes)}
    for edge in edges:
        u, v, w = edge[0], edge[1], edge[2]
        graph[u].append((v, w))
    return graph


def dijkstra(num_nodes, edges, start=0):
    """Dijkstra：每次确定当前距离最短的未完成节点。"""
    graph = _build_weighted_graph(num_nodes, edges)
    distance = [float('inf')] * num_nodes
    distance[start] = 0
    visited = set()
    queue = [(0, start)]

    while queue:
        current_distance, node = heapq.heappop(queue)
        if node in visited:
            continue
        visited.add(node)
        for neighbor, weight in graph[node]:
            candidate = current_distance + weight
            if candidate < distance[neighbor]:
                distance[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))
    return distance
