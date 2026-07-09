from visual_tracer import StackTracer

tracer = StackTracer()



def stack_operations():
    stack = []
    tracer.init_stack(line=8)

    pages = ["首页", "列表页", "详情页", "评论页", "编辑页"]
    for page in pages:
        stack.append(page)
        tracer.push(page, line=13)

    if stack:
        top_page = stack[-1]

    if stack:
        stack.pop()
        tracer.pop(line=22)
    if stack:
        stack.pop()
        tracer.pop(line=25)

    stack.append("推荐页")
    tracer.push("推荐页", line=30)

    while stack:
        stack.pop()
        tracer.pop(line=35)

    if not stack:
        pass

    for i in range(1, 7):
        stack.append(f"层级{i}")
        tracer.push(f"层级{i}", line=45)
    depth = len(stack)

    tracer.finish(line=48)
    return stack, depth


stack_operations()
tracer.dump()
