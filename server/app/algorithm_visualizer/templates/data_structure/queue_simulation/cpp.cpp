// algorithm: queue_simulation | language: cpp | domain: data_structure
#include "visual_tracer.hpp"

QueueTracer tracer;

void queueSimulation() {
    tracer.initQueue();
    tracer.enqueue(10);
    tracer.enqueue(20);
    tracer.dequeue();
    tracer.enqueue(30);
    tracer.finish();
}

int main() {
    queueSimulation();
    return 0;
}
