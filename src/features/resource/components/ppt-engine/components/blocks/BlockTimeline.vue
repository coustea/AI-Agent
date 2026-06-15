<template>
  <div class="block-timeline">
    <div class="timeline-step" v-for="(step, index) in block.steps" :key="index">
      <div class="step-marker">
        <div class="dot"></div>
        <div class="line" v-if="index < block.steps.length - 1"></div>
      </div>
      <div class="step-content">
        <div class="time">{{ step.time }}</div>
        <div class="title">{{ step.title }}</div>
        <div class="desc" v-if="step.description">{{ step.description }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { BlockTimeline } from '../../types/ppt'

defineProps<{
  block: BlockTimeline
}>()
</script>

<style scoped>
.block-timeline {
  display: flex;
  flex-direction: column;
  margin-bottom: 1em;
}

.timeline-step {
  display: flex;
  gap: 16px;
}

.step-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 20px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: var(--ppt-accent);
  flex-shrink: 0;
  margin-top: 6px;
  box-shadow: 0 0 0 4px var(--ppt-bg-secondary);
}

.line {
  width: 2px;
  flex-grow: 1;
  background-color: var(--ppt-border);
  margin-top: 4px;
  margin-bottom: 4px;
  min-height: 40px;
}

.step-content {
  padding-bottom: 24px;
  flex-grow: 1;
}

.time {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--ppt-accent);
  margin-bottom: 4px;
}

.title {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--ppt-text-primary);
  margin-bottom: 4px;
}

.desc {
  font-size: 1rem;
  color: var(--ppt-text-secondary);
  line-height: 1.5;
}
</style>
