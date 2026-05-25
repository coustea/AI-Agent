<template>
  <div class="logic-blue-slide logic-blue-agenda">
    <div class="agenda-container">
      <h2 class="slide-title">目录 / Agenda</h2>
      <div class="agenda-list">
        <div class="agenda-item" v-for="(item, index) in data.list" :key="index">
          <div class="item-number">{{ String(index + 1).padStart(2, '0') }}</div>
          <div class="item-text">{{ item }}</div>
          <div class="item-line"></div>
        </div>
      </div>
    </div>
    
    <!-- 左侧装饰条 -->
    <div class="side-decoration"></div>
  </div>
</template>

<script setup lang="ts">
import type { AgendaData } from '../../types/ppt';

defineProps<{
  data: AgendaData
}>();
</script>

<style scoped>
.logic-blue-slide {
  width: 100%;
  height: 100%;
  background-color: #FFFFFF;
  display: flex;
  position: relative;
}

.side-decoration {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 120px;
  background-color: #0F172A;
  background-image: radial-gradient(#334155 2px, transparent 2px);
  background-size: 20px 20px;
}

.agenda-container {
  margin-left: 120px;
  padding: 80px 100px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.slide-title {
  font-size: 56px;
  color: #1E293B;
  margin-bottom: 80px;
  font-weight: 800;
  letter-spacing: 2px;
}

.agenda-list {
  display: flex;
  flex-direction: column;
  gap: 40px;
  flex: 1;
  justify-content: center;
  padding-bottom: 60px;
}

.agenda-item {
  display: flex;
  align-items: center;
  gap: 32px;
}

.item-number {
  font-size: 48px;
  font-weight: 900;
  color: #3B82F6;
  font-family: 'Courier New', Courier, monospace;
}

.item-text {
  font-size: 36px;
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
}

.item-line {
  flex: 1;
  height: 2px;
  background-image: linear-gradient(to right, #CBD5E1 50%, transparent 50%);
  background-size: 20px 2px;
  background-repeat: repeat-x;
  opacity: 0.5;
}
</style>
