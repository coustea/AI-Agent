from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def partition(arr, low, high):
    """快速选择分区"""
    tracer.init_array(arr, line=1)
    pivot = arr[high]
    i = low - 1

    for j in range(low, high):
        tracer.compare(j, high, line=7)
        if arr[j] <= pivot:
            i += 1
            tracer.swap(i, j, line=10)

    tracer.swap(i + 1, high, line=13)
    tracer.finish(line=15)
    return i + 1
