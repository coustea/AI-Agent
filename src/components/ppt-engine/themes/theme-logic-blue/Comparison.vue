<template>
  <div class="logic-blue-slide logic-blue-comparison">
    <header class="slide-header animate-slide-up">
      <div class="header-indicator"></div>
      <h2 class="slide-title">{{ data.title }}</h2>
    </header>
    
    <div class="comparison-container animate-fade-in">
      <!-- 比较栏表头 -->
      <div class="comparison-headers">
        <div class="compare-header left-header">
          <span class="header-label">{{ data.left_label }}</span>
        </div>
        <div class="compare-header right-header">
          <span class="header-label">{{ data.right_label }}</span>
        </div>
      </div>
      
      <!-- 核心对比表格（对齐斑马纹） -->
      <div class="comparison-table">
        <div 
          v-for="(_, index) in maxRows" 
          :key="index" 
          class="table-row"
          :class="{ 'zebra-row': index % 2 === 1 }"
        >
          <!-- 左侧内容 -->
          <div class="table-cell left-cell">
            <span class="row-marker marker-left">•</span>
            <span class="cell-text">{{ data.left_content[index] || '—' }}</span>
          </div>
          
          <!-- 中间渐变虚线分隔 -->
          <div class="row-divider"></div>
          
          <!-- 右侧内容 -->
          <div class="table-cell right-cell">
            <span class="row-marker marker-right">•</span>
            <span class="cell-text">{{ data.right_content[index] || '—' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ComparisonData } from '../../types/ppt';

const props = defineProps<{
  data: ComparisonData
}>();

const maxRows = computed(() => {
  const leftLen = props.data.left_content?.length || 0;
  const rightLen = props.data.right_content?.length || 0;
  return Math.max(leftLen, rightLen);
});
</script>

<style scoped>
.logic-blue-slide {
  width: 100%;
  height: 100%;
  padding: 60px 80px;
  background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%);
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
}

.slide-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 36px;
}

.header-indicator {
  width: 6px;
  height: 32px;
  background: #3B82F6;
  border-radius: 3px;
}

.slide-title {
  font-size: 38px;
  color: #0F172A;
  margin: 0;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.comparison-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
  overflow: hidden;
}

.comparison-headers {
  display: flex;
  background: #F8FAFC;
  border-bottom: 1px solid #E2E8F0;
  position: relative;
}

.compare-header {
  flex: 1;
  padding: 20px 40px;
  text-align: center;
  box-sizing: border-box;
}

.left-header {
  border-right: 1px dashed #E2E8F0;
}

.header-label {
  font-size: 22px;
  font-weight: 700;
  color: #334155;
}

.right-header .header-label {
  color: #2563EB; /* 右侧重点栏颜色 */
}

.comparison-table {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.table-row {
  display: flex;
  align-items: stretch;
  border-bottom: 1px solid #F1F5F9;
  position: relative;
}

.table-row:last-child {
  border-bottom: none;
}

.zebra-row {
  background-color: #F8FAFC;
}

.table-cell {
  flex: 1;
  padding: 20px 40px;
  box-sizing: border-box;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  text-align: left;
}

.left-cell {
  border-right: 1px dashed #E2E8F0;
}

.row-marker {
  font-size: 24px;
  line-height: 18px;
  font-weight: bold;
  flex-shrink: 0;
}

.marker-left {
  color: #94A3B8;
}

.marker-right {
  color: #3B82F6;
}

.cell-text {
  font-size: 18px;
  color: #475569;
  line-height: 1.55;
  font-weight: 500;
}

.right-cell .cell-text {
  color: #334155;
}

.table-row:hover {
  background-color: #EFF6FF;
}

/* 动效 */
.animate-slide-up {
  animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.animate-fade-in {
  animation: fadeIn 1s cubic-bezier(0.16, 1, 0.3, 1) 0.1s forwards;
  opacity: 0;
}

@keyframes slideUp {
  0% {
    opacity: 0;
    transform: translateY(20px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeIn {
  0% {
    opacity: 0;
  }
  100% {
    opacity: 1;
  }
}
</style>
