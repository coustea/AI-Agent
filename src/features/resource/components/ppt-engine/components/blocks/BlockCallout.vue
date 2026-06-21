<template>
  <div class="block-callout ppt-card" :class="`intent-${block.intent || 'info'}`">
    <div class="callout-icon-box" v-if="block.icon">
      <span class="callout-icon">{{ block.icon }}</span>
    </div>
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
  gap: 16px;
  padding: 24px;
  border-radius: var(--ppt-radius-md);
  margin-bottom: 1.2em;
  font-size: 1.1rem;
  line-height: 1.6;
  border-style: solid;
  border-width: 1px 1px 1px 6px;
}

.callout-icon-box {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
}

.callout-icon {
  font-size: 1.4rem;
}

.callout-content {
  flex-grow: 1;
  align-self: center;
}

.intent-info {
  background-color: var(--ppt-callout-info-bg);
  color: var(--ppt-callout-info-text);
  border-color: var(--ppt-border) var(--ppt-border) var(--ppt-border) var(--ppt-callout-info-text);
}

.intent-info .callout-icon-box {
  background: var(--ppt-bg-secondary);
}

.intent-warning {
  background-color: var(--ppt-callout-warning-bg);
  color: var(--ppt-callout-warning-text);
  border-color: var(--ppt-border) var(--ppt-border) var(--ppt-border) var(--ppt-callout-warning-text);
}

.intent-warning .callout-icon-box {
  background: var(--ppt-bg-secondary);
}

.intent-success {
  background-color: var(--ppt-callout-success-bg);
  color: var(--ppt-callout-success-text);
  border-color: var(--ppt-border) var(--ppt-border) var(--ppt-border) var(--ppt-callout-success-text);
}

.intent-success .callout-icon-box {
  background: var(--ppt-bg-secondary);
}

.intent-danger {
  background-color: var(--ppt-callout-danger-bg);
  color: var(--ppt-callout-danger-text);
  border-color: var(--ppt-border) var(--ppt-border) var(--ppt-border) var(--ppt-callout-danger-text);
}

.intent-danger .callout-icon-box {
  background: var(--ppt-bg-secondary);
}
</style>
