# algorithm: insertion_sort | language: python | domain: data_structure
from visual_tracer import ArrayTracer

tracer = ArrayTracer()

def insertion_sort(arr):
    nums = arr[:]
    tracer.init_array(nums)
    n = len(nums)
    for i in range(1, n):
        key = nums[i]
        j = i - 1
        while j >= 0:
            tracer.compare(j, j + 1)
            if nums[j] > key:
                tracer.assign(j + 1, nums[j])
                nums[j + 1] = nums[j]
                j -= 1
            else:
                break
        tracer.assign(j + 1, key)
        nums[j + 1] = key
    for i in range(n):
        tracer.mark_sorted(i)
    tracer.finish()
    return nums

result = insertion_sort([5, 3, 8, 1, 2])
