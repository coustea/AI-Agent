<template>
  <div class="markdown-resource" :class="{ compact }">
    <div v-if="content" class="technical-frame">
      
      <div class="frame-header">
        <div class="status-indicator"></div>
        <span class="technical-label">RESOURCE_CONTENT // VERSION 2.0</span>
      </div>

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

import { getMarkdownContent, type ResourceArtifactLike } from './resourceViewUtils'

import MarkdownPreview from '@/components/common/MarkdownPreview.vue'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const content = computed(() => getMarkdownContent(props.resultData))

declare function withDefaults<T, D>(props: T, defaults: D): T;
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

.markdown-resource {
  min-width: 0;
  width: 100%;
  --primary: #475569; /* Slate 600 */
  --bg: #FFFFFF;
  --fg: #334155; /* Slate 700 */
  --border: #E2E8F0;
  --accent: #6366F1; /* Indigo 500 */
}

/* 技术框架样式 */
.technical-frame {
  position: relative;
  background: var(--bg);
  border: none;
  border-radius: 4px;
  padding: 40px 32px 32px;
  box-shadow: none;
  transition: all 0.3s ease;
}

/* 拐角装饰 */
.frame-corners {
  position: absolute;
  width: 12px;
  height: 12px;
  border: 2px solid var(--primary);
  pointer-events: none;
}

.top-left { top: -1px; left: -1px; border-right: 0; border-bottom: 0; }
.top-right { top: -1px; right: -1px; border-left: 0; border-bottom: 0; }
.bottom-left { bottom: -1px; left: -1px; border-right: 0; border-top: 0; }
.bottom-right { bottom: -1px; right: -1px; border-left: 0; border-top: 0; }

/* 头部 HUD */
.frame-header {
  position: absolute;
  top: 12px;
  left: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-indicator {
  width: 6px;
  height: 6px;
  background: var(--accent);
  border-radius: 50%;
  box-shadow: none;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}

.technical-label {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.7rem;
  color: var(--primary);
  letter-spacing: 1px;
  opacity: 0.8;
}

/* 底部 HUD */
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
  background: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 2px;
}

.footer-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, var(--border), transparent);
}

/* Markdown 内容样式 */
.markdown-shell {
  color: var(--fg);
  line-height: 1.7;
  overflow-wrap: anywhere;
  font-family: 'Fira Code', monospace;
  font-size: 0.95rem;
}

/* 标题优化 */
.markdown-shell :deep(h1),
.markdown-shell :deep(h2),
.markdown-shell :deep(h3) {
  font-family: 'Share Tech Mono', monospace;
  color: var(--fg);
  border-bottom: 1px dashed var(--border);
  padding-bottom: 0.5em;
  margin-top: 2em;
  margin-bottom: 1em;
  font-weight: normal;
  display: flex;
  align-items: center;
  gap: 8px;
}

.markdown-shell :deep(h1)::before,
.markdown-shell :deep(h2)::before {
  content: '>';
  color: var(--primary);
  font-weight: bold;
}

/* 代码块优化 */
.markdown-shell :deep(pre) {
  border-radius: 8px;
  background: #FFFFFF !important; /* 深色终端背景 */
  border: 1px solid #334155;
  padding: 20px;
  margin: 1.5em 0;
  overflow: auto;
  position: relative;
}

/* 终端装饰点 */
.markdown-shell :deep(pre)::before {
  content: '•••';
  position: absolute;
  top: 8px;
  left: 12px;
  color: #334155;
  font-size: 14px;
  letter-spacing: 2px;
}

/* 复制按钮样式 */
.markdown-shell :deep(.copy-code-btn) {
  position: absolute;
  top: 10px;
  right: 12px;
  background: rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.2);
  color: var(--primary);
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.65rem;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 10;
  opacity: 0;
}

.markdown-shell :deep(pre:hover .copy-code-btn) {
  opacity: 1;
}

.markdown-shell :deep(.copy-code-btn:hover) {
  background: var(--primary);
  color: white;
}

.markdown-shell :deep(.copy-code-btn.copied) {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

.markdown-shell :deep(code) {
  font-family: 'Fira Code', monospace;
  font-size: 0.85em;
  background: transparent !important;
  padding: 0;
}

.markdown-shell :deep(p > code),
.markdown-shell :deep(li > code) {
  background: rgba(0, 0, 0, 0.1);
  padding: 0.2em 0.4em;
  border-radius: 4px;
  color: var(--primary);
  font-weight: 500;
}

/* 引用样式 */
.markdown-shell :deep(blockquote) {
  border-left: 3px solid var(--primary);
  background: rgba(0, 0, 0, 0.03);
  padding: 12px 20px;
  margin: 1.5em 0;
  border-radius: 2px;
  color: #475569;
  font-style: italic;
}

/* 列表样式 */
.markdown-shell :deep(ul),
.markdown-shell :deep(ol) {
  padding-left: 1.5em;
  margin: 1em 0;
}

.markdown-shell :deep(li) {
  margin-bottom: 0.5em;
}

/* 紧凑模式 */
.compact .technical-frame {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
}

.compact .frame-header,
.compact .frame-footer {
  display: none;
}

.compact .markdown-shell {
  max-height: 300px;
  overflow: hidden;
  font-size: 0.85rem;
  mask-image: linear-gradient(to bottom, #000 70%, transparent 100%);
}

.compact .markdown-shell :deep(h1),
.compact .markdown-shell :deep(h2),
.compact .markdown-shell :deep(h3) {
  margin-top: 1em;
  border-bottom: 0;
}

.markdown-empty {
  padding: 48px;
  border: 1px dashed var(--border);
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.5);
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
