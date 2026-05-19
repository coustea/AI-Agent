<template>
  <div class="tutor-message-content">
    <div
      class="stream-markdown markdown-body tutor-markdown-block"
      v-html="streamingHtml"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import { renderStreamingMarkdownHtml } from '@/utils/markdown'

const props = defineProps<{
  content: string
  isStreaming?: boolean
}>()

const streamingHtml = ref('')
let renderTimer: ReturnType<typeof setTimeout> | null = null

const shouldRenderMarkdownNow = (text: string): boolean => {
  if (!text) return true
  return /(\n\n|\r\n\r\n|\n[-*]\s|\n\d+\.\s|\n#{1,6}\s|[。！？.!?]\s*$|`{3,}\s*$)/.test(text)
}

const commitStreamingHtml = () => {
  renderTimer = null
  streamingHtml.value = renderStreamingMarkdownHtml(props.content || '')
}

watch(
  () => props.content,
  () => {
    if (!props.isStreaming) {
      if (renderTimer) {
        clearTimeout(renderTimer)
        renderTimer = null
      }
      commitStreamingHtml()
      return
    }
    if (shouldRenderMarkdownNow(props.content || '')) {
      if (renderTimer) {
        clearTimeout(renderTimer)
        renderTimer = null
      }
      commitStreamingHtml()
      return
    }
    if (renderTimer) return
    renderTimer = setTimeout(commitStreamingHtml, 90)
  },
  { immediate: true },
)

watch(
  () => props.isStreaming,
  (isStreaming) => {
    if (!isStreaming) {
      if (renderTimer) {
        clearTimeout(renderTimer)
        renderTimer = null
      }
      commitStreamingHtml()
    }
  },
)

onBeforeUnmount(() => {
  if (renderTimer) {
    clearTimeout(renderTimer)
    renderTimer = null
  }
})
</script>

<style scoped>
.tutor-message-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.tutor-markdown-block {
  min-width: 0;
}

.stream-markdown {
  min-width: 0;
  overflow-wrap: anywhere;
  line-height: 1.65;
}

.stream-markdown :deep(pre) {
  overflow-x: auto;
}
</style>
