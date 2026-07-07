#include <string>
#include <stack>
#include <unordered_map>

bool bracketMatch(const std::string& str) {
    std::stack<char> s;
    std::unordered_map<char, char> mapping = {{')', '('}, {'}', '{'}, {']', '['}};
    for (char c : str) {
        if (c == '(' || c == '{' || c == '[') {
            s.push(c);
        } else if (mapping.count(c)) {
            if (s.empty() || s.top() != mapping[c]) {
                return false;
            }
            s.pop();
        }
    }
    return s.empty();
}

int main() {
    bracketMatch("({[]})");
    return 0;
}