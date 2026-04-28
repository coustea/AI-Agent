<template>
  <div class="tutor-message-content">
    <template v-for="(block, index) in blocks" :key="`${index}-${block.type}`">
      <div
        v-if="block.type === 'markdown'"
        class="markdown-body tutor-markdown-block"
        v-html="block.html || ''"
      ></div>
      <div
        v-else
        class="tutor-code-block"
        v-html="block.html || ''"
      ></div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { parseTutorContentBlocks } from '@/utils/markdown'

const props = defineProps<{
  content: string
  isStreaming?: boolean
}>()

const blocks = computed(() => parseTutorContentBlocks(props.content, { isStreaming: Boolean(props.isStreaming) }))
</script>

<style scoped>
.tutor-message-content {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.tutor-markdown-block,
.tutor-code-block {
  min-width: 0;
}
</style>
