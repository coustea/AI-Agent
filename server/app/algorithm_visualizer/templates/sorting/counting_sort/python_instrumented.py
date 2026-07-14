from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def counting_sort(arr):
    tracer.init_array(arr, line=1)
    if not arr:
        tracer.finish(line=2)
        return arr
    min_val = min(arr)
    max_val = max(arr)
    range_val = max_val - min_val + 1
    count = [0] * range_val
    tracer.init_array(count, line=7)

    for x in arr:
        tracer.move_pointer({"val": x}, line=9)
        count[x - min_val] += 1
        tracer.assign(x - min_val, count[x - min_val], line=10)

    for i in range(1, len(count)):
        count[i] += count[i - 1]
        tracer.assign(i, count[i], line=11)

    output = [0] * len(arr)
    tracer.init_array(output, line=12)

    for i in range(len(arr) - 1, -1, -1):
        tracer.move_pointer({"i": i}, line=13)
        val = arr[i]
        output[count[val - min_val] - 1] = val
        tracer.assign(count[val - min_val] - 1, val, line=15)
        count[val - min_val] -= 1

    for i in range(len(arr)):
        arr[i] = output[i]
        tracer.assign(i, output[i], line=17)
        tracer.mark_sorted(i, line=18)

    tracer.finish(line=19)
    return arr

# 定义 counting_sort_unstable 函数
def counting_sort_unstable(arr):
    tracer.init_array(arr, line=21)
    if not arr:
        tracer.finish(line=23)
        return arr
    min_val = min(arr)
    max_val = max(arr)
    range_val = max_val - min_val + 1
    count = [0] * range_val
    tracer.init_array(count, line=28)

    for x in arr:
        tracer.move_pointer({"val": x}, line=29)
        count[x - min_val] += 1
        tracer.assign(x - min_val, count[x - min_val], line=30)

    result = []
    for i in range(range_val):
        tracer.move_pointer({"i": i}, line=32)
        for _ in range(count[i]):
            result.append(i + min_val)

    tracer.init_array(result, line=33)
    for i in range(len(result)):
        tracer.mark_sorted(i, line=34)
    tracer.finish(line=34)
    return result

# 定义 frequency_count 函数
def frequency_count(arr):
    tracer.init_array(arr, line=36)
    if not arr:
        tracer.finish(line=39)
        return {}
    min_val = min(arr)
    max_val = max(arr)
    freq = {}
    for x in arr:
        tracer.move_pointer({"val": x}, line=43)
        freq[x] = freq.get(x, 0) + 1
    tracer.finish(line=44)
    return freq
