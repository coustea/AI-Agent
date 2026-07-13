# 栈基础操作演示
# 栈(Stack)：后进先出(LIFO)的线性数据结构
# 特性：入栈/出栈 O(1)，只能访问栈顶元素
# 适用场景：函数调用栈、括号匹配、表达式求值、撤销操作、DFS遍历
# stack_base 算法实现 — domain: base_data_structure


# 定义 stack_operations 函数
def stack_operations(operations):
    stack = []
    for operation, value in operations:
        if operation == "push":
            stack.append(value)
        elif operation == "pop" and stack:
            stack.pop()
        elif operation == "clear":
            stack.clear()
    return stack, len(stack)
