<template>
  <div class="ppt-resource" :class="{ compact }">
    <ResourceCardWrapper :compact="compact" class="ppt-item">
      <div class="header-actions" v-if="!compact">
        <a v-if="downloadUrl" :href="downloadUrl" target="_blank" class="btn btn-primary btn-sm">
          <Download class="w-4 h-4 inline-block align-middle mr-1" />
          打开 HTML 课件
        </a>
        <button v-if="htmlUrl" class="btn btn-outline btn-sm" @click="toggleFullscreen">
          <Expand class="w-4 h-4 inline-block align-middle mr-1" />
          全屏预览
        </button>
      </div>
      <div class="player-wrapper">
        <iframe
          v-if="htmlUrl"
          :src="htmlUrl"
          class="slides-iframe"
          frameborder="0"
          sandbox="allow-scripts allow-downloads"
          allowfullscreen
        ></iframe>
        <div v-else class="no-preview">
          暂无幻灯片课件预览
        </div>
      </div>
    </ResourceCardWrapper>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ResourceCardWrapper from './ResourceCardWrapper.vue'
import { PhDownload as Download, PhArrowsOut as Expand } from '@phosphor-icons/vue'

const props = defineProps<{
  resource?: any
  documentData?: any
  compact?: boolean
}>()

function toggleFullscreen() {
  const iframe = document.querySelector('.slides-iframe') as HTMLIFrameElement | null
  if (!iframe) return

  if (!document.fullscreenElement) {
    iframe.requestFullscreen?.()
  } else {
    document.exitFullscreen?.()
  }
}

const htmlUrl = computed(() => {
  const rawMeta = props.resource?.metadata_json || props.resource?.metadata
  try {
    const metadata = typeof rawMeta === 'string' ? JSON.parse(rawMeta) : rawMeta
    const url = metadata?.html_url
    if (
      typeof url === 'string'
      && /^\/api\/v1\/ai\/resources\/public\/[A-Za-z0-9_-]+\/html$/.test(url)
    ) {
      return url
    }
  } catch {
    return ''
  }
  return ''
})

const downloadUrl = computed(() => htmlUrl.value)
</script>

<style scoped>
.ppt-resource {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ppt-item {
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.header-actions {
  display: flex;
  justify-content: flex-end;
  padding: 8px 16px;
  background: var(--ppt-bg-secondary, #ffffff);
  border: 1px solid var(--ppt-border, #e2e8f0);
  border-radius: 8px;
}

.player-wrapper {
  width: 100%;
  aspect-ratio: 16 / 9;
  max-height: 75vh;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--ppt-border, #e2e8f0);
  background: #000; /* 幻灯片一般是黑色或暗色底，保证 iframe 加载前不变白 */
}

.slides-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: transparent;
}

.no-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #a0aec0;
  font-size: 16px;
}

.compact .player-wrapper {
  aspect-ratio: 16 / 9;
  height: auto;
  max-height: 25vh;
}
</style>
