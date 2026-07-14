from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def enumerate_subsets(arr):
    """利用位运算枚举子集"""
    tracer.init_array(arr, line=1)
    n = len(arr)

    for mask in range(1 << n):
        tracer.move_pointer({"mask": mask}, line=7)

    tracer.finish(line=10)
    return []
