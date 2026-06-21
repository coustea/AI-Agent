<template>
  <div class="block-keypoint">
    <div class="label">{{ block.label }}</div>
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
  padding: 16px 18px;
  border-radius: var(--ppt-radius);
  background: var(--ppt-bg-tertiary);
  border: 1px solid var(--ppt-border);
}

.label {
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ppt-accent);
}

.content {
  margin-top: 8px;
  font-size: 1rem;
  line-height: 1.55;
  color: var(--ppt-text-primary);
}
</style>
