def bfs(graph, start):
    visited = {start}
    queue = [start]
    res = []
    
    while queue:
        node = queue.pop(0)
        res.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return res

graph = {
    0: [1, 2],
    1: [0, 3],
    2: [0, 3, 4],
    3: [1, 2, 5],
    4: [2],
    5: [3]
}
bfs(graph, 0)
