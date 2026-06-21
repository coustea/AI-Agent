<template>
  <div class="block-card-list">
    <div v-for="(card, index) in block.cards" :key="`${card.title}-${index}`" class="card-item">
      <div class="card-title">
        <span v-if="card.icon" class="icon">{{ card.icon }}</span>
        <span>{{ card.title }}</span>
      </div>
      <div class="card-content">{{ card.content }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CardListBlock } from '../../types/ppt'

defineProps<{
  block: CardListBlock
}>()
</script>

<style scoped>
.block-card-list {
  display: grid;
  gap: 12px;
}

.card-item {
  padding: 14px 16px;
  border-radius: var(--ppt-radius);
  background: var(--ppt-bg-secondary);
  border: 1px solid var(--ppt-border);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 800;
  color: var(--ppt-text-primary);
}

.icon {
  font-size: 1rem;
}

.card-content {
  margin-top: 8px;
  line-height: 1.55;
  color: var(--ppt-text-secondary);
}
</style>
