<template>
  <div class="ppt-resource" :class="{ compact }">
    <ResourceCardWrapper :compact="compact" class="ppt-item">
      <div class="player-wrapper">
        <PptPlayer :documentData="documentData" :isExportMode="false" />
      </div>
    </ResourceCardWrapper>
  </div>
</template>

<script setup lang="ts">
import ResourceCardWrapper from './ResourceCardWrapper.vue'
import PptPlayer from './ppt-engine/PptPlayer.vue'
import type { PPTDocument } from './ppt-engine/types/ppt'

defineProps<{
  documentData: PPTDocument
  compact?: boolean
}>()
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
</style>
