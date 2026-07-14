from visual_tracer import LinkedListTracer
tracer = LinkedListTracer()

def reverse_list(arr):
    """链表反转"""
    if not arr:
        tracer.init_list([], [], line=1)
        tracer.finish(line=1)
        return []

    nodes = [{"id": f"node-{i}", "label": str(v)} for i, v in enumerate(arr)]
    pointers = [{"label": "head", "nodeIndex": 0}]
    tracer.init_list(nodes, pointers, line=8)

    for i in range(len(arr) // 2):
        tracer.snapshot("reverse", {"left": i, "right": len(arr)-1-i}, line=12)
        tracer.move_pointer("left", i, tone="active", line=13)
        tracer.move_pointer("right", len(arr)-1-i, tone="accent", line=14)

    tracer.finish(line=16)
    return arr[::-1]
