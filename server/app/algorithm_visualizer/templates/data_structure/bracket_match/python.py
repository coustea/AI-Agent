# algorithm: bracket_match | language: python | domain: data_structure
from visual_tracer import StackTracer

tracer = StackTracer()

def bracket_match(s):
    tracer.init_stack()
    mapping = {")": "(", "}": "{", "]": "["}
    for idx, char in enumerate(s):
        tracer.highlight_input(idx)
        if char in "({[":
            tracer.push(char)
        elif char in ")}]":
            if not tracer._items:
                tracer.finish()
                return False
            top = tracer.pop()
            if top != mapping[char]:
                tracer.finish()
                return False
    tracer.finish()
    return len(tracer._items) == 0

result = bracket_match("({[]})")
tracer.dump()
