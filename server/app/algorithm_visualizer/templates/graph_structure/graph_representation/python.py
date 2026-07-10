"""
# graph_representation 算法实现 — domain: graph_structure
图的多种表示方式构建与一致性验证
================================
本程序演示无向加权图的三种经典表示方法：
  1. 邻接矩阵 (Adjacency Matrix)
  2. 邻接表 (Adjacency List)
  3. 边列表 (Edge List)

并验证三种表示的一致性，同时统计每个节点的度数。

时间复杂度分析：
  - 构建邻接矩阵：O(V^2) 空间，O(E) 填充时间
  - 构建邻接表：  O(V + E) 空间，O(E) 填充时间
  - 构建边列表：  O(E) 空间，O(E) 填充时间
  - 一致性验证：  O(V^2) 最坏情况（需遍历矩阵）

其中 V 为节点数，E 为边数。
"""


# 定义 build_graph 函数
def build_graph():
    labels = ["A", "B", "C", "D", "E", "F", "G"]
    num_nodes = len(labels)

    edges = [
        (0, 1, 3),
        (0, 2, 7),
        (1, 2, 2),
        (1, 3, 5),
        (2, 4, 1),
        (3, 4, 4),
        (3, 5, 6),
        (4, 6, 3),
        (5, 6, 2),
    ]

    self_loops = [(u, v, w) for u, v, w in edges if u == v]
    if self_loops:
        print(f"警告：发现自环边 {self_loops}，已跳过")
        edges = [(u, v, w) for u, v, w in edges if u != v]

    for u, v, w in edges:
        assert 0 <= u < num_nodes, f"节点编号越界：{u}"
        assert 0 <= v < num_nodes, f"节点编号越界：{v}"

    matrix = [[0] * num_nodes for _ in range(num_nodes)]
    for u, v, w in edges:
        matrix[u][v] = w
        matrix[v][u] = w

    adj = {i: [] for i in range(num_nodes)}
    for u, v, w in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))

    edge_list = []
    for u, v, w in edges:
        if u < v:
            edge_list.append((u, v, w))
        else:
            edge_list.append((v, u, w))

    degree = [0] * num_nodes
    for u, v, w in edges:
        degree[u] += 1
        degree[v] += 1

    isolated = [labels[i] for i in range(num_nodes) if degree[i] == 0]
    if isolated:
        print(f"发现孤立节点：{isolated}")
    else:
        print("所有节点均连通，无孤立节点")

    matrix_ok = True
    for u in range(num_nodes):
        for v, w in adj[u]:
            if matrix[u][v] != w:
                matrix_ok = False
                print(f"不一致：adj[{u}]→{v} 权重 {w}，但 matrix[{u}][{v}]={matrix[u][v]}")

    edge_list_ok = True
    for u, v, w in edge_list:
        if matrix[u][v] != w or matrix[v][u] != w:
            edge_list_ok = False
            print(f"不一致：edge_list ({u},{v},{w}) 与矩阵不匹配")

    if matrix_ok and edge_list_ok:
        print("验证通过：三种表示完全一致")
    else:
        print("验证失败：表示之间存在不一致")

    print("\n--- 邻接矩阵 ---")
    header = "    " + "  ".join(f"{l:>3}" for l in labels)
    print(header)
    for i, row in enumerate(matrix):
        print(f"{labels[i]:>3} " + "  ".join(f"{val:>3}" for val in row))

    print("\n--- 邻接表 ---")
    for i in range(num_nodes):
        neighbors = ", ".join(f"{labels[v]}({w})" for v, w in adj[i])
        print(f"  {labels[i]}: [{neighbors}]")

    print("\n--- 边列表 ---")
    for u, v, w in edge_list:
        print(f"  {labels[u]} — {labels[v]}, 权重 {w}")

    print("\n--- 度数统计 ---")
    for i in range(num_nodes):
        print(f"  节点 {labels[i]}: 度数 {degree[i]}")

    return matrix, adj, edge_list, degree


if __name__ == "__main__":
    build_graph()
