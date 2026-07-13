from visual_tracer import ArrayTracer
tracer = ArrayTracer()

# gcd_euclidean 算法实现 — domain: math
def extended_gcd(a, b):
    tracer.init_array([a, b], line=2)
    tracer.move_pointer({"a": a, "b": b}, line=3)
    if b == 0:
        tracer.highlight(0, tone="success", line=4)
        tracer.finish(line=4)
        return a, 1, 0
    tracer.highlight(1, tone="active", line=5)
    g, x1, y1 = extended_gcd(b, a % b)
    tracer.clear_highlights(line=5)
    tracer.finish(line=6)
    return g, y1, x1 - (a // b) * y1

# 定义 gcd 函数
def gcd(a, b):
    tracer.init_array([a, b], line=8)
    steps = 0
    while b != 0:
        tracer.move_pointer({"step": steps, "a": a, "b": b}, line=10)
        tracer.highlight(0, tone="active", line=10)
        tracer.highlight(1, tone="active", line=10)
        a, b = b, a % b
        steps += 1
    tracer.highlight(0, tone="success", line=11)
    tracer.finish(line=11)
    return a

# 定义 lcm 函数
def lcm(a, b):
    tracer.init_array([a, b], line=14)
    tracer.move_pointer({"a": a, "b": b}, line=15)
    result = abs(a * b) // gcd(a, b) if a and b else 0
    tracer.finish(line=15)
    return result

# 定义 mod_inverse 函数
def mod_inverse(a, m):
    tracer.init_array([a, m], line=18)
    g, x, _ = extended_gcd(a % m, m)
    if g == 1:
        tracer.highlight(0, tone="success", line=20)
        tracer.finish(line=20)
        return x % m
    tracer.highlight(0, tone="danger", line=20)
    tracer.finish(line=20)
    return None

# 定义 are_coprime 函数
def are_coprime(a, b):
    tracer.init_array([a, b], line=23)
    result = gcd(a, b) == 1
    if result:
        tracer.highlight(0, tone="success", line=25)
    else:
        tracer.highlight(0, tone="danger", line=25)
    tracer.finish(line=25)
    return result