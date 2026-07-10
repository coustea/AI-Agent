from visual_tracer import TreeTracer

tracer = TreeTracer()

# 定义 combination_sum 函数
def combination_sum(candidates, target):
    if not candidates or target <= 0:
        return []
    candidates = sorted(candidates)
    nodes = []
    counter = [0]

# 定义 make_node 函数
    def make_node(label):
        nid = f"node-{counter[0]}"
        counter[0] += 1
        return nid, {"id": nid, "label": label, "children": []}

# 定义 backtrack_build 函数
    def backtrack_build(start, remain, path):
        nid, node = make_node(str(path[:]))
        nodes.append(node)
        if remain == 0:
            return nid
        if remain < 0:
            return nid
# 循环遍历处理
        for i in range(start, len(candidates)):
            if candidates[i] > remain:
                break
            path.append(candidates[i])
            child_id = backtrack_build(i, remain - candidates[i], path)
            node["children"].append(child_id)
            path.pop()
        return nid

    backtrack_build(0, target, [])
    tracer.init_tree(nodes, line=4)

    visit_idx = [0]

# 定义 backtrack_visit 函数
    def backtrack_visit(start, remain, path):
        nid = f"node-{visit_idx[0]}"
        visit_idx[0] += 1
        tracer.visit_node(nid, line=22)
        if remain == 0:
            return
        if remain < 0:
            return
# 循环遍历处理
        for i in range(start, len(candidates)):
            if candidates[i] > remain:
                break
            path.append(candidates[i])
            backtrack_visit(i, remain - candidates[i], path)
            path.pop()

    backtrack_visit(0, target, [])
    tracer.finish(line=34)

    res = []
# 定义 collect 函数
    def collect(start, remain, path):
        if remain == 0:
            res.append(path[:])
            return
        if remain < 0:
            return
# 循环遍历处理
        for i in range(start, len(candidates)):
            if candidates[i] > remain:
                break
            path.append(candidates[i])
            collect(i, remain - candidates[i], path)
            path.pop()
    collect(0, target, [])
    return res

# 定义 combination_sum2 函数
def combination_sum2(candidates, target):
    if not candidates or target <= 0:
        return []
    candidates.sort()
    res = []
# 定义 backtrack 函数
    def backtrack(start, remain, path):
        if remain == 0:
            res.append(path[:])
            return
        if remain < 0:
            return
# 循环遍历处理
        for i in range(start, len(candidates)):
            if i > start and candidates[i] == candidates[i - 1]:
                continue
            if candidates[i] > remain:
                break
            path.append(candidates[i])
            backtrack(i + 1, remain - candidates[i], path)
            path.pop()
    backtrack(0, target, [])
    return res

# 定义 combination_sum_k 函数
def combination_sum_k(k, n):
    res = []
# 定义 backtrack 函数
    def backtrack(start, remain, path, depth):
        if depth == k and remain == 0:
            res.append(path[:])
            return
        if depth >= k or remain <= 0:
            return
# 循环遍历处理
        for i in range(start, 10):
            path.append(i)
            backtrack(i + 1, remain - i, path, depth + 1)
            path.pop()
    backtrack(1, n, [], 0)
    return res

combination_sum([2, 3, 5, 7], 8)
combination_sum2([10, 1, 2, 7, 6, 1, 5], 8)
combination_sum_k(3, 7)
tracer.dump()
