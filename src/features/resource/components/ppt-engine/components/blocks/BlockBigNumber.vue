<template>
  <div class="block-big-number">
    <div class="number-wrapper">
      <span class="number">{{ block.number }}</span>
      <span class="unit" v-if="block.unit">{{ block.unit }}</span>
    </div>
    <div class="label" v-if="block.label">{{ block.label }}</div>
  </div>
</template>

<script setup lang="ts">
import type { BlockBigNumber } from '../../types/ppt'

defineProps<{
  block: BlockBigNumber
}>()
</script>

<style scoped>
.block-big-number {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-bottom: 1em;
  padding: 1.5rem;
  background-color: var(--ppt-bg-secondary);
  border-radius: var(--ppt-radius);
  border: 1px solid var(--ppt-border);
}

.number-wrapper {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.number {
  font-size: 4rem;
  font-weight: 800;
  color: var(--ppt-accent);
  line-height: 1;
}

.unit {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--ppt-text-secondary);
}

.label {
  margin-top: 8px;
  font-size: 1.1rem;
  font-weight: 500;
  color: var(--ppt-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
</style>
