<template>
  <div class="block-keypoint ppt-card">
    <div class="keypoint-header">
      <span class="pulse-ring"></span>
      <div class="label">{{ block.label }}</div>
    </div>
    <div class="content">{{ block.content }}</div>
  </div>
</template>

<script setup lang="ts">
import type { KeyPointBlock } from '../../types/ppt'

defineProps<{
  block: KeyPointBlock
}>()
</script>

<style scoped>
.block-keypoint {
  padding: 24px;
  border-radius: var(--ppt-radius-md);
  border: 1px solid var(--ppt-border);
  background: linear-gradient(135deg, var(--ppt-bg-secondary) 0%, rgba(37, 99, 235, 0.03) 100%);
  position: relative;
  overflow: hidden;
}

.keypoint-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.pulse-ring {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ppt-accent);
  display: inline-block;
  box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.4);
  animation: pulse 2s infinite;
}

.label {
  font-size: 0.85rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ppt-accent);
}

.content {
  font-size: 1.45rem;
  font-weight: 800;
  line-height: 1.4;
  color: var(--ppt-text-primary);
  word-break: break-word;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.7);
  }
  70% {
    box-shadow: 0 0 0 6px rgba(37, 99, 235, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(37, 99, 235, 0);
  }
}
</style>
