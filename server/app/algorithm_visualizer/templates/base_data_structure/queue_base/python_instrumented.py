from visual_tracer import QueueTracer
tracer = QueueTracer()

# 队列基础操作演示
# 队列(Queue)：先进先出(FIFO)的线性数据结构
# 特性：入队/出队 O(1)，只能访问队首和队尾
# 适用场景：任务调度、消息队列、BFS遍历、请求缓冲
# queue_base 算法实现 — domain: base_data_structure


# 定义 queue_operations 函数
def queue_operations(operations):
    tracer.init_queue(line=8)
    queue = []
    for i, (operation, value) in enumerate(operations):
        tracer.highlight_input(i, line=11)
        if operation == "enqueue":
            queue.append(value)
            tracer.enqueue(value, line=13)
        elif operation == "dequeue" and queue:
            dequeued = queue.pop(0)
            tracer.dequeue(line=15)
        elif operation == "clear":
            queue.clear()
            tracer.finish(line=17)
            tracer.init_queue(line=17)
    tracer.finish(line=18)
    return queue, len(queue)