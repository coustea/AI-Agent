#include <vector>
#include <string>
#include <queue>
#include <utility>

void queueSimulation() {
    std::queue<int> q;
    std::vector<std::pair<std::string, int>> operations = {
        {"enqueue", 10}, {"enqueue", 20}, {"dequeue", 0}, {"enqueue", 30}
    };
    for (const auto& op : operations) {
        if (op.first == "enqueue") {
            q.push(op.second);
        } else if (op.first == "dequeue") {
            if (!q.empty()) {
                q.pop();
            }
        }
    }
}

int main() {
    queueSimulation();
    return 0;
}