<template>
  <div v-if="evaluation" class="cockpit-card">
    <div class="cockpit-header">
      <div class="header-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
        </svg>
      </div>
      <h3>AI 导师学习诊断</h3>
    </div>

    <!-- Metrics Grid -->
    <div class="metrics-grid">
      <div class="metric-item card-hover">
        <div class="metric-icon clock">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
          </svg>
        </div>
        <div class="metric-info">
          <label>学习时长</label>
          <strong>{{ evaluation.signal_snapshot.active_minutes }} <small>分钟</small></strong>
        </div>
      </div>

      <div class="metric-item card-hover">
        <div class="metric-icon score">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5"/>
          </svg>
        </div>
        <div class="metric-info">
          <label>测验均分</label>
          <strong :class="{ 'good': averageScore >= 80, 'warning': averageScore > 0 && averageScore < 80 }">
            {{ averageScore > 0 ? `${averageScore} 分` : '暂无' }}
          </strong>
        </div>
      </div>
    </div>

    <!-- Weak Topics -->
    <div class="diagnostic-section">
      <h4 class="section-title">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        薄弱知识点
      </h4>
      <div v-if="evaluation.signal_snapshot.weak_topics.length > 0" class="weak-tags">
        <span v-for="topic in evaluation.signal_snapshot.weak_topics" :key="topic" class="weak-tag">
          {{ topic }}
        </span>
      </div>
      <div v-else class="empty-weak">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        无明显薄弱知识点，继续保持！
      </div>
    </div>

    <!-- Tips Section -->
    <div v-if="evaluation.optimization_tips.length > 0" class="diagnostic-section advice-section">
      <h4 class="section-title">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>
        </svg>
        优化处方与建议
      </h4>
      <ul class="advice-list">
        <li v-for="(tip, idx) in evaluation.optimization_tips" :key="idx" class="advice-item">
          <span class="bullet">{{ idx + 1 }}</span>
          <p>{{ tip }}</p>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PropType } from 'vue'
import type { PathLearningEvaluationResponse } from '@/features/learning/model/path'

const props = defineProps({
  evaluation: {
    type: Object as PropType<PathLearningEvaluationResponse | null>,
    default: null,
  },
})

const averageScore = computed(() => {
  if (!props.evaluation || props.evaluation.signal_snapshot.average_score === null) return 0
  return Math.round(props.evaluation.signal_snapshot.average_score)
})
</script>

<style scoped>
.cockpit-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-shadow: var(--shadow-sm);
  border-top: 3px solid var(--color-primary);
  transition: all 0.3s ease;
}

.cockpit-card:hover {
  box-shadow: var(--shadow-md);
}

.cockpit-header {
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid var(--color-border-light);
  padding-bottom: 14px;
}

.header-icon {
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: pulse-glow 2s infinite alternate;
}

@keyframes pulse-glow {
  0% { transform: scale(0.95); opacity: 0.8; }
  100% { transform: scale(1.05); opacity: 1; }
}

.cockpit-header h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--color-text-strong);
}

/* Metrics styles */
.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.metric-item {
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s ease;
}

.metric-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.metric-icon.clock {
  background: rgba(79, 70, 229, 0.08);
  color: var(--color-primary);
}

.metric-icon.score {
  background: rgba(16, 185, 129, 0.08);
  color: var(--color-success);
}

.metric-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-info label {
  font-size: 0.6875rem;
  color: var(--color-text-muted);
  font-weight: 600;
  text-transform: uppercase;
}

.metric-info strong {
  font-size: 0.95rem;
  font-weight: 800;
  color: var(--color-text);
}

.metric-info strong.good {
  color: var(--color-success);
}

.metric-info strong.warning {
  color: var(--color-warning);
}

.metric-info strong small {
  font-size: 0.75rem;
  font-weight: var(--weight-medium);
  color: var(--color-text-muted);
}

/* Sections */
.diagnostic-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title {
  margin: 0;
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--color-text-muted);
  display: flex;
  align-items: center;
  gap: 6px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.section-title svg {
  color: var(--color-text-muted);
}

.weak-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.weak-tag {
  font-size: 0.75rem;
  background: var(--color-danger-soft);
  color: var(--color-danger);
  border: 1px solid rgba(239, 68, 68, 0.15);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-weight: 600;
}

.empty-weak {
  font-size: 0.75rem;
  background: var(--color-success-soft);
  color: var(--color-success);
  border: 1px solid rgba(16, 185, 129, 0.15);
  padding: 8px 12px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

/* Advice checklist */
.advice-section {
  border-top: 1px dashed var(--color-border);
  padding-top: 16px;
}

.advice-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.advice-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.bullet {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 0.6875rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.advice-item p {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.5;
  color: var(--color-text-secondary);
}
</style>
