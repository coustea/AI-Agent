def dijkstra(graph, start, num_nodes):
    import heapq
    distances = {i: float('inf') for i in range(num_nodes)}
    distances[start] = 0
    pq = [(0, start)] # (distance, node)
    
    while pq:
        curr_dist, u = heapq.heappop(pq)
        if curr_dist > distances[u]:
            continue
        for v, weight in graph.get(u, []):
            dist = curr_dist + weight
            if dist < distances[v]:
                distances[v] = dist
                heapq.heappush(pq, (dist, v))
    return distances

graph = {
    0: [(1, 4), (2, 1)],
    1: [(3, 1)],
    2: [(1, 2), (3, 5)],
    3: []
}
dijkstra(graph, 0, 4)
