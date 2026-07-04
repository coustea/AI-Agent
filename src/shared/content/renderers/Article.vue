<template>
  <div class="markdown-resource" :class="{ compact }">
    <div v-if="content" class="markdown-shell">
      <MarkdownRenderer :content="content" />
    </div>
    <div v-else class="markdown-empty">
      <div class="empty-icon">!</div>
      <div class="empty-text">NULL_CONTENT: NO_MARKDOWN_RECEIVED</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownRenderer from '@/shared/ui/MarkdownRenderer.vue'
import { getMarkdownContent, type ResourceArtifactLike } from '../artifact'

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
  background: transparent;
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
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: #ffffff;
  color: var(--color-primary-text);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  box-shadow: var(--shadow-sm);
}

.empty-icon {
  font-family: var(--font-mono);
  font-size: 2rem;
  opacity: 0.5;
}

.empty-text {
  font-family: var(--font-sans);
  font-size: 0.8rem;
}
</style>
