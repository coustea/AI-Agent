<template>
  <div class="ppt-resource" :class="{ compact }">
    <Frame :compact="compact" class="ppt-item">
      <div v-if="!compact" class="deck-toolbar">
        <span class="deck-label">教学课件 <span v-if="previews.length">{{ current + 1 }} / {{ previews.length }}</span></span>
        <div class="toolbar-actions">
          <button class="nav-button" :disabled="current <= 0" @click="current--">上一页</button>
          <button class="nav-button" :disabled="current >= previews.length - 1" @click="current++">下一页</button>
          <a v-if="pptxUrl" :href="pptxUrl" class="nav-button" download>下载 PPTX</a>
          <a v-if="pdfUrl" :href="pdfUrl" class="nav-button" target="_blank" rel="noopener">打开 PDF</a>
          <button class="nav-button" @click="player?.requestFullscreen()">全屏</button>
        </div>
      </div>
      <div ref="player" class="player-wrapper">
        <img v-if="previews[current]" :src="previews[current]" :alt="`第 ${current + 1} 页`" class="slide-image" />
        <div v-else class="no-preview">暂无课件预览</div>
      </div>
    </Frame>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Frame from '../Frame.vue'
const props = defineProps<{ resource?: unknown; compact?: boolean }>()
const current = ref(0)
const player = ref<HTMLElement | null>(null)
function object(value: unknown): Record<string, unknown> {
  if (typeof value === 'string') {
    try { return object(JSON.parse(value)) } catch { return {} }
  }
  return value && typeof value === 'object' ? value as Record<string, unknown> : {}
}
const metadata = computed(() => {
  const resource = object(props.resource)
  return object(resource.metadata_json ?? resource.metadata)
})
const previews = computed(() => Array.isArray(metadata.value.preview_urls)
  ? metadata.value.preview_urls.filter((url): url is string => typeof url === 'string') : [])
const pptxUrl = computed(() => typeof metadata.value.pptx_url === 'string' ? metadata.value.pptx_url : '')
const pdfUrl = computed(() => typeof metadata.value.pdf_url === 'string' ? metadata.value.pdf_url : '')
watch(previews, () => { current.value = 0 })
</script>

<style scoped>
.ppt-resource { width: 100%; display: flex; flex-direction: column; gap: 14px; }
.ppt-item { padding: 0 !important; background: transparent !important; border: none !important; box-shadow: none !important; }

.deck-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 18px;
  border: 1px solid rgba(200, 228, 227, 0.44);
  border-radius: 12px;
  background: var(--color-surface, #ffffff);
  box-shadow: 0 2px 10px rgba(31, 76, 80, 0.02);
}

.deck-status {
  display: flex;
  align-items: center;
  gap: 12px;
}

.deck-label {
  color: var(--color-text-strong, #173b42);
  font-size: 14px;
  font-weight: 800;
}

.deck-page {
  color: var(--color-text-secondary, #58747a);
  font-variant-numeric: tabular-nums;
  font-size: 13px;
  font-weight: 500;
  background: rgba(200, 228, 227, 0.22);
  padding: 2px 8px;
  border-radius: 6px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-button, .icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid rgba(200, 228, 227, 0.7);
  border-radius: 8px;
  background: var(--color-surface, #ffffff);
  color: var(--color-text-strong, #173b42);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s ease;
}

.icon-button {
  width: 36px;
  padding: 0;
}

.nav-primary {
  border-color: var(--color-primary, #46b8b4);
  background: var(--color-primary, #46b8b4);
  color: white;
  box-shadow: 0 2px 6px rgba(70, 184, 180, 0.15);
}

.nav-primary:hover:not(:disabled) {
  background: #3fa8a4;
  border-color: #3fa8a4;
  box-shadow: 0 4px 12px rgba(70, 184, 180, 0.25);
}

.nav-button:hover:not(.nav-primary):not(:disabled),
.icon-button:hover:not(:disabled) {
  border-color: var(--color-primary, #46b8b4);
  color: var(--color-primary-text, #205f67);
  background: rgba(70, 184, 180, 0.04);
}

.nav-button:disabled,
.icon-button:disabled {
  cursor: not-allowed;
  opacity: .35;
  border-color: rgba(200, 228, 227, 0.3) !important;
  background: rgba(200, 228, 227, 0.05) !important;
  color: var(--color-text-faint, #8da4a8) !important;
  box-shadow: none !important;
}

.player-wrapper {
  width: 100%;
  aspect-ratio: 16 / 9;
  max-height: 75vh;
  overflow: hidden;
  border: 1px solid rgba(200, 228, 227, 0.5);
  border-radius: 12px;
  background: #fafcfc;
  box-shadow: 0 4px 20px rgba(31, 76, 80, 0.03);
}

.slide-image {
  width: 100%;
  height: 100%;
  border: none;
  object-fit: contain;
}

.no-preview {
  display: grid;
  height: 100%;
  place-items: center;
  color: var(--color-text-faint, #8da4a8);
  font-size: 16px;
  font-weight: 500;
}

.compact .player-wrapper {
  max-height: 25vh;
}

@media (max-width: 640px) {
  .deck-toolbar {
    align-items: flex-start;
    flex-direction: column;
    padding: 14px;
  }
}
</style>
