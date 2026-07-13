from visual_tracer import QueueTracer
tracer = QueueTracer()

def max_sliding_window(arr, k):
    """单调队列滑动窗口最大值"""
    tracer.init_queue(line=1)

    for i, val in enumerate(arr[:k]):
        tracer.enqueue(val, line=8)

    tracer.finish(line=11)
    return max(arr[:k])
