<template>
  <div class="logic-blue-slide logic-blue-bullet">
    <div class="header-band">
      <h2 class="slide-title">{{ data.title }}</h2>
    </div>
    
    <div class="content-area">
      <ul class="bullet-list">
        <li class="bullet-item" v-for="(point, index) in data.points" :key="index">
          <div class="bullet-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
          <span class="bullet-text">{{ point }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { BulletPointsData } from '../../../types/ppt';

defineProps<{
  data: BulletPointsData
}>();

declare function withDefaults<T, D>(props: T, defaults: D): T;
</script>

<style scoped>
.logic-blue-slide {
  width: 100%;
  height: 100%;
  background-color: #F8FAFC;
  display: flex;
  flex-direction: column;
}

.header-band {
  background-color: #1E293B;
  padding: 50px 100px;
  border-bottom: 8px solid #2563EB;
}

.slide-title {
  font-size: 52px;
  color: #FFFFFF;
  margin: 0;
  font-weight: 700;
}

.content-area {
  flex: 1;
  padding: 60px 100px;
  display: flex;
  align-items: center;
}

.bullet-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 36px;
}

.bullet-item {
  display: flex;
  align-items: flex-start;
  gap: 24px;
}

.bullet-icon {
  width: 36px;
  height: 36px;
  background-color: #DBEAFE;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2563EB;
  flex-shrink: 0;
  margin-top: 6px;
}

.bullet-icon svg {
  width: 20px;
  height: 20px;
}

.bullet-text {
  font-size: 32px;
  color: #334155;
  line-height: 1.5;
  font-weight: 500;
}
</style>
