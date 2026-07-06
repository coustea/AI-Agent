// algorithm: bracket_match | language: cpp | domain: data_structure
#include "visual_tracer.hpp"
#include <string>

StackTracer tracer;

bool isOpening(char c) {
    return c == '(' || c == '[' || c == '{';
}

bool isMatching(char open, char close) {
    return (open == '(' && close == ')') ||
           (open == '[' && close == ']') ||
           (open == '{' && close == '}');
}

void bracketMatch(const std::string& s) {
    tracer.initStack();
    for (size_t i = 0; i < s.size(); i++) {
        tracer.highlightInput((int)i);
        if (isOpening(s[i])) {
            tracer.push((int)s[i]);
        } else {
            tracer.pop();
        }
    }
    tracer.finish();
}

int main() {
    bracketMatch("({[]})");
    return 0;
}
