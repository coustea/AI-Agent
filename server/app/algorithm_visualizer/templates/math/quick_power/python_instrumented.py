from visual_tracer import ArrayTracer
tracer = ArrayTracer()

# quick_power 算法实现 — domain: math
def quick_pow(base, exp):
    tracer.init_array([base, exp], line=2)
    result = 1
    step = 0
    tracer.move_pointer({"result": result, "exp": exp}, line=4)
    while exp > 0:
        tracer.move_pointer({"step": step, "exp": exp}, line=5)
        tracer.highlight(1, tone="active", line=5)
        if exp & 1:
            result *= base
            tracer.assign(0, result, line=6)
        exp >>= 1
        base *= base
        step += 1
        tracer.clear_highlights(line=8)
    tracer.highlight(0, tone="success", line=9)
    tracer.finish(line=9)
    return result

# 定义 mod_pow 函数
def mod_pow(base, exp, m):
    tracer.init_array([base, exp, m], line=11)
    result = 1
    base %= m
    tracer.assign(0, base, line=14)
    tracer.move_pointer({"result": result, "exp": exp}, line=15)
    while exp > 0:
        tracer.move_pointer({"exp": exp}, line=16)
        tracer.highlight(1, tone="active", line=16)
        if exp & 1:
            result = result * base % m
            tracer.assign(0, result, line=17)
        exp >>= 1
        base = base * base % m
        tracer.clear_highlights(line=19)
    tracer.highlight(0, tone="success", line=20)
    tracer.finish(line=20)
    return result

# 定义 mat_mul 函数
def mat_mul(A, B, m=None):
    # 矩阵乘法复杂，简化可视化
    n = len(A)
    C = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            for k in range(n):
                C[i][j] += A[i][k] * B[k][j]
            if m:
                C[i][j] %= m
    return C

# 定义 mat_pow 函数
def mat_pow(M, exp, m=None):
    n = len(M)
    result = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    tracer.init_array([exp], line=35)
    while exp > 0:
        tracer.move_pointer({"exp": exp}, line=38)
        if exp & 1:
            result = mat_mul(result, M, m)
        exp >>= 1
        M = mat_mul(M, M, m)
    tracer.finish(line=43)
    return result

# 定义 fib_matrix 函数
def fib_matrix(n, m=None):
    tracer.init_array([n], line=45)
    if n <= 1:
        tracer.highlight(0, tone="success", line=47)
        tracer.finish(line=47)
        return n
    M = [[1, 1], [1, 0]]
    result = mat_pow(M, n - 1, m)
    tracer.finish(line=50)
    return result[0][0] if not m else result[0][0] % m