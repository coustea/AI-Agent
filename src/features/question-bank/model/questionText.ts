export function summarizeQuestionText(text: string, maxLength?: number): string {
  const summary = String(text || '').replace(/\s+/g, ' ').trim()
  if (!maxLength || summary.length <= maxLength) return summary
  return `${summary.slice(0, maxLength)}...`
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

/**
 * 渲染题库中的轻量 Markdown。
 *
 * 兼容导入数据里被压成单行的 ```c code```，同时保留标准多行代码块。
 * 所有原始文本都会先转义，避免题库内容通过 v-html 注入标签。
 */
export function renderQuestionMarkdown(text: string): string {
  if (!text) return ''

  const source = String(text).replace(/\r\n?/g, '\n')
  const fencedCode: string[] = []
  const tokenized = source.replace(
    /```([^\s`]*)[ \t]*\n?([\s\S]*?)```/g,
    (match, rawLanguage: string, rawCode: string, offset: number) => {
      const language = rawLanguage.replace(/[^a-z0-9_+#.-]/gi, '').toLowerCase()
      const code = rawCode.trim()
      const before = source.slice(0, offset)
      const after = source.slice(offset + match.length)
      const isStandalone = /(^|\n)[ \t]*$/.test(before) && /^[ \t]*(\n|$)/.test(after)
      const isBlock = isStandalone || code.includes('\n')
      const rendered = isBlock
        ? `<pre class="question-code-block"${language ? ` data-language="${language}"` : ''}><code>${escapeHtml(code)}</code></pre>`
        : `<code class="question-inline-code">${escapeHtml(code)}</code>`

      const index = fencedCode.push(rendered) - 1
      return `\u0000QUESTION_CODE_${index}\u0000`
    },
  )

  const rendered = escapeHtml(tokenized)
    .replace(/`([^`\n]+)`/g, '<code class="question-inline-code">$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')

  return rendered.replace(/\u0000QUESTION_CODE_(\d+)\u0000/g, (_, index: string) => fencedCode[Number(index)] || '')
}
