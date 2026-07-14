from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def sequential_search(arr, target):
    tracer.init_array(arr, line=1)
    for i, val in enumerate(arr):
        tracer.move_pointer({"i": i}, line=2)
        tracer.compare(i, i, line=3)
        if val == target:
            tracer.mark_sorted(i, line=4)
            tracer.finish(line=4)
            return i
    tracer.finish(line=5)
    return -1

# 定义 sentinel_search 函数
def sentinel_search(arr, target):
    tracer.init_array(arr, line=7)
    last = arr[-1]
    arr[-1] = target
    i = 0
    while arr[i] != target:
        tracer.move_pointer({"i": i}, line=12)
        i += 1
    arr[-1] = last
    tracer.move_pointer({"i": i}, line=14)
    if i < len(arr) - 1 or last == target:
        tracer.mark_sorted(i, line=15)
        tracer.finish(line=15)
        return i
    tracer.finish(line=17)
    return -1

# 定义 multi_key_search 函数
def multi_key_search(arr, keys):
    tracer.init_array(arr, line=19)
    results = {}
    for key in keys:
        for i, v in enumerate(arr):
            tracer.move_pointer({"i": i}, line=22)
            tracer.compare(i, i, line=23)
            if v == key:
                if key not in results:
                    results[key] = []
                results[key].append(i)
                tracer.mark_sorted(i, line=24)
    tracer.finish(line=25)
    return results

# 定义 search_with_count 函数
def search_with_count(arr, target):
    tracer.init_array(arr, line=27)
    comparisons = 0
    for i, val in enumerate(arr):
        tracer.move_pointer({"i": i}, line=30)
        comparisons += 1
        tracer.compare(i, i, line=31)
        if val == target:
            tracer.mark_sorted(i, line=33)
            tracer.finish(line=33)
            return i, comparisons
    tracer.finish(line=34)
    return -1, comparisons
