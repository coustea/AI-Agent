<template>
  <div class="dynamic-slot-grid" :style="gridStyle">
    <div 
      v-for="(blocks, slotName) in slots" 
      :key="slotName"
      :class="[`pane-${slotName}`, { 'single-centered': isSingleCenter(slotName) }]"
      class="grid-pane"
    >
      <component
        v-for="block in blocks"
        :key="block.block_id"
        :is="resolveBlock(block.type)"
        :block="block"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SlideBlock, LayoutId } from '../../types/ppt'
import { resolveBlock } from '../blocks/registry'

const props = defineProps<{
  layout: LayoutId
  slots: Record<string, SlideBlock[]>
}>()

const gridStyle = computed(() => {
  const layouts: Record<LayoutId, string> = {
    HeroCover: '1fr',
    DualPane: '1.62fr 1fr',
    TriplePane: '1.13fr 1fr 0.9fr',
    DiagramFocus: '2.12fr 1fr',
    FlowCanvas: '1.85fr 1fr',
    CompareTable: '2.33fr 1fr',
    CardCluster: '1fr 1.85fr',
    KnowledgeMap: '2.12fr 1fr',
  }
  return {
    display: 'grid',
    gridTemplateColumns: layouts[props.layout] || '1fr',
    gap: '36px',
    height: '100%',
    padding: '32px 48px',
  }
})

const isSingleCenter = (slotName: string | number) => {
  return props.layout === 'HeroCover' && slotName === 'main'
}
</script>

<style scoped>
.dynamic-slot-grid {
  width: 100%;
  box-sizing: border-box;
}

.grid-pane {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  justify-content: center;
}

/* 默认双栏或多栏的右边栏之间有一条极细的实线分隔，减少视觉杂音 */
.dynamic-slot-grid > .grid-pane:not(:first-child) {
  border-left: 1px solid var(--ppt-border);
  padding-left: 36px;
}

/* 封面特殊居中排版 */
.grid-pane.single-centered {
  align-items: center;
  text-align: center;
  justify-content: center;
}
</style>
