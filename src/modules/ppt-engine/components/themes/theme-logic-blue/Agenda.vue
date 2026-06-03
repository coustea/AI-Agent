<template>
  <div class="logic-blue-slide logic-blue-agenda">
    <header class="slide-header">
      <div class="header-indicator"></div>
      <h2 class="slide-title">目录 / Agenda</h2>
    </header>
    
    <div class="agenda-content">
      <div class="timeline-container">
        <!-- 贯穿线 -->
        <div class="timeline-line"></div>
        
        <div class="agenda-items-wrapper">
          <div 
            v-for="(item, index) in (data.list || (data as any).items || [])" 
            :key="index" 
            class="agenda-row animate-fade-in"
            :style="{ animationDelay: `${index * 0.1}s` }"
          >
            <!-- 节点圆圈与序号 -->
            <div class="timeline-node">
              <span class="node-number">{{ String(index + 1).padStart(2, '0') }}</span>
            </div>
            
            <!-- 内容卡片 -->
            <div class="agenda-card">
              <div class="agenda-text">{{ item }}</div>
              <div class="agenda-decor-dot"></div>
            </div>
          </div>
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
.logic-blue-slide {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%);
  padding: 60px 80px;
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
  margin-bottom: 40px;
}

.header-indicator {
  width: 6px;
  height: 32px;
  background: #3B82F6;
  border-radius: 3px;
}

.slide-title {
  font-size: 38px;
  color: #0F172A; /* 深海蓝/黑 */
  margin: 0;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.agenda-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding-left: 20px;
}

.timeline-container {
  position: relative;
  width: 100%;
  display: flex;
}

/* 垂直指示线 */
.timeline-line {
  position: absolute;
  left: 24px;
  top: 15px;
  bottom: 15px;
  width: 2px;
  background: #E2E8F0;
  z-index: 1;
}

.agenda-items-wrapper {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 80%;
  z-index: 2;
}

.agenda-row {
  display: flex;
  align-items: center;
  gap: 28px;
  opacity: 0; /* 配合动画 */
}

.timeline-node {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: #FFFFFF;
  border: 2px solid #E2E8F0;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
  flex-shrink: 0;
}

.node-number {
  font-size: 18px;
  font-weight: 700;
  color: #64748B;
  font-family: "JetBrains Mono", Consolas, monospace;
}

.agenda-row:hover .timeline-node {
  border-color: #3B82F6;
  box-shadow: 0 4px 10px rgba(59, 130, 246, 0.15);
}

.agenda-row:hover .node-number {
  color: #3B82F6;
}

.agenda-card {
  flex: 1;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  padding: 16px 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
  transition: all 0.3s;
}

.agenda-row:hover .agenda-card {
  border-color: #BFDBFE;
  transform: translateX(4px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
}

.agenda-text {
  font-size: 22px;
  font-weight: 600;
  color: #334155;
}

.agenda-decor-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #CBD5E1;
  transition: all 0.3s;
}

.agenda-row:hover .agenda-decor-dot {
  background: #3B82F6;
  transform: scale(1.3);
}

/* 动效 */
.animate-fade-in {
  animation: slideInRight 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes slideInRight {
  0% {
    opacity: 0;
    transform: translateX(20px);
  }
  100% {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
