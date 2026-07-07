def queue_operations():
    queue = []
    # Enqueue elements
    queue.append(10)
    queue.append(20)
    queue.append(30)
    # Dequeue elements
    front = queue.pop(0)
    return queue, front

queue_operations()
