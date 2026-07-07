def max_sliding_window(nums, k):
    from collections import deque
    q = deque() # Store indices
    res = []
    for i in range(len(nums)):
        # Remove elements out of window range
        if q and q[0] < i - k + 1:
            q.popleft()
        # Maintain monotonic decreasing queue
        while q and nums[q[-1]] < nums[i]:
            q.pop()
        q.append(i)
        # Record max of window
        if i >= k - 1:
            res.append(nums[q[0]])
    return res

max_sliding_window([1, 3, -1, -3, 5, 3, 6, 7], 3)
