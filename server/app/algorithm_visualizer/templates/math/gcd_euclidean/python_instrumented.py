from visual_tracer import ArrayTracer

tracer = ArrayTracer()

def extended_gcd(a, b):
    if b == 0:
        return a, 1, 0
    g, x1, y1 = extended_gcd(b, a % b)
    return g, y1, x1 - (a // b) * y1

def gcd(a, b):
    arr = [a, b]
    tracer.init_array(arr, line=7)
    while b != 0:
        a, b = b, a % b
        arr[0] = a
        arr[1] = b
        tracer.assign(0, a, line=9)
        tracer.assign(1, b, line=10)
    tracer.finish(line=11)
    return a

def lcm(a, b):
    return abs(a * b) // gcd(a, b) if a and b else 0

def mod_inverse(a, m):
    g, x, _ = extended_gcd(a % m, m)
    return x % m if g == 1 else None

def are_coprime(a, b):
    return gcd(a, b) == 1

pairs = [
    (48, 18), (252, 105), (1071, 462), (35, 14),
    (101, 103), (0, 7), (13, 13), (56, 98), (81, 27), (144, 89),
]

for a, b in pairs:
    g = gcd(a, b)
    l = lcm(a, b)
    cop = are_coprime(a, b)
    if g > 0 and are_coprime(a // g, b // g):
        inv = mod_inverse(a, b) if cop else None
tracer.dump()
