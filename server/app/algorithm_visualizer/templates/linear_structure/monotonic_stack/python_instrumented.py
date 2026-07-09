from visual_tracer import StackTracer

tracer = StackTracer()


def next_greater_element(nums):
    """对数组中每个元素，找到右边第一个比它大的元素。
    返回结果数组，若不存在则为 -1。"""
    n = len(nums)
    if n == 0:
        return []

    res = [-1] * n
    stack = []
    tracer.init_stack(line=15)

    for i in range(n):
        tracer.highlight_input(i, line=17)
        while stack and nums[stack[-1]] < nums[i]:
            prev_idx = stack.pop()
            tracer.pop(line=20)
            res[prev_idx] = nums[i]
        stack.append(i)
        tracer.push(i, line=22)

    tracer.finish(line=25)
    return res


def next_greater_element_circular(nums):
    """环形数组的下一个更大元素（变体）。
    将数组视为环形，即可以从头部继续寻找。
    技巧：遍历两遍数组，利用取模访问。"""
    n = len(nums)
    if n == 0:
        return []

    res = [-1] * n
    stack = []

    for i in range(2 * n):
        while stack and nums[stack[-1]] < nums[i % n]:
            prev_idx = stack.pop()
            if res[prev_idx] == -1:
                res[prev_idx] = nums[i % n]
        if i < n:
            stack.append(i)

    return res


data = [3, 1, 4, 2, 5, 7, 6, 9, 8, 0, 3, 11]
print("下一个更大元素:", next_greater_element(data))
print("环形下一个更大元素:", next_greater_element_circular(data))
tracer.dump()
