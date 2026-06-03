<template>
  <div class="logic-blue-slide logic-blue-grid">
    <header class="slide-header animate-slide-up">
      <div class="header-indicator"></div>
      <h2 class="slide-title">{{ data.title }}</h2>
    </header>
    
    <div class="cards-container">
      <div 
        class="card-item animate-fade-in" 
        v-for="(card, index) in data.cards" 
        :key="index"
        :style="{ animationDelay: `${index * 0.1}s` }"
      >
        <!-- 卡片序号区 -->
        <div class="card-meta">
          <span class="card-index">{{ String(index + 1).padStart(2, '0') }}</span>
          <div class="card-index-dot"></div>
        </div>
        
        <!-- 卡片正文区 -->
        <div class="card-body">
          <h3 class="card-title">{{ card.title }}</h3>
          <p class="card-desc">{{ card.desc }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GridCardsData } from '../../types/ppt';

defineProps<{
  data: GridCardsData
}>();
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
  color: #0F172A;
  margin: 0;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.cards-container {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  gap: 28px;
  flex: 1;
  align-items: stretch;
  padding-bottom: 20px;
}

.card-item {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 16px;
  padding: 28px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  box-sizing: border-box;
  opacity: 0; /* 配合入场动画 */
}

.card-item:hover {
  border-color: #BFDBFE;
  transform: translateY(-6px);
  box-shadow: 0 20px 25px -5px rgba(59, 130, 246, 0.05), 0 8px 10px -6px rgba(59, 130, 246, 0.05);
}

.card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  border-bottom: 1px solid #F1F5F9;
  padding-bottom: 12px;
}

.card-index {
  font-size: 24px;
  font-weight: 800;
  color: #94A3B8;
  font-family: "JetBrains Mono", Consolas, monospace;
}

.card-item:hover .card-index {
  color: #3B82F6;
}

.card-index-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #E2E8F0;
  transition: all 0.3s;
}

.card-item:hover .card-index-dot {
  background: #3B82F6;
  transform: scale(1.3);
}

.card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
}

.card-title {
  font-size: 22px;
  color: #1E293B;
  font-weight: 700;
  margin: 0 0 14px 0;
  line-height: 1.3;
}

.card-desc {
  font-size: 16px;
  color: #64748B;
  line-height: 1.6;
  margin: 0;
  font-weight: 500;
}

.card-item:hover .card-desc {
  color: #475569;
}

/* 动效 */
.animate-slide-up {
  animation: slideUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.animate-fade-in {
  animation: slideInUp 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
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

@keyframes slideInUp {
  0% {
    opacity: 0;
    transform: translateY(30px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
