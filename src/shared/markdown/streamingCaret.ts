const STREAMING_CARET_HTML = '<span class="markdown-stream-caret" aria-hidden="true"></span>'

/** Insert the streaming caret inside the final text-bearing block. */
export function appendStreamingCaret(html: string): string {
  if (!html) return STREAMING_CARET_HTML

  const closingTagPattern = /<\/(p|li|h[1-6]|blockquote|td|th|code)>/gi
  let insertionIndex = -1
  let match: RegExpExecArray | null

  while ((match = closingTagPattern.exec(html)) !== null) {
    insertionIndex = match.index
  }

  if (insertionIndex < 0) return `${html}${STREAMING_CARET_HTML}`
  return `${html.slice(0, insertionIndex)}${STREAMING_CARET_HTML}${html.slice(insertionIndex)}`
}
