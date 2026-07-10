"""Rabin-Karp 字符串匹配算法
# rabin_karp 算法实现 — domain: string_structure

核心思想：将字符串比较转化为数值比较，利用滚动哈希（Rolling Hash）
在 O(1) 时间内完成窗口滑动时的哈希值更新，从而避免逐字符重新计算。

滚动哈希原理：
  采用多项式哈希函数 H(s) = s[0]*d^(m-1) + s[1]*d^(m-2) + ... + s[m-1]*d^0 (mod q)
  当窗口从位置 i 滑动到 i+1 时：
    H_new = (d * (H_old - s[i] * h) + s[i+m]) (mod q)
  其中 h = d^(m-1) (mod q) 是最高位权重，预计算一次即可复用。
  这样每次滑动只需 O(1) 时间，无需重新计算整个窗口的哈希值。

为什么使用素数取模：
  - 取模运算将哈希值限制在 [0, q) 范围内，避免大数溢出
  - 素数 q 能使哈希值分布更均匀，减少碰撞概率
  - 常用素数：101、1009、10007、10^9+7 等，q 越大碰撞越少

哈希碰撞处理：
  - 哈希值相等时，必须逐字符验证（二次确认），否则可能产生误匹配
  - 这也是 Rabin-Karp 最坏时间复杂度为 O(n*m) 的原因：
    当大量碰撞发生时（如精心构造的输入），每次哈希匹配都需要 O(m) 验证
  - 平均情况下碰撞极少，时间复杂度为 O(n+m)

时间复杂度：
  - 预处理（计算模式串哈希 + 首个窗口哈希 + h 值）：O(m)
  - 滑动窗口扫描：O(n) 次滑动，每次 O(1) 哈希更新 + O(m) 最坏验证
  - 平均：O(n + m)，最坏：O(n * m)
空间复杂度：O(k)，k 为匹配位置数
"""


# 定义 rabin_karp 函数
def rabin_karp(text, pattern):
    if not pattern:
        return list(range(len(text) + 1))
    if not text or len(pattern) > len(text):
        return []

    d = 256
    q = 101
    m = len(pattern)
    n = len(text)
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
        if p == t:
            if text[i : i + m] == pattern:
                res.append(i)
        if i < n - m:
            t = (d * (t - ord(text[i]) * h) + ord(text[i + m])) % q
            if t < 0:
                t = t + q
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
