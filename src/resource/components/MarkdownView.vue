<template>
  <div class="markdown-resource" :class="{ compact }">
    <div v-if="content" class="technical-frame">


      <MarkdownPreview class="markdown-shell" :content="content" />

      <div class="frame-footer">
        <span class="mono-tag">EOF_READY</span>
        <div class="footer-line"></div>
      </div>
    </div>
    <div v-else class="markdown-empty">
      <div class="empty-icon">!</div>
      <div class="empty-text">NULL_CONTENT: NO_MARKDOWN_RECEIVED</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownPreview from '@/shared/components/MarkdownPreview.vue'
import { getMarkdownContent, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const content = computed(() => getMarkdownContent(props.resultData))
</script>
<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

.markdown-resource {
  min-width: 0;
  width: 100%;

  --primary: #475569;
  --bg: #ffffff;
  --fg: #334155;
  --muted: #64748b;
  --border: #e2e8f0;
  --soft-bg: #f8fafc;
  --code-bg: #f9fafb;
  --inline-code-bg: #eef2ff;
  --accent: #6366f1;
}

.technical-frame {
  position: relative;
  background: var(--bg);
  border-radius: 8px;
  padding: 24px 32px 32px;
  box-shadow: none;
  transition: all 0.3s ease;
}

.frame-footer {
  margin-top: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.mono-tag {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.65rem;
  color: var(--primary);
  background: #f1f5f9;
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
  font-family:
      'Fira Code',
      Consolas,
      Monaco,
      'Courier New',
      monospace;
  font-size: 0.95rem;
  background: #ffffff;
}

/* 标题 */
.markdown-shell :deep(h1),
.markdown-shell :deep(h2),
.markdown-shell :deep(h3) {
  font-family: 'Share Tech Mono', monospace;
  color: #1e293b;
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

/* 引用块：浅色背景 */
.markdown-shell :deep(blockquote) {
  border-left: 4px solid #c7d2fe;
  background: #f8fafc;
  padding: 12px 20px;
  margin: 1.5em 0;
  border-radius: 6px;
  color: #475569;
  font-style: normal;
}

/* 表格 */
.markdown-shell :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1.5em 0;
  background: #ffffff;
  border: 1px solid var(--border);
}

.markdown-shell :deep(th),
.markdown-shell :deep(td) {
  border: 1px solid var(--border);
  padding: 10px 12px;
  color: var(--fg);
}

.markdown-shell :deep(th) {
  background: #f1f5f9;
  color: #1e293b;
  font-weight: 600;
}

.markdown-shell :deep(tr:nth-child(even)) {
  background: #f8fafc;
}

/* 代码块：浅色背景，禁止黑色背景 */
.markdown-shell :deep(pre) {
  position: relative;
  border-radius: 10px;
  background: #f8fafc !important;
  border: 1px solid #e2e8f0;
  padding: 20px;
  margin: 1.5em 0;
  overflow: auto;
  color: #334155;
}

/* 代码块内部 code */
.markdown-shell :deep(pre code) {
  display: block;
  font-family:
      'Fira Code',
      Consolas,
      Monaco,
      'Courier New',
      monospace;
  font-size: 0.88rem;
  line-height: 1.7;
  background: transparent !important;
  color: inherit;
  padding: 0;
}

/* 行内代码：浅色背景 */
.markdown-shell :deep(p > code),
.markdown-shell :deep(li > code),
.markdown-shell :deep(td > code) {
  font-family:
      'Fira Code',
      Consolas,
      Monaco,
      'Courier New',
      monospace;
  background: #eef2ff !important;
  color: #4338ca;
  padding: 0.18em 0.4em;
  border-radius: 5px;
  font-size: 0.86em;
  font-weight: 500;
}

/* 代码块语言标签 */
.markdown-shell :deep(pre)::before {
  content: 'CODE';
  position: absolute;
  top: 8px;
  right: 12px;
  color: #94a3b8;
  font-size: 0.7rem;
  letter-spacing: 1px;
  font-family: 'Share Tech Mono', monospace;
}

/* 复制按钮：浅色风格 */
.markdown-shell :deep(.copy-code-btn) {
  position: absolute;
  top: 10px;
  right: 12px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.65rem;
  padding: 4px 8px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 10;
  opacity: 0;
}

.markdown-shell :deep(pre:hover .copy-code-btn) {
  opacity: 1;
}

.markdown-shell :deep(.copy-code-btn:hover) {
  background: #eef2ff;
  border-color: #c7d2fe;
  color: #4338ca;
}

.markdown-shell :deep(.copy-code-btn.copied) {
  background: #ecfdf5;
  color: #047857;
  border-color: #a7f3d0;
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
  color: #94a3b8;
  font-style: italic;
}

.markdown-shell :deep(.hljs-built_in),
.markdown-shell :deep(.hljs-type),
.markdown-shell :deep(.hljs-class .hljs-title) {
  color: #2563eb;
}

.markdown-shell :deep(.hljs-variable),
.markdown-shell :deep(.hljs-template-variable) {
  color: #be123c;
}

/* Shiki 浅色主题兜底 */
.markdown-shell :deep(.shiki) {
  background: #f8fafc !important;
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
.compact .technical-frame {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
}

.compact .frame-footer {
  display: none;
}

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
  background: #f8fafc;
  color: var(--primary);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.empty-icon {
  font-family: 'Share Tech Mono', monospace;
  font-size: 2rem;
  opacity: 0.5;
}

.empty-text {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.8rem;
  letter-spacing: 1px;
}
</style>
