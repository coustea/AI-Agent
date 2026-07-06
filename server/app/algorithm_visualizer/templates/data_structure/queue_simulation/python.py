# algorithm: queue_simulation | language: python | domain: data_structure
from visual_tracer import QueueTracer

tracer = QueueTracer()

def queue_simulation(operations):
    tracer.init_queue()
    for op, val in operations:
        if op == "enqueue":
            tracer.enqueue(val)
        elif op == "dequeue":
            tracer.dequeue()
    tracer.finish()

queue_simulation([("enqueue", 10), ("enqueue", 20), ("dequeue", None), ("enqueue", 30)])
tracer.dump()
