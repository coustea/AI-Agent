<template>
  <div class="markdown-resource" :class="{ compact }">
    <ResourceCardWrapper v-if="content" :compact="compact">


      <MarkdownRenderer class="markdown-shell" :content="content" />

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
import MarkdownRenderer from '@/shared/ui/MarkdownRenderer.vue'
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
  line-height: 1.78;
  overflow-wrap: anywhere;
  font-family: var(--font-sans, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
  font-size: 0.98rem;
  background: transparent;
}

/* 标题 */
.markdown-shell :deep(h1),
.markdown-shell :deep(h2),
.markdown-shell :deep(h3) {
  font-family: var(--font-sans, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
  color: var(--color-text-strong);
  margin-top: 1.8em;
  margin-bottom: 0.8em;
  font-weight: 800;
  line-height: 1.3;
}

.markdown-shell :deep(h1) {
  font-size: 1.5rem;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  padding-bottom: 0.4em;
}

.markdown-shell :deep(h2) {
  font-size: 1.25rem;
  border-bottom: 1px solid rgba(15, 23, 42, 0.05);
  padding-bottom: 0.3em;
}

.markdown-shell :deep(h3) {
  font-size: 1.1rem;
}

/* 段落 */
.markdown-shell :deep(p) {
  color: var(--color-text-secondary, #334155);
  margin: 1em 0 1.2em;
}

/* 列表 */
.markdown-shell :deep(ul),
.markdown-shell :deep(ol) {
  padding-left: 1.5em;
  margin: 1em 0;
  color: var(--color-text-secondary, #334155);
}

.markdown-shell :deep(li) {
  margin-bottom: 0.5em;
}

/* 引用块：优雅左侧标识风格 */
.markdown-shell :deep(blockquote) {
  border-left: 4px solid var(--color-primary);
  background: rgba(99, 102, 241, 0.03);
  padding: 14px 20px;
  margin: 1.5em 0;
  color: var(--color-text-secondary);
  border-radius: 0 10px 10px 0;
  font-style: normal;
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
