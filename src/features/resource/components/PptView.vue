<template>
  <div class="ppt-resource" :class="{ compact }">
    <ResourceCardWrapper :compact="compact" class="ppt-item">
      <div class="header-actions" v-if="!compact">
        <button class='btn btn-primary btn-sm' :disabled="isExporting" @click="handleExport">
          <Download class='w-4 h-4 inline-block align-middle' />
          导出 PPTX
        </button>
      </div>
      <div class="player-wrapper">
        <PptPreview :documentData="documentData" />
      </div>
    </ResourceCardWrapper>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ResourceCardWrapper from './ResourceCardWrapper.vue'
import PptPreview from './ppt-engine/pptxgenjs-renderer/preview/PptPreview.vue'
import type { PPTDocument } from './ppt-engine/types/ppt'
import { renderPPT, downloadPPTX } from './ppt-engine/pptxgenjs-renderer'
import { toast } from 'vue-sonner'
import {
  PhDownload as Download
} from '@phosphor-icons/vue'

const props = defineProps<{
  documentData: PPTDocument
  compact?: boolean
}>()

const isExporting = ref(false)

const handleExport = async () => {
  isExporting.value = true
  try {
    const pptx = renderPPT(props.documentData)
    const filename = `${props.documentData.title || 'presentation'}.pptx`
    await downloadPPTX(pptx, filename)
    toast.success('PPTX 导出成功')
  } catch (e) {
    console.error('Export error:', e)
    toast.error('导出失败，请重试')
  } finally {
    isExporting.value = false
  }
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
