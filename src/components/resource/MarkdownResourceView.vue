<template>
  <div class="markdown-resource" :class="{ compact }">
    <div v-if="content" class="markdown-body markdown-shell" v-html="renderMarkdown(content)"></div>
    <div v-else class="markdown-empty">暂未收到可展示的 Markdown 内容</div>
  </div>
</template>

<script setup lang="ts">
import 'github-markdown-css/github-markdown-light.css'
import { computed } from 'vue'
import { getMarkdownContent, renderMarkdown, type ResourceArtifactLike } from './resourceViewUtils'

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
}

.markdown-shell {
  color: #263446;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.markdown-shell :deep(pre) {
  border-radius: 8px;
  background: #0f172a;
}

.markdown-shell :deep(code) {
  white-space: pre-wrap;
}

.compact .markdown-shell {
  max-height: 158px;
  overflow: hidden;
  font-size: 0.86rem;
  mask-image: linear-gradient(to bottom, #000 68%, transparent 100%);
}

.compact .markdown-shell :deep(h1),
.compact .markdown-shell :deep(h2),
.compact .markdown-shell :deep(h3) {
  margin-top: 0;
  border-bottom: 0;
  font-size: 1rem;
}

.markdown-empty {
  padding: 16px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  color: #64748b;
  font-size: 0.9rem;
}
</style>
