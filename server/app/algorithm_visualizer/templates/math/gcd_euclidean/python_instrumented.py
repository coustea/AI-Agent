from visual_tracer import ArrayTracer

tracer = ArrayTracer()

# 定义 extended_gcd 函数
def extended_gcd(a, b):
    if b == 0:
        return a, 1, 0
    g, x1, y1 = extended_gcd(b, a % b)
    return g, y1, x1 - (a // b) * y1

# 定义 gcd 函数
def gcd(a, b):
    arr = [a, b]
    tracer.init_array(arr, line=7)
# 循环条件判断
    while b != 0:
        a, b = b, a % b
        arr[0] = a
        arr[1] = b
        tracer.assign(0, a, line=9)
        tracer.assign(1, b, line=10)
    tracer.finish(line=11)
    return a

# 定义 lcm 函数
def lcm(a, b):
    return abs(a * b) // gcd(a, b) if a and b else 0

# 定义 mod_inverse 函数
def mod_inverse(a, m):
    g, x, _ = extended_gcd(a % m, m)
    return x % m if g == 1 else None

# 定义 are_coprime 函数
def are_coprime(a, b):
    return gcd(a, b) == 1

pairs = [
    (48, 18), (252, 105), (1071, 462), (35, 14),
    (101, 103), (0, 7), (13, 13), (56, 98), (81, 27), (144, 89),
]

# 循环遍历处理
for a, b in pairs:
    g = gcd(a, b)
    l = lcm(a, b)
    cop = are_coprime(a, b)
    if g > 0 and are_coprime(a // g, b // g):
        inv = mod_inverse(a, b) if cop else None
tracer.dump()
