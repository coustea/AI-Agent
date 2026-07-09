from visual_tracer import TreeTracer

tracer = TreeTracer()

def fib_naive(n):
    if n <= 1:
        return n
    return fib_naive(n - 1) + fib_naive(n - 2)

def fib_memo(n, memo=None):
    if memo is None:
        memo = {0: 0, 1: 1}
    if n in memo:
        return memo[n]
    memo[n] = fib_memo(n - 1, memo) + fib_memo(n - 2, memo)
    return memo[n]

def fib_tabulation(n):
    if n <= 1:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]

def fib_optimized(n):
    if n <= 1:
        return n
    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr
    return curr

def fib_matrix(n):
    def mat_mul(A, B):
        return [
            [A[0][0]*B[0][0] + A[0][1]*B[1][0], A[0][0]*B[0][1] + A[0][1]*B[1][1]],
            [A[1][0]*B[0][0] + A[1][1]*B[1][0], A[1][0]*B[0][1] + A[1][1]*B[1][1]],
        ]
    def mat_pow(M, n):
        result = [[1, 0], [0, 1]]
        while n > 0:
            if n & 1:
                result = mat_mul(result, M)
            M = mat_mul(M, M)
            n >>= 1
        return result
    if n <= 1:
        return n
    M = [[1, 1], [1, 0]]
    return mat_pow(M, n - 1)[0][0]

nodes = []
_counter = [0]

def build_fib_tree(n):
    if n <= 1:
        nid = f"node-{_counter[0]}"
        _counter[0] += 1
        nodes.append({"id": nid, "label": f"fib({n})", "children": []})
        return nid
    nid = f"node-{_counter[0]}"
    _counter[0] += 1
    children = []
    left_id = build_fib_tree(n - 1)
    if left_id:
        children.append(left_id)
    right_id = build_fib_tree(n - 2)
    if right_id:
        children.append(right_id)
    nodes.append({"id": nid, "label": f"fib({n})", "children": children})
    return nid

build_fib_tree(7)
tracer.init_tree(nodes, line=1)

_visit_idx = [0]

def fib_trace(n):
    if n <= 1:
        nid = f"node-{_visit_idx[0]}"
        _visit_idx[0] += 1
        tracer.visit_node(nid, line=1)
        return n
    nid = f"node-{_visit_idx[0]}"
    _visit_idx[0] += 1
    tracer.visit_node(nid, line=1)
    return fib_trace(n - 1) + fib_trace(n - 2)

fib_trace(7)
tracer.finish(line=66)

for n in [10, 20, 30]:
    r1 = fib_memo(n)
    r2 = fib_tabulation(n)
    r3 = fib_optimized(n)
    r4 = fib_matrix(n)
    assert r1 == r2 == r3 == r4

dp_table = [fib_tabulation(i) for i in range(15)]
tracer.dump()
