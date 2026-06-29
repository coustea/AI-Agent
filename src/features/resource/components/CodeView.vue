<template>
  <div class="code-resource" :class="{ compact }" @click="handleMessageClick" ref="rootRef">
    <ResourceCardWrapper v-if="parsedData || markdownContent" :compact="compact" class="code-card-content">
      <div v-if="!compact && parsedData?.explanation" class="code-header-meta">
        <span class="code-summary-text">{{ parsedData.explanation }}</span>
      </div>

      <div class="code-main-body">
        <div v-if="displayMarkdown" class="markdown-shell code-markdown-shell">
          <MarkdownPreview :content="displayMarkdown" />
        </div>

        <div v-else-if="pureCode" class="code-block-wrapper pure-code-block">
          <div class="code-block-header">
            <span class="lang-label">{{ pureLanguage.toUpperCase() }}</span>
            <button class="code-copy-btn" type="button">复制</button>
          </div>
          <pre><code :class="`language-${pureLanguage}`">{{ pureCode }}</code></pre>
        </div>

        <div v-else-if="markdownContent" class="markdown-shell code-markdown-shell">
          <MarkdownPreview :content="markdownContent" />
        </div>
      </div>

      <div v-if="!compact && hasExtraInfo" class="code-footer-extras">
        <div class="footer-divider">
          <span class="divider-label">实现指标</span>
          <div class="divider-line"></div>
        </div>

        <div class="extras-grid">
          <div v-if="hasComplexity" class="extra-item complexity-info">
            <div class="extra-label"><Timer class='w-4 h-4 inline-block align-middle' /> 复杂度分析</div>
            <div class="extra-content">
              <span v-if="parsedData?.complexity?.time">时间: <code>{{ parsedData!.complexity!.time }}</code></span>
              <span v-if="parsedData?.complexity?.space" class="ml-4">空间: <code>{{ parsedData!.complexity!.space }}</code></span>
            </div>
          </div>

          <div v-if="parsedData?.debug_tips?.length" class="extra-item tips-info">
            <div class="extra-label"><Warning class='w-4 h-4 inline-block align-middle' /> 调试建议</div>
            <ul class="tips-list">
              <li v-for="(tip, idx) in parsedData!.debug_tips" :key="idx">{{ tip }}</li>
            </ul>
          </div>
        </div>

        <div v-if="parsedData?.exercises?.length" class="extra-item exercises-info">
          <div class="extra-label"><EditPen class='w-4 h-4 inline-block align-middle' /> 练习序列</div>
          <div class="exercises-container">
            <div v-for="(ex, idx) in parsedData!.exercises" :key="idx" class="exercise-item">
              <span class="ex-num">{{ (Number(idx) + 1).toString().padStart(2, '0') }}</span>
              <span class="ex-text">{{ typeof ex === 'string' ? ex : ex.question || ex.title }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="frame-footer">
        <span class="mono-tag">可执行</span>
        <div class="footer-line"></div>
      </div>
    </ResourceCardWrapper>

    <div v-else class="code-empty-hud">
      <div class="empty-frame">
        <div class="empty-icon">NULL</div>
        <p>未检测到代码内容</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import {
  PhClock as Timer,
  PhWarning as Warning,
  PhNotePencil as EditPen
} from '@phosphor-icons/vue'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { toast } from 'vue-sonner'
import MarkdownPreview from '@/shared/ui/MarkdownPreview.vue'
import ResourceCardWrapper from './ResourceCardWrapper.vue'
import { parseJsonObject, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const rootRef = ref<HTMLElement | null>(null)

type FenceResult = {
  code: string
  language: string
}

const languageAlias: Record<string, string> = {
  py: 'python',
  js: 'javascript',
  ts: 'typescript',
  sh: 'bash',
  shell: 'bash',
  yml: 'yaml',
  md: 'markdown',
  cplusplus: 'cpp',
  'c++': 'cpp',
}

const knownLanguages = [
  'python', 'javascript', 'typescript', 'java', 'cpp', 'c', 'csharp', 'go', 'rust',
  'html', 'css', 'scss', 'vue', 'json', 'yaml', 'markdown', 'bash', 'shell', 'sql', 'xml', 'text'
]

function toText(value: unknown): string {
  if (typeof value === 'string') return value
  if (value == null) return ''
  return typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)
}

function normalizeLanguage(language: unknown, defaultLanguage = 'text'): string {
  const raw = toText(language || defaultLanguage).trim().toLowerCase()
  return languageAlias[raw] || raw || defaultLanguage
}

function unwrapFencedCode(text: string, defaultLanguage = 'text'): FenceResult {
  const trimmed = text.trim()
  const match = trimmed.match(/^```([\w#+.-]*)\s*\n([\s\S]*?)\n```$/)
  if (!match) return { code: text, language: normalizeLanguage(defaultLanguage) }
  return {
    language: normalizeLanguage(match[1]!, defaultLanguage),
    code: match[2]!.trimEnd(),
  }
}

function looksLikeMarkdownDocument(text: string): boolean {
  if (!text.trim()) return false

  const fenceCount = text.match(/```/g)?.length ?? 0
  if (fenceCount >= 2) return true

  const hasMarkdownTitle = /(^|\n)#{1,4}\s+\S/.test(text)
  const hasMarkdownList = /(^|\n)([-*]|\d+\.)\s+\S/.test(text)
  const hasCodeSignals = /(^|\n)\s*(import|from|def|class|#include|public\s+class|function|const|let|var)\b/.test(text)

  return hasMarkdownTitle && hasMarkdownList && !hasCodeSignals
}

const parsedData = computed(() => {
  if (!props.resultData) return null

  let raw: unknown = props.resultData
  if (typeof raw === 'string') {
    const parsed = parseJsonObject(raw)
    if (!parsed) return null
    raw = parsed
  }

  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null

  let data = raw as Record<string, any>
  if (data.resource && typeof data.resource === 'object' && !Array.isArray(data.resource)) {
    data = data.resource
  }

  const content = data.content
  if (content && typeof content === 'object' && !Array.isArray(content)) {
    return content as Record<string, any>
  }

  const parsedContent = parseJsonObject(content)
  if (parsedContent) return parsedContent

  if (data.code || data.full_code || data.markdown || data.markdown_content || data.language) return data

  return null
})

const displayMarkdown = computed(() => {
  const data = parsedData.value
  if (!data) return ''

  const explicitMarkdown = data.markdown || data.markdown_content || data.document || data.content_markdown
  if (typeof explicitMarkdown === 'string' && explicitMarkdown.trim()) return explicitMarkdown

  const codeContent = toText(data.code || data.full_code || '')
  return looksLikeMarkdownDocument(codeContent) ? codeContent : ''
})

const pureCodeInfo = computed(() => {
  if (displayMarkdown.value) return { code: '', language: 'text' }

  const data = parsedData.value
  if (!data) return { code: '', language: 'text' }

  const defaultLanguage = normalizeLanguage(data.language || data.lang || 'text')
  const codeContent = toText(data.code || data.full_code || '')
  if (!codeContent.trim()) return { code: '', language: defaultLanguage }

  return unwrapFencedCode(codeContent, defaultLanguage)
})

const pureCode = computed(() => pureCodeInfo.value.code)
const pureLanguage = computed(() => pureCodeInfo.value.language || 'text')

const markdownContent = computed(() => {
  if (parsedData.value) return ''
  return typeof props.resultData === 'string' ? props.resultData : ''
})

const hasExtraInfo = computed(() => {
  const data = parsedData.value
  return !!(data?.complexity?.time || data?.complexity?.space || data?.debug_tips?.length || data?.exercises?.length)
})

const hasComplexity = computed(() => {
  const complexity = parsedData.value?.complexity
  return !!(complexity?.time || complexity?.space)
})

function resolveLanguage(code: HTMLElement): string {
  const className = code.className || ''
  const match = className.match(/language-([\w#+.-]+)/)
  return normalizeLanguage(match?.[1] || pureLanguage.value || 'text').toUpperCase()
}

function looksLikeDetachedCodeToolbar(element: HTMLElement): boolean {
  const text = element.innerText.replace(/\s+/g, '').toLowerCase()
  if (!text || text.length > 28) return false

  const copyWords = ['复制', 'copy', 'copied', '已复制']
  const variants = knownLanguages.flatMap((lang) => [
    lang,
    `${lang}复制`,
    `${lang}copy`,
    `${lang}copied`,
    `${lang}已复制`,
  ])

  return variants.includes(text) || copyWords.includes(text)
}

function hideDetachedCodeToolbar(pre: HTMLElement) {
  const previous = pre.previousElementSibling as HTMLElement | null
  if (previous && looksLikeDetachedCodeToolbar(previous)) {
    previous.dataset.hiddenByCodeView = 'true'
    previous.style.display = 'none'
  }

  const parent = pre.parentElement as HTMLElement | null
  if (!parent) return

  Array.from(parent.children).forEach((child) => {
    if (child === pre || !(child instanceof HTMLElement)) return
    if (child.dataset.hiddenByCodeView === 'true') return
    if (looksLikeDetachedCodeToolbar(child)) {
      child.dataset.hiddenByCodeView = 'true'
      child.style.display = 'none'
    }
  })
}

// 核心优化：结构化渲染与高亮
const performHighlight = async () => {
  await nextTick()
  if (!rootRef.value) return

  const preBlocks = rootRef.value.querySelectorAll<HTMLElement>('pre')
  preBlocks.forEach((pre) => {
    const code = pre.querySelector<HTMLElement>('code')
    if (!code) return

    hideDetachedCodeToolbar(pre)

    // 对当前 Markdown 协议中的代码块执行高亮
    if (!code.dataset.highlighted && !code.classList.contains('hljs')) {
      try {
        hljs.highlightElement(code)
      } catch {}
    }

    const langText = resolveLanguage(code)

    // 如果已经被包裹（例如纯代码模式或已处理过的Markdown），只需更新语言标签
    if (pre.parentElement?.classList.contains('code-block-wrapper')) {
      const langLabel = pre.parentElement.querySelector('.lang-label')
      if (langLabel) (langLabel as HTMLElement).innerText = langText
      return
    }

    // --- 对未经包裹的 Markdown 生成的 <pre> 进行结构重组 ---
    const wrapper = document.createElement('div')
    wrapper.className = 'code-block-wrapper'

    const header = document.createElement('div')
    header.className = 'code-block-header'

    const langLabel = document.createElement('span')
    langLabel.className = 'lang-label'
    langLabel.innerText = langText

    const btn = document.createElement('button')
    btn.className = 'code-copy-btn'
    btn.innerText = '复制'
    btn.type = 'button'

    header.appendChild(langLabel)
    header.appendChild(btn)

    // 将新建的容器插入原先 <pre> 的位置，并把 <pre> 移入容器中
    pre.parentNode?.insertBefore(wrapper, pre)
    wrapper.appendChild(header)
    wrapper.appendChild(pre)

    // 移除 markdown 解析器可能自带的旧复制按钮
    const oldBtns = pre.querySelectorAll('button')
    oldBtns.forEach(b => b.remove())
  })
}

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    toast.success({ message: '代码已复制', plain: true })
  } catch {
    toast.error({ message: '复制失败，请重试', plain: true })
  }
}

const handleMessageClick = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (!target?.classList.contains('code-copy-btn')) return

  // 从顶层卡片向下寻找 code 内容，避免将数千行代码写入 data 属性
  const wrapper = target.closest('.code-block-wrapper')
  const codeNode = wrapper?.querySelector('code')
  const codeContent = codeNode?.innerText || codeNode?.textContent || ''

  if (!codeContent) return

  copyToClipboard(codeContent)
  const originalText = target.innerText
  target.innerText = '已复制'
  target.classList.add('copied')

  window.setTimeout(() => {
    target.innerText = originalText
    target.classList.remove('copied')
  }, 1400)
}

onMounted(performHighlight)
watch([parsedData, displayMarkdown, pureCode, markdownContent], performHighlight, { flush: 'post' })
</script>

<style scoped>
.code-resource {
  min-width: 0;
  width: 100%;
  --primary: var(--color-primary);
  --bg: var(--color-surface);
  --fg: var(--color-text);
  --border: var(--color-border);
  --accent: var(--color-primary);
  --code-bg: #ffffff;
  --code-head-bg: #f8fafc;
  --code-border: #e2e8f0;
  --code-text: #24292f;
}

.code-card-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.code-main-body {
  min-width: 0;
}

.code-header-meta {
  margin-bottom: 4px;
}

.code-summary-text {
  color: var(--color-text-secondary);
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.6;
}

.markdown-shell {
  min-width: 0;
  color: var(--fg);
  line-height: 1.78;
  overflow-wrap: anywhere;
  font-family: var(--font-sans, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
  font-size: 0.96rem;
}

.code-markdown-shell :deep(h1),
.code-markdown-shell :deep(h2),
.code-markdown-shell :deep(h3) {
  margin: 1.7em 0 0.85em;
  padding-bottom: 0.48em;
  border-bottom: 1px solid #e5e7eb;
  color: var(--color-text-strong);
  font-family: var(--font-sans, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
  line-height: 1.35;
  font-weight: 700;
}

.code-markdown-shell :deep(h1) { font-size: 1.42rem; }
.code-markdown-shell :deep(h2) { font-size: 1.18rem; }
.code-markdown-shell :deep(h3) { font-size: 1.02rem; }

.code-markdown-shell :deep(p) {
  margin: 0.85em 0;
  color: var(--color-text-secondary);
}

.code-markdown-shell :deep(ul),
.code-markdown-shell :deep(ol) {
  padding-left: 1.35em;
  margin: 0.85em 0;
}

.code-markdown-shell :deep(li) { margin: 0.35em 0; }

.code-markdown-shell :deep(blockquote) {
  margin: 1em 0;
  padding: 10px 14px;
  border-left: 3px solid var(--color-primary-border, var(--primary));
  background: #f8fafc;
  color: var(--color-text-secondary);
  border-radius: 0 10px 10px 0;
}

/* --- 重构的代码块卡片外观 --- */

.code-resource :deep(.code-block-wrapper) {
  margin: 1.2em 0;
  border: 1px solid var(--code-border);
  border-radius: 10px;
  background: var(--code-bg);
  overflow: hidden; /* 保证圆角能裁剪内部区域 */
  box-shadow: 0 2px 14px rgba(15, 23, 42, 0.03);
}

.code-resource :deep(.code-block-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: var(--code-head-bg);
  border-bottom: 1px solid var(--code-border);
}

.code-resource :deep(.lang-label) {
  font-size: 0.75rem;
  color: #64748b;
  font-family: var(--font-mono, Consolas, monospace);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.code-resource :deep(.code-copy-btn) {
  font-size: 0.75rem;
  color: #64748b;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 4px 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: var(--font-sans, system-ui, sans-serif);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  outline: none;
}

.code-resource :deep(.code-copy-btn:hover) {
  background: #f1f5f9;
  color: #334155;
  border-color: #94a3b8;
}

.code-resource :deep(.code-copy-btn.copied) {
  color: #059669;
  border-color: #34d399;
  background: #ecfdf5;
}

/* 内部代码区域完全撑开显示 */
.code-resource :deep(.code-block-wrapper pre) {
  margin: 0 !important;
  padding: 18px !important;
  border: none !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  overflow-x: auto;
  overflow-y: hidden;
}

.code-resource :deep(pre code),
.code-resource :deep(.code-block-wrapper code) {
  display: block;
  min-width: max-content;
  padding: 0;
  background: transparent !important;
  color: var(--code-text) !important;
  font-family: var(--font-mono, "JetBrains Mono", "Fira Code", Consolas, monospace);
  font-size: 0.9rem;
  line-height: 1.76;
  white-space: pre;
  tab-size: 4;
}

.code-resource :deep(.hljs) {
  background: transparent !important;
  color: var(--code-text) !important;
}

.code-resource :deep(pre::-webkit-scrollbar) {
  width: 10px;
  height: 10px;
}

.code-resource :deep(pre::-webkit-scrollbar-track) {
  background: transparent;
}

.code-resource :deep(pre::-webkit-scrollbar-thumb) {
  border: 3px solid transparent;
  border-radius: 999px;
  background-clip: padding-box;
  background-color: #cbd5e1;
}

.code-resource :deep(pre::-webkit-scrollbar-thumb:hover) {
  background-color: #94a3b8;
}

/* 行内小代码块样式 */
.code-resource :deep(:not(pre) > code) {
  padding: 0.16em 0.42em;
  border: 1px solid #dbeafe;
  border-radius: 6px;
  background: #eff6ff !important;
  color: #1d4ed8;
  font-family: var(--font-mono, "JetBrains Mono", Consolas, monospace);
  font-size: 0.86em;
  font-weight: 600;
}

/* --- 隐藏兜底工具栏 --- */
.code-resource :deep([data-hidden-by-code-view="true"]) {
  display: none !important;
}

/* --- hljs 浅色主题配色调优 --- */
.code-resource :deep(.hljs-comment),
.code-resource :deep(.hljs-quote) {
  color: #6a737d !important;
  font-style: italic;
}

.code-resource :deep(.hljs-keyword),
.code-resource :deep(.hljs-selector-tag) {
  color: #d73a49 !important;
  font-weight: 700;
}

.code-resource :deep(.hljs-string),
.code-resource :deep(.hljs-attr),
.code-resource :deep(.hljs-symbol) {
  color: #22863a !important;
}

.code-resource :deep(.hljs-title),
.code-resource :deep(.hljs-title.function_),
.code-resource :deep(.hljs-section) {
  color: #6f42c1 !important;
  font-weight: 700;
}

.code-resource :deep(.hljs-number),
.code-resource :deep(.hljs-literal),
.code-resource :deep(.hljs-boolean) {
  color: #005cc5 !important;
}

.code-resource :deep(.hljs-built_in),
.code-resource :deep(.hljs-type),
.code-resource :deep(.hljs-class .hljs-title) {
  color: #e36209 !important;
}

.code-resource :deep(.hljs-variable),
.code-resource :deep(.hljs-template-variable) {
  color: #24292f !important;
}

/* --- 底部执行标签栏 --- */

.frame-footer {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.mono-tag {
  padding: 4px 12px;
  border-radius: 999px;
  background: #e6f7ec; /* 清新浅绿色背景 */
  color: #0aa55a;      /* 绿色文本 */
  font-family: var(--font-mono, "JetBrains Mono", Consolas, monospace);
  font-size: 0.75rem;
  font-weight: 600;
}

.footer-line {
  flex: 1;
  height: 1px;
  background: #e2e8f0; /* 实色浅灰线条 */
}

/* --- 其余复杂度及练习题样式保持一致 --- */

.code-footer-extras {
  margin-top: 16px;
  padding: 18px;
  border: 1px solid var(--code-border);
  border-radius: 14px;
  background: #f8fafc;
}

.footer-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.divider-label {
  font-family: var(--font-mono, "JetBrains Mono", Consolas, monospace);
  font-size: 0.75rem;
  color: var(--primary);
  letter-spacing: 1px;
  font-weight: 700;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, var(--border), transparent);
}

.extras-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
  margin-bottom: 18px;
}

.extra-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.extra-label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--primary);
  font-family: var(--font-mono, "JetBrains Mono", Consolas, monospace);
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.extra-content {
  color: var(--code-text);
  font-family: var(--font-mono, "JetBrains Mono", Consolas, monospace);
  font-size: 0.9rem;
}

.extra-content code {
  padding: 2px 6px;
  border-radius: 6px;
  background: #e0f2fe;
  color: #0369a1;
  font-weight: 700;
}

.tips-list {
  margin: 0;
  padding-left: 20px;
  color: var(--color-text-secondary);
  font-family: var(--font-sans, system-ui, sans-serif);
  font-size: 0.9rem;
  line-height: 1.65;
}

.exercises-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 4px;
}

.exercise-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border: 1px solid var(--code-border);
  border-radius: 10px;
  background: #ffffff;
  color: var(--code-text);
  font-family: var(--font-sans, system-ui, sans-serif);
  font-size: 0.92rem;
  transition: border-color 0.18s ease, transform 0.18s ease;
}

.exercise-item:hover {
  border-color: var(--primary);
  transform: translateX(4px);
}

.ex-num {
  flex-shrink: 0;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--color-primary-soft, #eef2ff);
  color: var(--primary);
  font-family: var(--font-mono, "JetBrains Mono", Consolas, monospace);
  font-size: 0.78rem;
  font-weight: 700;
}

.code-empty-hud {
  padding: 48px;
  border: 1px dashed var(--border);
  border-radius: 14px;
  background: #f8fafc;
  color: var(--primary);
  text-align: center;
}

.empty-frame {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.empty-icon {
  font-family: var(--font-mono, "JetBrains Mono", Consolas, monospace);
  font-size: 1.8rem;
  opacity: 0.55;
}

.compact .markdown-shell {
  max-height: 300px;
  overflow: hidden;
  font-size: 0.86rem;
  mask-image: linear-gradient(to bottom, #000 70%, transparent 100%);
}
</style>
