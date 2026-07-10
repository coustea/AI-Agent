from visual_tracer import TreeTracer

tracer = TreeTracer()

# 定义 subsets 函数
def subsets(nums):
    if not nums:
        return [[]]
    nodes = []
    counter = [0]

# 定义 make_node 函数
    def make_node(label):
        nid = f"node-{counter[0]}"
        counter[0] += 1
        return nid, {"id": nid, "label": label, "children": []}

# 定义 backtrack_build 函数
    def backtrack_build(start, path):
        nid, node = make_node(str(path[:]))
        nodes.append(node)
# 循环遍历处理
        for i in range(start, len(nums)):
            path.append(nums[i])
            child_id = backtrack_build(i + 1, path)
            node["children"].append(child_id)
            path.pop()
        return nid

    backtrack_build(0, [])
    tracer.init_tree(nodes, line=4)

    visit_idx = [0]

# 定义 backtrack_visit 函数
    def backtrack_visit(start, path):
        nid = f"node-{visit_idx[0]}"
        visit_idx[0] += 1
        tracer.visit_node(nid, line=20)
# 循环遍历处理
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack_visit(i + 1, path)
            path.pop()

    backtrack_visit(0, [])
    tracer.finish(line=28)

    res = []
# 定义 collect 函数
    def collect(start, path):
        res.append(path[:])
# 循环遍历处理
        for i in range(start, len(nums)):
            path.append(nums[i])
            collect(i + 1, path)
            path.pop()
    collect(0, [])
    return res

# 定义 subsets_with_dup 函数
def subsets_with_dup(nums):
    nums.sort()
    res = []
# 定义 backtrack 函数
    def backtrack(start, path):
        res.append(path[:])
# 循环遍历处理
        for i in range(start, len(nums)):
            if i > start and nums[i] == nums[i - 1]:
                continue
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    backtrack(0, [])
    return res

# 定义 subsets_bitmask 函数
def subsets_bitmask(nums):
    n = len(nums)
    res = []
# 循环遍历处理
    for mask in range(1 << n):
        subset = []
# 循环遍历处理
        for i in range(n):
            if mask & (1 << i):
                subset.append(nums[i])
        res.append(subset)
    return res

# 定义 subset_sum 函数
def subset_sum(nums, target):
    res = []
# 定义 backtrack 函数
    def backtrack(start, remain, path):
        if remain == 0:
            res.append(path[:])
            return
        if remain < 0:
            return
# 循环遍历处理
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i + 1, remain - nums[i], path)
            path.pop()
    backtrack(0, target, [])
    return res

subsets([1, 2, 3, 4, 5])
subsets_with_dup([1, 2, 2, 3])
subsets_bitmask([1, 2, 3])
subset_sum([3, 1, 4, 2, 5, 6], 6)
tracer.dump()
