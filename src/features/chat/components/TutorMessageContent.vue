<template>
  <div class="tutor-message-content">
    <div
      class="stream-markdown markdown-body tutor-markdown-block"
      :class="{ 'is-streaming': props.isStreaming }"
      v-html="streamingHtml"
      @click="handleContentClick"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { toast } from 'vue-sonner'
import { renderStreamingMarkdownHtml } from '@/shared/utils/markdown'

const props = defineProps<{
  content: string
  isStreaming?: boolean
}>()

const streamingHtml = ref('')
let renderTimer: ReturnType<typeof setTimeout> | null = null

const normalizeComparisonTables = (text: string): string => {
  if (!text || !text.includes('对比项')) return text

  return text
    .split('\n')
    .map((line) => {
      if (!line.trim()) return line
      if (line.includes('对比项') && !line.includes('|')) {
        return line.replace(/\s{2,}/g, ' | ').replace(/^/, '| ').replace(/$/, ' |')
      }
      if (/^-{3,}\s+-{3,}/.test(line.trim()) && !line.includes('|')) {
        return line.replace(/\s{2,}/g, ' | ').replace(/^/, '| ').replace(/$/, ' |')
      }
      if (/^\S+\s{2,}\S+/.test(line) && !line.includes('|')) {
        return line.replace(/\s{2,}/g, ' | ').replace(/^/, '| ').replace(/$/, ' |')
      }
      return line
    })
    .join('\n')
}

const renderContentHtml = () => {
  const normalized = normalizeComparisonTables(props.content || '')
  const html = renderStreamingMarkdownHtml(normalized, props.isStreaming)
  streamingHtml.value = props.isStreaming ? appendStreamingCaret(html) : html
}

const appendStreamingCaret = (html: string): string => {
  if (!html.trim()) return html

  const template = document.createElement('template')
  template.innerHTML = html

  const candidates = Array.from(template.content.querySelectorAll<HTMLElement>(
    'p, li, h1, h2, h3, h4, h5, h6, td, th, blockquote, pre code',
  )).filter((element) => !element.closest('.code-block-header'))
  const target = candidates[candidates.length - 1]
  if (!target) return `${html}<span class="stream-caret" aria-hidden="true"></span>`

  const caret = document.createElement('span')
  caret.className = 'stream-caret'
  caret.setAttribute('aria-hidden', 'true')
  target.appendChild(caret)

  return template.innerHTML
}

const handleContentClick = async (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (!target.classList.contains('code-block-copy-btn')) return

  const wrapper = target.closest('.code-block-wrapper')
  const code = wrapper?.querySelector('code')
  if (!code) return

  try {
    await navigator.clipboard.writeText(code.textContent || '')
    const originalText = target.innerText
    target.innerText = '已复制'
    target.classList.add('copied')
    toast.success('代码已复制到剪贴板')

    setTimeout(() => {
      target.innerText = originalText
      target.classList.remove('copied')
    }, 1600)
  } catch (error) {
    console.error('Copy failed:', error)
    toast.error('复制失败，请重试')
  }
}

