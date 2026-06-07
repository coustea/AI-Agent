<template>
  <div
    class="app-markdown-preview markdown-body"
    v-html="renderedContent"
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

.app-markdown-preview :deep(pre),
.app-markdown-preview :deep(pre code) {
  background-color: var(--color-surface) !important;
  color: var(--color-text-strong) !important;
}

.app-markdown-preview :deep(pre .title),
.app-markdown-preview :deep(pre .attribute) {
  color: #0284C7 !important;
  font-weight: 600;
}

.app-markdown-preview :deep(pre .string),
.app-markdown-preview :deep(pre .value) {
  color: #16A34A !important;
}

.app-markdown-preview :deep(pre .keyword) {
  color: #9333EA !important;
  font-weight: bold;
}

.app-markdown-preview :deep(pre .comment) {
  color: var(--color-text-secondary) !important;
  font-style: italic;
}

.app-markdown-preview :deep(pre .number) {
  color: #D97706 !important;
}

.app-markdown-preview :deep(pre .built_in),
.app-markdown-preview :deep(pre .type) {
  color: #B91C1C !important;
  font-weight: 600;
}
</style>
