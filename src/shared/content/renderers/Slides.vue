<template>
  <div class="ppt-resource" :class="{ compact }">
    <Frame :compact="compact" class="ppt-item">
      <div v-if="!compact" class="deck-toolbar">
        <div class="deck-status">
          <span class="deck-label">教学课件</span>
          <span v-if="totalSlides" class="deck-page">{{ currentSlide }} / {{ totalSlides }}</span>
        </div>
        <div class="toolbar-actions">
          <button class="nav-button" :disabled="currentSlide <= 1" @click="sendCommand('previous')">上一页</button>
          <button class="nav-button nav-primary" :disabled="!totalSlides || currentSlide >= totalSlides" @click="sendCommand('next')">下一页</button>
          <button v-if="htmlUrl" class="icon-button" aria-label="全屏预览" @click="toggleFullscreen">
            <Expand class="w-5 h-5" />
          </button>
          <a v-if="htmlUrl" :href="htmlUrl" target="_blank" class="icon-button" aria-label="在新窗口打开">
            <ArrowSquareOut class="w-5 h-5" />
          </a>
        </div>
      </div>
      <div ref="playerRef" class="player-wrapper">
        <iframe
          v-if="htmlUrl"
          ref="iframeRef"
          :src="htmlUrl"
          class="slides-iframe"
          frameborder="0"
          sandbox="allow-scripts allow-downloads"
          allowfullscreen
          @load="requestDeckState"
        ></iframe>
        <div v-else class="no-preview">暂无幻灯片课件预览</div>
      </div>
    </Frame>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import Frame from '../Frame.vue'
import { PhArrowsOut as Expand, PhArrowSquareOut as ArrowSquareOut } from '@phosphor-icons/vue'

const props = defineProps<{ resource?: unknown; compact?: boolean }>()

const iframeRef = ref<HTMLIFrameElement | null>(null)
const playerRef = ref<HTMLElement | null>(null)
const currentSlide = ref(1)
const totalSlides = ref(0)

function parseObject(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === 'object') return value as Record<string, unknown>
  if (typeof value !== 'string') return null
  try {
    const parsed = JSON.parse(value)
    return parsed && typeof parsed === 'object' ? parsed as Record<string, unknown> : null
  } catch {
    return null
  }
}

const htmlUrl = computed(() => {
  const resource = parseObject(props.resource)
  if (!resource) return ''
  const metadata = parseObject(resource.metadata_json ?? resource.metadata)
  const content = parseObject(resource.content)
  const url = metadata?.html_url ?? content?.html_url
  return typeof url === 'string' ? url : ''
})

function sendCommand(action: 'previous' | 'next' | 'state') {
  iframeRef.value?.contentWindow?.postMessage({ source: 'mentorly-ppt', type: 'command', action }, '*')
}

function requestDeckState() {
  sendCommand('state')
}

function handleMessage(event: MessageEvent) {
  if (event.source !== iframeRef.value?.contentWindow) return
  const data = event.data
  if (!data || data.source !== 'mentorly-ppt' || !['ready', 'state'].includes(data.type)) return
  if (typeof data.current === 'number') currentSlide.value = data.current
  if (typeof data.total === 'number') totalSlides.value = data.total
}

function toggleFullscreen() {
  const player = playerRef.value
  if (!player) return
  if (document.fullscreenElement) document.exitFullscreen?.()
  else player.requestFullscreen?.()
}

onMounted(() => window.addEventListener('message', handleMessage))
onBeforeUnmount(() => window.removeEventListener('message', handleMessage))
</script>

<style scoped>
.ppt-resource { width: 100%; display: flex; flex-direction: column; gap: 12px; }
.ppt-item { padding: 0 !important; background: transparent !important; border: none !important; box-shadow: none !important; }
.deck-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 12px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-surface); }
.deck-status, .toolbar-actions { display: flex; align-items: center; gap: 10px; }
.deck-label { color: var(--color-text); font-weight: 700; }
.deck-page { color: var(--color-text-faint); font-variant-numeric: tabular-nums; }
.nav-button, .icon-button { display: inline-flex; align-items: center; justify-content: center; min-height: 34px; padding: 0 12px; border: 1px solid var(--color-border); border-radius: 8px; background: var(--color-surface); color: var(--color-text); font-size: 13px; cursor: pointer; text-decoration: none; }
.icon-button { width: 36px; padding: 0; }
.nav-primary { border-color: var(--color-primary); background: var(--color-primary); color: white; }
.nav-button:disabled { cursor: not-allowed; opacity: .45; }
.player-wrapper { width: 100%; aspect-ratio: 16 / 9; max-height: 75vh; overflow: hidden; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: #eef4fb; }
.slides-iframe { width: 100%; height: 100%; border: none; background: transparent; }
.no-preview { display: grid; height: 100%; place-items: center; color: var(--color-text-faint); font-size: 16px; }
.compact .player-wrapper { max-height: 25vh; }
@media (max-width: 640px) { .deck-toolbar { align-items: flex-start; flex-direction: column; } }
</style>
