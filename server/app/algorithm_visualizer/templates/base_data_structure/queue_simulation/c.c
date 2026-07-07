#include <string.h>

void queueSimulation() {
    int queue[100];
    int head = 0, tail = 0;
    const char* ops[] = {"enqueue", "enqueue", "dequeue", "enqueue"};
    int vals[] = {10, 20, 0, 30};
    for (int i = 0; i < 4; i++) {
        if (strcmp(ops[i], "enqueue") == 0) {
            queue[tail++] = vals[i];
        } else if (strcmp(ops[i], "dequeue") == 0) {
            if (head < tail) {
                head++;
            }
        }
    }
}

int main() {
    queueSimulation();
    return 0;
}