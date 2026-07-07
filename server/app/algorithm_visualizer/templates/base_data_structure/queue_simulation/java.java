import java.util.LinkedList;
import java.util.Queue;

public class Solution {
    public static void queueSimulation() {
        Queue<Integer> queue = new LinkedList<>();
        String[] ops = {"enqueue", "enqueue", "dequeue", "enqueue"};
        int[] vals = {10, 20, 0, 30};
        for (int i = 0; i < ops.length; i++) {
            if (ops[i].equals("enqueue")) {
                queue.offer(vals[i]);
            } else if (ops[i].equals("dequeue")) {
                if (!queue.isEmpty()) {
                    queue.poll();
                }
            }
        }
    }

    public static void main(String[] args) {
        queueSimulation();
    }
}