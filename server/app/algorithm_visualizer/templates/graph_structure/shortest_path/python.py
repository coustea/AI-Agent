import heapq


def dijkstra(graph, source, num_nodes):
    """Dijkstra：每次确定当前距离最短的未完成节点。"""
    distance = [float('inf')] * num_nodes
    distance[source] = 0
    visited = set()
    queue = [(0, source)]

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
