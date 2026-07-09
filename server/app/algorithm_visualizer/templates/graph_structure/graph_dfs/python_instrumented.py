from visual_tracer import GraphTracer

tracer = GraphTracer()

graph = {
    0: [1, 2],
    1: [3, 4],
    2: [0, 5],
    3: [],
    4: [6],
    5: [6],
    6: [2],
}

labels = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E", 5: "F", 6: "G"}

nodes = []
for node_id in sorted(graph.keys()):
    node_edges = [{"to": str(neighbor)} for neighbor in graph[node_id]]
    nodes.append({"id": str(node_id), "label": labels[node_id], "edges": node_edges})
tracer.init_graph(nodes, line=44)

WHITE, GRAY, BLACK = 0, 1, 2
color = [WHITE] * 7

discovery = [0] * 7
finish = [0] * 7
time = 0

has_cycle = False
back_edges = []

def dfs(node):
    """递归 DFS，同时进行环检测并记录发现/完成时间。"""
    global time, has_cycle

    color[node] = GRAY
    time += 1
    discovery[node] = time
    tracer.visit_node(str(node), line=75)

    for neighbor in graph[node]:
        if color[neighbor] == WHITE:
            dfs(neighbor)
        elif color[neighbor] == GRAY:
            has_cycle = True
            back_edges.append((labels[node], labels[neighbor]))

    color[node] = BLACK
    time += 1
    finish[node] = time

for node in range(7):
    if color[node] == WHITE:
        dfs(node)

tracer.finish(line=99)
tracer.dump()
