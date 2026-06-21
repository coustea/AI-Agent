<template>
  <div class="block-text" :class="{ 'is-markdown': block.format === 'markdown' }">
    <MarkdownPreview
      v-if="block.format === 'markdown'"
      :content="block.content"
      :is-streaming="false"
      class="ppt-markdown"
    />
    <p v-else class="text-content">{{ block.content }}</p>
  </div>
</template>

<script setup lang="ts">
import MarkdownPreview from '@/shared/ui/MarkdownPreview.vue'
import type { TextBlock } from '../../types/ppt'

defineProps<{
  block: TextBlock
}>()
</script>

<style scoped>
.block-text {
  color: var(--ppt-text-secondary);
  line-height: 1.7;
  font-size: 1.12rem;
  margin-bottom: 0.5em;
  min-width: 0;
}

.text-content {
  margin: 0;
  white-space: pre-wrap;
}

.ppt-markdown {
  color: inherit;
}

.ppt-markdown :deep(p) {
  margin: 0 0 0.75em;
  line-height: 1.7;
}

.ppt-markdown :deep(strong) {
  color: var(--ppt-accent);
  font-weight: 700;
  background: rgba(37, 99, 235, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
}

.ppt-markdown :deep(ul),
.ppt-markdown :deep(ol) {
  padding-left: 1.4em;
  margin: 0 0 0.85em;
}

.ppt-markdown :deep(li) {
  margin: 0.35em 0;
}

.ppt-markdown :deep(code) {
  font-family: var(--ppt-font-mono);
  background: var(--ppt-bg-tertiary);
  color: var(--ppt-code-text);
  padding: 3px 6px;
  border-radius: 6px;
  font-size: 0.95em;
}

.ppt-markdown :deep(.code-block-wrapper) {
  margin: 1em 0;
  max-width: 100%;
  border-radius: var(--ppt-radius-md);
  overflow: hidden;
  box-shadow: var(--ppt-shadow-soft);
}
</style>
