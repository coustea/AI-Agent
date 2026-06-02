import hljs from 'highlight.js'
import MarkdownIt from 'markdown-it'
import markdownItKatex from 'markdown-it-katex'
import 'katex/dist/katex.min.css'

const copiedCodeLanguages = new Set([
  'bash', 'c', 'cpp', 'c++', 'css', 'go', 'html', 'java', 'javascript',
  'js', 'json', 'jsx', 'python', 'py', 'sql', 'ts', 'tsx', 'typescript',
  'vue', 'xml', 'yaml', 'yml',
])

const knownFenceLanguages = Array.from(new Set([
  'typescript', 'javascript', 'markdown', 'python', 'json', 'bash', 'html',
  'tsx', 'jsx', 'vue', 'sql', 'css', 'xml', 'yaml', 'java', 'text', 'plain',
  'shell', 'sh', 'ts', 'js', 'py', 'go', 'cpp', 'c++', 'c',
])).sort((left, right) => right.length - left.length)

const canonicalFenceLanguageMap: Record<string, string> = {
  py: 'python',
  js: 'javascript',
  ts: 'typescript',
  sh: 'shell',
  yml: 'yaml',
  'c++': 'cpp',
  plain: 'text',
}

const fencePattern = /(^|\n)(`{3,}|~{3,})/g
const sectionHeadingPattern = /^([一二三四五六七八九十]+\s*[、.．]|方式\d+[:：]|第\d+[步部分点节][:：]|最后[：:]|总结[：:])/

const baseMarkdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: false,
  typographer: false,
})

const streamingMarkdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: false,
  typographer: false,
})

baseMarkdown.use(markdownItKatex)
streamingMarkdown.use(markdownItKatex)

function escapeHtml(raw: string): string {
  return raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function getFenceLanguage(info: string): string {
  return info.trim().split(/\s+/, 1)[0]?.toLowerCase() ?? ''
}

function getDisplayFenceLanguage(language: string): string {
  const normalized = language.trim().toLowerCase()
  if (!normalized) return 'text'
  return canonicalFenceLanguageMap[normalized] || normalized
}

function looksLikeFenceCodeStart(fragment: string): boolean {
  return /^[#</{\[(\w@'"`-]|^from\s+|^import\s+|^class\s+|^def\s+|^const\s+|^let\s+|^var\s+|^function\s+/.test(fragment)
}

