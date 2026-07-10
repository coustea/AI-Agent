"""
# topological_sort 算法实现 — domain: graph_structure
拓扑排序（Kahn 算法）— 课程先修关系示例
==========================================

拓扑排序是对有向无环图（DAG）的顶点进行线性排序，使得对于每条有向边 u -> v，
u 在排序中出现在 v 之前。拓扑排序广泛应用于任务调度、编译依赖分析、课程先修关系等场景。

Kahn 算法（BFS 版本）核心思想：
1. 计算所有顶点的入度（in-degree），即指向该顶点的边数
2. 将入度为 0 的顶点入队（没有前置依赖，可以最先执行）
3. 依次出队顶点，将其所有邻居的入度减 1；若邻居入度变为 0 则入队
4. 重复直到队列为空

时间复杂度：O(V + E)，其中 V 为顶点数，E 为边数
空间复杂度：O(V + E)，存储邻接表和入度数组

环检测：若最终排序结果长度 < 顶点总数，说明图中存在环，无法完成拓扑排序。
因为环中的顶点入度永远无法归零，不会被加入队列。

本示例用 7 门课程（A-G）的先修关系建模一个 DAG：
  A(0) -> B(1)   A 是 B 的先修课
  A(0) -> C(2)   A 是 C 的先修课
  B(1) -> D(3)   B 是 D 的先修课
  B(1) -> E(4)   B 是 E 的先修课
  C(2) -> E(4)   C 也是 E 的先修课
  C(2) -> F(5)   C 是 F 的先修课
  D(3) -> G(6)   D 是 G 的先修课
  E(4) -> G(6)   E 也是 G 的先修课
  F(5) -> G(6)   F 也是 G 的先修课
"""


def topological_sort(num_nodes, edges):
    """Kahn 算法实现拓扑排序，同时检测图中是否存在环。"""

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
    else:
        return None


num_nodes = 7
edges = [
    (0, 1),
    (0, 2),
    (1, 3),
    (1, 4),
    (2, 4),
    (2, 5),
    (3, 6),
    (4, 6),
    (5, 6),
]

labels = ["A", "B", "C", "D", "E", "F", "G"]
result = topological_sort(num_nodes, edges)

if result is not None:
    order_labels = [labels[i] for i in result]
    print(f"拓扑排序结果: {result} -> {order_labels}")
else:
    print("图中存在环，无法拓扑排序")

cyclic_edges = edges + [(6, 0)]
cyclic_result = topological_sort(num_nodes, cyclic_edges)

if cyclic_result is not None:
    print(f"环图结果: {cyclic_result}")
else:
    print("环检测: 图中存在环，无法完成拓扑排序")
