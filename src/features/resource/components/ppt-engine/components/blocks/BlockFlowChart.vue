<template>
  <div class="block-flow-chart">
    <div class="flow-steps">
      <div
        v-for="(step, index) in block.steps"
        :key="step.step_id"
        class="flow-step"
        :class="{ active: index === activeStep }"
        @click="activeStep = index"
      >
        <div class="step-number">{{ index + 1 }}</div>
        <div class="step-content">
          <div class="step-title">{{ step.title }}</div>
          <div class="step-description">{{ step.description }}</div>
        </div>
        <div v-if="step.state_before && step.state_after" class="step-state">
          <span class="state-before">{{ step.state_before }}</span>
          <span class="state-arrow">→</span>
          <span class="state-after">{{ step.state_after }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { FlowChartBlock } from '../../types/ppt'

defineProps<{
  block: FlowChartBlock
}>()

const activeStep = ref(0)
</script>

<style scoped>
.block-flow-chart {
  width: 100%;
}

.flow-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.flow-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  background: var(--ppt-bg-secondary, #f8fafc);
  border: 1px solid var(--ppt-border, #e2e8f0);
  cursor: pointer;
  transition: all 0.2s ease;
}

.flow-step:hover {
  background: var(--ppt-bg-hover, #f1f5f9);
}

.flow-step.active {
  border-color: var(--ppt-primary, #2563eb);
  background: var(--ppt-bg-active, #eff6ff);
}

.step-number {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--ppt-primary, #2563eb);
  color: white;
  font-weight: 700;
  font-size: 14px;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-weight: 600;
  font-size: 15px;
  color: var(--ppt-text-primary, #0f172a);
  margin-bottom: 4px;
}

.step-description {
  font-size: 13px;
  color: var(--ppt-text-secondary, #64748b);
  line-height: 1.4;
}

.step-state {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 4px;
  background: var(--ppt-bg-tertiary, #f1f5f9);
  font-size: 12px;
  font-family: monospace;
}

.state-before {
  color: var(--ppt-text-muted, #94a3b8);
}

.state-arrow {
  color: var(--ppt-primary, #2563eb);
}

.state-after {
  color: var(--ppt-success, #16a34a);
  font-weight: 600;
}
</style>
