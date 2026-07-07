def build_graph():
    edges = [(0, 1), (0, 2), (1, 2), (2, 3)]
    num_nodes = 4
    
    # 1. Adjacency Matrix
    matrix = [[0] * num_nodes for _ in range(num_nodes)]
    for u, v in edges:
        matrix[u][v] = 1
        matrix[v][u] = 1
        
    # 2. Adjacency List
    adj = {i: [] for i in range(num_nodes)}
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
        
    return matrix, adj

build_graph()
