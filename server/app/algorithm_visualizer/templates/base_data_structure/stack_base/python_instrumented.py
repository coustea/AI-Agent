from visual_tracer import StackTracer
tracer = StackTracer()

# 栈基础操作演示
# 栈(Stack)：后进先出(LIFO)的线性数据结构
# 特性：入栈/出栈 O(1)，只能访问栈顶元素
# 适用场景：函数调用栈、括号匹配、表达式求值、撤销操作、DFS遍历
# stack_base 算法实现 — domain: base_data_structure


# 定义 stack_operations 函数
def stack_operations(operations):
    tracer.init_stack(line=8)
    stack = []
    for i, (operation, value) in enumerate(operations):
        tracer.highlight_input(i, line=11)
        if operation == "push":
            stack.append(value)
            tracer.push(value, line=13)
        elif operation == "pop" and stack:
            popped = stack.pop()
            tracer.pop(line=15)
        elif operation == "clear":
            stack.clear()
            tracer.finish(line=17)
            tracer.init_stack(line=17)
    tracer.finish(line=18)
    return stack, len(stack)