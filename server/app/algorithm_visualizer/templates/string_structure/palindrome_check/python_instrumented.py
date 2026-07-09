from visual_tracer import ArrayTracer

tracer = ArrayTracer()

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
    arr = list(cleaned)
    tracer.init_array(arr, line=48)

    left = 0
    right = len(cleaned) - 1
    while left < right:
        tracer.move_pointer({"left": left, "right": right}, line=51)
        tracer.compare(left, right, line=54)
        if cleaned[left] != cleaned[right]:
            tracer.finish(line=55)
            return False
        left += 1
        right -= 1
    tracer.finish(line=58)
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

tracer.dump()
