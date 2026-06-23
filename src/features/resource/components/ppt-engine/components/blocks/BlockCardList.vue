<template>
  <div class="block-card-list">
    <div v-for="(card, index) in block.cards" :key="`${card.title}-${index}`" class="card-item ppt-card">
      <div class="card-title">
        <span v-if="card.icon" class="icon">{{ card.icon }}</span>
        <span class="title-text">{{ card.title }}</span>
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
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
  width: 100%;
}

.card-item {
  padding: 22px;
  border-radius: var(--ppt-radius-md);
  background: linear-gradient(135deg, var(--ppt-bg-secondary) 0%, rgba(148, 163, 184, 0.04) 100%);
  border: 1px solid var(--ppt-border);
  box-shadow: var(--ppt-shadow-card);
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), 
              border-color 0.3s ease, 
              box-shadow 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card-item:hover {
  transform: translateY(-5px);
  border-color: var(--ppt-accent);
  box-shadow: 0 20px 30px rgba(0, 0, 0, 0.07);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-text {
  font-weight: 800;
  font-size: 1.1rem;
  color: var(--ppt-text-primary);
}

.icon {
  font-size: 1.25rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.card-content {
  line-height: 1.6;
  font-size: 0.98rem;
  color: var(--ppt-text-secondary);
}
</style>
