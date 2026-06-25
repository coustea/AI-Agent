<template>
  <div class="framework-diagram">
    <div class="framework-container">
      <svg class="connections-svg" preserveAspectRatio="none" viewBox="0 0 100 100">
        <!-- SVG lines drawn via CSS absolute positioning from center to cards -->
      </svg>
      
      <div class="center-core">
        <div class="core-pulse"></div>
        <div class="core-content">{{ payload.center }}</div>
      </div>
      
      <div class="modules-grid">
        <div v-for="(mod, idx) in payload.modules" :key="mod.title" class="module-card" :class="`theme-${idx % 4}`">
          <div class="module-header">
            <div class="module-icon"></div>
            <strong class="module-title">{{ mod.title }}</strong>
          </div>
          <ul class="module-items">
            <li v-for="item in mod.items" :key="item">{{ item }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { FrameworkPayload } from '@/features/chat/types/chat'

defineProps<{
  payload: FrameworkPayload
}>()
</script>

<style scoped>
.framework-diagram {
  display: flex;
  justify-content: center;
  padding: 24px 16px;
  background: var(--color-bg);
  border-radius: 16px;
}

.framework-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
  position: relative;
  width: 100%;
}

.connections-svg {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  pointer-events: none;
  z-index: 0;
}

.center-core {
  position: relative;
  z-index: 2;
}

.core-pulse {
  position: absolute;
  inset: -12px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.4) 0%, transparent 70%);
  border-radius: 50%;
  animation: pulse-ring 3s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(0.8); opacity: 0.5; }
  50% { transform: scale(1.2); opacity: 0.8; }
  100% { transform: scale(0.8); opacity: 0.5; }
}

.core-content {
  background: linear-gradient(135deg, var(--color-info), #1d4ed8);
  color: white;
  padding: 16px 32px;
  border-radius: 999px;
  font-size: 18px;
  font-weight: 800;
  box-shadow: 0 10px 20px -5px rgba(37, 99, 235, 0.4), inset 0 2px 4px rgba(255, 255, 255, 0.2);
  border: 2px solid #60a5fa;
  position: relative;
  letter-spacing: 0.05em;
  text-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  width: 100%;
  position: relative;
  z-index: 1;
}

.modules-grid::before {
  content: '';
  position: absolute;
  top: -32px;
  left: 10%;
  right: 10%;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--color-border-hover), transparent);
  z-index: -1;
}

.module-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  position: relative;
  display: flex;
  flex-direction: column;
}

.module-card::after {
  content: '';
  position: absolute;
  top: -32px;
  left: 50%;
  width: 2px;
  height: 32px;
  background: var(--color-border-hover);
  z-index: -1;
}

.module-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
}

.module-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-surface-hover);
}

.module-icon {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.theme-0 .module-icon { background: #3b82f6; box-shadow: 0 0 8px #3b82f6; }
.theme-1 .module-icon { background: var(--color-success); box-shadow: 0 0 8px var(--color-success); }
.theme-2 .module-icon { background: var(--color-warning); box-shadow: 0 0 8px var(--color-warning); }
.theme-3 .module-icon { background: #8b5cf6; box-shadow: 0 0 8px #8b5cf6; }

.module-title {
  font-size: 15px;
  font-weight: 800;
  color: var(--color-text-strong);
}

.module-items {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.module-items li {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.4;
  position: relative;
  padding-left: 14px;
}

.module-items li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 6px;
  width: 4px;
  height: 4px;
  background: var(--color-border-hover);
  border-radius: 50%;
}

.theme-0 .module-items li::before { background: #93c5fd; }
.theme-1 .module-items li::before { background: #6ee7b7; }
.theme-2 .module-items li::before { background: #fcd34d; }
.theme-3 .module-items li::before { background: #c4b5fd; }
</style>
