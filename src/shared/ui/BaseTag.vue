<template>
  <span
    :class="[
      'base-tag',
      `tone-${tone}`,
      `size-${size}`,
      { 'is-pill': pill, 'is-outline': outline }
    ]"
  >
    <span v-if="$slots.icon" class="tag-icon">
      <slot name="icon"></slot>
    </span>
    <span class="tag-content">
      <slot></slot>
    </span>
  </span>
</template>

<script setup lang="ts">
defineProps({
  tone: {
    type: String,
    default: 'slate', // slate, primary, emerald, amber, rose, indigo
    validator: (val: string) => ['slate', 'primary', 'emerald', 'amber', 'rose', 'indigo', 'blue'].includes(val)
  },
  size: {
    type: String,
    default: 'default',
    validator: (val: string) => ['small', 'default', 'large'].includes(val)
  },
  pill: {
    type: Boolean,
    default: false
  },
  outline: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.base-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-sans);
  font-weight: var(--weight-bold);
  white-space: nowrap;
  box-sizing: border-box;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
}

.base-tag.is-pill {
  border-radius: var(--radius-pill);
}

/* Sizing */
.size-small {
  height: 22px;
  padding: 0 8px;
  font-size: 0.68rem;
}

.size-default {
  height: 26px;
  padding: 0 10px;
  font-size: 0.75rem;
}

.size-large {
  height: 32px;
  padding: 0 14px;
  font-size: 0.85rem;
}

/* Tones (Solid/Soft) */
.tone-slate {
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
}
.tone-slate.is-outline {
  background: transparent;
  border-color: var(--color-border);
}

.tone-primary, .tone-indigo {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.tone-primary.is-outline, .tone-indigo.is-outline {
  background: transparent;
  border-color: var(--color-primary-border);
}

.tone-emerald {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.tone-emerald.is-outline {
  background: transparent;
  border-color: #A7F3D0; /* Emerald 200 */
}

.tone-amber {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}
.tone-amber.is-outline {
  background: transparent;
  border-color: #FDE68A; /* Amber 200 */
}

.tone-rose {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}
.tone-rose.is-outline {
  background: transparent;
  border-color: #FECDD3; /* Rose 200 */
}

.tone-blue {
  background: var(--color-info-soft);
  color: var(--color-info);
}
.tone-blue.is-outline {
  background: transparent;
  border-color: #BFDBFE; /* Blue 200 */
}

.tag-icon {
  display: flex;
  align-items: center;
  font-size: 1.1em;
}
</style>