const shouldRenderMarkdownNow = (text: string): boolean => {
  if (!text) return true
  return /(\n\n|\r\n\r\n|\n[-*]\s|\n\d+\.\s|\n#{1,6}\s|[。！？?!?]\s*$|`{3,}\s*$)/.test(text)
}

const commitStreamingHtml = () => {
  renderTimer = null
  renderContentHtml()
}

watch(
  () => props.content,
  () => {
    if (!props.isStreaming) {
      if (renderTimer) {
        clearTimeout(renderTimer)
        renderTimer = null
      }
      commitStreamingHtml()
      return
    }

    if (shouldRenderMarkdownNow(props.content || '')) {
      if (renderTimer) {
        clearTimeout(renderTimer)
        renderTimer = null
      }
      commitStreamingHtml()
      return
    }

    if (renderTimer) return
    renderTimer = setTimeout(commitStreamingHtml, 75)
  },
  { immediate: true },
)

watch(
  () => props.isStreaming,
  (isStreaming) => {
    if (!isStreaming) {
      if (renderTimer) {
        clearTimeout(renderTimer)
        renderTimer = null
      }
      commitStreamingHtml()
    }
  },
)

onBeforeUnmount(() => {
  if (renderTimer) clearTimeout(renderTimer)
})
</script>

<style scoped>
.tutor-message-content {
  min-width: 0;
}

.tutor-markdown-block {
  min-width: 0;
}

.stream-markdown {
  min-width: 0;
  color: inherit;
  font-size: 0.96rem;
  line-height: 1.78;
  overflow-wrap: anywhere;
}

.stream-markdown :deep(.stream-caret) {
  display: inline-block;
  width: 2px;
  height: 1.05em;
  margin-left: 3px;
  background: currentColor;
  border-radius: 1px;
  vertical-align: -0.12em;
  content: '';
  animation: stream-caret 0.85s steps(1) infinite;
}

.stream-markdown :deep(p) {
  margin: 0 0 0.72rem;
}

.stream-markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.stream-markdown :deep(h1),
.stream-markdown :deep(h2),
.stream-markdown :deep(h3),
.stream-markdown :deep(h4) {
  margin: 1.1rem 0 0.5rem;
  color: var(--color-text);
  font-weight: 720;
  line-height: 1.42;
}

.stream-markdown :deep(h1) { font-size: 1.22rem; }
.stream-markdown :deep(h2) { font-size: 1.12rem; }
.stream-markdown :deep(h3) { font-size: 1.03rem; }
.stream-markdown :deep(h4) { font-size: 0.98rem; }

.stream-markdown :deep(ul),
.stream-markdown :deep(ol) {
  display: grid;
  gap: 0.28rem;
  margin: 0.6rem 0 0.8rem;
  padding-left: 1.35rem;
}

.stream-markdown :deep(li) {
  padding-left: 0.12rem;
}

.stream-markdown :deep(a) {
  color: #2563eb;
  text-decoration: underline;
  text-decoration-color: color-mix(in srgb, #2563eb 35%, transparent);
  text-underline-offset: 3px;
}

.stream-markdown :deep(blockquote) {
  margin: 0.85rem 0;
  padding: 0.55rem 0.8rem;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  border-left: 3px solid #94a3b8;
}

.stream-markdown :deep(hr) {
  margin: 1rem 0;
  border: 0;
  border-top: 1px solid var(--color-border);
}

.stream-markdown :deep(table) {
  display: table;
  width: 100%;
  margin: 0.9rem 0;
  border-collapse: separate;
  border-spacing: 0;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 0.9rem;
}

.stream-markdown :deep(th),
.stream-markdown :deep(td) {
  padding: 0.7rem 0.78rem;
  border-right: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
  text-align: left;
  vertical-align: top;
}

.stream-markdown :deep(th:last-child),
.stream-markdown :deep(td:last-child) {
  border-right: 0;
}

.stream-markdown :deep(tr:last-child td) {
  border-bottom: 0;
}

.stream-markdown :deep(th) {
  color: var(--color-text-secondary);
  background: #f8fafc;
  font-weight: 700;
}

.stream-markdown :deep(tr:nth-child(even) td) {
  background: #fcfcfd;
}

.stream-markdown :deep(code:not(pre code)) {
  padding: 0.12rem 0.34rem;
  color: #be123c;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 0.88em;
}

.stream-markdown :deep(.hljs-comment),
.stream-markdown :deep(.hljs-quote) {
  color: #15803d !important;
  font-style: normal;
}

.stream-markdown :deep(.code-block-wrapper) {
  margin: 0.9rem 0;
  overflow: hidden;
  background: #fbfcfe;
  border: 1px solid #dfe4ea;
  border-radius: 8px;
}

.stream-markdown :deep(.code-block-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  min-height: 38px;
  padding: 0.5rem 0.72rem;
  background: #f4f6f8;
  border-bottom: 1px solid #dfe4ea;
}

.stream-markdown :deep(.code-block-lang) {
  min-width: 0;
  color: #64748b;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  user-select: none;
  white-space: nowrap;
}

.stream-markdown :deep(.code-block-copy-btn) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex: 0 0 auto;
  padding: 4px 7px;
  color: #64748b;
  background: #fff;
  border: 1px solid #dfe4ea;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.72rem;
  transition: border-color 150ms ease, color 150ms ease, background 150ms ease;
}

.stream-markdown :deep(.code-block-copy-btn:hover) {
  color: #334155;
  background: #f8fafc;
  border-color: #cbd5e1;
}

.stream-markdown :deep(.code-block-copy-btn.copied) {
  color: #15803d;
  border-color: #86efac;
}

.stream-markdown :deep(.code-block-wrapper pre) {
  margin: 0;
  padding: 15px 16px;
  overflow-x: auto;
  background: transparent;
  font-size: 0.88rem;
  line-height: 1.65;
}

.stream-markdown :deep(.code-block-wrapper code) {
  font-family: var(--font-mono);
}

@keyframes stream-caret {
  0%, 45% { opacity: 1; }
  46%, 100% { opacity: 0; }
}

@media (max-width: 640px) {
  .stream-markdown {
    font-size: 0.93rem;
    line-height: 1.72;
  }

  .stream-markdown :deep(table) {
    display: block;
    overflow-x: auto;
    white-space: nowrap;
  }
}

@media (prefers-reduced-motion: reduce) {
  .stream-markdown :deep(.stream-caret) {
    animation: none;
  }
}
</style>
