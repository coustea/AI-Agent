from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def can_jump(arr):
    """跳跃游戏"""
    if not arr:
        tracer.finish(line=1)
        return False

    tracer.init_array(arr, line=5)
    max_reach = 0

    for i, jump in enumerate(arr):
        tracer.move_pointer({"i": i, "max": max_reach}, line=10)
        if i > max_reach:
            tracer.finish(line=12)
            return False
        max_reach = max(max_reach, i + jump)
        tracer.mark_sorted(i, line=15)

    tracer.finish(line=18)
    return True
