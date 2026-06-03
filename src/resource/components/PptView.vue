<template>
  <div class="ppt-resource" :class="{ compact }">
    <article class="technical-frame ppt-item">
      
      <!-- PptPlayer wrapper -->
      <div class="player-wrapper" v-if="pptDocument">
        <PptPlayer :documentData="pptDocument" :isExportMode="false" />
      </div>
      <div v-else class="empty-state">
        <p>正在渲染 PPT 文稿... / RENDERING</p>
      </div>
    </article>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { type ResourceArtifactLike, parseJsonObject } from './resourceViewUtils'
import PptPlayer from './ppt-engine/PptPlayer.vue'
import type { PPTDocument } from './ppt-engine/types/ppt'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

// extract and parse the JSON string or object
const pptDocument = computed<PPTDocument | null>(() => {
  let content = (typeof props.resultData === 'object' && props.resultData !== null)
    ? (props.resultData as Record<string, any>).content || props.resultData
    : props.resultData
  if (typeof content === 'string') {
    // maybe wrapped in markdown ```json
    const match = content.match(/```json\s*([\s\S]*?)\s*```/)
    if (match) {
      content = match[1]
    }
  }
  return parseJsonObject(content) as PPTDocument | null
})
</script>

<style scoped>
.ppt-resource {
  width: 100%;
}

.technical-frame {
  position: relative;
  background: #FFFFFF;
  border-radius: 4px;
  padding: 24px 32px 32px;
  box-shadow: none;
  transition: all 0.3s ease;
}

.technical-frame.ppt-item {
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.compact .technical-frame {
  padding: 0;
  background: transparent;
}

.frame-header {
  position: absolute;
  top: 12px;
  left: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.compact .frame-header {
  display: none;
}

.status-indicator {
  width: 6px;
  height: 6px;
  background: #EC4899; /* pink-500 matching PPT color */
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.technical-label {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.7rem;
  color: #475569;
}

.player-wrapper {
  margin-top: 10px;
  width: 100%;
  aspect-ratio: 16 / 9;
  max-height: 75vh;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #E2E8F0;
  background: #E5E7EB;
}

.compact .player-wrapper {
  aspect-ratio: 16 / 9;
  height: auto;
  max-height: 25vh;
  margin-top: 0;
}

@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}

.empty-state {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F8FAFC;
  color: #94A3B8;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.9rem;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
}
</style>
