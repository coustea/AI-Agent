from visual_tracer import GraphTracer

tracer = GraphTracer()

LABELS = ["A", "B", "C", "D", "E", "F", "G"]

vis_edges = {i: [] for i in range(7)}


def build_vis_nodes():
    """根据当前 vis_edges 构建可视化节点列表"""
    nodes = []
    for i in range(7):
        nodes.append({
            "id": str(i),
            "label": LABELS[i],
            "edges": vis_edges[i]
        })
    return nodes


class DSU:
    """并查集类，支持路径压缩与按秩合并"""

    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
        self.components = n

        tracer.init_graph(build_vis_nodes(), line=27)

    def find(self, x):
        """查找节点 x 的根，同时执行路径压缩"""
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        tracer.visit_node(str(x), line=35)
        return self.parent[x]

    def union(self, x, y):
        """合并节点 x 和 y 所在的集合，按秩合并。返回是否成功合并。"""
        root_x = self.find(x)
        root_y = self.find(y)

        tracer.visit_node(str(x), line=42)
        tracer.visit_node(str(y), line=42)

        if root_x == root_y:
            return False

        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1

        self.components -= 1

        vis_edges[x].append({"to": str(y)})
        vis_edges[y].append({"to": str(x)})

        return True



dsu = DSU(7)

dsu.union(0, 1)

dsu.union(2, 3)

dsu.union(4, 5)

dsu.union(0, 2)

dsu.find(3)

dsu.union(4, 6)

dsu.union(1, 5)

dsu.find(6)

dsu.union(0, 3)

tracer.finish(line=98)
tracer.dump()
