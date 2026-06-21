<template>
  <div class="block-text" :class="{ 'is-markdown': block.format === 'markdown' }">
    <MarkdownPreview
      v-if="block.format === 'markdown'"
      :content="block.content"
      :is-streaming="false"
      class="ppt-markdown"
    />
    <p v-else>{{ block.content }}</p>
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
  line-height: 1.55;
  font-size: 1.08rem;
  margin-bottom: 0.85em;
  min-width: 0;
}

.block-text p {
  margin: 0;
}

.ppt-markdown {
  color: inherit;
}

.ppt-markdown :deep(p),
.ppt-markdown :deep(ul),
.ppt-markdown :deep(ol) {
  margin: 0 0 0.55em;
}

.ppt-markdown :deep(ul),
.ppt-markdown :deep(ol) {
  padding-left: 1.2em;
}

.ppt-markdown :deep(li) {
  margin: 0.18em 0;
}

.ppt-markdown :deep(.code-block-wrapper) {
  margin: 0.6em 0;
  max-width: 100%;
}
</style>