function repairMalformedFenceOpeners(text: string): string {
  if (!text) return text

  return text
    .split('\n')
    .map((line) => {
      const matched = line.match(/^(\s*)(`{3,}|~{3,})([^\s].*)$/)
      if (!matched) return line

      const indent = matched[1] ?? ''
      const fence = matched[2] ?? '```'
      const rest = matched[3] ?? ''
      const lowerRest = rest.toLowerCase()

      for (const language of knownFenceLanguages) {
        if (!lowerRest.startsWith(language) || rest.length <= language.length) continue

        const trailing = rest.slice(language.length)
        if (!looksLikeFenceCodeStart(trailing)) continue

        return `${indent}${fence}${language}\n${trailing}`
      }

      return line
    })
    .join('\n')
}

function repairSplitFenceLanguages(text: string): string {
  if (!text) return text

  const lines = text.split('\n')
  const repaired: string[] = []

  for (let index = 0; index < lines.length; index += 1) {
    const current = lines[index] ?? ''
    const matched = current.match(/^(\s*)(`{3,}|~{3,})([A-Za-z+#-]+)?\s*$/)
    if (!matched) {
      repaired.push(current)
      continue
    }

    const prefix = (matched[3] ?? '').toLowerCase()
    const nextLine = lines[index + 1] ?? ''
    if (!prefix || !nextLine.trim()) {
      repaired.push(current)
      continue
    }

    const candidate = `${prefix}${nextLine.trim().toLowerCase()}`
    const canonical = knownFenceLanguages.find((language) => language === candidate)
    if (!canonical) {
      repaired.push(current)
      continue
    }

    repaired.push(`${matched[1] ?? ''}${matched[2] ?? '```'}${canonical}`)
    index += 1
  }

  return repaired.join('\n')
}

function renderHighlightedCode(code: string, language: string): string {
  if (language && hljs.getLanguage(language)) {
    try {
      return hljs.highlight(code, { language, ignoreIllegals: true }).value
    } catch {
      return escapeHtml(code)
    }
  }

  try {
    return hljs.highlightAuto(code).value
  } catch {
    return escapeHtml(code)
  }
}

const defaultLinkOpen
  = streamingMarkdown.renderer.rules.link_open
  || ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))

function patchLinkOpen(renderer: MarkdownIt['renderer']) {
  const currentLinkOpen = renderer.rules.link_open
    || ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))

  renderer.rules.link_open = (tokens, idx, options, _env, self) => {
    tokens[idx]?.attrSet('target', '_blank')
    tokens[idx]?.attrSet('rel', 'noopener noreferrer nofollow')
    return currentLinkOpen(tokens, idx, options, _env, self)
  }
}

patchLinkOpen(baseMarkdown.renderer)
streamingMarkdown.renderer.rules.link_open = (tokens, idx, options, _env, self) => {
  tokens[idx]?.attrSet('target', '_blank')
  tokens[idx]?.attrSet('rel', 'noopener noreferrer nofollow')
  return defaultLinkOpen(tokens, idx, options, _env, self)
}

const defaultFenceRender
  = streamingMarkdown.renderer.rules.fence
  || ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))

streamingMarkdown.renderer.rules.fence = (tokens, idx, options, _env, self) => {
  const token = tokens[idx]
  if (!token) return defaultFenceRender(tokens, idx, options, _env, self)

  const language = getFenceLanguage(token.info || '')
  const code = token.content || ''
  const highlightedCode = renderHighlightedCode(code, language)
  const languageClass = language ? `language-${escapeHtml(language)} ` : ''
  const displayLang = getDisplayFenceLanguage(language)

  return `<div class="code-block-wrapper">
  <div class="code-block-header">
    <span class="code-block-lang">${escapeHtml(displayLang)}</span>
    <button class="code-block-copy-btn">复制</button>
  </div>
  <pre><code class="${languageClass}hljs">${highlightedCode}</code></pre>
</div>`
}

function isCopiedCodeStart(lines: string[], index: number): boolean {
  const language = lines[index]?.trim().toLowerCase()
  const copyLabel = lines[index + 1]?.trim()
  if (!language || !copiedCodeLanguages.has(language)) return false
  if (copyLabel !== '复制' && copyLabel !== '复制代码') return false

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

function looksLikeCodeLine(line: string): boolean {
  const trimmed = line.trim()
  if (!trimmed) return false
  if (/^(public|private|protected|class|interface|enum|import|package)\b/.test(trimmed)) return true
  if (/^(def|class|from|import|if|elif|else:|for|while|try:|except|return|print)\b/.test(trimmed)) return true
  if (/^(const|let|var|function|export|async|await)\b/.test(trimmed)) return true
  if (/^(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|WITH)\b/i.test(trimmed)) return true
  if (/^[A-Za-z_$][\w$]*\s*=\s*.+/.test(trimmed)) return true
  if (/^[}\])];?$/.test(trimmed)) return true
  if (/[{}();]/.test(trimmed)) return true
  if (/\/\/|\/\*|\*\/|#/.test(trimmed)) return true
  return false
}

function inferCodeLanguage(lines: string[]): string {
  const joined = lines.join('\n')
  if (/\b(public|private|protected|class)\b/.test(joined) || /System\.out\.println/.test(joined)) return 'java'
  if (/\b(def|print|elif|None|True|False)\b/.test(joined)) return 'python'
  if (/\b(const|let|var|function|=>)\b/.test(joined)) return 'javascript'
  if (/\b(interface|type)\b/.test(joined)) return 'typescript'
  if (/^\s*<[^>]+>/.test(joined)) return 'html'
  if (/\bSELECT\b|\bFROM\b|\bWHERE\b/i.test(joined)) return 'sql'
  return 'text'
}

function repairLooseCodeBlocks(text: string): string {
  if (!text) return text
  const lines = text.split('\n')
  const repaired: string[] = []

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index] ?? ''
    repaired.push(line)

    if (!/(代码示例|示例代码|参考代码|如下代码|代码如下)\s*[:：]?\s*$/.test(line.trim())) {
      continue
    }

    let probe = index + 1
    while (probe < lines.length && !(lines[probe] ?? '').trim()) {
      repaired.push(lines[probe] ?? '')
      probe += 1
    }

    if (probe >= lines.length) break
    const firstCandidate = lines[probe] ?? ''
    if (/^\s*(`{3,}|~{3,})/.test(firstCandidate) || !looksLikeCodeLine(firstCandidate)) {
      index = probe - 1
      continue
    }

    const codeLines: string[] = []
    while (probe < lines.length) {
      const current = lines[probe] ?? ''
      if (!current.trim()) {
        codeLines.push(current)
        probe += 1
        continue
      }
      if (!looksLikeCodeLine(current)) break
      codeLines.push(current)
      probe += 1
    }

    if (!codeLines.length) {
      index = probe - 1
      continue
    }

    repaired.push(`\`\`\`${inferCodeLanguage(codeLines)}`)
    repaired.push(...codeLines)
    repaired.push('```')
    index = probe - 1
  }

  return repaired.join('\n')
}

function shouldPromoteInlineMath(content: string): boolean {
  const normalized = content.replace(/\s+/g, ' ').trim()
  if (!normalized) return false

  if (/\\begin\{|\\end\{|\\sum|\\int|\\lim|\\prod|\\frac|\\sqrt|\\displaystyle|\\left|\\right/.test(normalized)) {
    return true
  }

  if ((normalized.match(/\^|_/g) || []).length >= 3) {
    return true
  }

  return normalized.length >= 40
}

function promoteComplexInlineMath(text: string): string {
  if (!text) return text

  return text.replace(/\$([^$\n]+)\$/g, (matched, content: string) => {
    if (!shouldPromoteInlineMath(content)) return matched
    return `\n$$\n${content.trim()}\n$$\n`
  })
}

function repairSingleLineDelimitedMathBlocks(text: string): string {
  if (!text) return text

  const lines = text.split('\n')
  const repaired: string[] = []

  for (let index = 0; index < lines.length; index += 1) {
    const current = lines[index] ?? ''
    if (current.trim() !== '$') {
      repaired.push(current)
      continue
    }

    let probe = index + 1
    const mathLines: string[] = []
    let foundClosing = false

    while (probe < lines.length) {
      const line = lines[probe] ?? ''
      if (line.trim() === '$') {
        foundClosing = true
        break
      }
      mathLines.push(line)
      probe += 1
    }

    if (!foundClosing || !mathLines.some((line) => line.trim())) {
      repaired.push(current)
      continue
    }

    repaired.push('$$')
    repaired.push(...mathLines)
    repaired.push('$$')
    index = probe
  }

  return repaired.join('\n')
}

function repairEscapedMathDelimiters(text: string): string {
  if (!text) return text

  return text
    .replace(/\\\$/g, '$')
    .replace(/\\([()[\]])/g, '\\$1')
}

function normalizeLatexDelimiters(text: string): string {
  if (!text) return text

  return text
    .replace(/\\\[((?:.|\n)*?)\\\]/g, (_matched, content: string) => `\n$$\n${content.trim()}\n$$\n`)
    .replace(/\\\(((?:.|\n)*?)\\\)/g, (_matched, content: string) => `$${content.trim()}$`)
}

function repairMissingLatexCommands(text: string): string {
  if (!text) return text

  return text
    .replace(/(^|[^\\a-zA-Z])(int_|iint_|iiint_|oint_|sum_|prod_|lim_)/g, '$1\\$2')
    .replace(/(^|[^\\a-zA-Z])(frac|sqrt|sin|cos|tan|cot|sec|csc|ln|log|exp|to|rightarrow|infty|cdots|ldots|mathrm|mathbf|boldsymbol|operatorname\*?)\b/g, '$1\\$2')
    .replace(/(^|[^\\a-zA-Z])(left|right)(?=\s*[\(\)\[\]\{\}|])/g, '$1\\$2')
}

function repairBrokenDelimiterCommands(text: string): string {
  if (!text) return text

  return text
    .replace(/\\left\{/g, '\\left\\{')
    .replace(/\\right\}(?![\])}])/g, '\\right\\}')
    .replace(/\\right\\(?=\s|$)/g, '\\right\\}')
    .replace(/\\left\[/g, '\\left[')
    .replace(/\\right\]/g, '\\right]')
    .replace(/\\left\(/g, '\\left(')
    .replace(/\\right\)/g, '\\right)')
}

function repairIsolatedDollarBlocks(text: string): string {
  if (!text) return text

  const lines = text.split('\n')
  const repaired: string[] = []

  for (let index = 0; index < lines.length; index += 1) {
    const current = lines[index] ?? ''
    if (current.trim() !== '$') {
      repaired.push(current)
      continue
    }

    let probe = index + 1
    while (probe < lines.length && !(lines[probe] ?? '').trim()) {
      probe += 1
    }

    const contentLine = lines[probe] ?? ''
    if (!contentLine.trim()) {
      repaired.push(current)
      continue
    }

    let closing = probe + 1
    while (closing < lines.length && !(lines[closing] ?? '').trim()) {
      closing += 1
    }

    if ((lines[closing] ?? '').trim() !== '$') {
      repaired.push(current)
      continue
    }

    const normalized = repairMissingLatexCommands(contentLine.trim())
    const isDisplayMath = /\\(?:int_|iint_|iiint_|oint_|sum_|prod_|lim_|frac|sqrt|begin|left|right)/.test(normalized)

    repaired.push(isDisplayMath ? '$$' : '$')
    repaired.push(normalized)
    repaired.push(isDisplayMath ? '$$' : '$')
    index = closing
  }

  return repaired.join('\n')
}

function repairCommonBrokenMathSyntax(text: string): string {
  if (!text) return text

  return text
    .replace(/\\\$(?=\s*$)/gm, '$')
    .replace(/\$\$(?=\S)/g, '$$\n')
    .replace(/(?<=\S)\$\$/g, '\n$$')
    .replace(/\$([^\n$]+?)\}\$/g, (_matched, content: string) => {
      const opens = (content.match(/\{/g) || []).length
      const closes = (content.match(/\}/g) || []).length
      if (opens >= closes) return `$${content}$`
      return `$${content.replace(/\}+$/g, '')}$`
    })
    .replace(/\$\$([^\n$]*?)\}\s*=\s*____/g, (_matched, content: string) => `$$${content}=____`)
    .replace(/\$([^\n$]*?)\}\s*=\s*____/g, (_matched, content: string) => `$${content}=____`)
    .replace(/\\left\(/g, '\\left(')
    .replace(/\\right\)/g, '\\right)')
}

