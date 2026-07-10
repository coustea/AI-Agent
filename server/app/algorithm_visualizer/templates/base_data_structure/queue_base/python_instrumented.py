from visual_tracer import QueueTracer

tracer = QueueTracer()

# 定义 queue_operations 函数
def queue_operations():
    queue = []
    tracer.init_queue(line=2)
    # Enqueue elements
    queue.append(10)
    tracer.enqueue(10, line=4)
    queue.append(20)
    tracer.enqueue(20, line=5)
    queue.append(30)
    tracer.enqueue(30, line=6)
    # Dequeue elements
    front = queue.pop(0)
    tracer.dequeue(line=8)
    tracer.finish(line=9)
    return queue, front

queue_operations()
tracer.dump()
