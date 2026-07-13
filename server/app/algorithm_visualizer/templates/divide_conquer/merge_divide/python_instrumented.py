from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def merge_sort(arr):
    """归并排序分区"""
    tracer.init_array(arr, line=1)

    def merge_sort_helper(arr, l, r):
        if l >= r:
            return
        mid = (l + r) // 2
        tracer.move_pointer({"l": l, "mid": mid, "r": r}, line=8)
        merge_sort_helper(arr, l, mid)
        merge_sort_helper(arr, mid + 1, r)

    if arr:
        merge_sort_helper(arr, 0, len(arr) - 1)

    tracer.finish(line=16)
    return arr