function repairBrokenMultilineInlineMath(text: string): string {
  if (!text) return text

  return text.replace(
    /\$([^$]*?(?:\n[^$]*?)*)\n\s*\$(?=\s|$)/g,
    (_matched, content: string) => `$$\n${content.trim()}\n$$`,
  )
}

function normalizeMathBlocks(text: string): string {
  if (!text) return text

  return text
    .replace(/[ \t]*\$\$[ \t]*/g, '\n$$\n')
    .replace(/\$\$\n+_{2,}/g, '$$\n\n____')
    .replace(/([^\n])(\$\$)/g, '$1\n$2')
    .replace(/(\$\$)([^\n])/g, '$1\n$2')
    .replace(/([^\n])(\$[^$\n]+\$)/g, '$1 $2')
    .replace(/(\$[^$\n]+\$)([^\s\n])/g, '$1 $2')
    .replace(/([^\n])(\\begin\{(?:cases|aligned|array|matrix|pmatrix|bmatrix)\})/g, '$1\n$2')
    .replace(/(\\end\{(?:cases|aligned|array|matrix|pmatrix|bmatrix)\})([^\n])/g, '$1\n$2')
    .replace(/([^\n])(\\\[)/g, '$1\n$2')
    .replace(/(\\\])([^\n])/g, '$1\n$2')
    .replace(/(\\begin\{cases\})/g, '$$\n$1')
    .replace(/(\\end\{cases\})/g, '$1\n$$')
    .replace(/(\$\$\n)(\s*\n)+/g, '$1')
    .replace(/(\n\$\$)([ \t]*)(\n\$\$)/g, '$1\n$3')
    .replace(/\n{3,}/g, '\n\n')
}

