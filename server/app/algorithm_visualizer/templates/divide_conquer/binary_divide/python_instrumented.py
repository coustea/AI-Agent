from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def binary_search_first(arr, target):
    """二分思想分治"""
    tracer.init_array(arr, line=1)
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = (left + right) // 2
        tracer.move_pointer({"left": left, "mid": mid, "right": right}, line=7)
        tracer.compare(mid, mid, line=8)

        if arr[mid] == target:
            tracer.mark_sorted(mid, line=11)
            tracer.finish(line=12)
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    tracer.finish(line=20)
    return -1
