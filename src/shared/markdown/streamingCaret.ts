const STREAMING_CARET_HTML = '<span class="markdown-stream-caret" aria-hidden="true"></span>'

/**
 * 将流式呼吸光标精准注入到 Markdown HTML 的最末尾活动位置。
 * 彻底避免：
 * 1. 在未闭合代码块输出时，光标停留在上一段闭合标签内原地不动；
 * 2. 在末尾有未闭合文本时，光标错位停留在早前段落内；
 * 3. 产生额外不必要的孤立空白行。
 */
export function appendStreamingCaret(html: string): string {
  const trimmed = html.trim()
  if (!trimmed) {
    return `<p class="stream-caret-line">${STREAMING_CARET_HTML}</p>`
  }

  // 1. 检测最末尾的内容承载闭合标签
  const closingTagPattern = /<\/(p|li|h[1-6]|blockquote|td|th|code|span)>/gi
  let lastMatchIndex = -1
  let lastMatchLength = 0
  let match: RegExpExecArray | null

  while ((match = closingTagPattern.exec(html)) !== null) {
    lastMatchIndex = match.index
    lastMatchLength = match[0].length
  }

  // 2. 如果找到了闭合标签，检查该标签之后是否还有“有效残留文本或未闭合结构”
  if (lastMatchIndex >= 0) {
    const afterMatch = html.slice(lastMatchIndex + lastMatchLength)
    // 过滤掉纯容器闭合标签（如 </div>、</pre> 等）和空白字符
    const strippedAfter = afterMatch.replace(/<\/(div|pre|table|tbody|thead|tr|ul|ol|section|article)>/gi, '').trim()

    // 如果闭合标签之后还有实际内容（比如正在流式输出的新文本、未闭合的代码块等），
    // 则光标必须紧随整个 HTML 的最末尾，绝不能倒退插在上一段！
    if (strippedAfter.length > 0) {
      return `${html}${STREAMING_CARET_HTML}`
    }

    // 否则说明末尾正是该内容闭合标签（或外层只有容器闭合），光标优雅插入在内容闭合标签之前
    return `${html.slice(0, lastMatchIndex)}${STREAMING_CARET_HTML}${html.slice(lastMatchIndex)}`
  }

  // 3. 未匹配到任何闭合标签时，直接贴合在最末尾
  return `${html}${STREAMING_CARET_HTML}`
}
