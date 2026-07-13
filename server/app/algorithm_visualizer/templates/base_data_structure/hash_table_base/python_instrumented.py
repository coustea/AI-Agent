from visual_tracer import DpTableTracer
tracer = DpTableTracer()

def hash_table_operations(arr):
    """哈希表基础操作演示"""
    if not arr:
        tracer.finish(line=1)
        return {}

    table_size = 10
    headers = [str(i) for i in range(table_size)]
    tracer.init_table(headers, table_size, 1, fill_value=0, line=8)

    for val in arr:
        idx = val % table_size
        tracer.highlight(idx, 0, tone="active", line=12)
        tracer.set_value(idx, 0, val, line=13)
        tracer.clear_highlights(line=14)

    tracer.finish(line=16)
    return {val % table_size: val for val in arr}
