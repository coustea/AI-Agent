# algorithm: bubble_sort | language: python | domain: data_structure

from visual_tracer import ArrayTracer

tracer = ArrayTracer()

def bubble_sort(arr):
    nums = arr[:]
    tracer.init_array(nums)
    for i in range(len(nums)):
        for j in range(len(nums) - i - 1):
            tracer.compare(j, j + 1)
            if nums[j] > nums[j + 1]:
                tracer.swap(j, j + 1)
                nums[j], nums[j + 1] = nums[j + 1], nums[j]
        tracer.mark_sorted(len(nums) - i - 1)
    tracer.finish()
    return nums

result = bubble_sort([5, 3, 8, 1, 2])
tracer.dump()
