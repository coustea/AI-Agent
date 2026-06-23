<template>
  <div class="slide-shell summary-master ppt-grid-bg">
    <div class="slide-header">
      <div>
        <div class="slide-title summary-title-accent">{{ slide.title }}</div>
      </div>
      <div class="slide-role-badge summary-badge">
        <span class="role-icon">⚡</span>
        <span class="role-text">SUMMARY & TAKEAWAY</span>
      </div>
    </div>

    <div class="slide-content-wrapper">
      <component :is="resolveComposition(slide.composition_id)" :slide="slide" />
    </div>

    <div class="slide-footer">
      <div class="slide-takeaway-container">
        <span class="takeaway-tag summary-tag">核心总结</span>
        <div class="slide-takeaway">{{ slide.key_message }}</div>
      </div>
      <div class="slide-index">{{ index + 1 }} / {{ total }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ResolvedSlide } from '../model/resolvedSlide'
import { resolveComposition } from '../compositions'

defineProps<{
  slide: ResolvedSlide
  index: number
  total: number
}>()
</script>

<style scoped>
.summary-master {
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: var(--ppt-radius-lg);
  background: var(--ppt-bg-primary);
  display: grid;
  grid-template-rows: auto 1fr auto;
  position: relative;
  border: 2px solid var(--ppt-accent);
  box-sizing: border-box;
}

.slide-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 36px 8px;
  border-bottom: 1px dashed var(--ppt-border);
  z-index: 5;
  box-sizing: border-box;
}

.slide-title {
  font-size: 2.1rem;
  font-weight: 800;
  line-height: 1.2;
  color: var(--ppt-text-primary);
  letter-spacing: -0.02em;
}

.summary-title-accent {
  background: linear-gradient(135deg, var(--ppt-text-primary) 0%, var(--ppt-accent) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.slide-role-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  background: var(--ppt-badge-bg);
  border: 1px solid var(--ppt-border);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02);
}

.summary-badge {
  background: rgba(37, 99, 235, 0.08) !important;
  border-color: var(--ppt-accent) !important;
}

.role-icon {
  color: var(--ppt-accent);
  font-size: 0.9rem;
}

.role-text {
  font-size: 0.75rem;
  font-weight: 800;
  color: var(--ppt-badge-text);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.slide-content-wrapper {
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.slide-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 8px 36px 20px;
  border-top: 1px dashed var(--ppt-border);
  z-index: 5;
  box-sizing: border-box;
}

.slide-takeaway-container {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.takeaway-tag {
  font-size: 0.7rem;
  font-weight: 800;
  color: #ffffff;
  background: var(--ppt-accent-gradient);
  padding: 3px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.summary-tag {
  background: var(--ppt-accent-gradient) !important;
}

.slide-takeaway {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--ppt-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.slide-index {
  flex-shrink: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--ppt-text-secondary);
}

.ppt-grid-bg {
  background-image: radial-gradient(rgba(148, 163, 184, 0.12) 1px, transparent 1px);
  background-size: 20px 20px;
}
</style>
