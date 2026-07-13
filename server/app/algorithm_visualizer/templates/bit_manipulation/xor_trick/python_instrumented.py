from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def find_single_number(arr):
    """只出现一次的数字"""
    tracer.init_array(arr, line=1)
    result = 0

    for i, num in enumerate(arr):
        tracer.move_pointer({"i": i}, line=6)
        tracer.compare(i, i, line=7)
        result ^= num

    tracer.finish(line=11)
    return result
