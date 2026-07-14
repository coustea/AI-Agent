from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def rabin_karp(text, pattern):
    """Rabin-Karp 字符串匹配"""
    tracer.init_array(list(text), line=1)
    n, m = len(text), len(pattern)

    for i in range(n - m + 1):
        tracer.move_pointer({"i": i}, line=6)

    tracer.finish(line=10)
    return -1
