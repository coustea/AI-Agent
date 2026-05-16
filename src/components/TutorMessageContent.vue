<template>
  <div class="tutor-message-content">
    <template v-if="isStreaming">
      <div class="stream-plain-text">{{ content }}</div>
    </template>
    <template v-else>
      <MarkdownPreview
        class="tutor-markdown-block"
        :content="content"
        :is-streaming="false"
      />
    </template>
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

.stream-plain-text {
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  line-height: 1.7;
}
</style>
