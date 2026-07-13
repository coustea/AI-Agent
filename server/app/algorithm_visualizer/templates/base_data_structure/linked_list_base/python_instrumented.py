from visual_tracer import LinkedListTracer
tracer = LinkedListTracer()

def linked_list_operations(arr):
    """链表基础操作演示"""
    if not arr:
        tracer.init_list([], [], line=1)
        tracer.finish(line=1)
        return []

    nodes = [{"id": f"node-{i}", "label": str(v)} for i, v in enumerate(arr)]
    pointers = [{"label": "head", "nodeIndex": 0}]
    tracer.init_list(nodes, pointers, line=8)

    # 演示添加节点
    new_idx = tracer.add_node("NEW", tone="accent", line=12)
    tracer.move_pointer("current", new_idx, tone="active", line=13)

    # 演示删除节点
    tracer.remove_node(new_idx, line=16)

    # 遍历链表
    for i in range(len(arr)):
        tracer.move_pointer("current", i, tone="active", line=20)

    tracer.finish(line=22)
    return arr
