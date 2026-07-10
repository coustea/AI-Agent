from visual_tracer import ArrayTracer

tracer = ArrayTracer()

# 定义 can_jump 函数
def can_jump(nums):
    tracer.init_array(nums, line=1)
    max_reach = 0
# 循环遍历处理
    for i, jump in enumerate(nums):
        tracer.move_pointer({"i": i, "reach": min(max_reach, len(nums) - 1)}, line=4)
        if i > max_reach:
            tracer.finish(line=6)
            return False
        max_reach = max(max_reach, i + jump)
    tracer.finish(line=9)
    return True

# 定义 min_jumps 函数
def min_jumps(nums):
    if len(nums) <= 1:
        return 0
    if nums[0] == 0:
        return -1
    max_reach = nums[0]
    steps = nums[0]
    jumps = 1
# 循环遍历处理
    for i in range(1, len(nums)):
        if i == len(nums) - 1:
            return jumps
        max_reach = max(max_reach, i + nums[i])
        steps -= 1
        if steps == 0:
            jumps += 1
            if i >= max_reach:
                return -1
            steps = max_reach - i
    return -1

# 定义 can_reach 函数
def can_reach(arr, start):
    n = len(arr)
    visited = set()
    stack = [start]
# 循环条件判断
    while stack:
        i = stack.pop()
        if arr[i] == 0:
            return True
        visited.add(i)
# 循环遍历处理
        for ni in [i + arr[i], i - arr[i]]:
            if 0 <= ni < n and ni not in visited:
                stack.append(ni)
    return False

tests_can = [([2, 3, 1, 1, 4], True), ([3, 2, 1, 0, 4], False), ([0], True), ([1, 0, 1, 0], False)]
# 循环遍历处理
for nums, expected in tests_can:
    assert can_jump(nums) == expected

tests_min = [([2, 3, 1, 1, 4], 2), ([2, 1, 1, 1, 4], 3), ([1, 1, 1, 1, 1], 4)]
# 循环遍历处理
for nums, expected in tests_min:
    assert min_jumps(nums) == expected

tests_reach = [([4, 2, 3, 0, 3, 1, 2], 5, True), ([3, 0, 2, 1, 2], 2, False)]
# 循环遍历处理
for arr, start, expected in tests_reach:
    assert can_reach(arr, start) == expected
tracer.dump()
