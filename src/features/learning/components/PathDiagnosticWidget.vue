<template>
  <div class="diagnostic-widget">
    <div class="widget-header">
      <h4><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg> 路径说明</h4>
      <span class="confidence-badge">{{ path.confidence }}% 置信</span>
    </div>

    <div class="widget-body scroll-y">
      <div v-if="path.strategy_report" class="section">
        <h5>规划摘要</h5>
        <p>{{ path.strategy_report }}</p>
      </div>

      <div v-if="path.capstone_project" class="section">
        <h5><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="section-icon"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg> 终极实战项目</h5>
        <div class="project-box">
          <h6>{{ path.capstone_project.title }}</h6>
          <p>{{ path.capstone_project.description }}</p>
        </div>
      </div>

      <div v-if="path.pre_check_knowledge && path.pre_check_knowledge.length > 0" class="section">
        <h5><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="section-icon"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/><path d="m9 16 2 2 4-4"/></svg> 开课自检清单</h5>
        <div class="checklist">
          <label v-for="(item, index) in path.pre_check_knowledge" :key="index" class="check-item">
            <div class="custom-checkbox">
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </div>
            <span>{{ item }}</span>
          </label>
        </div>
      </div>

      <div v-if="path.adjustment_rationale && path.adjustment_rationale.length > 0" class="section">
        <h5>生成依据</h5>
        <ul class="dense-list">
          <li v-for="(rationale, index) in path.adjustment_rationale" :key="index">
            {{ rationale }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type { LearningPathOverview } from '@/features/learning/model/path'

defineProps({
  path: {
    type: Object as PropType<LearningPathOverview>,
    required: true,
  },
})
</script>

<style scoped>
.diagnostic-widget {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
}

.widget-header h4 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.95rem;
  color: var(--color-primary);
  font-weight: 700;
}

.confidence-badge {
  font-size: 0.75rem;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.widget-body {
  padding: 16px;
  flex: 1;
  overflow-y: auto;
}

.scroll-y {
  scrollbar-width: thin;
}

.scroll-y::-webkit-scrollbar {
  width: 4px;
}
.scroll-y::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 4px;
}

.section {
  margin-bottom: 16px;
}

.section:last-child {
  margin-bottom: 0;
}

.section h5 {
  margin: 0 0 8px;
  font-size: 0.8rem;
  text-transform: uppercase;
  color: var(--color-text-muted);
  letter-spacing: 0.05em;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
}

.section-icon {
  color: var(--color-primary);
  opacity: 0.8;
}

.section p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--color-text);
  line-height: 1.5;
}

.project-box {
  background: var(--color-primary-soft);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  margin-top: 8px;
  transition: all 0.3s ease;
}
.project-box:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}
.project-box h6 {
  margin: 0 0 4px;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-primary);
}
.project-box p {
  font-size: 0.8rem !important;
  color: var(--color-text-muted) !important;
  line-height: 1.4 !important;
}

.checklist {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}
.check-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 0.85rem;
  color: var(--color-text);
  cursor: default;
}
.custom-checkbox {
  flex-shrink: 0;
  margin-top: 2px;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  background: var(--color-primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dense-list {
  margin: 0;
  padding-left: 16px;
  color: var(--color-text);
  font-size: 0.9rem;
}

.dense-list li {
  margin-bottom: 4px;
  line-height: 1.4;
}
</style>
