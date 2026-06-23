<template>
  <div class="ppt-resource" :class="{ compact }">
    <ResourceCardWrapper :compact="compact" class="ppt-item">
      <div class="header-actions" v-if="!compact">
        <el-button type="primary" size="small" :loading="isExporting" @click="handleExport">
          <el-icon v-if="!isExporting" style="margin-right: 4px;"><Download /></el-icon>
          导出 PPTX (3x DPI)
        </el-button>
      </div>
      <div class="player-wrapper">
        <PptPlayer :documentData="documentData" :isExportMode="isExporting" />
      </div>
    </ResourceCardWrapper>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ResourceCardWrapper from './ResourceCardWrapper.vue'
import PptPlayer from './ppt-engine/PptPlayer.vue'
import type { PPTDocument } from './ppt-engine/types/ppt'
import { convertToPptistSlides } from './ppt-engine/converters/slideConverter'
import { exportToPptx } from './ppt-engine/utils/exportUtils'
import { ElButton, ElIcon } from 'element-plus'
import { Download } from '@element-plus/icons-vue'

const props = defineProps<{
  documentData: PPTDocument
  compact?: boolean
}>()

const isExporting = ref(false)

const handleExport = async () => {
  isExporting.value = true
  setTimeout(async () => {
    try {
      await exportToPptx(convertToPptistSlides(props.documentData), props.documentData.title || 'presentation')
    } catch (e) {
      console.error('Export error:', e)
    } finally {
      isExporting.value = false
    }
  }, 600)
}
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
  background: transparent;
}

.compact .player-wrapper {
  aspect-ratio: 16 / 9;
  height: auto;
  max-height: 25vh;
}
</style>
