from visual_tracer import ArrayTracer
tracer = ArrayTracer()

# mod_arithmetic 算法实现 — domain: math
def mod_pow(base, exp, m):
    """同余幂运算"""
    # 将指数转为二进制展示
    bits = [(exp >> i) & 1 for i in range(exp.bit_length())]
    tracer.init_array(bits, line=1)

    result = 1
    base %= m
    for i in range(len(bits)):
        tracer.move_pointer({"bit": i}, line=8)
        if bits[i]:
            result = result * base % m
            tracer.assign(i, result, line=11)
        base = base * base % m

    tracer.finish(line=15)
    return result