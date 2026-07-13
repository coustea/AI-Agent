from visual_tracer import StackTracer
tracer = StackTracer()

def is_valid_brackets(s):
    """括号匹配"""
    stack = []
    tracer.init_stack(line=1)
    pairs = {')': '(', ']': '[', '}': '{'}

    for i, ch in enumerate(s):
        tracer.highlight_input(i, line=12)
        if ch in pairs.values():
            tracer.push(ch, line=13)
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack[-1] != pairs[ch]:
                tracer.pop(line=15)
                tracer.snapshot("mismatch", {"stack": stack}, line=16)
                tracer.finish(line=17)
                return False
            tracer.pop(line=18)
            stack.pop()
        tracer.snapshot("step", {"stack": stack, "ch": ch}, line=21)

    tracer.finish(line=23)
    return len(stack) == 0
