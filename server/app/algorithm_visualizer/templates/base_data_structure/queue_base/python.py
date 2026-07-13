# 队列基础操作演示
# 队列(Queue)：先进先出(FIFO)的线性数据结构
# 特性：入队/出队 O(1)，只能访问队首和队尾
# 适用场景：任务调度、消息队列、BFS遍历、请求缓冲
# queue_base 算法实现 — domain: base_data_structure


# 定义 queue_operations 函数
def queue_operations(operations):
    queue = []
    for operation, value in operations:
        if operation == "enqueue":
            queue.append(value)
        elif operation == "dequeue" and queue:
            queue.pop(0)
        elif operation == "clear":
            queue.clear()
    return queue, len(queue)
