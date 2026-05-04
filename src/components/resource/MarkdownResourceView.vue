<template>
  <div class="markdown-resource" :class="{ compact }">
    <div v-if="content" class="markdown-body markdown-shell" v-html="renderMarkdown(content)"></div>
    <div v-else class="markdown-empty">暂未收到可展示的 Markdown 内容</div>
  </div>
</template>

<script setup lang="ts">
import 'github-markdown-css/github-markdown-dark.css'
import { computed, onMounted, nextTick, watch } from 'vue'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { getMarkdownContent, renderMarkdown, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const content = computed(() => getMarkdownContent(props.resultData))

const performHighlight = async () => {
  await nextTick()
  hljs.highlightAll()
}

onMounted(performHighlight)
watch(content, performHighlight)
</script>

<style scoped>
.markdown-resource {
  min-width: 0;
  width: 100%;
}

.markdown-shell {
  color: #334155;
  line-height: 1.8;
  overflow-wrap: anywhere;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* 标题优化 */
.markdown-shell :deep(h1),
.markdown-shell :deep(h2),
.markdown-shell :deep(h3) {
  color: #0F172A;
  border-bottom: 2px solid #F1F5F9;
  padding-bottom: 0.3em;
  margin-top: 1.6em;
  font-weight: 800;
  letter-spacing: -0.02em;
}

/* 代码块优化 */
.markdown-shell :deep(pre) {
  border-radius: 16px;
  background: #F8FAFC !important;
  border: 1px solid #E2E8F0;
  padding: 24px;
  margin: 1.5em 0;
  overflow: auto;
}

.markdown-shell :deep(code) {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9em;
  color: #1E293B;
}

.markdown-shell :deep(p > code),
.markdown-shell :deep(li > code) {
  background: #F1F5F9;
  padding: 0.2em 0.5em;
  border-radius: 6px;
  color: #3B82F6;
  font-weight: 600;
}

/* 引用样式 */
.markdown-shell :deep(blockquote) {
  border-left: 4px solid #3B82F6;
  background: #F0F7FF;
  padding: 16px 24px;
  margin: 1.5em 0;
  border-radius: 0 12px 12px 0;
  color: #475569;
  font-style: italic;
}

/* 表格优化 */
.markdown-shell :deep(table) {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 1.5em 0;
  border-radius: 12px;
  border: 1px solid #E2E8F0;
  overflow: hidden;
}

.markdown-shell :deep(th) {
  background: #F8FAFC;
  font-weight: 700;
  color: #0F172A;
}

.markdown-shell :deep(td),
.markdown-shell :deep(th) {
  padding: 14px 20px;
  border-bottom: 1px solid #F1F5F9;
}

.markdown-shell :deep(tr:last-child td) {
  border-bottom: none;
}

/* 紧凑模式 */
.compact .markdown-shell {
  max-height: 220px;
  overflow: hidden;
  font-size: 0.9rem;
  mask-image: linear-gradient(to bottom, #000 75%, transparent 100%);
}

.compact .markdown-shell :deep(h1),
.compact .markdown-shell :deep(h2),
.compact .markdown-shell :deep(h3) {
  margin-top: 1em;
  border-bottom: 0;
  font-size: 1.15rem;
}

.markdown-empty {
  padding: 32px;
  border: 2px dashed #E2E8F0;
  border-radius: 16px;
  background: #F8FAFC;
  color: #94A3B8;
  text-align: center;
}
</style>
