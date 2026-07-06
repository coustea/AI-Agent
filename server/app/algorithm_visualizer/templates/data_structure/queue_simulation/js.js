// algorithm: queue_simulation | language: javascript | domain: data_structure
import { QueueTracer } from './js_tracer.js';

const tracer = new QueueTracer();

function queueSimulation(operations) {
    tracer.initQueue();
    for (let i = 0; i < operations.length; i++) {
        const [op, val] = operations[i];
        if (op === 'enqueue') {
            tracer.enqueue(val);
        } else if (op === 'dequeue') {
            tracer.dequeue();
        }
    }
    tracer.finish();
}

queueSimulation([['enqueue', 10], ['enqueue', 20], ['dequeue', null], ['enqueue', 30]]);
