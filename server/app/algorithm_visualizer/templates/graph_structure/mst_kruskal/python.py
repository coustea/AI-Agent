def kruskal(num_nodes, edges):
    # DSU setup
    parent = list(range(num_nodes))
    def find(i):
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]
        
    def union(i, j):
        root_i = find(i)
        root_j = find(j)
        if root_i != root_j:
            parent[root_i] = root_j
            return True
        return False
        
    # Sort edges by weight
    edges.sort(key=lambda edge: edge[2])
    mst = []
    mst_weight = 0
    for u, v, weight in edges:
        if union(u, v):
            mst.append((u, v, weight))
            mst_weight += weight
            
    return mst, mst_weight

edges = [(0, 1, 10), (0, 2, 6), (0, 3, 5), (1, 3, 15), (2, 3, 4)]
kruskal(4, edges)
