<template>
  <div class="logic-blue-slide logic-blue-agenda">
    <header class="slide-header">
      <div>
        <div class="eyebrow">NAVIGATION</div>
        <h2 class="slide-title">Agenda / 目录</h2>
      </div>
      <div class="header-meta">{{ data.list.length }} Sections</div>
    </header>

    <div class="agenda-content">
      <div class="timeline-container">
        <div class="timeline-line"></div>

        <div class="agenda-items-wrapper">
          <div
            v-for="(item, index) in data.list"
            :key="index"
            class="agenda-row animate-fade-in"
            :style="{ animationDelay: `${index * 0.1}s` }"
          >
            <div class="timeline-node">
              <span class="node-number">{{ String(index + 1).padStart(2, '0') }}</span>
            </div>

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
  background:
    radial-gradient(circle at 100% 0%, rgba(37, 99, 235, 0.14), transparent 42%),
    radial-gradient(circle at 0% 100%, rgba(14, 165, 233, 0.1), transparent 38%),
    linear-gradient(180deg, #eef4ff 0%, #f8fbff 100%);
  padding: 58px 76px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  font-family: "Avenir Next", "Segoe UI", sans-serif;
}

.slide-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 28px;
}

.eyebrow {
  color: #2563eb;
  font-size: 12px;
  letter-spacing: 2px;
  font-weight: 800;
  margin-bottom: 10px;
}

.slide-title {
  font-size: 42px;
  color: #0f172a;
  margin: 0;
  font-weight: 800;
  letter-spacing: -0.8px;
}

.header-meta {
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-size: 13px;
  font-weight: 700;
}

.agenda-content {
  flex: 1;
  display: flex;
  align-items: stretch;
  justify-content: center;
}

.timeline-container {
  position: relative;
  width: 100%;
  display: flex;
  padding: 18px 0 8px;
}

.timeline-line {
  position: absolute;
  left: 24px;
  top: 24px;
  bottom: 24px;
  width: 2px;
  background: linear-gradient(180deg, rgba(96, 165, 250, 0.15), rgba(37, 99, 235, 0.4), rgba(125, 211, 252, 0.12));
  z-index: 1;
}

.agenda-items-wrapper {
  display: flex;
  flex-direction: column;
  gap: 18px;
  width: 100%;
  z-index: 2;
}

.agenda-row {
  display: flex;
  align-items: center;
  gap: 28px;
  opacity: 0; /* 配合动画 */
}

.timeline-node {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(219, 234, 254, 0.88));
  backdrop-filter: blur(12px);
  border: 1px solid rgba(96, 165, 250, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.12);
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  flex-shrink: 0;
}

.node-number {
  font-size: 18px;
  font-weight: 700;
  color: #2563eb;
  font-family: "JetBrains Mono", Consolas, monospace;
}

.agenda-row:hover .timeline-node {
  transform: scale(1.06);
  box-shadow: 0 18px 30px rgba(59, 130, 246, 0.18);
}

.agenda-card {
  flex: 1;
  min-height: 96px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(191, 219, 254, 0.8);
  border-radius: 22px;
  padding: 22px 26px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 16px 34px rgba(148, 163, 184, 0.12);
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.agenda-row:hover .agenda-card {
  border-color: rgba(37, 99, 235, 0.28);
  transform: translateX(6px);
  box-shadow: 0 18px 36px rgba(59, 130, 246, 0.14);
}

.agenda-text {
  font-size: 24px;
  font-weight: 600;
  color: #1e293b;
}

.agenda-decor-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: linear-gradient(180deg, #38bdf8, #2563eb);
  transition: all 0.3s;
}

.agenda-row:hover .agenda-decor-dot {
  transform: scale(1.3);
}

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
