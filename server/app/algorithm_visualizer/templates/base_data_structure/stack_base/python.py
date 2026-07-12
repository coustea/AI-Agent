# 栈基础操作演示
# 栈(Stack)：后进先出(LIFO)的线性数据结构
# 特性：入栈/出栈 O(1)，只能访问栈顶元素
# 适用场景：函数调用栈、括号匹配、表达式求值、撤销操作、DFS遍历
# stack_base 算法实现 — domain: base_data_structure


# 定义 stack_operations 函数
def stack_operations():
    stack = []

    # ========== 1. 批量入栈 — O(1) 每次 ==========
    # 模拟浏览器历史记录：依次访问5个页面
    pages = ["首页", "列表页", "详情页", "评论页", "编辑页"]
    for page in pages:
        stack.append(page)

    # ========== 2. 查看栈顶 — O(1) ==========
    # peek操作：只查看不弹出
    if stack:
        top_page = stack[-1]  # 当前页面：编辑页

    # ========== 3. 连续出栈(回退) — O(1) 每次 ==========
    # 模拟浏览器后退：从编辑页回退到详情页
    if stack:
        stack.pop()  # 弹出"编辑页"
    if stack:
        stack.pop()  # 弹出"评论页"

    # ========== 4. 再次入栈(前进) — O(1) ==========
    # 模拟点击新链接：从详情页跳转到推荐页
    stack.append("推荐页")

    # ========== 5. 清空栈 — O(n) ==========
    # 逐个弹出直到栈为空
    while stack:
        stack.pop()

    # ========== 6. 空栈保护 — 边界检查 ==========
    # 对空栈执行操作前必须检查，避免下溢(Underflow)
    if not stack:
        pass  # 栈为空，无法弹出

    # ========== 7. 重新入栈并统计深度 ==========
    # 栈的深度即元素个数，反映递归/嵌套的层数
    for i in range(1, 7):
        stack.append(f"层级{i}")
    depth = len(stack)  # 栈深度：6

    return stack, depth
