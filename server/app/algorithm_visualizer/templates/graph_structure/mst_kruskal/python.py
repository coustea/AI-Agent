"""Kruskal 最小生成树算法 —— 含并查集（路径压缩 + 按秩合并）与连通性检测

Kruskal 算法核心思想：
  将所有边按权重从小到大排序，依次考虑每条边：
  - 若该边连接的两个顶点不在同一连通分量中（即加入后不形成环），则将其加入 MST
  - 否则跳过该边
  重复直到 MST 包含 V-1 条边（V 为顶点数）

并查集（Disjoint Set Union, DSU）：
  用于高效判断两个顶点是否属于同一连通分量。
  - find(x)：查找 x 的根节点，沿途进行路径压缩，使后续查询接近 O(1)
  - union(x, y)：合并两个集合，采用按秩合并策略，将较矮的树挂到较高的树下，
    保证树的高度增长缓慢，使 find 操作的均摊复杂度为 O(α(V))，
    其中 α 为反阿克曼函数，增长极慢，实际可视为常数。

时间复杂度：O(E log E)
  - 边排序：O(E log E)，这是算法的瓶颈
  - DSU 操作：E 次 find + 最多 V-1 次 union，均摊 O(E α(V))
  - 总计：O(E log E + E α(V)) = O(E log E)

空间复杂度：O(V)，parent 和 rank 数组各 O(V)

本示例包含 7 个节点（A-G），11 条带权无向边。
"""

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
    """并查集（Disjoint Set Union）—— 路径压缩 + 按秩合并

    路径压缩：find 操作中，将沿途节点的 parent 直接指向根，
    使后续查询路径长度大幅缩短，均摊复杂度接近 O(1)。

    按秩合并：union 操作中，将秩（rank，近似树高）较小的树
    挂到秩较大的树下，避免树退化成链表，保证树高为 O(log V)。
    配合路径压缩后，均摊复杂度为 O(α(V))。
    """

    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        """查找节点 x 的根，同时进行路径压缩。"""
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        """合并 x 和 y 所在的集合，采用按秩合并。

        返回 True 表示合并成功（x 和 y 原本不在同一集合），
        返回 False 表示 x 和 y 已在同一集合（无需合并，加入该边会形成环）。
        """
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
    """Kruskal 最小生成树算法

    参数：
        num_nodes: 顶点数
        edges: 边列表，每条边为 (u, v, weight) 三元组

    返回：
        mst: 最小生成树的边列表
        mst_weight: 最小生成树的总权重
        若图不连通则返回 None, None
    """
    dsu = DSU(num_nodes)

    edges_sorted = sorted(edges, key=lambda e: e[2])

    mst = []
    mst_weight = 0

    for u, v, weight in edges_sorted:
        if dsu.union(u, v):
            mst.append((u, v, weight))
            mst_weight += weight

        if len(mst) == num_nodes - 1:
            break

    if len(mst) < num_nodes - 1:
        print("图不连通，无法构建覆盖所有顶点的最小生成树！")
        return None, None

    return mst, mst_weight


mst, total_weight = kruskal(num_nodes, edges)

if mst is not None:
    print("Kruskal 最小生成树结果：")
    print(f"  总权重: {total_weight}")
    print(f"  MST 边数: {len(mst)} (V-1 = {num_nodes - 1})")
    print("  MST 边：")
    for u, v, w in mst:
        print(f"    {labels[u]}({u}) -- {labels[v]}({v}), 权重 = {w}")
