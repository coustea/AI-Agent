from visual_tracer import DpTableTracer
tracer = DpTableTracer()

def tsp(dist):
    """旅行商问题"""
    n = len(dist)
    headers = [str(i) for i in range(n)]
    tracer.init_table(headers, n, n, fill_value=0, line=5)

    for i in range(n):
        tracer.visit_node = lambda node, **kw: None
        tracer.highlight(0, i, tone="active", line=9)

    tracer.finish(line=12)
    return 0
