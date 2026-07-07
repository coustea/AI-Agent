def queue_simulation(operations):
    queue = []
    result = []
    for op, val in operations:
        if op == "enqueue":
            queue.append(val)
            result.append(list(queue))
        elif op == "dequeue":
            if queue:
                queue.pop(0)
            result.append(list(queue))
    return result

queue_simulation([["enqueue", 10], ["enqueue", 20], ["dequeue", None], ["enqueue", 30]])