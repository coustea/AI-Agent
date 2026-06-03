<template>
  <div class="framework-diagram">
    <div class="center-node">{{ payload.center }}</div>
    <div class="modules-grid">
      <div v-for="mod in payload.modules" :key="mod.title" class="module-card">
        <strong class="module-title">{{ mod.title }}</strong>
        <ul class="module-items">
          <li v-for="item in mod.items" :key="item">{{ item }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { FrameworkPayload } from '@/chat/types/chat'

defineProps<{
  payload: FrameworkPayload
}>()
</script>

<style scoped>
.framework-diagram {
  display: grid;
  gap: 16px;
}

.center-node {
  justify-self: center;
  padding: 14px 28px;
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.95) 0%, rgba(219, 234, 254, 0.8) 100%);
  border: 2px solid rgba(59, 130, 246, 0.5);
  border-radius: 999px;
  font-size: 18px;
  font-weight: 800;
  color: #1d4ed8;
  box-shadow: 0 0 20px rgba(59, 130, 246, 0.2);
  position: relative;
  z-index: 2;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.module-card {
  padding: 16px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  position: relative;
  overflow: hidden;
}

.module-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
}

.module-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, #3b82f6, #06b6d4);
  opacity: 0.8;
}

.module-title {
  display: block;
  margin-bottom: 12px;
  font-size: 15px;
  font-weight: 800;
  color: var(--c-ink, #0f172a);
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
  overflow-wrap: break-words;
  word-break: break-all;
}

.module-items {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 4px;
}

.module-items li {
  padding: 4px 0;
  font-size: 13px;
  color: var(--c-muted, #64748b);
  line-height: 1.5;
  overflow-wrap: break-words;
  word-break: break-all;
}

.module-items li::before {
  content: '';
  display: inline-block;
  width: 6px;
  height: 6px;
  background: #94a3b8;
  border-radius: 50%;
  margin-right: 8px;
  transform: translateY(-1px);
}
</style>
