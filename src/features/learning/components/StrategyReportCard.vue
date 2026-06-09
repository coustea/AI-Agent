<template>
  <BaseCard class="strategy-report-card">
    <div class="strategy-header">
      <div class="strategy-title">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="ai-icon">
          <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
        </svg>
        <h3>AI 诊断与个性化报告</h3>
      </div>
      <div class="confidence-badge">
        <span class="confidence-value">{{ path.confidence }}%</span>
        <span class="confidence-label">规划置信度</span>
      </div>
    </div>

    <div class="strategy-content">
      <div v-if="path.strategy_report" class="strategy-report">
        <h4>诊断结论</h4>
        <p>{{ path.strategy_report }}</p>
      </div>

      <div v-if="path.adjustment_rationale && path.adjustment_rationale.length > 0" class="adjustment-rationale">
        <h4>路径裁剪策略</h4>
        <ul>
          <li v-for="(rationale, index) in path.adjustment_rationale" :key="index">
            {{ rationale }}
          </li>
        </ul>
      </div>
    </div>
  </BaseCard>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import BaseCard from '@/shared/ui/BaseCard.vue'
import type { LearningPathOverview } from '@/features/learning/model/path'

defineProps({
  path: {
    type: Object as PropType<LearningPathOverview>,
    required: true,
  },
})
</script>

<style scoped>
.strategy-report-card {
  background: linear-gradient(145deg, var(--color-surface), rgba(255, 255, 255, 0.6));
  border: 1px solid var(--color-border);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.02);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.strategy-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 16px;
}

.strategy-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-primary);
}

.ai-icon {
  color: var(--color-primary);
  opacity: 0.8;
}

.strategy-title h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.01em;
}

.confidence-badge {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.confidence-value {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-primary);
  line-height: 1.1;
}

.confidence-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}

.strategy-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.strategy-content h4 {
  margin: 0 0 8px;
  font-size: 0.9rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
}

.strategy-report p {
  margin: 0;
  font-size: 0.95rem;
  color: var(--color-text);
  line-height: 1.6;
}

.adjustment-rationale ul {
  margin: 0;
  padding-left: 20px;
  color: var(--color-text);
}

.adjustment-rationale li {
  margin-bottom: 6px;
  font-size: 0.95rem;
  line-height: 1.5;
}

.adjustment-rationale li:last-child {
  margin-bottom: 0;
}
</style>
