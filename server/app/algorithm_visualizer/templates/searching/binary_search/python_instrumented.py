from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def binary_search(arr, target):
    tracer.init_array(arr, line=1)
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        tracer.move_pointer({"lo": lo, "hi": hi, "mid": mid}, line=4)
        tracer.compare(mid, mid, line=5)
        if arr[mid] == target:
            tracer.mark_sorted(mid, line=6)
            tracer.finish(line=6)
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    tracer.finish(line=10)
    return -1

# 定义 lower_bound 函数
def lower_bound(arr, target):
    tracer.init_array(arr, line=13)
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        tracer.move_pointer({"lo": lo, "hi": hi, "mid": mid}, line=16)
        tracer.compare(mid, mid, line=18)
        if arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    tracer.finish(line=22)
    return lo

# 定义 upper_bound 函数
def upper_bound(arr, target):
    tracer.init_array(arr, line=24)
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        tracer.move_pointer({"lo": lo, "hi": hi, "mid": mid}, line=27)
        tracer.compare(mid, mid, line=29)
        if arr[mid] <= target:
            lo = mid + 1
        else:
            hi = mid
    tracer.finish(line=33)
    return lo

# 定义 search_rotated 函数
def search_rotated(arr, target):
    tracer.init_array(arr, line=35)
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        tracer.move_pointer({"lo": lo, "hi": hi, "mid": mid}, line=38)
        tracer.compare(mid, mid, line=40)
        if arr[mid] == target:
            tracer.mark_sorted(mid, line=41)
            tracer.finish(line=41)
            return mid
        tracer.compare(lo, mid, line=42)
        if arr[lo] <= arr[mid]:
            tracer.compare(lo, mid, line=43)
            if arr[lo] <= target < arr[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:
            tracer.compare(mid, hi, line=48)
            if arr[mid] < target <= arr[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    tracer.finish(line=52)
    return -1
