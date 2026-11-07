import { describe, expect, it } from 'vitest'
import { appendStreamingCaret } from './streamingCaret'
import { cleanMermaidSource } from './mermaid'

describe('appendStreamingCaret', () => {
  it('appends caret inside closed paragraph when paragraph is at the end', () => {
    const html = '<p>这是一个完整的段落。</p>'
    const res = appendStreamingCaret(html)
    expect(res).toBe('<p>这是一个完整的段落。<span class="markdown-stream-caret" aria-hidden="true"></span></p>')
  })

  it('never puts caret inside earlier paragraph when new unclosed text exists after it', () => {
    const html = '<p>第一段已闭合</p>\n这里是第二段正在输出的内容'
    const res = appendStreamingCaret(html)
    // 光标必须在第二段末尾，绝对不能插在第一段里面！
    expect(res).toContain('这里是第二段正在输出的内容<span class="markdown-stream-caret" aria-hidden="true"></span>')
    expect(res).not.toContain('第一段已闭合<span class="markdown-stream-caret"')
  })

  it('never puts caret inside earlier paragraph when streaming an unclosed code block', () => {
    const html = '<p>请看以下代码：</p>\n<pre><code class="language-python">def hello():\n    print(1)'
    const res = appendStreamingCaret(html)
    // 光标必须在代码最末尾，而不是停留在“请看以下代码：”里！
    expect(res).toContain('print(1)<span class="markdown-stream-caret" aria-hidden="true"></span>')
    expect(res).not.toContain('请看以下代码：<span class="markdown-stream-caret"')
  })

  it('handles empty input gracefully', () => {
    const res = appendStreamingCaret('')
    expect(res).toContain('stream-caret-line')
  })
})

describe('cleanMermaidSource', () => {
  it('fixes unquoted parenthesis inside node labels', () => {
    const raw = 'graph TD\n  A[用户提问(Query)] --> B[检索增强]'
    const cleaned = cleanMermaidSource(raw)
    expect(cleaned).toContain('A["用户提问(Query)"]')
  })

  it('strips redundant code fences if leaked', () => {
    const raw = '```mermaid\ngraph TD\n  A --> B\n```'
    const cleaned = cleanMermaidSource(raw)
    expect(cleaned).toBe('graph TD\n  A --> B')
  })
})
