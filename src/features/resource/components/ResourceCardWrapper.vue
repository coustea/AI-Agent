<template>
  <div class="resource-card-wrapper" :class="{ 'is-compact': compact }">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  compact?: boolean
}>()
</script>

<style scoped>
.resource-card-wrapper {
  position: relative;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: var(--radius-xl);
  padding: 24px 32px 32px; /* 保持原有较宽裕的内边距，提升高级感 */
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.04);
  transition: all var(--transition-base);
  width: 100%;
  box-sizing: border-box;
  overflow: hidden; /* 防止内部内容溢出破坏圆角 */
}

.resource-card-wrapper:hover {
  background: rgba(255, 255, 255, 0.75);
  border-color: rgba(255, 255, 255, 0.6);
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.06);
}

/* 紧凑模式：去除所有边框、阴影和背景，适应内联场景 */
.resource-card-wrapper.is-compact {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
  border-radius: 0;
}

.resource-card-wrapper.is-compact:hover {
  box-shadow: none;
}
</style>
