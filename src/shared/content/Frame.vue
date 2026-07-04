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
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: 24px 32px 32px; /* 保持原有较宽裕的内边距，提升高级感 */
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);
  width: 100%;
  box-sizing: border-box;
  overflow: hidden; /* 防止内部内容溢出破坏圆角 */
}

.resource-card-wrapper:hover {
  transform: translateY(-1.5px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary-border);
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
