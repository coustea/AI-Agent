from visual_tracer import GraphTracer
tracer = GraphTracer()

def build_graph(num_nodes, edges, start):
    """图的表示"""
    nodes = [{"id": str(i), "label": str(i), "edges": []} for i in range(num_nodes)]
    for u, v, *w in edges:
        nodes[u]["edges"].append({"to": str(v)})

    tracer.init_graph(nodes, line=8)
    tracer.visit_node(str(start), line=10)
    tracer.finish(line=12)
    return nodes
