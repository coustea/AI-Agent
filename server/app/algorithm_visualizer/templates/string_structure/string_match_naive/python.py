"""朴素字符串匹配算法（Brute-Force / Naive String Matching）
# string_match_naive 算法实现 — domain: string_structure

核心思想：从主串的每个起始位置 i 逐字符与模式串比较，
若全部匹配则记录该位置，否则回溯到 i+1 重新开始。

时间复杂度：O(n * m)，其中 n 为主串长度，m 为模式串长度
  - 最坏情况：主串 "aaaa...a"，模式串 "aaaab"，每次比较 m-1 次后失配
  - 最好情况：第一次就匹配成功，O(m)
空间复杂度：O(k)，k 为匹配位置数

为什么叫"暴力"（Brute-Force）：
  - 不利用任何已匹配字符的信息，失配后仅将起始位置右移一位
  - 与 KMP / Rabin-Karp 等算法相比，没有预处理阶段，也没有跳跃优化
  - 实现简单直观，但在大量重复字符的场景下效率较低
"""


# 定义 naive_match 函数
def naive_match(text, pattern):
    if not pattern:
        return list(range(len(text) + 1))
    if not text or len(pattern) > len(text):
        return []

    n, m = len(text), len(pattern)
    indices = []

    for i in range(n - m + 1):
        match = True
        for j in range(m):
            if text[i + j] != pattern[j]:
                match = False
                break
        if match:
            indices.append(i)

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
