<template>
  <div v-if="evaluation && evaluation.needs_optimization && evaluation.optimization_tips.length > 0" class="evaluation-banner">
    <div class="banner-icon">
      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
      </svg>
    </div>
    <div class="banner-content">
      <strong>当前学习建议：</strong>
      <span>{{ evaluation.optimization_tips[0] }}</span>
      <span v-if="evaluation.optimization_tips.length > 1" class="more-tips">
        (共 {{ evaluation.optimization_tips.length }} 条建议)
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type { PathLearningEvaluationResponse } from '@/features/learning/model/path'

defineProps({
  evaluation: {
    type: Object as PropType<PathLearningEvaluationResponse | null>,
    default: null,
  },
})
</script>

<style scoped>
.evaluation-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--color-primary-soft);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  margin-bottom: 20px;
  animation: pulse-border 2s infinite alternate;
}

@keyframes pulse-border {
  0% {
    border-color: rgba(37, 99, 235, 0.3);
    box-shadow: 0 0 0 0 rgba(37, 99, 235, 0);
  }
  100% {
    border-color: rgba(37, 99, 235, 0.8);
    box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);
  }
}

.banner-icon {
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: spin-slow 10s linear infinite;
}

@keyframes spin-slow {
  100% { transform: rotate(360deg); }
}

.banner-content {
  font-size: 0.95rem;
  color: var(--color-text);
  line-height: 1.5;
}

.banner-content strong {
  color: var(--color-primary);
  font-weight: 700;
  margin-right: 4px;
}

.more-tips {
  margin-left: 8px;
  font-size: 0.85rem;
  color: var(--color-text-muted);
}
</style>
