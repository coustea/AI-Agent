// algorithm: bracket_match | language: c | domain: data_structure
#include "visual_tracer.h"
#include <string.h>

int isMatching(char open, char close) {
    return (open == '(' && close == ')') ||
           (open == '[' && close == ']') ||
           (open == '{' && close == '}');
}

int isOpening(char c) {
    return c == '(' || c == '[' || c == '{';
}

void bracketMatch(const char* s) {
    vt_init_stack();
    int len = strlen(s);
    for (int i = 0; i < len; i++) {
        vt_highlight_input(i);
        if (isOpening(s[i])) {
            vt_push((int)s[i]);
        } else {
            vt_pop();
        }
    }
    vt_stack_finish();
}

int main() {
    bracketMatch("({[]})");
    return 0;
}
