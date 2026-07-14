from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def perm_to_mask(perm_list):
    """位掩码状态转换"""
    tracer.init_array(perm_list, line=1)

    for i, perm in enumerate(perm_list):
        tracer.move_pointer({"i": i}, line=6)

    tracer.finish(line=9)
    return 0
