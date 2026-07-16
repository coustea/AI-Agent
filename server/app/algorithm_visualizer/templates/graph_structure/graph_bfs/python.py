from collections import deque


def _build_undirected_graph(num_nodes, edges):
    """从节点数和边列表构建无向图邻接表。"""
    graph = {i: [] for i in range(num_nodes)}
    for edge in edges:
        u, v = edge[0], edge[1]
        graph[u].append(v)
        graph[v].append(u)
    return graph


def bfs_all_components(num_nodes, edges, start=0):
    """广度优先搜索：从每个未访问节点向外逐层扩展。"""
    graph = _build_undirected_graph(num_nodes, edges)
    visited = set()
    order = []
    for node in graph:
        if node in visited:
            continue
        queue = deque([node])
        visited.add(node)
        while queue:
            current = queue.popleft()
            order.append(current)
            for neighbor in graph[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
    return order
