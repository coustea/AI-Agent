from visual_tracer import DpTableTracer
tracer = DpTableTracer()

# combination_num 算法实现 — domain: math
def pascals_triangle(n):
    """杨辉三角"""
    if n <= 0:
        tracer.finish(line=1)
        return []

    headers = [str(i) for i in range(n)]
    tracer.init_table(headers, n, n, fill_value=0, line=8)

    triangle = []
    for i in range(n):
        row = [1] * (i + 1)
        for j in range(1, i):
            row[j] = triangle[i - 1][j - 1] + triangle[i - 1][j]
            tracer.set_value(i, j, row[j], line=13)
            tracer.highlight(i, j, tone="active", line=14)
        tracer.set_value(i, 0, 1, line=16)
        if i > 0:
            tracer.set_value(i, i, 1, line=18)
        tracer.clear_highlights(line=20)
        triangle.append(row)

    tracer.finish(line=23)
    return triangle