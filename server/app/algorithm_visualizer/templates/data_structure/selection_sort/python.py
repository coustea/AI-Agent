# algorithm: selection_sort | language: python | domain: data_structure
from visual_tracer import ArrayTracer

tracer = ArrayTracer()

def selection_sort(arr):
    nums = arr[:]
    tracer.init_array(nums)
    n = len(nums)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            tracer.compare(j, min_idx)
            if nums[j] < nums[min_idx]:
                min_idx = j
        if min_idx != i:
            tracer.swap(i, min_idx)
            nums[i], nums[min_idx] = nums[min_idx], nums[i]
        tracer.mark_sorted(i)
    tracer.finish()
    return nums

result = selection_sort([5, 3, 8, 1, 2])
