# algorithm: binary_search | language: python | domain: data_structure
from visual_tracer import ArrayTracer

tracer = ArrayTracer()

def binary_search(arr, target):
    nums = arr[:]
    tracer.init_array(nums)
    low = 0
    high = len(nums) - 1
    while low <= high:
        mid = (low + high) // 2
        tracer.move_pointer({"low": low, "mid": mid, "high": high})
        tracer.compare(mid, mid)
        if nums[mid] == target:
            tracer.finish()
            return mid
        elif nums[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    tracer.finish()
    return -1

result = binary_search([1, 2, 3, 5, 8], 5)
tracer.dump()
