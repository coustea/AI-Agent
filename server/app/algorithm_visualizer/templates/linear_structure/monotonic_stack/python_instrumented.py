from visual_tracer import StackTracer
tracer = StackTracer()

# 单调栈算法 —— 下一个更大元素
# 核心思想：维护一个从栈底到栈顶单调递减的栈，存储元素下标
# 当新元素大于栈顶时，栈顶元素找到了"下一个更大元素"，弹出栈顶
# 时间复杂度：O(n)，每个元素最多入栈出栈各一次
# 空间复杂度：O(n)，最坏情况下所有元素都在栈中
# monotonic_stack 算法实现 — domain: linear_structure

def next_greater_element(nums):
    """对数组中每个元素，找到右边第一个比它大的元素。
    返回结果数组，若不存在则为 -1。"""
    from visual_tracer import ArrayTracer
    arr_tracer = ArrayTracer()
    arr_tracer.init_array(nums, line=8)

    n = len(nums)
    if n == 0:
        arr_tracer.finish(line=13)
        return []

    tracer.init_stack(line=15)
    res = [-1] * n  # 默认值为 -1，表示没有更大元素
    stack = []       # 单调递减栈，存储元素下标

    for i in range(n):
        arr_tracer.move_pointer({"i": i}, line=18)
        arr_tracer.highlight(i, tone="active", line=18)
        # 当前元素比栈顶元素大时，栈顶找到了"下一个更大元素"
        while stack and nums[stack[-1]] < nums[i]:
            prev_idx = stack.pop()
            tracer.pop(line=20)
            res[prev_idx] = nums[i]
            arr_tracer.mark_sorted(prev_idx, line=22)
        stack.append(i)
        tracer.push(i, line=23)
        arr_tracer.clear_highlights(line=23)

    # 栈中剩余元素没有下一个更大元素，res 中已为 -1
    arr_tracer.finish(line=26)
    return res


def next_greater_element_circular(nums):
    """环形数组的下一个更大元素（变体）。
    将数组视为环形，即可以从头部继续寻找。
    技巧：遍历两遍数组，利用取模访问。"""
    from visual_tracer import ArrayTracer
    arr_tracer = ArrayTracer()
    arr_tracer.init_array(nums, line=29)

    n = len(nums)
    if n == 0:
        arr_tracer.finish(line=34)
        return []

    tracer.init_stack(line=37)
    res = [-1] * n
    stack = []

    # 遍历两遍数组，第二遍只处理栈中残留元素
    for i in range(2 * n):
        arr_tracer.move_pointer({"i": i % n}, line=41)
        arr_tracer.highlight(i % n, tone="active", line=41)
        while stack and nums[stack[-1]] < nums[i % n]:
            prev_idx = stack.pop()
            tracer.pop(line=43)
            if res[prev_idx] == -1:
                res[prev_idx] = nums[i % n]
                arr_tracer.mark_sorted(prev_idx, line=45)
        if i < n:
            stack.append(i)
            tracer.push(i, line=47)
        arr_tracer.clear_highlights(line=47)

    arr_tracer.finish(line=49)
    return res
