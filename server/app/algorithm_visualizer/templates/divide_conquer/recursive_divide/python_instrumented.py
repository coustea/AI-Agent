from visual_tracer import TreeTracer
tracer = TreeTracer()

def tower_of_hanoi(n):
    """汉诺塔递归分解"""
    nodes = [{"id": "root", "label": f"hanoi({n})"}]
    tracer.init_tree(nodes, line=1)

    def hanoi(n, src, aux, dst):
        if n == 1:
            tracer.visit_node("root", line=6)
            return
        hanoi(n-1, src, dst, aux)
        tracer.visit_node("root", line=9)
        hanoi(n-1, aux, src, dst)

    hanoi(n, 'A', 'B', 'C')
    tracer.finish(line=13)
