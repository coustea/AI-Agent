def next_greater_element(nums):
    res = [-1] * len(nums)
    stack = [] # Store indices
    for i in range(len(nums)):
        while stack and nums[stack[-1]] < nums[i]:
            prev_idx = stack.pop()
            res[prev_idx] = nums[i]
        stack.append(i)
    return res

next_greater_element([2, 1, 2, 4, 3])
