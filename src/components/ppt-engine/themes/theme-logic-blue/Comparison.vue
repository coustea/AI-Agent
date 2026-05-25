<template>
  <div class="logic-blue-slide logic-blue-comparison">
    <h2 class="slide-title">{{ data.title }}</h2>
    
    <div class="comparison-container">
      <!-- 左侧栏 -->
      <div class="compare-col left-col">
        <div class="col-header">{{ data.left_label }}</div>
        <ul class="col-list">
          <li v-for="(item, index) in data.left_content" :key="`left-${index}`">
            <span class="marker marker-left"></span>
            {{ item }}
          </li>
        </ul>
      </div>
      
      <!-- VS 分隔 -->
      <div class="vs-divider">
        <div class="vs-circle">VS</div>
      </div>
      
      <!-- 右侧栏 -->
      <div class="compare-col right-col">
        <div class="col-header">{{ data.right_label }}</div>
        <ul class="col-list">
          <li v-for="(item, index) in data.right_content" :key="`right-${index}`">
            <span class="marker marker-right"></span>
            {{ item }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ComparisonData } from '../../types/ppt';

defineProps<{
  data: ComparisonData
}>();
</script>

<style scoped>
.logic-blue-slide {
  width: 100%;
  height: 100%;
  padding: 80px 100px;
  background-color: #FFFFFF;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.slide-title {
  font-size: 52px;
  color: #0F172A;
  margin-bottom: 60px;
  text-align: center;
  font-weight: 800;
}

.comparison-container {
  display: flex;
  flex: 1;
  position: relative;
  gap: 80px;
}

.compare-col {
  flex: 1;
  background: #F8FAFC;
  border-radius: 24px;
  padding: 40px;
  border: 2px solid #E2E8F0;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
}

.left-col {
  border-top: 8px solid #94A3B8;
}

.right-col {
  border-top: 8px solid #3B82F6;
  background: #EFF6FF;
  border-color: #BFDBFE;
}

.col-header {
  font-size: 36px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 40px;
  color: #1E293B;
}

.right-col .col-header {
  color: #1D4ED8;
}

.col-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.col-list li {
  font-size: 26px;
  color: #475569;
  line-height: 1.6;
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.marker {
  margin-top: 10px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  flex-shrink: 0;
}

.marker-left {
  background-color: #94A3B8;
}

.marker-right {
  background-color: #3B82F6;
}

.vs-divider {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.vs-divider::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background-color: #E2E8F0;
  z-index: 0;
}

.vs-circle {
  width: 80px;
  height: 80px;
  background: #1E293B;
  color: #FFFFFF;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 900;
  font-style: italic;
  z-index: 1;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border: 4px solid #FFFFFF;
}
</style>
