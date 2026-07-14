from collections import deque


def bfs_all_components(graph):
    """广度优先搜索：从每个未访问节点向外逐层扩展。"""
    visited = set()
    order = []
    for start in graph:
        if start in visited:
            continue
        queue = deque([start])
        visited.add(start)
        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in graph[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
    return order
