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
    validator: (val: string) => ['primary', 'secondary', 'ghost', 'outline', 'icon', 'danger'].includes(val)
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
/* ============================================================
   Base Button — Professional Design System
   Follows: Apple HIG, Material Design 3, WCAG 2.1
   ============================================================ */

.base-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: none;
  border-radius: var(--radius-lg);
  font-family: var(--font-sans);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  transition:
    background-color 180ms cubic-bezier(0.4, 0, 0.2, 1),
    box-shadow 180ms cubic-bezier(0.4, 0, 0.2, 1),
    transform 120ms cubic-bezier(0.4, 0, 0.2, 1),
    opacity 180ms ease;
  box-sizing: border-box;
  text-decoration: none;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
  overflow: hidden;
  /* Ensure touch target >= 44px (HIG/MD standard) */
  min-height: 44px;
  min-width: 44px;
}

/* State Layer — Material Design 3 approach */
.base-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: currentColor;
  opacity: 0;
  transition: opacity 120ms ease;
  pointer-events: none;
}

/* Sizing — Touch targets meet 44pt minimum */
.size-small {
  height: 36px;
  padding: 0 16px;
  font-size: var(--text-sm);
  border-radius: var(--radius-md);
}

.size-default {
  height: 44px;
  padding: 0 20px;
  font-size: var(--text-sm);
}

.size-large {
  height: 52px;
  padding: 0 28px;
  font-size: var(--text-base);
  border-radius: var(--radius-xl);
}

/* Icon-only buttons — square with centered icon */
.is-icon-only.size-small { width: 44px; padding: 0; }
.is-icon-only.size-default { width: 44px; padding: 0; }
.is-icon-only.size-large { width: 52px; padding: 0; }

/* ============================================================
   Variants — Clear visual hierarchy
   ============================================================ */

/* Primary — Filled, highest emphasis */
.variant-primary {
  background: var(--color-primary);
  color: #FFFFFF !important;
  box-shadow: var(--shadow-sm), 0 1px 0 rgba(0, 0, 0, 0.05) inset;
}

.variant-primary .btn-text {
  color: #FFFFFF !important;
}
.variant-primary:hover:not(.is-disabled) {
  background: var(--color-primary-hover);
  box-shadow: var(--shadow-md), 0 1px 0 rgba(0, 0, 0, 0.05) inset;
}
.variant-primary:active:not(.is-disabled) {
  background: var(--color-primary-hover);
  box-shadow: var(--shadow-xs), 0 1px 0 rgba(0, 0, 0, 0.05) inset;
  transform: scale(0.98);
}
.variant-primary:hover:not(.is-disabled)::before {
  opacity: 0.08;
}
.variant-primary:active:not(.is-disabled)::before {
  opacity: 0.16;
}

/* Secondary — Tonal, medium emphasis */
.variant-secondary {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.variant-secondary:hover:not(.is-disabled) {
  background: var(--color-primary-border);
}
.variant-secondary:active:not(.is-disabled) {
  background: var(--color-primary-border);
  transform: scale(0.98);
}
.variant-secondary:hover:not(.is-disabled)::before {
  opacity: 0.06;
}
.variant-secondary:active:not(.is-disabled)::before {
  opacity: 0.12;
}

/* Outline — Bordered, lower emphasis */
.variant-outline {
  background: transparent;
  border: 1.5px solid var(--color-border);
  color: var(--color-text);
}
.variant-outline:hover:not(.is-disabled) {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
}
.variant-outline:active:not(.is-disabled) {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  transform: scale(0.98);
}

/* Ghost — Text-only, lowest emphasis */
.variant-ghost {
  background: transparent;
  color: var(--color-text-secondary);
}
.variant-ghost:hover:not(.is-disabled) {
  background: var(--color-surface-hover);
  color: var(--color-text-strong);
}
.variant-ghost:active:not(.is-disabled) {
  background: var(--color-surface-hover);
  transform: scale(0.98);
}
.variant-ghost:hover:not(.is-disabled)::before {
  opacity: 0.04;
}
.variant-ghost:active:not(.is-disabled)::before {
  opacity: 0.08;
}

/* Icon — Icon-only button */
.variant-icon {
  background: transparent;
  color: var(--color-text-muted);
  border-radius: var(--radius-md);
}
.variant-icon:hover:not(.is-disabled) {
  background: var(--color-surface-hover);
  color: var(--color-primary);
}
.variant-icon:active:not(.is-disabled) {
  background: var(--color-surface-hover);
  transform: scale(0.95);
}

/* Danger — Destructive actions */
.variant-danger {
  background: var(--color-danger);
  color: #FFFFFF;
  box-shadow: var(--shadow-sm);
}
.variant-danger:hover:not(.is-disabled) {
  background: #DC2626;
  box-shadow: var(--shadow-md);
}
.variant-danger:active:not(.is-disabled) {
  background: #DC2626;
  transform: scale(0.98);
}
.variant-danger:hover:not(.is-disabled)::before {
  opacity: 0.08;
}
.variant-danger:active:not(.is-disabled)::before {
  opacity: 0.16;
}

/* ============================================================
   States — Clear visual feedback
   ============================================================ */

/* Disabled — Reduced opacity, no interaction */
.base-btn.is-disabled {
  opacity: 0.48;
  cursor: not-allowed;
  pointer-events: none;
  box-shadow: none;
  transform: none !important;
}

/* Loading — Spinner replaces content */
.base-btn.is-loading {
  cursor: wait;
  pointer-events: none;
}

.btn-loader {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: btn-spin 0.6s linear infinite;
}

@keyframes btn-spin {
  100% { transform: rotate(360deg); }
}

/* ============================================================
   Focus — Accessibility (WCAG 2.1)
   ============================================================ */

.base-btn:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 2px;
}

/* Icon wrapper */
.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.btn-text {
  white-space: nowrap;
}
</style>
