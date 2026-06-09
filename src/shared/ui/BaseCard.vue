<template>
  <div class="base-card" :class="[paddingClass, { 'is-hoverable': hoverable }]">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

defineOptions({ name: 'BaseCard' })

const props = defineProps({
  padding: {
    type: String,
    default: 'standard', // 'none', 'small', 'standard', 'large'
  },
  hoverable: {
    type: Boolean,
    default: false
  }
})

const paddingClass = computed(() => {
  switch (props.padding) {
    case 'none': return 'p-none'
    case 'small': return 'p-small'
    case 'large': return 'p-large'
    case 'standard':
    default: return 'p-standard'
  }
})
</script>

<style scoped>
.base-card {
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  color: var(--color-text);
  transition: transform var(--transition-base), box-shadow var(--transition-base), border-color var(--transition-base);
  overflow: hidden;
}

.base-card.is-hoverable:hover {
  border-color: var(--color-border-hover);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.p-none { padding: 0; }
.p-small { padding: var(--space-4); }
.p-standard { padding: var(--space-6); }
.p-large { padding: var(--space-8); }
</style>
