from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def activity_selection(intervals):
    """区间调度"""
    if not intervals:
        tracer.finish(line=1)
        return 0

    intervals.sort(key=lambda x: x[1])
    tracer.init_array([i[1] for i in intervals], line=6)

    count = 1
    end = intervals[0][1]
    tracer.mark_sorted(0, line=10)

    for i, (s, e) in enumerate(intervals[1:], 1):
        tracer.move_pointer({"i": i}, line=13)
        if s >= end:
            count += 1
            end = e
            tracer.mark_sorted(i, line=17)

    tracer.finish(line=20)
    return count
