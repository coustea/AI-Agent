<template>
  <div class="logic-blue-slide">
    <header class="slide-header">
      <div>
        <div class="eyebrow">SEQUENCE TRACE</div>
        <h2 class="slide-title">{{ data.flow_title }}</h2>
      </div>
      <div class="header-chip">{{ data.swimlanes.join(' / ') }}</div>
    </header>

    <section class="flow-board">
      <div class="lane-row lane-header">
        <div class="lane-time">SEQ</div>
        <div v-for="lane in data.swimlanes" :key="lane" class="lane-name">{{ lane }}</div>
        <div class="lane-state">STATE</div>
      </div>

      <div v-for="step in data.timeline_steps" :key="step.time_seq" class="lane-row">
        <div class="lane-time">
          <span class="time-pill">{{ step.time_seq }}</span>
        </div>
        <div class="lane-action" :style="{ gridColumn: `${laneIndex(step.from) + 1} / span ${spanWidth(step.from, step.to)}` }">
          <span class="from-to">{{ step.from }} → {{ step.to }}</span>
          <strong>{{ step.action }}</strong>
        </div>
        <div class="lane-state-card">{{ step.internal_state }}</div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { ProcessFlowData } from '../../types/ppt'

const props = defineProps<{
  data: ProcessFlowData
}>()

const laneIndex = (name: string) => Math.max(props.data.swimlanes.indexOf(name), 0)

const spanWidth = (from: string, to: string) => {
  const start = laneIndex(from)
  const end = laneIndex(to)
  return Math.max(Math.abs(end - start) + 1, 1)
}
</script>

<style scoped>
.logic-blue-slide {
  width: 100%;
  height: 100%;
  padding: 56px 62px;
  box-sizing: border-box;
  color: #eff6ff;
  background:
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.14), transparent 28%),
    linear-gradient(180deg, #091527 0%, #0f1d35 100%);
  font-family: "Avenir Next", "Segoe UI", sans-serif;
}

.slide-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 24px;
}

.eyebrow {
  color: #7dd3fc;
  font-size: 12px;
  letter-spacing: 2px;
  font-weight: 800;
  margin-bottom: 10px;
}

.slide-title {
  margin: 0;
  font-size: 38px;
  line-height: 1.08;
  font-weight: 800;
}

.header-chip {
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(125, 211, 252, 0.12);
  color: #bae6fd;
  font-size: 13px;
  font-weight: 700;
}

.flow-board {
  height: calc(100% - 98px);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.lane-row {
  display: grid;
  grid-template-columns: 88px repeat(3, 1fr) 320px;
  gap: 12px;
  align-items: stretch;
}

.lane-header {
  align-items: center;
  color: #7dd3fc;
  font-size: 12px;
  letter-spacing: 1.8px;
  font-weight: 800;
  text-transform: uppercase;
}

.lane-time,
.lane-name,
.lane-state {
  padding: 0 8px;
}

.time-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 64px;
  padding: 10px 12px;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.18);
  color: #bae6fd;
  font-size: 14px;
  font-weight: 800;
  font-family: "JetBrains Mono", monospace;
}

.lane-action {
  min-height: 92px;
  padding: 18px 20px;
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.24), rgba(14, 165, 233, 0.14));
  border: 1px solid rgba(125, 211, 252, 0.14);
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  box-shadow: 0 18px 34px rgba(2, 6, 23, 0.2);
}

.from-to {
  color: #7dd3fc;
  font-size: 12px;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  font-weight: 800;
}

.lane-action strong {
  font-size: 18px;
  line-height: 1.4;
}

.lane-state-card {
  min-height: 92px;
  padding: 18px 18px;
  border-radius: 22px;
  background: rgba(15, 23, 42, 0.42);
  border: 1px solid rgba(125, 211, 252, 0.12);
  color: rgba(226, 232, 240, 0.88);
  font-size: 15px;
  line-height: 1.62;
}
</style>
