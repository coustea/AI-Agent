def is_valid_brackets(s):
    """括号匹配：用栈保存尚未匹配的左括号。"""
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for char in s:
        if char in '([{':
            stack.append(char)
        elif char in pairs:
            if not stack or stack[-1] != pairs[char]:
                return False
            stack.pop()
    return not stack
