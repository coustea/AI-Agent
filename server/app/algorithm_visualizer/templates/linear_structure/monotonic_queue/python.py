# monotonic_queue 算法实现 — domain: linear_structure
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

    for i in range(n):
        if q and q[0] < i - k + 1:
            q.popleft()

        while q and nums[q[-1]] < nums[i]:
            q.pop()

        q.append(i)

        if i >= k - 1:
            res.append(nums[q[0]])

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

    for i in range(n):
        if q and q[0] < i - k + 1:
            q.popleft()
        while q and nums[q[-1]] > nums[i]:
            q.pop()
        q.append(i)
        if i >= k - 1:
            res.append(nums[q[0]])

    return res
