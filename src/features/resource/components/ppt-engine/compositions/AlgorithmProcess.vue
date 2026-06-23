<template>
  <div class="composition algorithm-process">
    <div class="subtitle">{{ slide.key_message }}</div>
    <div class="process-flow">
      <div v-for="(el, idx) in slide.elements" :key="el.content || ''" class="process-node-wrapper">
        <div class="process-card ppt-card">
          <div class="step-badge">STEP {{ idx + 1 }}</div>
          <div class="step-title">{{ el.content }}</div>
          <div class="step-desc" v-if="el.properties && !Array.isArray(el.properties)">
            {{ el.properties.description || '' }}
          </div>
        </div>
        <div v-if="idx < slide.elements.length - 1" class="flow-arrow">
          <svg viewBox="0 0 24 24" width="24" height="24">
            <path d="M5 12h14M12 5l7 7-7 7" stroke="var(--ppt-accent)" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ResolvedSlide } from '../model/resolvedSlide'
defineProps<{ slide: ResolvedSlide }>()
</script>

<style scoped>
.algorithm-process {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 40px 60px;
  box-sizing: border-box;
}
.subtitle {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--ppt-text-secondary);
  margin-bottom: 30px;
  border-left: 3px solid var(--ppt-accent);
  padding-left: 12px;
}
.process-flow {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  overflow-x: auto;
  padding-bottom: 20px;
}
.process-node-wrapper {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  min-width: 200px;
}
.process-card {
  flex: 1;
  padding: 20px;
  border-top: 4px solid var(--ppt-accent);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.step-badge {
  font-size: 0.75rem;
  font-weight: 800;
  color: var(--ppt-accent);
}
.step-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--ppt-text-primary);
}
.step-desc {
  font-size: 0.85rem;
  color: var(--ppt-text-secondary);
  line-height: 1.4;
}
.flow-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
