from visual_tracer import QueueTracer

tracer = QueueTracer()

# CircularQueue 类定义
class CircularQueue:
# 定义 __init__ 函数
    def __init__(self, capacity):
        self.capacity = capacity
        self.queue = [None] * capacity
        self.front = 0
        self.rear = -1
        self.size = 0

# 定义 enqueue 函数
    def enqueue(self, value):
        if self.size == self.capacity:
            return False
        self.rear = (self.rear + 1) % self.capacity
        self.queue[self.rear] = value
        self.size += 1
        return True

# 定义 dequeue 函数
    def dequeue(self):
        if self.size == 0:
            return None
        value = self.queue[self.front]
        self.front = (self.front + 1) % self.capacity
        self.size -= 1
        return value

# 定义 peek 函数
    def peek(self):
        if self.size == 0:
            return None
        return self.queue[self.front]

# 定义 is_empty 函数
    def is_empty(self):
        return self.size == 0

# 定义 is_full 函数
    def is_full(self):
        return self.size == self.capacity

# 定义 simulate_bank_queue 函数
def simulate_bank_queue(customers, num_counters):
    from collections import deque
    tracer.init_queue(line=35)
    counters = [0] * num_counters
    wait_times = []
    queue = deque()
    time = 0
    ci = 0
# 循环条件判断
    while ci < len(customers) or queue:
# 循环条件判断
        while ci < len(customers) and customers[ci][0] <= time:
            queue.append(customers[ci])
            tracer.enqueue(f"P{ci}", line=43)
            ci += 1
# 循环遍历处理
        for i in range(num_counters):
            if counters[i] <= time and queue:
                arrival, duration = queue.popleft()
                tracer.dequeue(line=48)
                wait = time - arrival
                wait_times.append(wait)
                counters[i] = time + duration
        time += 1
    tracer.finish(line=54)
    avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0
    return avg_wait, wait_times

cq = CircularQueue(5)
# 循环遍历处理
for v in [10, 20, 30, 40, 50]:
    cq.enqueue(v)
assert cq.is_full()
assert not cq.enqueue(60)
assert cq.dequeue() == 10
assert cq.dequeue() == 20
cq.enqueue(60)
cq.enqueue(70)
assert cq.size == 5

customers = [(0, 3), (1, 5), (2, 2), (3, 4), (5, 1), (6, 3), (8, 2)]
avg, times = simulate_bank_queue(customers, 2)
tracer.dump()
