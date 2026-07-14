from visual_tracer import TreeTracer
tracer = TreeTracer()

def fib_naive(n):
    """递归斐波那契"""
    nodes = [{"id": "root", "label": f"fib({n})"}]
    tracer.init_tree(nodes, line=1)

    def fib(n, parent_id="root"):
        if n <= 1:
            tracer.visit_node(parent_id, line=6)
            return n
        tracer.visit_node(parent_id, line=8)
        return fib(n-1, parent_id) + fib(n-2, parent_id)

    result = fib(n)
    tracer.finish(line=12)
    return result
