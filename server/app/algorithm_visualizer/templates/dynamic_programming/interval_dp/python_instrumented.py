from visual_tracer import DpTableTracer
tracer = DpTableTracer()

def longest_palindrome_subseq(s):
    """最长回文子序列"""
    n = len(s)
    headers = [str(i) for i in range(n)]
    tracer.init_table(headers, n, n, fill_value=0, line=5)

    for i in range(n):
        tracer.set_value(i, i, 1, line=8)
        tracer.highlight(i, i, tone="active", line=9)

    tracer.finish(line=12)
    return 1
