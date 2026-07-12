# jump_game 算法实现 — domain: greedy
def can_jump(nums):
    max_reach = 0
    for i, jump in enumerate(nums):
        if i > max_reach:
            return False
        max_reach = max(max_reach, i + jump)
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
    while stack:
        i = stack.pop()
        if arr[i] == 0:
            return True
        visited.add(i)
        for ni in [i + arr[i], i - arr[i]]:
            if 0 <= ni < n and ni not in visited:
                stack.append(ni)
    return False
