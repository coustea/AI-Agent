from visual_tracer import ArrayTracer

tracer = ArrayTracer()

# 定义 quick_pow 函数
def quick_pow(base, exp):
    arr = [base, exp, 1]
    tracer.init_array(arr, line=3)
    result = 1
# 循环条件判断
    while exp > 0:
        if exp & 1:
            result *= base
            arr[2] = result
            tracer.assign(2, result, line=8)
        exp >>= 1
        base *= base
        arr[0] = base
        arr[1] = exp
        tracer.assign(0, base, line=12)
        tracer.assign(1, exp, line=13)
    tracer.finish(line=15)
    return result

# 定义 mod_pow 函数
def mod_pow(base, exp, m):
    result = 1
    base %= m
# 循环条件判断
    while exp > 0:
        if exp & 1:
            result = result * base % m
        exp >>= 1
        base = base * base % m
    return result

# 定义 mat_mul 函数
def mat_mul(A, B, m=None):
    n = len(A)
    C = [[0] * n for _ in range(n)]
# 循环遍历处理
    for i in range(n):
# 循环遍历处理
        for j in range(n):
# 循环遍历处理
            for k in range(n):
                C[i][j] += A[i][k] * B[k][j]
            if m:
                C[i][j] %= m
    return C

# 定义 mat_pow 函数
def mat_pow(M, exp, m=None):
    n = len(M)
    result = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
# 循环条件判断
    while exp > 0:
        if exp & 1:
            result = mat_mul(result, M, m)
        exp >>= 1
        M = mat_mul(M, M, m)
    return result

# 定义 fib_matrix 函数
def fib_matrix(n, m=None):
    if n <= 1:
        return n
    M = [[1, 1], [1, 0]]
    result = mat_pow(M, n - 1, m)
    return result[0][0] if not m else result[0][0] % m

tests = [quick_pow(2, 10), quick_pow(3, 7), mod_pow(2, 100, 1000000007)]
fib_tests = [fib_matrix(i) for i in range(15)]
fib_mod = [fib_matrix(i, 1000000007) for i in [50, 100, 500, 1000]]
tracer.dump()
