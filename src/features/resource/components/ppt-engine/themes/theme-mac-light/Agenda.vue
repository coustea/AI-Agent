<template>
  <div class="mac-light-slide mac-light-agenda">
    <div class="mac-window">
      <div class="mac-titlebar">
        <div class="mac-buttons">
          <span class="mac-btn close"></span>
          <span class="mac-btn minimize"></span>
          <span class="mac-btn maximize"></span>
        </div>
      </div>
      <div class="mac-content">
        <header class="slide-header">
          <h2 class="slide-title">Agenda / 目录</h2>
        </header>
        
        <div class="agenda-content">
          <div class="agenda-items-wrapper">
            <div 
              v-for="(item, index) in data.list" 
              :key="index" 
              class="agenda-row"
              :style="{ animationDelay: `${index * 0.15}s` }"
            >
              <div class="node-number">{{ String(index + 1).padStart(2, '0') }}</div>
              <div class="agenda-card">
                <div class="agenda-text">{{ item }}</div>
              </div>
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
.mac-light-slide {
  width: 100%;
  height: 100%;
  background: #F9FAFB;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
  padding: 60px 80px;
  box-sizing: border-box;
}

.mac-window {
  width: 100%;
  height: 100%;
  background: #FFFFFF;
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.mac-titlebar {
  height: 38px;
  background: #F3F4F6;
  border-bottom: 1px solid #E5E7EB;
  display: flex;
  align-items: center;
  padding: 0 16px;
}

.mac-buttons {
  display: flex;
  gap: 8px;
}

.mac-btn {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
.mac-btn.close { background: #FF5F56; border: 1px solid #E0443E; }
.mac-btn.minimize { background: #FFBD2E; border: 1px solid #DEA123; }
.mac-btn.maximize { background: #27C93F; border: 1px solid #1AAB29; }

.mac-content {
  flex: 1;
  padding: 40px 60px;
  display: flex;
  flex-direction: column;
}

.slide-header {
  margin-bottom: 40px;
  border-bottom: 2px solid #F3F4F6;
  padding-bottom: 20px;
}

.slide-title {
  font-size: 36px;
  color: #111827;
  margin: 0;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.agenda-content {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.agenda-items-wrapper {
  display: flex;
  flex-direction: column;
  gap: 24px;
  width: 100%;
  max-width: 800px;
}

.agenda-row {
  display: flex;
  align-items: center;
  gap: 32px;
  opacity: 0;
  animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.node-number {
  font-size: 48px;
  font-weight: 800;
  color: #E5E7EB;
  font-family: var(--font-mono, monospace);
  width: 80px;
  text-align: right;
  transition: color 0.3s;
}

.agenda-row:hover .node-number {
  color: #3B82F6;
}

.agenda-card {
  flex: 1;
  background: #F9FAFB;
  border: 1px solid #F3F4F6;
  border-radius: 12px;
  padding: 24px 32px;
  transition: all 0.3s;
}

.agenda-row:hover .agenda-card {
  background: #FFFFFF;
  border-color: #BFDBFE;
  box-shadow: 0 10px 20px rgba(59, 130, 246, 0.08);
  transform: translateX(8px);
}

.agenda-text {
  font-size: 24px;
  font-weight: 600;
  color: #374151;
}

@keyframes slideUp {
  0% { opacity: 0; transform: translateY(20px); }
  100% { opacity: 1; transform: translateY(0); }
}
</style>
