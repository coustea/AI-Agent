<template>
  <div class="tutor-message-content">
    <div
      class="stream-markdown markdown-body tutor-markdown-block"
      v-html="streamingHtml"
      @click="handleContentClick"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
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
  streamingHtml.value = renderStreamingMarkdownHtml(normalized)
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
    ElMessage.success('代码已复制到剪贴板')

    setTimeout(() => {
      target.innerText = originalText
      target.classList.remove('copied')
    }, 2000)
  } catch (error) {
    console.error('Copy failed:', error)
    ElMessage.error('复制失败，请重试')
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
    renderTimer = setTimeout(commitStreamingHtml, 90)
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
  if (renderTimer) {
    clearTimeout(renderTimer)
    renderTimer = null
  }
})
</script>

<style scoped>
.tutor-message-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.tutor-markdown-block {
  min-width: 0;
}

.stream-markdown {
  min-width: 0;
  overflow-wrap: anywhere;
  line-height: 1.65;
}

.stream-markdown :deep(pre) {
  overflow-x: auto;
}

.stream-markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
  border-radius: 10px;
  overflow: hidden;
}

.stream-markdown :deep(th),
.stream-markdown :deep(td) {
  padding: 0.75rem 0.85rem;
  border: 1px solid #e5e7eb;
  text-align: left;
  vertical-align: top;
}

.stream-markdown :deep(th) {
  background: #f8fafc;
  font-weight: 700;
}

.stream-markdown :deep(tr:nth-child(even) td) {
  background: #fcfcfd;
}

.stream-markdown :deep(.hljs-comment),
.stream-markdown :deep(.hljs-quote) {
  color: #16a34a !important;
  font-style: normal;
}

.stream-markdown :deep(.code-block-wrapper) {
  margin: 1rem 0;
  border-radius: 8px;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid #e5e7eb;
}

.stream-markdown :deep(.code-block-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.65rem 0.85rem;
  background: var(--color-bg);
  border-bottom: 1px solid #e5e7eb;
}

.stream-markdown :deep(.code-block-lang) {
  min-width: 0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  font-weight: 600;
  user-select: none;
  white-space: nowrap;
}

.stream-markdown :deep(.code-block-copy-btn) {
  flex: 0 0 auto;
  background: var(--color-surface);
  border: 1px solid #e5e7eb;
  color: var(--color-text-muted);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 4px;
}

.stream-markdown :deep(.code-block-copy-btn:hover) {
  background: var(--color-surface-hover);
  color: #334155;
}

.stream-markdown :deep(.code-block-copy-btn.copied) {
  color: var(--color-success);
  border-color: var(--color-success);
}

.stream-markdown :deep(.code-block-wrapper pre) {
  margin: 0;
  padding: 16px;
  background: transparent;
  overflow-x: auto;
  font-size: 0.9rem;
}

.stream-markdown :deep(.code-block-wrapper code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
</style>
