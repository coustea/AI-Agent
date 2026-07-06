// algorithm: bracket_match | language: javascript | domain: data_structure
import { StackTracer } from './js_tracer.js';

const tracer = new StackTracer();

function bracketMatch(s) {
    tracer.initStack();
    const mapping = {')': '(', '}': '{', ']': '['};
    for (let i = 0; i < s.length; i++) {
        const char = s[i];
        tracer.highlightInput(i);
        if (char === '(' || char === '{' || char === '[') {
            tracer.push(char);
        } else if (char === ')' || char === '}' || char === ']') {
            if (tracer._items.length === 0) {
                tracer.finish();
                return false;
            }
            const top = tracer.pop();
            if (top !== mapping[char]) {
                tracer.finish();
                return false;
            }
        }
    }
    tracer.finish();
    return tracer._items.length === 0;
}

bracketMatch("({[]})");
