<template>
  <div class="block-flow-chart">
    <div class="flow-steps">
      <div
        v-for="(step, index) in block.steps"
        :key="step.step_id"
        class="flow-step-card"
        :class="{ active: index === activeStep }"
        @click="activeStep = index"
      >
        <div class="step-badge-wrap">
          <div class="step-index-badge">
            <span class="step-num-text">0{{ index + 1 }}</span>
          </div>
          <!-- 虚线连接器 (非最后一个元素) -->
          <div v-if="index < block.steps.length - 1" class="step-timeline-connector"></div>
        </div>
        
        <div class="step-body-card ppt-card">
          <div class="step-header">
            <div class="step-title">{{ step.title }}</div>
            <div v-if="step.state_before || step.state_after" class="step-state-badge">
              <span class="state-value before">{{ step.state_before || '无' }}</span>
              <span class="state-arrow">→</span>
              <span class="state-value after">{{ step.state_after || '无' }}</span>
            </div>
          </div>
          <div class="step-description">{{ step.description }}</div>
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
  gap: 16px;
}

.flow-step-card {
  display: flex;
  align-items: stretch;
  gap: 20px;
  cursor: pointer;
}

.step-badge-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  flex-shrink: 0;
}

.step-index-badge {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--ppt-bg-tertiary);
  border: 2px solid var(--ppt-border);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  transition: all 0.2s ease;
}

.step-num-text {
  font-family: var(--ppt-font-mono);
  font-weight: 800;
  font-size: 0.95rem;
  color: var(--ppt-text-secondary);
}

.step-timeline-connector {
  width: 2px;
  position: absolute;
  top: 40px;
  bottom: -16px;
  background-image: linear-gradient(to bottom, var(--ppt-border) 50%, transparent 50%);
  background-size: 2px 8px;
  background-repeat: repeat-y;
  z-index: 1;
}

.step-body-card {
  flex: 1;
  min-width: 0;
  padding: 18px 24px;
  background: var(--ppt-bg-secondary);
  border: 1px solid var(--ppt-border);
  border-radius: var(--ppt-radius-md);
  box-shadow: var(--ppt-shadow-card);
  transition: all 0.2s ease;
}

/* 激活状态 */
.flow-step-card.active .step-index-badge {
  background: var(--ppt-accent-gradient);
  border-color: transparent;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.2);
}

.flow-step-card.active .step-num-text {
  color: #FFFFFF;
}

.flow-step-card.active .step-body-card {
  border-color: var(--ppt-accent);
  box-shadow: var(--ppt-shadow-glow), var(--ppt-shadow-card);
  transform: translateX(4px);
}

.step-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 8px;
}

.step-title {
  font-weight: 800;
  font-size: 1.08rem;
  color: var(--ppt-text-primary);
}

.step-description {
  font-size: 0.95rem;
  color: var(--ppt-text-secondary);
  line-height: 1.5;
}

.step-state-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--ppt-bg-tertiary);
  border: 1px solid var(--ppt-border);
  font-size: 0.78rem;
  font-family: var(--ppt-font-mono);
}

.state-value.before {
  color: var(--ppt-text-secondary);
}

.state-arrow {
  color: var(--ppt-accent);
  font-weight: 800;
}

.state-value.after {
  color: #059669;
  font-weight: 700;
}
</style>
