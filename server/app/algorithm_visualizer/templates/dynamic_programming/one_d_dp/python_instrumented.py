from visual_tracer import DpTableTracer
tracer = DpTableTracer()

def climb_stairs(n):
    """爬楼梯"""
    if n <= 2:
        tracer.init_table(["0", "1"], n, 1, fill_value=0, line=1)
        tracer.finish(line=2)
        return n

    headers = [str(i) for i in range(n+1)]
    tracer.init_table(headers, 1, n+1, fill_value=0, line=6)

    for i in range(3, n+1):
        tracer.set_value(0, i, i, line=9)
        tracer.highlight(0, i, tone="active", line=10)

    tracer.finish(line=13)
    return n
