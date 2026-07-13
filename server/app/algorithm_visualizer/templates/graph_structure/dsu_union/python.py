"""并查集（Disjoint Set Union, DSU）—— 路径压缩 + 按秩合并
# dsu_union 算法实现 — domain: graph_structure

并查集是一种用于管理不相交集合的数据结构，核心操作：
  - find(x)：查找元素 x 所属集合的代表（根节点）
  - union(x, y)：合并元素 x 和 y 所在的两个集合

优化策略：
  1. 路径压缩（Path Compression）：find 时将沿途节点直接挂到根上，
     使树的高度大幅降低，后续查询接近 O(1)。
  2. 按秩合并（Union by Rank）：union 时将秩（近似高度）较小的树
     挂到秩较大的树下，避免树退化成链表。

时间复杂度：单次 find/union 均摊 O(α(n))，其中 α 为反阿克曼函数，
增长极慢，在实际规模下可视为常数。

本示例使用 7 个节点（0-6，标签 A-G），演示：
  - 多次 union 合并集合
  - find 触发路径压缩
  - union 已连通节点返回 False（边界情况）
  - 连通分量计数
"""


# DSU 类定义
class DSU:
    """并查集类，支持路径压缩与按秩合并"""

# 定义 __init__ 函数
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n
        self.components = n

    def find(self, x):
        """查找节点 x 的根，同时执行路径压缩"""
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        """合并节点 x 和 y 所在的集合，按秩合并。返回是否成功合并。"""
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

        self.components -= 1
        return True

# 定义 dsu_operations 函数
def dsu_operations(num_nodes, edges):
    dsu = DSU(num_nodes)
    for left, right, *_ in edges:
        dsu.union(left, right)
    for node in range(num_nodes):
        dsu.find(node)
    return {"parent": dsu.parent, "components": dsu.components}
