#include <stdbool.h>

bool bracketMatch(const char* str) {
    char stack[100];
    int top = -1;
    for (int i = 0; str[i] != '\0'; i++) {
        char c = str[i];
        if (c == '(' || c == '{' || c == '[') {
            stack[++top] = c;
        } else if (c == ')' || c == '}' || c == ']') {
            if (top == -1) return false;
            char top_char = stack[top--];
            if (c == ')' && top_char != '(') return false;
            if (c == '}' && top_char != '{') return false;
            if (c == ']' && top_char != '[') return false;
        }
    }
    return top == -1;
}

int main() {
    bracketMatch("({[]})");
    return 0;
}