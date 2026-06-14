<template>
  <div class="notion-light-slide notion-agenda">
    <div class="notion-page">
      <h2 class="slide-title">Table of Contents</h2>
      
      <div class="agenda-list">
        <div 
          class="agenda-item" 
          v-for="(item, idx) in data.list" 
          :key="idx"
        >
          <div class="item-index">{{ idx + 1 }}</div>
          <div class="item-text">{{ item }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AgendaData } from '../../types/ppt';

defineProps<{
  data: AgendaData
}>();
</script>

<style scoped>
.notion-light-slide {
  width: 100%;
  height: 100%;
  background: #FFFFFF;
  display: flex;
  justify-content: center;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, "Apple Color Emoji", Arial, sans-serif, "Segoe UI Emoji", "Segoe UI Symbol";
  color: #37352f;
  padding: 80px;
  box-sizing: border-box;
}

.notion-page {
  width: 100%;
  max-width: 900px;
  display: flex;
  flex-direction: column;
}

.slide-title {
  font-size: 40px;
  font-weight: 700;
  margin: 0 0 40px 0;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(55, 53, 47, 0.09);
}

.agenda-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.agenda-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  border-radius: 6px;
  transition: background 0.2s;
  cursor: pointer;
}

.agenda-item:hover {
  background: rgba(55, 53, 47, 0.08);
}

.item-index {
  font-size: 16px;
  color: rgba(55, 53, 47, 0.4);
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, Courier, monospace;
  width: 24px;
}

.item-text {
  font-size: 20px;
  font-weight: 500;
  color: #37352f;
}
</style>
