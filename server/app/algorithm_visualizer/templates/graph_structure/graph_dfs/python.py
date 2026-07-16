def dfs_graph(num_nodes, edges, start=0):
    """深度优先搜索：沿一条分支访问到底后再回溯。"""
    graph = {node: [] for node in range(num_nodes)}
    for source, target in edges:
        graph[source].append(target)
        graph[target].append(source)

    visited = set()
    order = []

    def visit(node):
        visited.add(node)
        order.append(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                visit(neighbor)

    visit(start)
    return order
