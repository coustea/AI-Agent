<template>
  <div :class="['base-input-wrapper', { 'is-focused': focused, 'is-disabled': disabled }]">
    <div v-if="$slots.prefix" class="input-prefix">
      <slot name="prefix"></slot>
    </div>
    <input
      ref="inputRef"
      class="base-input-inner"
      :value="modelValue"
      :disabled="disabled"
      v-bind="$attrs"
      @input="handleInput"
      @focus="handleFocus"
      @blur="handleBlur"
    />
    <div v-if="$slots.suffix" class="input-suffix">
      <slot name="suffix"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'focus', 'blur'])

const focused = ref(false)

const handleInput = (e: Event) => {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
}

const handleFocus = (e: FocusEvent) => {
  focused.value = true
  emit('focus', e)
}

const handleBlur = (e: FocusEvent) => {
  focused.value = false
  emit('blur', e)
}
</script>

<style scoped>
.base-input-wrapper {
  display: inline-flex;
  align-items: center;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 0 12px;
  height: 40px;
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
  box-sizing: border-box;
  width: 100%;
}

.base-input-wrapper.is-focused {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
}

.base-input-wrapper.is-disabled {
  background: var(--color-bg);
  cursor: not-allowed;
}

.base-input-inner {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  color: var(--color-text);
  font-family: var(--font-sans);
  font-size: 0.95rem;
  min-width: 0;
  height: 100%;
}

.base-input-inner::placeholder {
  color: var(--color-text-faint);
}

.base-input-inner:disabled {
  cursor: not-allowed;
}

.input-prefix {
  margin-right: 8px;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
}

.input-suffix {
  margin-left: 8px;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
}
</style>
