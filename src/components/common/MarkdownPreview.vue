<template>
  <MdPreview
    class="app-markdown-preview"
    :model-value="normalizedContent"
    :id="previewId"
    theme="light"
    language="zh-CN"
    preview-theme="default"
    code-theme="github"
    :show-code-row-number="false"
    :code-foldable="false"
    :no-img-zoom-in="true"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'
import { normalizeStreamingMarkdown } from '@/utils/markdown'

const props = withDefaults(defineProps<{
  content: string
  isStreaming?: boolean
  id?: string
}>(), {
  content: '',
  isStreaming: false,
})

const previewId = computed(() => props.id || `md-preview-${Math.random().toString(36).slice(2)}`)
const normalizedContent = computed(() => normalizeStreamingMarkdown(props.content, props.isStreaming))
</script>

<style scoped>
.app-markdown-preview {
  width: 100%;
  min-width: 0;
  height: auto;
  border: 0;
  background: transparent;
  color: inherit;
}

.app-markdown-preview :deep(.md-editor-preview-wrapper),
.app-markdown-preview :deep(.md-editor-preview) {
  overflow: visible;
}

.app-markdown-preview :deep(.md-editor-preview) {
  padding: 0;
  color: inherit;
  font-size: inherit;
  line-height: inherit;
  word-break: normal;
  overflow-wrap: anywhere;
  background: transparent;
}

.app-markdown-preview :deep(.md-editor-preview > :first-child) {
  margin-top: 0;
}

.app-markdown-preview :deep(.md-editor-preview > :last-child) {
  margin-bottom: 0;
}

.app-markdown-preview :deep(.md-editor-preview p) {
  margin-top: 0 !important;
  margin-bottom: 0 !important;
}

/* 强制覆盖代码块的背景色为纯白色 */
.app-markdown-preview :deep(.md-editor-preview pre),
.app-markdown-preview :deep(.md-editor-preview pre code),
.app-markdown-preview :deep(.md-editor-preview figure.md-editor-code) {
  background-color: #FFFFFF !important;
  color: #1E293B !important;
}

/* 确保内置代码的外部容器也无背景色 */
.app-markdown-preview :deep(.md-editor-preview .default-theme pre) {
  background-color: #FFFFFF !important;
}

/* 优化语法高亮，拒绝浅色和灰色，提高对比度 */
.app-markdown-preview :deep(.md-editor-preview pre .title),
.app-markdown-preview :deep(.md-editor-preview pre .attribute) {
  color: #0284C7 !important; /* 深蓝色 */
  font-weight: 600;
}

.app-markdown-preview :deep(.md-editor-preview pre .string),
.app-markdown-preview :deep(.md-editor-preview pre .value) {
  color: #16A34A !important; /* 深绿色 */
}

.app-markdown-preview :deep(.md-editor-preview pre .keyword) {
  color: #9333EA !important; /* 深紫色 */
  font-weight: bold;
}

.app-markdown-preview :deep(.md-editor-preview pre .comment) {
  color: #475569 !important; /* 深蓝灰色，不再是浅灰 */
  font-style: italic;
}

.app-markdown-preview :deep(.md-editor-preview pre .number) {
  color: #D97706 !important; /* 深橙色 */
}

.app-markdown-preview :deep(.md-editor-preview pre .built_in),
.app-markdown-preview :deep(.md-editor-preview pre .type) {
  color: #B91C1C !important; /* 深红色 */
  font-weight: 600;
}
</style>
