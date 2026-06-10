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
  margin: 0 0 6px;
  font-size: 0.8rem;
  text-transform: uppercase;
  color: var(--color-text-muted);
  letter-spacing: 0.05em;
}

.section p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--color-text);
  line-height: 1.5;
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
