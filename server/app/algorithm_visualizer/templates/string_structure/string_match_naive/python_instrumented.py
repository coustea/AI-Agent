from visual_tracer import ArrayTracer

tracer = ArrayTracer()


# 定义 naive_match 函数
def naive_match(text, pattern):
    if not pattern:
        return list(range(len(text) + 1))
    if not text or len(pattern) > len(text):
        return []

    n, m = len(text), len(pattern)
    text_arr = list(text)
    tracer.init_array(text_arr, line=26)
    indices = []

# 循环遍历处理
    for i in range(n - m + 1):
        match = True
# 循环遍历处理
        for j in range(m):
            tracer.move_pointer({"i": i, "j": i + j}, line=33)
            tracer.compare(i + j, i + j, line=34)
            if text[i + j] != pattern[j]:
                match = False
                break
        if match:
            indices.append(i)

    tracer.finish(line=42)
    return indices



text1 = "abacabacaba"
pattern1 = "abacaba"
result1 = naive_match(text1, pattern1)
print(f"测试1 - 多次匹配: text='{text1}', pattern='{pattern1}'")
print(f"  匹配位置: {result1}")

text2 = "abacabacaba"
pattern2 = "cab"
result2 = naive_match(text2, pattern2)
print(f"测试2 - 较少匹配: text='{text2}', pattern='{pattern2}'")
print(f"  匹配位置: {result2}")

text3 = "abacabacaba"
pattern3 = "xyz"
result3 = naive_match(text3, pattern3)
print(f"测试3 - 无匹配: text='{text3}', pattern='{pattern3}'")
print(f"  匹配位置: {result3}")

text4 = "abc"
pattern4 = ""
result4 = naive_match(text4, pattern4)
print(f"测试4 - 空模式串: text='{text4}', pattern=''")
print(f"  匹配位置: {result4}")

text5 = "ab"
pattern5 = "abcde"
result5 = naive_match(text5, pattern5)
print(f"测试5 - 模式串更长: text='{text5}', pattern='{pattern5}'")
print(f"  匹配位置: {result5}")

tracer.dump()
