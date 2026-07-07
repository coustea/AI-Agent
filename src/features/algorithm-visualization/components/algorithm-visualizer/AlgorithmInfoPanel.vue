<template>
  <section class="algorithm-info-panel">
    <div class="info-header">
      <h3>{{ algorithmName }}</h3>
      <span v-if="difficulty" :class="['difficulty-badge', difficulty]">{{ difficultyLabel }}</span>
    </div>

    <div v-if="currentEvent?.message" class="step-message">
      <span class="step-index">步骤 {{ currentStepIndex + 1 }}</span>
      <p>{{ currentEvent.message }}</p>
    </div>

    <div v-else class="step-message empty">
      <p>选择算法并运行以查看步骤说明</p>
    </div>

    <div v-if="runError" class="error-message">
      <p>{{ runError.message }}</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RunError, TraceEvent } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  algorithmName: string
  difficulty: 'easy' | 'medium' | 'hard' | ''
  currentEvent: TraceEvent | null
  currentStepIndex: number
  totalSteps: number
  runError: RunError | null
}>()

const difficultyLabel = computed(() => {
  const map = { easy: '简单', medium: '中等', hard: '困难' } as const
  return props.difficulty ? map[props.difficulty] : ''
})
</script>

<style scoped>
.algorithm-info-panel {
  padding: 12px;
  border-radius: 4px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  box-shadow: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f1f5f9;
}

.info-header h3 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.difficulty-badge {
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
}

.difficulty-badge.easy {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.difficulty-badge.medium {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fde68a;
}

.difficulty-badge.hard {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.step-message {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}

.step-index {
  font-size: 11px;
  font-weight: 600;
  color: #2563eb;
}

.step-message p {
  margin: 0;
  font-size: 12px;
  color: #334155;
  line-height: 1.4;
}

.step-message.empty p {
  color: #94a3b8;
}

.error-message p {
  margin: 0;
  font-size: 12px;
  color: #dc2626;
  font-weight: 500;
}
</style>
