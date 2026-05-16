<template>
  <div class="tutor-message-content">
    <MarkdownPreview
      class="tutor-markdown-block"
      :content="content"
      :is-streaming="isStreaming"
    />
  </div>
</template>

<script setup lang="ts">
import MarkdownPreview from '@/components/common/MarkdownPreview.vue'

defineProps<{
  content: string
  isStreaming?: boolean
}>()
</script>

<style scoped>
.tutor-message-content {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.tutor-markdown-block {
  min-width: 0;
}
</style>
