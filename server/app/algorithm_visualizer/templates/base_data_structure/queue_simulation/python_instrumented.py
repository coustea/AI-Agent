from visual_tracer import QueueTracer
tracer = QueueTracer()

def simulate_bank_queue(customers, num_counters):
    """队列模拟"""
    tracer.init_queue(line=1)

    for i, customer in enumerate(customers):
        tracer.enqueue(customer[0], line=12)
        tracer.snapshot("customer", {"id": i, "time": customer[1]}, line=13)

    # 处理队列
    while True:
        tracer.snapshot("process", {"counters": num_counters}, line=17)
        break

    tracer.finish(line=20)
    return customers
