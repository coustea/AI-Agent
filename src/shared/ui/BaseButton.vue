<template>
  <button
    :class="[
      'base-btn',
      `variant-${variant}`,
      `size-${size}`,
      { 'is-loading': loading, 'is-disabled': disabled, 'is-icon-only': iconOnly }
    ]"
    :disabled="disabled || loading"
    v-bind="$attrs"
  >
    <span v-if="loading" class="btn-loader"></span>
    <span v-if="$slots.icon && !loading" class="btn-icon">
      <slot name="icon"></slot>
    </span>
    <span v-if="$slots.default" class="btn-text">
      <slot></slot>
    </span>
  </button>
</template>

<script setup lang="ts">


const props = defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (val: string) => ['primary', 'secondary', 'ghost', 'outline', 'icon'].includes(val)
  },
  size: {
    type: String,
    default: 'default',
    validator: (val: string) => ['small', 'default', 'large'].includes(val)
  },
  loading: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  iconOnly: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.base-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: none;
  border-radius: var(--radius-md);
  font-family: var(--font-sans);
  font-weight: var(--weight-bold);
  cursor: pointer;
  transition: all var(--transition-base);
  box-sizing: border-box;
  text-decoration: none;
}

.base-btn.is-disabled {
  opacity: 0.6;
  cursor: not-allowed;
  pointer-events: none; /* prevents hover/active states */
}

/* Base Interactions */
.base-btn:hover:not(.is-disabled) {
  transform: translateY(-1px);
}

.base-btn:active:not(.is-disabled) {
  transform: scale(0.98);
}

.base-btn:focus-visible {
  outline: 3px solid var(--color-primary-soft);
  outline-offset: 2px;
}

/* Sizing */
.size-small {
  height: 32px;
  padding: 0 14px;
  font-size: 0.8rem;
  border-radius: var(--radius-sm);
}

.size-default {
  height: 40px;
  padding: 0 20px;
  font-size: 0.9rem;
}

.size-large {
  height: 48px;
  padding: 0 28px;
  font-size: 1rem;
  border-radius: var(--radius-lg);
}

.is-icon-only.size-small { width: 32px; padding: 0; }
.is-icon-only.size-default { width: 40px; padding: 0; }
.is-icon-only.size-large { width: 48px; padding: 0; }

/* Variants */
.variant-primary {
  background: var(--color-primary);
  color: #FFFFFF;
  box-shadow: var(--shadow-sm);
}
.variant-primary:hover:not(.is-disabled) {
  background: var(--color-primary-hover);
  box-shadow: var(--shadow-md);
}

.variant-secondary {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.variant-secondary:hover:not(.is-disabled) {
  background: var(--color-primary-border);
}

.variant-outline {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text);
}
.variant-outline:hover:not(.is-disabled) {
  border-color: var(--color-border-hover);
  background: var(--color-surface-hover);
  box-shadow: var(--shadow-xs);
}

.variant-ghost {
  background: transparent;
  color: var(--color-text-secondary);
}
.variant-ghost:hover:not(.is-disabled) {
  background: var(--color-surface-hover);
  color: var(--color-text-strong);
}

.variant-icon {
  background: transparent;
  color: var(--color-text-muted);
  border-radius: var(--radius-md);
}
.variant-icon:hover:not(.is-disabled) {
  background: var(--color-surface-hover);
  color: var(--color-primary);
}

/* Loader */
.btn-loader {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: btn-spin 0.75s linear infinite;
}

@keyframes btn-spin {
  100% {
    transform: rotate(360deg);
  }
}

.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
