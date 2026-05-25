<template>
  <div class="ppt-resource" :class="{ compact }">
    <article class="technical-frame ppt-item">
      <div class="frame-header">
        <div class="status-indicator"></div>
        <span class="technical-label">幻灯片引擎 // PRESENTATION_ENGINE</span>
      </div>
      
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

import PptPlayer from '../ppt-engine/PptPlayer.vue'

import type { PPTDocument } from '../ppt-engine/types/ppt'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const pptDocument = computed<PPTDocument | null>(() => {
  let content = props.resultData?.content || props.resultData
  if (typeof content === 'string') {
    // maybe wrapped in markdown ```json
    const match = content.match(/```json\s*([\s\S]*?)\s*```/)
    if (match) {
      content = match[1]
    }
  }
  return parseJsonObject(content) as PPTDocument | null
})

declare function withDefaults<T, D>(props: T, defaults: D): T;
</script>

<style scoped>
.ppt-resource {
  width: 100%;
}

.technical-frame {
  position: relative;
  background: #FFFFFF;
  border-radius: 4px;
  padding: 40px 32px 32px;
  box-shadow: none;
  transition: all 0.3s ease;
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
  height: 500px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #E2E8F0;
  background: #E5E7EB;
}

.compact .player-wrapper {
  height: 200px;
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
