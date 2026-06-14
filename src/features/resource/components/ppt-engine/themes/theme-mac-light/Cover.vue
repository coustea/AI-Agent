<template>
  <div class="mac-light-slide mac-light-cover">
    <div class="mac-window">
      <div class="mac-titlebar">
        <div class="mac-buttons">
          <span class="mac-btn close"></span>
          <span class="mac-btn minimize"></span>
          <span class="mac-btn maximize"></span>
        </div>
      </div>
      <div class="mac-content">
        <h1 class="main-title">{{ data.main_title }}</h1>
        <h2 class="sub-title" v-if="data.sub_title">{{ data.sub_title }}</h2>
        
        <div class="meta-card">
          <div class="meta-item" v-if="data.lecturer">
            <span class="meta-label">讲师</span>
            <span class="meta-value">{{ data.lecturer }}</span>
          </div>
          <div class="meta-item" v-if="data.date">
            <span class="meta-label">日期</span>
            <span class="meta-value">{{ data.date }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CoverData } from '../../types/ppt';

defineProps<{
  data: CoverData
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
  padding: 60px 80px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  background-image: radial-gradient(#E5E7EB 1px, transparent 1px);
  background-size: 24px 24px;
}

.main-title {
  font-size: 64px;
  color: #111827;
  font-weight: 800;
  letter-spacing: -1px;
  margin: 0 0 24px 0;
  line-height: 1.15;
}

.sub-title {
  font-size: 32px;
  color: #4B5563;
  font-weight: 500;
  margin: 0 0 60px 0;
  line-height: 1.4;
}

.meta-card {
  display: flex;
  gap: 40px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  padding: 24px 32px;
  border-radius: 12px;
  border: 1px solid #E5E7EB;
  align-self: flex-start;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.meta-label {
  font-size: 14px;
  color: #6B7280;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.meta-value {
  font-size: 20px;
  color: #111827;
  font-weight: 500;
  font-family: var(--font-mono, monospace);
}
</style>
