// algorithm: queue_simulation | language: c | domain: data_structure
#include "visual_tracer.h"

void queueSimulation() {
    vt_init_queue();
    vt_enqueue(10);
    vt_enqueue(20);
    vt_dequeue();
    vt_enqueue(30);
    vt_queue_finish();
}

int main() {
    queueSimulation();
    return 0;
}
