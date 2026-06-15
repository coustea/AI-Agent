<template>
  <div
    class="app-markdown-preview markdown-body"
    v-html="renderedContent"
    @click="handleCopy"
  ></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { normalizeStreamingMarkdown, renderStreamingMarkdownHtml } from '@/shared/utils/markdown'

const props = withDefaults(defineProps<{
  content: string
  isStreaming?: boolean
}>(), {
  content: '',
  isStreaming: false,
})

const normalizedContent = computed(() => normalizeStreamingMarkdown(props.content, props.isStreaming))
const renderedContent = computed(() => renderStreamingMarkdownHtml(normalizedContent.value))

const handleCopy = async (event: MouseEvent) => {
  const target = event.target as HTMLElement
  const copyBtn = target.closest('.code-block-copy-btn') as HTMLElement
  if (!copyBtn) return

  const wrapper = copyBtn.closest('.code-block-wrapper')
  if (!wrapper) return

  const codeEl = wrapper.querySelector('pre code')
  if (!codeEl || !codeEl.textContent) return

  try {
    await navigator.clipboard.writeText(codeEl.textContent)
    const originalText = copyBtn.innerText
    copyBtn.innerText = '已复制!'
    copyBtn.classList.add('copied')
    
    setTimeout(() => {
      copyBtn.innerText = originalText
      copyBtn.classList.remove('copied')
    }, 2000)
  } catch (err) {
    console.error('Failed to copy code: ', err)
  }
}
</script>

<style scoped>
.app-markdown-preview {
  width: 100%;
  min-width: 0;
  height: auto;
  background: transparent;
  color: inherit;
}

.app-markdown-preview :deep(> :first-child) {
  margin-top: 0;
}

.app-markdown-preview :deep(> :last-child) {
  margin-bottom: 0;
}

.app-markdown-preview :deep(p) {
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}

/* Light Theme Premium Code Block Styles */
.app-markdown-preview :deep(.code-block-wrapper) {
  background: #f8f9fa;
  border-radius: 8px;
  overflow: hidden;
  margin: 1.5em 0;
  border: 1px solid #e9ecef;
}

.app-markdown-preview :deep(.code-block-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #ffffff;
  border-bottom: 1px solid #e9ecef;
}

.app-markdown-preview :deep(.code-block-lang) {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #868e96;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  user-select: none;
}

.app-markdown-preview :deep(.code-block-copy-btn) {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  color: #495057;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.app-markdown-preview :deep(.code-block-copy-btn:hover) {
  background: #e9ecef;
  color: #212529;
  border-color: #ced4da;
}

.app-markdown-preview :deep(.code-block-copy-btn.copied) {
  background: #d1e7dd;
  color: #0f5132;
  border-color: #badbcc;
}

.app-markdown-preview :deep(pre) {
  margin: 0 !important;
  padding: 16px !important;
  background: transparent !important;
}

.app-markdown-preview :deep(pre code) {
  background: transparent !important;
  color: #334155 !important;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  line-height: 1.6;
}

/* Syntax Highlighting overrides for Light Theme */
.app-markdown-preview :deep(.hljs-keyword),
.app-markdown-preview :deep(.hljs-selector-tag),
.app-markdown-preview :deep(.hljs-title.function_) {
  color: #7c3aed !important;
}

.app-markdown-preview :deep(.hljs-string),
.app-markdown-preview :deep(.hljs-attr),
.app-markdown-preview :deep(.hljs-symbol) {
  color: #059669 !important;
}

.app-markdown-preview :deep(.hljs-number),
.app-markdown-preview :deep(.hljs-literal),
.app-markdown-preview :deep(.hljs-boolean) {
  color: #ea580c !important;
}

.app-markdown-preview :deep(.hljs-comment) {
  color: #94a3b8 !important;
  font-style: italic;
}

.app-markdown-preview :deep(.hljs-built_in),
.app-markdown-preview :deep(.hljs-type),
.app-markdown-preview :deep(.hljs-class .hljs-title) {
  color: #0284c7 !important;
}

.app-markdown-preview :deep(.hljs-variable),
.app-markdown-preview :deep(.hljs-template-variable) {
  color: #be123c !important;
}
</style>
