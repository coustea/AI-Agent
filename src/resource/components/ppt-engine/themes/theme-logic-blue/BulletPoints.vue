<template>
  <div class="logic-blue-slide logic-blue-bullet">
    <div class="bullet-layout">
      <!-- 左侧：核心主题导读 -->
      <div class="layout-left animate-slide-up">
        <div class="header-indicator"></div>
        <h2 class="slide-title">{{ data.title }}</h2>
        <div class="title-decor-line"></div>
        <p class="title-sub-desc">CORE CONCEPTS & ANALYSIS</p>
      </div>
      
      <!-- 右侧：要点结构列表 -->
      <div class="layout-right">
        <div class="bullet-list">
          <div 
            v-for="(point, index) in data.points" 
            :key="index" 
            class="bullet-card animate-fade-in"
            :style="{ animationDelay: `${index * 0.1}s` }"
          >
            <div class="bullet-icon-container">
              <div class="bullet-icon-circle">
                <span class="bullet-index">{{ index + 1 }}</span>
              </div>
            </div>
            
            <div class="bullet-content">
              <template v-if="parsePoint(point).label">
                <span class="point-badge">{{ parsePoint(point).label }}</span>
                <span class="point-text with-badge">{{ parsePoint(point).text }}</span>
              </template>
              <template v-else>
                <span class="point-text">{{ point }}</span>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { BulletPointsData } from '../../types/ppt';

defineProps<{
  data: BulletPointsData
}>();

interface ParsedPoint {
  label: string;
  text: string;
}

// 解析带有 【】 括号前缀的结构化句子
const parsePoint = (point: string): ParsedPoint => {
  const match = point.match(/^【(.*?)】(.*)$/);
  if (match) {
    return {
      label: match[1] || '',
      text: (match[2] || '').trim()
    };
  }
  return {
    label: '',
    text: point
  };
};
</script>

<style scoped>
.logic-blue-slide {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%);
  padding: 60px 80px;
  box-sizing: border-box;
  overflow: hidden;
  font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
}

.bullet-layout {
  display: flex;
  width: 100%;
  height: 100%;
  gap: 48px;
  align-items: center;
}

.layout-left {
  width: 35%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.header-indicator {
  width: 6px;
  height: 24px;
  background: #3B82F6;
  border-radius: 3px;
  margin-bottom: 16px;
}

.slide-title {
  font-size: 38px;
  color: #0F172A;
  font-weight: 800;
  line-height: 1.3;
  margin: 0 0 16px 0;
  text-align: left;
}

.title-decor-line {
  width: 60px;
  height: 2px;
  background: #E2E8F0;
  margin-bottom: 12px;
}

.title-sub-desc {
  font-size: 11px;
  font-weight: 600;
  color: #94A3B8;
  letter-spacing: 1.5px;
  margin: 0;
}

.layout-right {
  width: 65%;
  display: flex;
  flex-direction: column;
}

.bullet-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.bullet-card {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 18px 24px;
  display: flex;
  align-items: flex-start;
  gap: 18px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.01);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  opacity: 0; /* 配合动画 */
}

.bullet-card:hover {
  border-color: #BFDBFE;
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.05);
}

.bullet-icon-container {
  flex-shrink: 0;
  margin-top: 2px;
}

.bullet-icon-circle {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3B82F6;
}

.bullet-index {
  font-size: 12px;
  font-weight: 700;
  font-family: "JetBrains Mono", Consolas, monospace;
}

.bullet-content {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  text-align: left;
}

.point-badge {
  font-size: 12px;
  font-weight: 700;
  background: #EFF6FF;
  color: #2563EB;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #DBEAFE;
}

.point-text {
  font-size: 19px;
  color: #334155;
  line-height: 1.5;
  font-weight: 500;
}

.point-text.with-badge {
  color: #475569;
}

/* 动效 */
.animate-slide-up {
  animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.animate-fade-in {
  animation: slideInLeft 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
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

@keyframes slideInLeft {
  0% {
    opacity: 0;
    transform: translateX(-20px);
  }
  100% {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
