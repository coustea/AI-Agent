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
  padding: 16px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.info-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 720;
  color: #0f172a;
}

.difficulty-badge {
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}

.difficulty-badge.easy {
  background: rgba(220, 252, 231, 0.92);
  color: #059669;
}

.difficulty-badge.medium {
  background: rgba(254, 243, 199, 0.92);
  color: #d97706;
}

.difficulty-badge.hard {
  background: rgba(254, 226, 226, 0.92);
  color: #dc2626;
}

.step-message {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.step-index {
  font-size: 11px;
  font-weight: 700;
  color: #2563eb;
}

.step-message p {
  margin: 0;
  font-size: 13px;
  color: #334155;
  line-height: 1.5;
}

.step-message.empty p {
  color: #94a3b8;
}

.error-message p {
  margin: 0;
  font-size: 13px;
  color: #dc2626;
  font-weight: 600;
}
</style>
