<template>
  <div class="ppt-resource" :class="{ compact }">
    <ResourceCardWrapper :compact="compact" class="ppt-item">
      
      <!-- PptPlayer wrapper -->
      <div class="player-wrapper" v-if="pptDocument">
        <PptPlayer :documentData="pptDocument" :isExportMode="false" />
      </div>
      <div v-else class="empty-state">
        <p>正在渲染 PPT 文稿... / RENDERING</p>
      </div>
    </ResourceCardWrapper>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { type ResourceArtifactLike, parseJsonObject } from './resourceViewUtils'
import ResourceCardWrapper from './ResourceCardWrapper.vue'
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

.ppt-item {
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.status-indicator {
  width: 6px;
  height: 6px;
  background: #EC4899; /* pink-500 matching PPT color */
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.technical-label {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--color-text-secondary);
}

.player-wrapper {
  margin-top: 10px;
  width: 100%;
  aspect-ratio: 16 / 9;
  max-height: 75vh;
  border-radius: 8px;
  overflow: hidden;
  border: none;
  background: transparent;
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
  background: rgba(0, 0, 0, 0.02);
  color: var(--color-text-faint);
  font-family: var(--font-mono);
  font-size: 0.9rem;
  border: none;
  border-radius: 8px;
}
</style>
