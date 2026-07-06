// algorithm: bracket_match | language: java | domain: data_structure
public class Solution {
    static boolean isOpening(char c) {
        return c == '(' || c == '[' || c == '{';
    }

    public static void main(String[] args) {
        StackTracer tracer = new StackTracer();
        String s = "({[]})";
        tracer.initStack();
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            tracer.highlightInput(i);
            if (isOpening(c)) {
                tracer.push((int)c);
            } else {
                tracer.pop();
            }
        }
        tracer.finish();
    }
}
