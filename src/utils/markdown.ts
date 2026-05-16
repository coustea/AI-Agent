const copiedCodeLanguages = new Set([
  'bash', 'c', 'cpp', 'c++', 'css', 'go', 'html', 'java', 'javascript',
  'js', 'json', 'jsx', 'python', 'py', 'sql', 'ts', 'tsx', 'typescript',
  'vue', 'xml', 'yaml', 'yml',
])

const fencePattern = /(^|\n)(`{3,}|~{3,})/g
const sectionHeadingPattern = /^([一二三四五六七八九十]+、|方式\d+[:：]|第\d+[步点][:：]|最后[:：]|总结[:：])/

function isCopiedCodeStart(lines: string[], index: number): boolean {
  const language = lines[index]?.trim().toLowerCase()
  const copyLabel = lines[index + 1]?.trim()
  if (!language || !copiedCodeLanguages.has(language)) return false
  if (copyLabel !== '复制') return false

  const nextLine = lines[index + 2]?.trim()
  if (!nextLine) return false

  return /^[#</{\[\w@]|from\s+|import\s+|class\s+|def\s+|const\s+|let\s+|var\s+/.test(nextLine)
}

function looksLikeCodeContinuation(line: string): boolean {
  const trimmed = line.trim()
  if (!trimmed) return true
  if (sectionHeadingPattern.test(trimmed)) return false
  if (/^[-*]\s+/.test(trimmed)) return false
  if (/^\d+\.\s+/.test(trimmed)) return false
  if (/^[\u4e00-\u9fa5].*[。！？；]$/.test(trimmed)) return false
  return true
}

export function repairCopiedCodeBlocks(text: string): string {
  if (!text) return text
  const lines = text.split('\n')
  const repaired: string[] = []

  for (let index = 0; index < lines.length; index += 1) {
    if (!isCopiedCodeStart(lines, index)) {
      repaired.push(lines[index] ?? '')
      continue
    }

    const language = (lines[index] ?? '').trim()
    repaired.push(`\`\`\`${language}`)
    index += 2

    while (index < lines.length && looksLikeCodeContinuation(lines[index] ?? '')) {
      repaired.push(lines[index] ?? '')
      index += 1
    }

    repaired.push('```')
    index -= 1
  }

  return repaired.join('\n')
}

export function normalizeStreamingMarkdown(text: string, isStreaming = false): string {
  const repaired = repairCopiedCodeBlocks(text)
  if (!isStreaming || !repaired) return repaired

  const fences = repaired.match(fencePattern)
  if (!fences || fences.length % 2 === 0) return repaired

  return `${repaired}\n\`\`\``
}