function containsMathSyntax(text: string): boolean {
  if (!text) return false
  const normalized = repairSingleLineDelimitedMathBlocks(text)
  return /(^|[^\\])\$(?!\s)|^\s*\$\$\s*$|\\\(|\\\[|\\begin\{(?:cases|aligned|array|matrix|pmatrix|bmatrix)\}/m.test(normalized)
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
  const repairedBase = repairLooseCodeBlocks(
    repairSplitFenceLanguages(
      repairMalformedFenceOpeners(
        repairCopiedCodeBlocks(text),
      ),
    ),
  )

  if (!containsMathSyntax(repairedBase)) {
    const repaired = repairedBase
    if (!isStreaming || !repaired) return repaired

    const fences = repaired.match(fencePattern)
    if (!fences || fences.length % 2 === 0) return repaired

    return `${repaired}\n\`\`\``
  }

  const repaired = normalizeMathBlocks(
    promoteComplexInlineMath(
      repairBrokenMultilineInlineMath(
        repairCommonBrokenMathSyntax(
          repairBrokenDelimiterCommands(
            repairMissingLatexCommands(
              normalizeLatexDelimiters(
                repairIsolatedDollarBlocks(
                  repairSingleLineDelimitedMathBlocks(
                    repairEscapedMathDelimiters(repairedBase),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    ),
  )
  if (!isStreaming || !repaired) return repaired

  const fences = repaired.match(fencePattern)
  if (!fences || fences.length % 2 === 0) return repaired

  return `${repaired}\n\`\`\``
}

export function renderStreamingMarkdownHtml(text: string): string {
  const normalized = normalizeStreamingMarkdown(text, true)
  if (!normalized.trim()) return ''

  try {
    return streamingMarkdown.render(normalized)
  } catch {
    return baseMarkdown.render(normalized || text || '')
  }
}
