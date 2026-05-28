<template>
  <div class="tutor-message-content">
    <div
      ref="markdownRef"
      class="stream-markdown markdown-body tutor-markdown-block"
      v-html="streamingHtml"
      @click="handleContentClick"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { renderStreamingMarkdownHtml } from '@/utils/markdown'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  content: string
  isStreaming?: boolean
}>()

const streamingHtml = ref('')
const markdownRef = ref<HTMLElement | null>(null)
let renderTimer: ReturnType<typeof setTimeout> | null = null
let copyResetTimer: ReturnType<typeof setTimeout> | null = null

const copyCode = async (button: HTMLButtonElement, code: string) => {
  try {
    await navigator.clipboard.writeText(code)
    button.textContent = '已复制'
  } catch {
    button.textContent = '复制失败'
  }

  if (copyResetTimer) {
    clearTimeout(copyResetTimer)
  }
  copyResetTimer = setTimeout(() => {
    button.textContent = '复制'
    copyResetTimer = null
  }, 1800)
}

const enhanceCodeBlocks = () => {
  const root = markdownRef.value
  if (!root) return

  const blocks = root.querySelectorAll('pre')
  blocks.forEach((pre) => {
    if (pre.querySelector('.code-copy-button')) return

    const code = pre.querySelector('code')
    if (!code) return

    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'code-copy-button'
    button.textContent = '复制'
    button.addEventListener('click', () => {
      void copyCode(button, code.textContent || '')
    })

    pre.appendChild(button)
  })
}

const handleContentClick = async (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (target.classList.contains('code-block-copy-btn')) {
    const wrapper = target.closest('.code-block-wrapper')
    if (!wrapper) return
    
    const pre = wrapper.querySelector('pre')
    if (!pre) return
    
    const textToCopy = pre.textContent || ''
    
    try {
      await navigator.clipboard.writeText(textToCopy)
      const originalText = target.innerText
      target.innerText = '已复制'
      target.classList.add('copied')
      ElMessage.success('代码已复制到剪贴板')
      
      setTimeout(() => {
        target.innerText = originalText
        target.classList.remove('copied')
      }, 2000)
    } catch (err) {
      console.error('Copy failed:', err)
      ElMessage.error('复制失败，请重试')
    }
  }
}

const shouldRenderMarkdownNow = (text: string): boolean => {
  if (!text) return true
  return /(\n\n|\r\n\r\n|\n[-*]\s|\n\d+\.\s|\n#{1,6}\s|[。！？.!?]\s*$|`{3,}\s*$)/.test(text)
}

const commitStreamingHtml = () => {
  renderTimer = null
  streamingHtml.value = renderStreamingMarkdownHtml(props.content || '')
  void nextTick(enhanceCodeBlocks)
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
  if (copyResetTimer) {
    clearTimeout(copyResetTimer)
    copyResetTimer = null
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
  position: relative;
  overflow-x: auto;
  padding-top: 2.75rem;
}

.stream-markdown :deep(.code-copy-button) {
  position: absolute;
  top: 0.7rem;
  right: 0.75rem;
  z-index: 1;
  padding: 0.2rem 0.65rem;
  color: #14532d;
  font-size: 0.75rem;
  line-height: 1.4;
  background: #dcfce7;
  border: 1px solid #86efac;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.stream-markdown :deep(.code-copy-button:hover) {
  background: #bbf7d0;
  border-color: #4ade80;
}

.stream-markdown :deep(.hljs-comment),
.stream-markdown :deep(.hljs-quote) {
  color: #16a34a !important;
  font-style: normal;
}

.stream-markdown :deep(.code-block-wrapper) {
  position: relative;
  margin: 1rem 0;
  border-radius: 8px;
  overflow: hidden;
  background: #ffffff; /* 确保背景色为白色 */
  border: 1px solid #e5e7eb;
}

.stream-markdown :deep(.code-block-lang) {
  position: absolute;
  top: 8px;
  left: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.75rem;
  color: #94a3b8;
  text-transform: uppercase;
  font-weight: 600;
  user-select: none;
  z-index: 10;
}

.stream-markdown :deep(.code-block-copy-btn) {
  position: absolute;
  top: 8px;
  right: 8px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  color: #64748b;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  transition: all 0.2s;
  z-index: 10;
  opacity: 0; /* 默认隐藏，悬浮时显示 */
  display: flex;
  align-items: center;
  gap: 4px;
}

.stream-markdown :deep(.code-block-wrapper:hover .code-block-copy-btn) {
  opacity: 1;
}

.stream-markdown :deep(.code-block-copy-btn:hover) {
  background: #f1f5f9;
  color: #334155;
}

.stream-markdown :deep(.code-block-copy-btn.copied) {
  color: #10b981;
  border-color: #10b981;
}

.stream-markdown :deep(.code-block-wrapper pre) {
  margin: 0;
  padding: 32px 16px 16px 16px; /* 顶部留出空间给语言标识和复制按钮 */
  background: transparent;
  overflow-x: auto;
  font-size: 0.9rem;
}

.stream-markdown :deep(.code-block-wrapper code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
</style>
