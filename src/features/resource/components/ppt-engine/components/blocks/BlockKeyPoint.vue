<template>
  <div class="block-keypoint ppt-card">
    <div class="keypoint-header">
      <span class="bullet-dot"></span>
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
  padding: 28px;
  border-radius: var(--ppt-radius-md);
  border: 1px solid var(--ppt-border);
  background: linear-gradient(135deg, var(--ppt-bg-secondary) 0%, var(--ppt-bg-tertiary) 100%);
  position: relative;
  overflow: hidden;
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1),
              border-color 0.3s ease,
              box-shadow 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.block-keypoint:hover {
  transform: translateY(-4px);
  border-color: var(--ppt-accent);
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.03);
}

.keypoint-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.bullet-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ppt-accent);
  display: inline-block;
}

.label {
  font-family: var(--ppt-font-sans), sans-serif;
  font-size: 0.9rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ppt-accent);
}

.content {
  font-family: var(--ppt-font-sans), sans-serif;
  font-size: 1.55rem;
  font-weight: 800;
  line-height: 1.35;
  color: var(--ppt-text-primary);
  word-break: break-word;
}
</style>
