<template>
  <div class="logic-blue-slide">
    <header class="slide-header">
      <div>
        <div class="eyebrow">ENGINEERING DASHBOARD</div>
        <h2 class="slide-title">{{ data.title }}</h2>
      </div>
    </header>

    <div class="layout-grid">
      <section class="code-zone">
        <div class="code-card">
          <div class="window-bar">
            <span></span><span></span><span></span>
            <div class="window-label">{{ data.code_snippet.language }}</div>
          </div>
          <pre class="code-block"><code>{{ data.code_snippet.code }}</code></pre>
        </div>
        <div class="terminal-card" v-if="data.terminal_output">
          <div class="terminal-label">Terminal Output</div>
          <pre>{{ data.terminal_output }}</pre>
        </div>
      </section>

      <section class="insight-zone">
        <div class="metrics-grid">
          <div v-for="metric in data.stat_metrics" :key="metric.label" class="metric-card">
            <div class="metric-value">{{ metric.value }}<span v-if="metric.unit">{{ metric.unit }}</span></div>
            <div class="metric-label">{{ metric.label }}</div>
          </div>
        </div>

        <div class="summary-card">
          <div class="summary-label">Key Takeaways</div>
          <div v-for="point in data.summary_points" :key="point" class="summary-item">{{ point }}</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TechDashboardData } from '../../types/ppt'

defineProps<{
  data: TechDashboardData
}>()
</script>

<style scoped>
.logic-blue-slide {
  width: 100%;
  height: 100%;
  padding: 54px 60px;
  box-sizing: border-box;
  color: #eff6ff;
  background:
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.14), transparent 28%),
    linear-gradient(180deg, #091527 0%, #0f1d35 100%);
  font-family: "Avenir Next", "Segoe UI", sans-serif;
}

.slide-header {
  margin-bottom: 22px;
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

.layout-grid {
  height: calc(100% - 92px);
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 24px;
}

.code-zone {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.code-card,
.terminal-card {
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 24px 42px rgba(2, 6, 23, 0.22);
}

.code-card {
  flex: 1;
  background: #061120;
}

.window-bar {
  height: 46px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 18px;
  background: #0b1729;
}

.window-bar span {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: rgba(148, 163, 184, 0.5);
}

.window-label {
  margin-left: 10px;
  color: #94a3b8;
  font-size: 12px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  font-weight: 700;
}

.code-block {
  margin: 0;
  padding: 20px 22px;
  color: #e2e8f0;
  font-family: "JetBrains Mono", monospace;
  font-size: 14px;
  line-height: 1.65;
  white-space: pre-wrap;
}

.terminal-card {
  min-height: 148px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.86), rgba(15, 23, 42, 0.7));
  border: 1px solid rgba(125, 211, 252, 0.12);
  padding: 18px 20px;
}

.terminal-label {
  margin-bottom: 10px;
  color: #7dd3fc;
  font-size: 12px;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  font-weight: 800;
}

.terminal-card pre {
  margin: 0;
  color: rgba(226, 232, 240, 0.9);
  font-family: "JetBrains Mono", monospace;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}

.insight-zone {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.metric-card {
  min-height: 132px;
  padding: 20px 20px;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(226, 232, 240, 0.92));
  color: #0f172a;
  box-shadow: 0 18px 34px rgba(2, 6, 23, 0.18);
}

.metric-value {
  font-size: 46px;
  line-height: 1;
  font-weight: 800;
  color: #2563eb;
}

.metric-value span {
  margin-left: 4px;
  font-size: 18px;
  color: #64748b;
}

.metric-label {
  margin-top: 10px;
  font-size: 14px;
  font-weight: 700;
  color: #334155;
}

.summary-card {
  flex: 1;
  border-radius: 24px;
  padding: 22px 22px;
  background: rgba(15, 23, 42, 0.42);
  border: 1px solid rgba(125, 211, 252, 0.12);
  box-shadow: 0 18px 34px rgba(2, 6, 23, 0.18);
}

.summary-label {
  margin-bottom: 14px;
  color: #7dd3fc;
  font-size: 12px;
  letter-spacing: 1.8px;
  text-transform: uppercase;
  font-weight: 800;
}

.summary-item {
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(59, 130, 246, 0.12);
  color: rgba(226, 232, 240, 0.92);
  font-size: 15px;
  line-height: 1.55;
}

.summary-item + .summary-item {
  margin-top: 10px;
}
</style>
