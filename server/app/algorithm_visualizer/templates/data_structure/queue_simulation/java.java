// algorithm: queue_simulation | language: java | domain: data_structure
public class Solution {
    public static void main(String[] args) {
        QueueTracer tracer = new QueueTracer();
        tracer.initQueue();
        tracer.enqueue(10);
        tracer.enqueue(20);
        tracer.dequeue();
        tracer.enqueue(30);
        tracer.finish();
    }
}
