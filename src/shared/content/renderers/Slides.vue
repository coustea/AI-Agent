<template>
  <div class="ppt-resource" :class="{ compact }">
    <Frame :compact="compact" class="ppt-item">
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
    </Frame>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Frame from '../Frame.vue'
import { PhDownload as Download, PhArrowsOut as Expand } from '@phosphor-icons/vue'

const props = defineProps<{
  resource?: any
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
  const raw = props.resource
  if (!raw) return ''

  // 后端 PPT agent 将 HTML 课件发布引用写入 metadata.html_url
  // （server/app/resource/agents/ppt.py），_item_to_dto 把 metadata_json
  // 同时放入 content 与 metadata，因此两处都需读取 html_url。
  const meta = raw.metadata_json || raw.metadata
  const metadata = typeof meta === 'string' ? JSON.parse(meta) : meta
  const url = metadata?.html_url
  if (typeof url === 'string' && url) return url

  const content = raw.content
  const contentObj = typeof content === 'string' ? JSON.parse(content) : content
  const contentUrl = contentObj?.html_url
  if (typeof contentUrl === 'string' && contentUrl) return contentUrl

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
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.player-wrapper {
  width: 100%;
  aspect-ratio: 16 / 9;
  max-height: 75vh;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
  background: #ffffff;
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
  color: var(--color-text-faint);
  font-size: 16px;
}

.compact .player-wrapper {
  aspect-ratio: 16 / 9;
  height: auto;
  max-height: 25vh;
}
</style>
