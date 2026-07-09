from visual_tracer import GraphTracer

tracer = GraphTracer()

edges = [
    (0, 1, 7),
    (0, 3, 5),
    (1, 2, 8),
    (1, 3, 9),
    (1, 4, 7),
    (2, 4, 5),
    (3, 4, 15),
    (3, 5, 6),
    (4, 5, 8),
    (4, 6, 9),
    (5, 6, 11),
]

labels = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E", 5: "F", 6: "G"}
num_nodes = 7


class DSU:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x == root_y:
            return False
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1
        return True


def kruskal(num_nodes, edges):
    nodes = []
    for i in range(num_nodes):
        node_edges = []
        for u, v, w in edges:
            if u == i:
                node_edges.append({"to": str(v), "weight": w})
            elif v == i:
                node_edges.append({"to": str(u), "weight": w})
        nodes.append({"id": str(i), "label": labels[i], "edges": node_edges})
    tracer.init_graph(nodes, line=42)

    dsu = DSU(num_nodes)

    edges_sorted = sorted(edges, key=lambda e: e[2])

    mst = []
    mst_weight = 0

    for u, v, weight in edges_sorted:
        tracer.visit_node(str(u), line=136)
        tracer.visit_node(str(v), line=136)

        if dsu.union(u, v):
            tracer.visit_node(str(u), line=140)
            tracer.visit_node(str(v), line=140)
            mst.append((u, v, weight))
            mst_weight += weight

        if len(mst) == num_nodes - 1:
            break

    if len(mst) < num_nodes - 1:
        tracer.finish(line=150)
        return None, None

    tracer.finish(line=154)
    return mst, mst_weight


mst, total_weight = kruskal(num_nodes, edges)
tracer.dump()
