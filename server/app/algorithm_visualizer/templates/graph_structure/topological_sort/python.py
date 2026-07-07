def topological_sort(num_nodes, edges):
    in_degree = [0] * num_nodes
    adj = {i: [] for i in range(num_nodes)}
    for u, v in edges:
        adj[u].append(v)
        in_degree[v] += 1
        
    queue = [i for i in range(num_nodes) if in_degree[i] == 0]
    order = []
    
    while queue:
        u = queue.pop(0)
        order.append(u)
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
                
    if len(order) == num_nodes:
        return order
    return [] # Has cycle

topological_sort(4, [(0, 1), (0, 2), (1, 3), (2, 3)])
