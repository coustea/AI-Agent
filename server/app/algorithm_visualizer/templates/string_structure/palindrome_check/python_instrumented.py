from visual_tracer import ArrayTracer
tracer = ArrayTracer()

def is_palindrome(s):
    """回文串检测"""
    arr = list(s)
    tracer.init_array(arr, line=1)
    left, right = 0, len(arr) - 1

    while left < right:
        tracer.move_pointer({"left": left, "right": right}, line=6)
        tracer.compare(left, right, line=7)
        if arr[left] != arr[right]:
            tracer.finish(line=9)
            return False
        left += 1
        right -= 1

    tracer.finish(line=14)
    return True
