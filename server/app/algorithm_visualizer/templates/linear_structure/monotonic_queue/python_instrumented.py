from visual_tracer import QueueTracer

tracer = QueueTracer()


from collections import deque

def max_sliding_window(nums, k):
    """求滑动窗口的最大值序列。
    窗口从左向右滑动，每次移动一步。
    返回每个窗口的最大值列表。"""
    n = len(nums)
    if n == 0 or k <= 0:
        return []
    if k == 1:
        return list(nums)
    if k > n:
        return [max(nums)]

    q = deque()
    res = []
    tracer.init_queue(line=22)

# 循环遍历处理
    for i in range(n):
        if q and q[0] < i - k + 1:
            q.popleft()
            tracer.dequeue(line=28)

# 循环条件判断
        while q and nums[q[-1]] < nums[i]:
            q.pop()
            tracer.dequeue(line=32)

        q.append(i)
        tracer.enqueue(i, line=34)

        if i >= k - 1:
            res.append(nums[q[0]])

    tracer.finish(line=40)
    return res


def min_sliding_window(nums, k):
    """滑动窗口最小值（单调递增队列变体）。"""
    n = len(nums)
    if n == 0 or k <= 0:
        return []
    if k == 1:
        return list(nums)
    if k > n:
        return [min(nums)]

    q = deque()
    res = []

# 循环遍历处理
    for i in range(n):
        if q and q[0] < i - k + 1:
            q.popleft()
# 循环条件判断
        while q and nums[q[-1]] > nums[i]:
            q.pop()
        q.append(i)
        if i >= k - 1:
            res.append(nums[q[0]])

    return res


data = [4, 2, 12, 3, 5, 1, 6, 8, 7, 10, 2, 9, 5, 3]
print(f"滑动窗口最大值 (k=4): {max_sliding_window(data, 4)}")
print(f"滑动窗口最小值 (k=4): {min_sliding_window(data, 4)}")
tracer.dump()
