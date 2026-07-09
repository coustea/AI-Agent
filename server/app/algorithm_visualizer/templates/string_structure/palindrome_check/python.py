"""回文字符串检测 (Palindrome Check) — 双指针法

回文 (Palindrome) 是指正读和反读都相同的字符串。
例如 "racecar"、"A man, a plan, a canal: Panama" 清洗后都是回文。

=== 核心概念 ===

1. 双指针技术 (Two-Pointer Technique)
   - 左指针 left 从字符串头部向右移动，右指针 right 从尾部向左移动
   - 每步比较 left 和 right 所指字符是否相同
   - 若全部相同则字符串是回文；若出现不匹配则不是回文
   - 指针相遇或交叉时停止，无需继续比较（对称性保证）

2. 为什么双指针适合回文检测？
   - 回文的定义天然具有对称性：第 i 个字符必须等于第 n-1-i 个字符
   - 双指针恰好从两端向中间收敛，逐对验证对称性
   - 每次比较排除一对字符，最多 n/2 次比较即可得出结论

3. 为什么要过滤非字母数字字符？
   - 回文检测通常只关注字母和数字，忽略标点、空格等
   - 例如 "A man, a plan, a canal: Panama" 清洗后为 "amanaplanacanalpanama"
   - 这是回文检测的常见约定，使算法更实用

4. 时间复杂度：O(n)
   - 清洗字符串：遍历一次 O(n)
   - 双指针比较：最多 n/2 次，O(n)
   - 总体线性时间

5. 空间复杂度：O(n)
   - 清洗后的字符串占用 O(n) 额外空间
   - 若需 O(1) 空间，可直接在原字符串上用双指针跳过非字母数字字符
"""


def is_palindrome(s):
    """检测字符串是否为回文（忽略非字母数字字符，不区分大小写）。

    使用双指针法：left 从头部、right 从尾部向中间收敛，
    逐对比较字符。若所有对称位置的字符都相同，则为回文。

    Args:
        s: 待检测的字符串

    Returns:
        True 表示是回文，False 表示不是回文
    """
    cleaned = "".join(char.lower() for char in s if char.isalnum())

    left = 0
    right = len(cleaned) - 1
    while left < right:
        if cleaned[left] != cleaned[right]:
            return False
        left += 1
        right -= 1
    return True



s1 = "A man, a plan, a canal: Panama"
result1 = is_palindrome(s1)
print(f"测试1 - 经典回文: '{s1}' => {result1}")

s2 = "hello world"
result2 = is_palindrome(s2)
print(f"测试2 - 非回文: '{s2}' => {result2}")

s3 = ""
result3 = is_palindrome(s3)
print(f"测试3 - 空字符串: '{s3}' => {result3}")

s4 = "a"
result4 = is_palindrome(s4)
print(f"测试4 - 单字符: '{s4}' => {result4}")

s5 = "!@#$%^&*()"
result5 = is_palindrome(s5)
print(f"测试5 - 仅非字母数字: '{s5}' => {result5}")

s6 = "Was it a car or a cat I saw"
result6 = is_palindrome(s6)
print(f"测试6 - 较长回文: '{s6}' => {result6}")
