from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def range_updates(arr, updates):
    """差分数组区间更新"""
    tracer.init_array(arr, line=1)
    diff = [0] * (len(arr) + 1)

    for l, r, val in updates:
        tracer.move_pointer({"l": l, "r": r}, line=6)
        diff[l] += val
        diff[r+1] -= val

    tracer.finish(line=12)
    return arr
