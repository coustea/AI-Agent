"""KMP 字符串匹配算法 (Knuth-Morris-Pratt Algorithm)
# kmp_match 算法实现 — domain: string_structure

KMP 算法是一种高效的字符串匹配算法，核心思想是利用已匹配的信息避免主串指针回溯。

=== 核心概念 ===

1. LPS 数组 (Longest Proper Prefix which is also Suffix)
   - 也称为"部分匹配表"或"失配函数" (failure function)
   - lps[i] 表示 pattern[0..i] 中最长的"既是真前缀又是后缀"的子串长度
   - "真前缀"指不包含整个字符串本身的前缀
   - 例如 pattern = "abacaba":
     - lps[0] = 0  ("a" 没有真前缀=后缀)
     - lps[1] = 0  ("ab" 前缀 a ≠ 后缀 b)
     - lps[2] = 1  ("aba" 前缀 a = 后缀 a)
     - lps[3] = 0  ("abac" 无匹配)
     - lps[4] = 1  ("abaca" 前缀 a = 后缀 a)
     - lps[5] = 2  ("abacab" 前缀 ab = 后缀 ab)
     - lps[6] = 3  ("abacaba" 前缀 aba = 后缀 aba)

2. 为什么 KMP 能避免回溯？
   - 朴素算法失配时，主串指针 i 回退，模式串指针 j 归零 → O(n*m)
   - KMP 利用 LPS：失配时 j 跳到 lps[j-1]，i 不回退
   - 本质：已匹配的 pattern 前缀中，利用"前缀=后缀"的性质，
     将模式串对齐到下一个可能匹配的位置，跳过不可能匹配的位置

3. 时间复杂度：O(n + m)
   - LPS 预处理：O(m)，每个字符最多被访问两次
   - 匹配阶段：O(n)，i 只增不减，j 的减少总量不超过 j 的增加总量
   - 总体线性时间，远优于朴素算法的 O(n*m)
"""


def compute_lps(pattern):
    """计算 LPS (最长真前缀-后缀) 数组，即 KMP 的失配函数。

    LPS 数组是 KMP 算法的核心预处理步骤。
    lps[i] = pattern[0..i] 中最长的"既是真前缀又是后缀"的子串长度。

    构建过程利用了递推性质：
    - 若 pattern[i] == pattern[length]，则 lps[i] = length + 1
    - 若不等且 length > 0，则 length 回退到 lps[length-1]（利用已计算的 LPS）
    - 若不等且 length == 0，则 lps[i] = 0

    Args:
        pattern: 模式字符串

    Returns:
        LPS 数组，长度与 pattern 相同
    """
    m = len(pattern)
    lps = [0] * m
    length = 0
    i = 1
    while i < m:
        if pattern[i] == pattern[length]:
            length += 1
            lps[i] = length
            i += 1
        else:
            if length != 0:
                length = lps[length - 1]
            else:
                lps[i] = 0
                i += 1
    return lps


def kmp_search(text, pattern):
    """KMP 字符串匹配算法主函数。

    利用 LPS 数组在 O(n+m) 时间内查找 pattern 在 text 中的所有出现位置。
    匹配过程中主串指针 i 永不回退，失配时通过 LPS 跳跃模式串指针 j。

    Args:
        text: 主串（待搜索的文本）
        pattern: 模式串（要查找的模式）

    Returns:
        匹配起始位置的列表；空列表表示无匹配
    """
    if not pattern:
        return list(range(len(text) + 1))
    if not text:
        return []
    if len(pattern) > len(text):
        return []

    lps = compute_lps(pattern)

    res = []
    i = 0
    j = 0
    n, m = len(text), len(pattern)

    while i < n:
        if text[i] == pattern[j]:
            i += 1
            j += 1
        if j == m:
            res.append(i - j)
            j = lps[j - 1]
        elif i < n and text[i] != pattern[j]:
            if j != 0:
                j = lps[j - 1]
            else:
                i += 1
    return res
