from visual_tracer import GraphTracer

tracer = GraphTracer()

def topological_sort(num_nodes, edges, trace=True):
    """Kahn 算法实现拓扑排序，同时检测图中是否存在环。"""

    in_degree = [0] * num_nodes
    adj = {i: [] for i in range(num_nodes)}

    if trace:
        nodes = []
# 循环遍历处理
        for i in range(num_nodes):
            node_edges = [{"to": str(v)} for u, v in edges if u == i]
            nodes.append({"id": str(i), "label": labels[i], "edges": node_edges})
        tracer.init_graph(nodes, line=39)

# 循环遍历处理
    for u, v in edges:
        adj[u].append(v)
        in_degree[v] += 1

    queue = [i for i in range(num_nodes) if in_degree[i] == 0]
    order = []

    if trace:
# 循环遍历处理
        for node_id in queue:
            tracer.visit_node(str(node_id), line=50)

# 循环条件判断
    while queue:
        u = queue.pop(0)
        order.append(u)
        if trace:
            tracer.visit_node(str(u), line=57)

# 循环遍历处理
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
                if trace:
                    tracer.visit_node(str(v), line=64)

    if trace:
        tracer.finish(line=70)
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
result = topological_sort(num_nodes, edges, trace=True)

if result is not None:
    order_labels = [labels[i] for i in result]
    print(f"拓扑排序结果: {result} -> {order_labels}")
else:
    print("图中存在环，无法拓扑排序")

cyclic_edges = edges + [(6, 0)]
cyclic_result = topological_sort(num_nodes, cyclic_edges, trace=False)

if cyclic_result is not None:
    print(f"环图结果: {cyclic_result}")
else:
    print("环检测: 图中存在环，无法完成拓扑排序")

tracer.dump()
