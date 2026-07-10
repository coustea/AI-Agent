from visual_tracer import GraphTracer

tracer = GraphTracer()

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
        edges = [(u, v, w) for u, v, w in edges if u != v]

# 循环遍历处理
    for u, v, w in edges:
        assert 0 <= u < num_nodes, f"节点编号越界：{u}"
        assert 0 <= v < num_nodes, f"节点编号越界：{v}"

    nodes = []
# 循环遍历处理
    for i in range(num_nodes):
        node_edges = []
# 循环遍历处理
        for u, v, w in edges:
            if u == i:
                node_edges.append({"to": str(v), "weight": w})
            elif v == i:
                node_edges.append({"to": str(u), "weight": w})
        nodes.append({"id": str(i), "label": labels[i], "edges": node_edges})
    tracer.init_graph(nodes, line=29)

    matrix = [[0] * num_nodes for _ in range(num_nodes)]
# 循环遍历处理
    for u, v, w in edges:
        matrix[u][v] = w
        matrix[v][u] = w
        tracer.visit_node(str(u), line=58)
        tracer.visit_node(str(v), line=59)

    adj = {i: [] for i in range(num_nodes)}
# 循环遍历处理
    for u, v, w in edges:
        adj[u].append((v, w))
        adj[v].append((u, w))
        tracer.visit_node(str(u), line=66)
        tracer.visit_node(str(v), line=67)

    edge_list = []
# 循环遍历处理
    for u, v, w in edges:
        if u < v:
            edge_list.append((u, v, w))
        tracer.visit_node(str(u), line=73)
        tracer.visit_node(str(v), line=74)

    degree = [0] * num_nodes
# 循环遍历处理
    for u, v, w in edges:
        degree[u] += 1
        degree[v] += 1

    isolated = [labels[i] for i in range(num_nodes) if degree[i] == 0]
    if isolated:
        print(f"发现孤立节点：{isolated}")
    else:
        print("所有节点均连通，无孤立节点")

    matrix_ok = True
# 循环遍历处理
    for u in range(num_nodes):
# 循环遍历处理
        for v, w in adj[u]:
            if matrix[u][v] != w:
                matrix_ok = False

    edge_list_ok = True
# 循环遍历处理
    for u, v, w in edge_list:
        if matrix[u][v] != w or matrix[v][u] != w:
            edge_list_ok = False

    if matrix_ok and edge_list_ok:
        print("验证通过：三种表示完全一致")
    else:
        print("验证失败：表示之间存在不一致")

    print("\n--- 邻接矩阵 ---")
    header = "    " + "  ".join(f"{l:>3}" for l in labels)
    print(header)
# 循环遍历处理
    for i, row in enumerate(matrix):
        print(f"{labels[i]:>3} " + "  ".join(f"{val:>3}" for val in row))

    print("\n--- 邻接表 ---")
# 循环遍历处理
    for i in range(num_nodes):
        neighbors = ", ".join(f"{labels[v]}({w})" for v, w in adj[i])
        print(f"  {labels[i]}: [{neighbors}]")

    print("\n--- 边列表 ---")
# 循环遍历处理
    for u, v, w in edge_list:
        print(f"  {labels[u]} — {labels[v]}, 权重 {w}")

    print("\n--- 度数统计 ---")
# 循环遍历处理
    for i in range(num_nodes):
        print(f"  节点 {labels[i]}: 度数 {degree[i]}")

    tracer.finish(line=138)

    return matrix, adj, edge_list, degree


if __name__ == "__main__":
    build_graph()
    tracer.dump()
