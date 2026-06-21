<template>
  <div class="block-callout" :class="`intent-${block.intent || 'info'}`">
    <div class="callout-icon" v-if="block.icon">{{ block.icon }}</div>
    <div class="callout-content">{{ block.content }}</div>
  </div>
</template>

<script setup lang="ts">
import type { CalloutBlock } from '../../types/ppt'

defineProps<{
  block: CalloutBlock
}>()
</script>

<style scoped>
.block-callout {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: var(--ppt-radius);
  margin-bottom: 1em;
  font-size: 1.05rem;
  line-height: 1.5;
}

.callout-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.callout-content {
  flex-grow: 1;
}

.intent-info {
  background-color: var(--ppt-callout-info-bg);
  color: var(--ppt-callout-info-text);
  border-left: 4px solid var(--ppt-callout-info-text);
}

.intent-warning {
  background-color: var(--ppt-callout-warning-bg);
  color: var(--ppt-callout-warning-text);
  border-left: 4px solid var(--ppt-callout-warning-text);
}

.intent-success {
  background-color: var(--ppt-callout-success-bg);
  color: var(--ppt-callout-success-text);
  border-left: 4px solid var(--ppt-callout-success-text);
}

.intent-danger {
  background-color: var(--ppt-callout-danger-bg);
  color: var(--ppt-callout-danger-text);
  border-left: 4px solid var(--ppt-callout-danger-text);
}
</style>
