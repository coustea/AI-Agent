<template>
  <div class="layout-split-screen" :style="gridStyle">
    <div class="pane left-pane">
      <component 
        v-for="block in slots.left || []" 
        :key="block.id" 
        :is="resolveBlock(block.type)" 
        :block="block" 
      />
    </div>
    <div class="pane right-pane">
      <component 
        v-for="block in slots.right || []" 
        :key="block.id" 
        :is="resolveBlock(block.type)" 
        :block="block" 
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SlideBlock, LayoutConfig } from '../../types/ppt'
import { resolveBlock } from '../blocks/registry'

const props = defineProps<{
  slots: Record<string, SlideBlock[]>
  config?: LayoutConfig
}>()

const gridStyle = computed(() => {
  const ratio = props.config?.ratio || '5:5'
  const [left, right] = ratio.split(':')
  return {
    gridTemplateColumns: `${left}fr ${right}fr`
  }
})
</script>

<style scoped>
.layout-split-screen {
  display: grid;
  height: 100%;
  width: 100%;
  gap: 40px;
  padding: 64px 72px;
  box-sizing: border-box;
}

.pane {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
  min-width: 0;
  overflow: hidden;
}
</style>
