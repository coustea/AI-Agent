from visual_tracer import ArrayTracer

tracer = ArrayTracer()


def compute_lps(pattern):
    """计算 LPS (最长真前缀-后缀) 数组，即 KMP 的失配函数。"""
    m = len(pattern)
    lps = [0] * m
    length = 0
    i = 1
    while i < m:
        tracer.move_pointer({"i": i, "length": length}, line=54)
        tracer.compare(i, length, line=55)
        if pattern[i] == pattern[length]:
            length += 1
            lps[i] = length
            tracer.assign(i, lps[i], line=58)
            i += 1
        else:
            if length != 0:
                length = lps[length - 1]
            else:
                lps[i] = 0
                tracer.assign(i, 0, line=67)
                i += 1
    return lps


def kmp_search(text, pattern):
    """KMP 字符串匹配算法主函数。"""
    if not pattern:
        return list(range(len(text) + 1))
    if not text:
        return []
    if len(pattern) > len(text):
        return []

    text_arr = list(text)
    tracer.init_array(text_arr, line=72)

    lps = compute_lps(pattern)

    res = []
    i = 0
    j = 0
    n, m = len(text), len(pattern)

    while i < n:
        tracer.move_pointer({"i": i, "j": j}, line=105)
        if text[i] == pattern[j]:
            tracer.compare(i, j, line=106)
            i += 1
            j += 1
        if j == m:
            res.append(i - j)
            tracer.mark_sorted(i - j, line=112)
            j = lps[j - 1]
        elif i < n and text[i] != pattern[j]:
            tracer.compare(i, j, line=115)
            if j != 0:
                j = lps[j - 1]
            else:
                i += 1
    tracer.finish(line=124)
    return res



text1 = "abacaabadcabacabaabbabacaba"
pattern1 = "abacaba"
result1 = kmp_search(text1, pattern1)
print(f"测试1 - 多次匹配: text='{text1}', pattern='{pattern1}'")
print(f"  匹配位置: {result1}")

text2 = "xyzabcabcdeffgh"
pattern2 = "abcde"
result2 = kmp_search(text2, pattern2)
print(f"测试2 - 单次匹配: text='{text2}', pattern='{pattern2}'")
print(f"  匹配位置: {result2}")

text3 = "aaaaaaaaaaaaaaaaaaaaaaaaaa"
pattern3 = "aab"
result3 = kmp_search(text3, pattern3)
print(f"测试3 - 无匹配: text='{text3}', pattern='{pattern3}'")
print(f"  匹配位置: {result3}")

result4 = kmp_search("hello", "")
print(f"测试4 - 空模式串: text='hello', pattern=''")
print(f"  匹配位置: {result4}")

result5 = kmp_search("", "abc")
print(f"测试 空文本: text='', pattern='abc'")
print(f"  匹配位置: {result5}")

result6 = kmp_search("ab", "abcde")
print(f"测试 模式串更长: text='ab', pattern='abcde'")
print(f"  匹配位置: {result6}")

tracer.dump()
