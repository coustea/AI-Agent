from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def naive_match(text, pattern):
    """暴力字符串匹配"""
    tracer.init_array(list(text), line=1)
    n, m = len(text), len(pattern)

    for i in range(n - m + 1):
        tracer.move_pointer({"i": i}, line=6)
        match = True
        for j in range(m):
            tracer.compare(i + j, i + j, line=9)
            if text[i + j] != pattern[j]:
                match = False
                break
        if match:
            tracer.mark_sorted(i, line=14)

    tracer.finish(line=17)
    return -1
