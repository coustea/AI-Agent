<template>
  <div class="block-formula ppt-card formula-whiteboard">
    <div class="whiteboard-top-pin"></div>
    <div class="formula-container">
      <span class="math-formula-text">{{ block.formula }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { FormulaBlock } from '../../types/ppt'

defineProps<{
  block: FormulaBlock
}>()
</script>

<style scoped>
.block-formula {
  margin-bottom: 1.2em;
  padding: 32px 24px;
  background-color: var(--ppt-bg-secondary);
  border-radius: var(--ppt-radius-md);
  border: 1px solid var(--ppt-border);
  box-shadow: var(--ppt-shadow-card);
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow-x: auto;
}

.formula-whiteboard {
  background: linear-gradient(180deg, var(--ppt-bg-secondary) 0%, rgba(37, 99, 235, 0.01) 100%);
  border-top: 4px solid var(--ppt-accent);
}

.whiteboard-top-pin {
  position: absolute;
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 6px;
  background: var(--ppt-border);
  border-radius: var(--ppt-radius-sm);
}

.formula-container {
  font-size: 1.65rem;
  color: var(--ppt-text-primary);
  font-family: 'Times New Roman', Times, serif;
  font-style: italic;
  padding: 10px;
  text-align: center;
}

.math-formula-text {
  display: inline-block;
  letter-spacing: 0.05em;
}
</style>
