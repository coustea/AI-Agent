<template>
  <div class="markdown-resource" :class="{ compact }">
    <ResourceCardWrapper v-if="content" :compact="compact">


      <MarkdownPreview class="markdown-shell" :content="content" />

      <div class="frame-footer">
        <span class="mono-tag">EOF_READY</span>
        <div class="footer-line"></div>
      </div>
    </ResourceCardWrapper>
    <div v-else class="markdown-empty">
      <div class="empty-icon">!</div>
      <div class="empty-text">NULL_CONTENT: NO_MARKDOWN_RECEIVED</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownPreview from '@/shared/ui/MarkdownPreview.vue'
import ResourceCardWrapper from './ResourceCardWrapper.vue'
import { getMarkdownContent, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const content = computed(() => getMarkdownContent(props.resultData))
</script>
<style scoped>
.markdown-resource {
  min-width: 0;
  width: 100%;

  --primary: var(--color-primary);
  --bg: var(--color-surface);
  --fg: var(--color-text);
  --muted: var(--color-text-muted);
  --border: var(--color-border);
  --soft-bg: var(--color-bg);
  --code-bg: var(--color-bg);
  --inline-code-bg: var(--color-primary-soft);
  --accent: var(--color-primary);
}

.frame-footer {
  margin-top: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.mono-tag {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--primary);
  background: var(--color-surface-hover);
  padding: 2px 6px;
  border-radius: 4px;
}

.footer-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, var(--border), transparent);
}

/* Markdown 主体 */
.markdown-shell {
  color: var(--fg);
  line-height: 1.75;
  overflow-wrap: anywhere;
  font-family: var(--font-mono);
  font-size: 0.95rem;
  background: transparent;
}

/* 标题 */
.markdown-shell :deep(h1),
.markdown-shell :deep(h2),
.markdown-shell :deep(h3) {
  font-family: var(--font-mono);
  color: var(--color-text-strong);
  border-bottom: 1px dashed var(--border);
  padding-bottom: 0.5em;
  margin-top: 2em;
  margin-bottom: 1em;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.markdown-shell :deep(h1)::before,
.markdown-shell :deep(h2)::before {
  content: '>';
  color: var(--accent);
  font-weight: bold;
}

/* 段落 */
.markdown-shell :deep(p) {
  color: var(--fg);
  margin: 1em 0;
}

/* 列表 */
.markdown-shell :deep(ul),
.markdown-shell :deep(ol) {
  padding-left: 1.5em;
  margin: 1em 0;
}

.markdown-shell :deep(li) {
  margin-bottom: 0.5em;
}

/* 引用块：无边界风格 */
.markdown-shell :deep(blockquote) {
  border-left: 3px solid rgba(0, 0, 0, 0.1);
  background: transparent;
  padding: 8px 16px;
  margin: 1.5em 0;
  color: var(--color-text-secondary);
  font-style: italic;
}

/* 表格：无感斑马纹 */
.markdown-shell :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1.5em 0;
  background: transparent;
  border: none;
}

.markdown-shell :deep(th),
.markdown-shell :deep(td) {
  border: none;
  padding: 12px 16px;
  color: var(--fg);
}

.markdown-shell :deep(th) {
  background: var(--color-surface-hover);
  color: var(--color-text-strong);
  font-weight: 600;
  border-bottom: 2px solid rgba(0, 0, 0, 0.05);
}

.markdown-shell :deep(tr:nth-child(even)) {
  background: rgba(0, 0, 0, 0.02);
}


/* 行内代码：浅色背景 */
.markdown-shell :deep(p > code),
.markdown-shell :deep(li > code),
.markdown-shell :deep(td > code) {
  font-family: var(--font-mono);
  background: var(--color-primary-soft) !important;
  color: var(--color-primary-hover);
  padding: 0.18em 0.4em;
  border-radius: 5px;
  font-size: 0.86em;
  font-weight: 500;
}


/* highlight.js 浅色语法高亮覆盖 */
.markdown-shell :deep(.hljs) {
  background: transparent !important;
  color: #334155 !important;
}

.markdown-shell :deep(.hljs-keyword),
.markdown-shell :deep(.hljs-selector-tag),
.markdown-shell :deep(.hljs-title.function_) {
  color: #7c3aed;
}

.markdown-shell :deep(.hljs-string),
.markdown-shell :deep(.hljs-attr),
.markdown-shell :deep(.hljs-symbol) {
  color: #059669;
}

.markdown-shell :deep(.hljs-number),
.markdown-shell :deep(.hljs-literal),
.markdown-shell :deep(.hljs-boolean) {
  color: #ea580c;
}

.markdown-shell :deep(.hljs-comment) {
  color: var(--color-text-faint);
  font-style: italic;
}

.markdown-shell :deep(.hljs-built_in),
.markdown-shell :deep(.hljs-type),
.markdown-shell :deep(.hljs-class .hljs-title) {
  color: var(--color-info);
}

.markdown-shell :deep(.hljs-variable),
.markdown-shell :deep(.hljs-template-variable) {
  color: #be123c;
}

/* Shiki 浅色主题兜底 */
.markdown-shell :deep(.shiki) {
  background: var(--color-bg) !important;
  color: #334155 !important;
}

.markdown-shell :deep(.shiki code) {
  background: transparent !important;
}

/* 防止第三方 Markdown 样式带入黑色背景 */
.markdown-shell :deep(pre),
.markdown-shell :deep(code),
.markdown-shell :deep(.hljs),
.markdown-shell :deep(.shiki) {
  text-shadow: none !important;
}

/* 紧凑模式 */
.compact .markdown-shell {
  max-height: 300px;
  overflow: hidden;
  font-size: 0.85rem;
  background: transparent;
  mask-image: linear-gradient(to bottom, #000 70%, transparent 100%);
}

.compact .markdown-shell :deep(h1),
.compact .markdown-shell :deep(h2),
.compact .markdown-shell :deep(h3) {
  margin-top: 1em;
  border-bottom: 0;
}

/* 空状态 */
.markdown-empty {
  padding: 48px;
  border: 1px dashed var(--border);
  border-radius: 8px;
  background: var(--color-bg);
  color: var(--primary);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.empty-icon {
  font-family: var(--font-mono);
  font-size: 2rem;
  opacity: 0.5;
}

.empty-text {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  letter-spacing: 1px;
}
</style>
