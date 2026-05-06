// src/utils/markdown.ts
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

const markdownUtils = MarkdownIt().utils
const escapeHtml = (value: string): string => markdownUtils.escapeHtml(value)

const copiedCodeLanguages = new Set([
  'bash', 'c', 'cpp', 'c++', 'css', 'go', 'html', 'java', 'javascript',
  'js', 'json', 'jsx', 'python', 'py', 'sql', 'ts', 'tsx', 'typescript',
  'vue', 'xml', 'yaml', 'yml',
])

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  typographer: false,
})

const fencePattern = /(^|\n)(`{3,}|~{3,})/g
const sectionHeadingPattern = /^([一二三四五六七八九十]+、|方式\d+[:：]|第\d+[步点][:：]|最后[:：]|总结[:：])/

export interface TutorContentBlock {
  type: 'markdown' | 'code'
  html?: string
  code?: string
  language?: string
}

interface ParseTutorContentOptions {
  isStreaming?: boolean
}

interface FenceBlock {
  language: string
  code: string
  closed: boolean
}

markdown.renderer.rules.fence = (tokens, index): string => {
  const token = tokens[index]
  if (!token) return ''
  const code = token.content
  const language = token.info.trim().split(/\s+/)[0] || ''
  return renderCodeBlockHtml(code, language)
}

function renderCodeBlockHtml(code: string, language = ''): string {
  const lang = language && hljs.getLanguage(language) ? language : 'plaintext'
  const highlighted = hljs.highlight(code, { language: lang }).value
  const copyableCode = escapeHtml(code)

  return [
    '<div class="code-block-wrapper">',
    '<div class="code-header">',
    `<span class="code-lang">${escapeHtml(lang)}</span>`,
    `<button class="copy-code-btn" type="button" data-code="${copyableCode}">复制</button>`,
    '</div>',
    `<pre><code class="hljs language-${escapeHtml(lang)}">${highlighted}</code></pre>`,
    '</div>',
  ].join('')
}

function renderStreamingCodeBlockHtml(code: string, language = ''): string {
  const lang = language && hljs.getLanguage(language) ? language : 'plaintext'
  const copyableCode = escapeHtml(code)
  const escapedCode = escapeHtml(code)

  return [
    '<div class="code-block-wrapper">',
    '<div class="code-header">',
    `<span class="code-lang">${escapeHtml(lang)}</span>`,
    `<button class="copy-code-btn" type="button" data-code="${copyableCode}">复制</button>`,
    '</div>',
    `<pre><code class="language-${escapeHtml(lang)}">${escapedCode}</code></pre>`,
    '</div>',
  ].join('')
}

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

export function renderTutorMarkdown(text: string, isStreaming = false): string {
  const normalized = normalizeStreamingMarkdown(text, isStreaming)
  return normalized ? markdown.render(normalized) : ''
}

function pushMarkdownBlock(blocks: TutorContentBlock[], text: string): void {
  const normalized = text.trim()
  if (!normalized) return
  blocks.push({
    type: 'markdown',
    html: markdown.render(normalized),
  })
}

function parseFenceBlock(source: string, startIndex: number): { block: FenceBlock; nextIndex: number } | null {
  const rest = source.slice(startIndex)
  const openingMatch = rest.match(/^(```|~~~)([\w+-]*)[ \t]*\n?/)
  if (!openingMatch) return null

  const fenceToken = openingMatch[1] || '```'
  const language = (openingMatch[2] || '').trim()
  const contentStart = startIndex + openingMatch[0].length
  const closingPattern = new RegExp(`(?:^|\\n)${fenceToken}[ \\t]*(?=\\n|$)`, 'g')
  closingPattern.lastIndex = 0

  const searchArea = source.slice(contentStart)
  const closingMatch = closingPattern.exec(searchArea)
  if (!closingMatch) {
    return {
      block: {
        language,
        code: source.slice(contentStart),
        closed: false,
      },
      nextIndex: source.length,
    }
  }

  const codeEnd = contentStart + closingMatch.index
  const closingTokenLength = closingMatch[0].replace(/^\n/, '').length
  const nextIndex = codeEnd + closingMatch[0].length

  return {
    block: {
      language,
      code: source.slice(contentStart, codeEnd),
      closed: true,
    },
    nextIndex: Math.max(nextIndex, codeEnd + closingTokenLength),
  }
}

export function parseTutorContentBlocks(text: string, options: ParseTutorContentOptions = {}): TutorContentBlock[] {
  const normalized = normalizeStreamingMarkdown(text, Boolean(options.isStreaming))
  const blocks: TutorContentBlock[] = []
  let cursor = 0

  while (cursor < normalized.length) {
    const fenceStart = normalized.slice(cursor).search(/(^|\n)(```|~~~)/)
    if (fenceStart < 0) {
      pushMarkdownBlock(blocks, normalized.slice(cursor))
      break
    }

    const absoluteFenceStart = cursor + fenceStart + (normalized.slice(cursor + fenceStart, cursor + fenceStart + 1) === '\n' ? 1 : 0)
    pushMarkdownBlock(blocks, normalized.slice(cursor, absoluteFenceStart))

    const parsed = parseFenceBlock(normalized, absoluteFenceStart)
    if (!parsed) {
      pushMarkdownBlock(blocks, normalized.slice(absoluteFenceStart))
      break
    }

    const normalizedLanguage = parsed.block.language || 'text'
    const code = parsed.block.code.replace(/\r\n/g, '\n').trimEnd()
    blocks.push({
      type: 'code',
      code,
      language: normalizedLanguage,
      html: options.isStreaming
        ? renderStreamingCodeBlockHtml(code, normalizedLanguage)
        : renderCodeBlockHtml(code, normalizedLanguage),
    })
    cursor = parsed.nextIndex
  }
  
  const filtered = blocks.filter(b => b.type === 'code' || (b.type === 'markdown' && b.html?.trim() !== ''))
  return filtered.length > 0 ? filtered : [{ type: 'markdown', html: '' }]
}