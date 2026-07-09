from visual_tracer import ArrayTracer

tracer = ArrayTracer()


def rabin_karp(text, pattern):
    if not pattern:
        return list(range(len(text) + 1))
    if not text or len(pattern) > len(text):
        return []

    d = 256
    q = 101
    m = len(pattern)
    n = len(text)
    text_arr = list(text)
    tracer.init_array(text_arr, line=32)
    p = 0
    t = 0
    h = 1

    for i in range(m - 1):
        h = (h * d) % q

    for i in range(m):
        p = (d * p + ord(pattern[i])) % q
        t = (d * t + ord(text[i])) % q

    res = []
    for i in range(n - m + 1):
        tracer.move_pointer({"i": i, "j": i + m - 1}, line=59)
        tracer.compare(i, i + m - 1, line=61)
        if p == t:
            if text[i : i + m] == pattern:
                res.append(i)
        if i < n - m:
            t = (d * (t - ord(text[i]) * h) + ord(text[i + m])) % q
            if t < 0:
                t = t + q
    tracer.finish(line=70)
    return res



text1 = "abacabacabacabaabacaba"
pattern1 = "abacaba"
result1 = rabin_karp(text1, pattern1)
print(f"测试1 - 多次匹配: text='{text1}', pattern='{pattern1}'")
print(f"  匹配位置: {result1}")

text2 = "acabacabacabaabacaba"
pattern2 = "cabac"
result2 = rabin_karp(text2, pattern2)
print(f"测试2 - 单次匹配: text='{text2}', pattern='{pattern2}'")
print(f"  匹配位置: {result2}")

text3 = "abacabacabacabaabacaba"
pattern3 = "xyz"
result3 = rabin_karp(text3, pattern3)
print(f"测试3 - 无匹配: text='{text3}', pattern='{pattern3}'")
print(f"  匹配位置: {result3}")

text4 = "abc"
pattern4 = ""
result4 = rabin_karp(text4, pattern4)
print(f"测试4 - 空模式串: text='{text4}', pattern=''")
print(f"  匹配位置: {result4}")

text5 = "ab"
pattern5 = "abcde"
result5 = rabin_karp(text5, pattern5)
print(f"测试5 - 模式串更长: text='{text5}', pattern='{pattern5}'")
print(f"  匹配位置: {result5}")

tracer.dump()
