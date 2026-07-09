from visual_tracer import TreeTracer

tracer = TreeTracer()

def permute(nums):
    if not nums:
        return []
    if len(nums) == 1:
        return [nums[:]]
    nodes = []
    node_counter = [0]

    def make_node(label):
        nid = f"node-{node_counter[0]}"
        node_counter[0] += 1
        return nid, {"id": nid, "label": label, "children": []}

    def backtrack_build(start):
        if start == len(nums):
            nid, node = make_node(str(nums[:]))
            nodes.append(node)
            return nid
        nid, node = make_node(f"pos{start}:swap")
        nodes.append(node)
        for i in range(start, len(nums)):
            nums[start], nums[i] = nums[i], nums[start]
            child_id = backtrack_build(start + 1)
            node["children"].append(child_id)
            nums[start], nums[i] = nums[i], nums[start]
        return nid

    backtrack_build(0)
    tracer.init_tree(nodes, line=4)

    visit_idx = [0]

    def backtrack_visit(start):
        if start == len(nums):
            nid = f"node-{visit_idx[0]}"
            visit_idx[0] += 1
            tracer.visit_node(nid, line=22)
            return
        nid = f"node-{visit_idx[0]}"
        visit_idx[0] += 1
        tracer.visit_node(nid, line=26)
        for i in range(start, len(nums)):
            nums[start], nums[i] = nums[i], nums[start]
            backtrack_visit(start + 1)
            nums[start], nums[i] = nums[i], nums[start]

    backtrack_visit(0)
    tracer.finish(line=34)

    res = []
    def collect(start):
        if start == len(nums):
            res.append(nums[:])
            return
        for i in range(start, len(nums)):
            nums[start], nums[i] = nums[i], nums[start]
            collect(start + 1)
            nums[start], nums[i] = nums[i], nums[start]
    collect(0)
    return res

def permute_with_dup(nums):
    nums.sort()
    res = []
    def backtrack(path, used):
        if len(path) == len(nums):
            res.append(path[:])
            return
        for i in range(len(nums)):
            if used[i]:
                continue
            if i > 0 and nums[i] == nums[i - 1] and not used[i - 1]:
                continue
            used[i] = True
            path.append(nums[i])
            backtrack(path, used)
            path.pop()
            used[i] = False
    backtrack([], [False] * len(nums))
    return res

def permute_k(nums, k):
    if k <= 0 or k > len(nums):
        return []
    res = []
    def backtrack(start, depth, path):
        if depth == k:
            res.append(path[:])
            return
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, depth + 1, path)
            path.pop()
    backtrack(0, 0, [])
    return res

def next_permutation(nums):
    n = len(nums)
    i = n - 2
    while i >= 0 and nums[i] >= nums[i + 1]:
        i -= 1
    if i >= 0:
        j = n - 1
        while j > i and nums[j] <= nums[i]:
            j -= 1
        nums[i], nums[j] = nums[j], nums[i]
    left, right = i + 1, n - 1
    while left < right:
        nums[left], nums[right] = nums[right], nums[left]
        left += 1
        right -= 1

permute([1, 2, 3, 4])
permute_with_dup([1, 1, 2])
permute_k([1, 2, 3, 4, 5], 3)

arr = [1, 2, 3]
next_permutation(arr)
tracer.dump()
