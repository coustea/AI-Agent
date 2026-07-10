# 队列基础操作演示
# 队列(Queue)：先进先出(FIFO)的线性数据结构
# 特性：入队/出队 O(1)，只能访问队首和队尾
# 适用场景：任务调度、消息队列、BFS遍历、请求缓冲
# queue_base 算法实现 — domain: base_data_structure


# 定义 queue_operations 函数
def queue_operations():
    queue = []

    # ========== 1. 批量入队 — O(1) 每次 ==========
    # 模拟打印任务队列：5个文档依次提交打印
    docs = ["报告.doc", "合同.pdf", "发票.xlsx", "简历.docx", "方案.ppt"]
    for doc in docs:
        queue.append(doc)

    # ========== 2. 查看队首 — O(1) ==========
    # peek操作：查看下一个待处理元素但不移除
    if queue:
        next_doc = queue[0]  # 下一个打印：报告.doc

    # ========== 3. 逐个出队(处理) — O(n) 用list.pop(0) ==========
    # 注意：Python list.pop(0)是O(n)，实际应用用collections.deque实现O(1)
    # 处理前3个打印任务
    for _ in range(3):
        if queue:
            queue.pop(0)

    # ========== 4. 继续入队 — O(1) ==========
    # 新任务到达：在处理旧任务的同时新任务入队
    queue.append("备忘.txt")
    queue.append("日程.xlsx")

    # ========== 5. 全部出队 — O(n) ==========
    # 清空队列：处理所有剩余任务
    while queue:
        queue.pop(0)

    # ========== 6. 空队保护 — 边界检查 ==========
    # 对空队列出队前必须检查，避免下溢(Underflow)
    if not queue:
        pass  # 队列为空，无任务可处理

    # ========== 7. 重新入队并统计长度 ==========
    # 队列长度反映待处理任务的积压量
    tasks = ["紧急-修复", "普通-优化", "低优-文档", "紧急-上线", "普通-测试", "低优-归档"]
    for task in tasks:
        queue.append(task)
    queue_len = len(queue)  # 队列长度：6

    return queue, queue_len


queue_operations()
