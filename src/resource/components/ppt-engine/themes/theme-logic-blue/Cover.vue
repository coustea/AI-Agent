<template>
  <div class="logic-blue-slide logic-blue-cover">
    <!-- 学术栅格背景线 -->
    <div class="grid-background"></div>
    
    <div class="cover-layout">
      <div class="cover-content-left animate-slide-up">
        <div class="title-indicator"></div>
        <h1 class="main-title">{{ data.main_title }}</h1>
        <h2 class="sub-title" v-if="data.sub_title">{{ data.sub_title }}</h2>
      </div>
      
      <div class="cover-content-right animate-fade-in">
        <div class="meta-card">
          <div class="meta-item" v-if="data.lecturer">
            <span class="meta-label">PRESENTER</span>
            <span class="meta-value">{{ data.lecturer }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">COURSEWARE</span>
            <span class="meta-value">学枢 AI 学习规划</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 极简装饰性横线 -->
    <div class="bottom-axis"></div>
  </div>
</template>

<script setup lang="ts">
import type { CoverData } from '../../types/ppt';

defineProps<{
  data: CoverData
}>();
</script>

<style scoped>
.logic-blue-slide {
  width: 100%;
  height: 100%;
  background-color: #0B0F19; /* 更沉稳的深黛色 */
  position: relative;
  overflow: hidden;
  box-sizing: border-box;
  font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
}

/* 严谨的背景网络格线，保持超低可见度 */
.grid-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: 
    linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
  background-size: 40px 40px;
  z-index: 1;
}

.cover-layout {
  position: relative;
  z-index: 10;
  width: 100%;
  height: 100%;
  display: flex;
  padding: 80px 100px;
  box-sizing: border-box;
  align-items: center;
  justify-content: space-between;
}

.cover-content-left {
  flex: 1;
  max-width: 60%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  position: relative;
  padding-left: 28px;
}

/* 精致的左侧垂直指示线条 */
.title-indicator {
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 4px;
  background: #3B82F6; /* 蔚蓝色 */
  border-radius: 2px;
}

.main-title {
  font-size: 52px;
  color: #F8FAFC;
  font-weight: 800;
  letter-spacing: -0.5px;
  margin: 0 0 16px 0;
  line-height: 1.25;
  text-align: left;
}

.sub-title {
  font-size: 22px;
  color: #64748B; /* 柔和暗灰 */
  font-weight: 400;
  margin: 0;
  text-align: left;
  line-height: 1.4;
}

.cover-content-right {
  width: 30%;
  display: flex;
  justify-content: flex-end;
}

.meta-card {
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  padding-left: 32px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.meta-label {
  font-size: 11px;
  font-weight: 600;
  color: #3B82F6;
  letter-spacing: 1.5px;
}

.meta-value {
  font-size: 18px;
  color: #E2E8F0;
  font-weight: 500;
}

/* 底部极细刻度基准线，增强结构感 */
.bottom-axis {
  position: absolute;
  left: 100px;
  right: 100px;
  bottom: 80px;
  height: 1px;
  background: rgba(255, 255, 255, 0.06);
  z-index: 5;
}

/* 入场动画 */
.animate-slide-up {
  animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.animate-fade-in {
  animation: fadeIn 1s cubic-bezier(0.16, 1, 0.3, 1) 0.2s forwards;
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
