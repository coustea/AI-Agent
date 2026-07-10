# bracket_match 算法实现 — domain: base_data_structure
def is_valid_brackets(s):
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for ch in s:
        if ch in '([{':
            stack.append(ch)
        elif ch in ')]}':
            if not stack or stack[-1] != pairs[ch]:
                return False
            stack.pop()
    return len(stack) == 0

# 定义 score_of_brackets 函数
def score_of_brackets(s):
    stack = [0]
    for ch in s:
        if ch == '(':
            stack.append(0)
        else:
            v = stack.pop()
            stack[-1] += max(2 * v, 1)
    return stack[0]

# 定义 generate_valid_brackets 函数
def generate_valid_brackets(n):
    result = []
# 定义 backtrack 函数
    def backtrack(current, open_count, close_count):
        if len(current) == 2 * n:
            result.append(current)
            return
        if open_count < n:
            backtrack(current + '(', open_count + 1, close_count)
        if close_count < open_count:
            backtrack(current + ')', open_count, close_count + 1)
    backtrack('', 0, 0)
    return result

# 定义 longest_valid_brackets 函数
def longest_valid_brackets(s):
    stack = [-1]
    max_len = 0
    for i, ch in enumerate(s):
        if ch == '(':
            stack.append(i)
        else:
            stack.pop()
            if not stack:
                stack.append(i)
            else:
                max_len = max(max_len, i - stack[-1])
    return max_len

tests = [
    ("()", True), ("()[]{}", True), ("(]", False),
    ("([)]", False), ("{[]}", True), ("{[]}", True), ("((()))", True),
    ("", True), ("([{}])", True), ("(())", True),
]

for s, expected in tests:
    result = is_valid_brackets(s)

score = score_of_brackets("(()(()))")
brackets = generate_valid_brackets(3)
longest = longest_valid_brackets(")()())")
