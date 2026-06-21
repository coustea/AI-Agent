<template>
  <div class="block-formula">
    <div class="formula-container">
      $$ {{ block.formula }} $$
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
  margin-bottom: 1em;
  padding: 2rem;
  background-color: var(--ppt-bg-secondary);
  border-radius: var(--ppt-radius);
  display: flex;
  justify-content: center;
  align-items: center;
  overflow-x: auto;
}

.formula-container {
  font-size: 1.5rem;
  color: var(--ppt-text-primary);
}
</style>
