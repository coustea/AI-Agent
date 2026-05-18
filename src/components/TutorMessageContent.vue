<template>
  <div class="tutor-message-content">
    <template v-if="isStreaming">
      <div
        class="stream-markdown markdown-body"
        v-html="streamingHtml"
      ></div>
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
import { onBeforeUnmount, ref, watch } from 'vue'
import MarkdownPreview from '@/components/common/MarkdownPreview.vue'
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
