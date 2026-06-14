<template>
  <div class="logic-blue-slide">
    <header class="slide-header">
      <div>
        <div class="eyebrow">SYSTEM MIXTURE</div>
        <h2 class="slide-title">{{ data.title }}</h2>
      </div>
    </header>

    <div class="layout-grid">
      <section class="left-panel">
        <div v-if="data.architecture_nodes?.length" class="architecture-board">
          <div v-for="node in data.architecture_nodes" :key="node.id" class="architecture-node">
            <div class="node-type">{{ node.type }}</div>
            <div class="node-label">{{ node.label }}</div>
          </div>
        </div>

        <div v-else-if="data.comparison_table" class="comparison-board">
          <div class="comparison-row header">
            <div class="comparison-cell">Dimension</div>
            <div class="comparison-cell">A</div>
            <div class="comparison-cell">B</div>
          </div>
          <div v-for="(dimension, index) in data.comparison_table.dimensions" :key="dimension" class="comparison-row">
            <div class="comparison-cell dimension">{{ dimension }}</div>
            <div class="comparison-cell">{{ data.comparison_table.left_features[index] }}</div>
            <div class="comparison-cell">{{ data.comparison_table.right_features[index] }}</div>
          </div>
        </div>
      </section>

      <section class="right-panel">
        <div class="deep-dive-card">
          <div class="card-label">Deep Dive</div>
          <p>{{ data.deep_dive_text }}</p>
        </div>
        <div class="code-card">
          <div class="card-label">Inline Code</div>
          <pre><code>{{ data.inline_code }}</code></pre>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { MixedTwoColumnData } from '../../types/ppt'

defineProps<{
  data: MixedTwoColumnData
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
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.left-panel,
.right-panel {
  min-width: 0;
}

.architecture-board,
.comparison-board,
.deep-dive-card,
.code-card {
  border-radius: 24px;
  box-shadow: 0 18px 34px rgba(2, 6, 23, 0.18);
}

.architecture-board,
.comparison-board {
  height: 100%;
  padding: 20px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(226, 232, 240, 0.92));
  color: #0f172a;
}

.architecture-board {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  align-content: start;
}

.architecture-node {
  min-height: 122px;
  border-radius: 20px;
  padding: 18px;
  background: #f8fbff;
  border: 1px solid #bfdbfe;
}

.node-type {
  color: #2563eb;
  font-size: 12px;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  font-weight: 800;
  margin-bottom: 10px;
}

.node-label {
  font-size: 22px;
  line-height: 1.35;
  font-weight: 800;
}

.comparison-row {
  display: grid;
  grid-template-columns: 0.86fr 1fr 1fr;
}

.comparison-row + .comparison-row {
  border-top: 1px solid #dbeafe;
}

.comparison-cell {
  padding: 14px 12px;
  font-size: 14px;
  line-height: 1.55;
}

.comparison-row.header .comparison-cell {
  color: #2563eb;
  font-size: 12px;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  font-weight: 800;
}

.comparison-cell.dimension {
  font-weight: 800;
  color: #0f172a;
}

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.deep-dive-card,
.code-card {
  padding: 22px;
  background: rgba(15, 23, 42, 0.42);
  border: 1px solid rgba(125, 211, 252, 0.12);
}

.deep-dive-card {
  flex: 1;
}

.code-card {
  min-height: 210px;
}

.card-label {
  margin-bottom: 12px;
  color: #7dd3fc;
  font-size: 12px;
  letter-spacing: 1.8px;
  text-transform: uppercase;
  font-weight: 800;
}

.deep-dive-card p {
  margin: 0;
  color: rgba(226, 232, 240, 0.92);
  font-size: 16px;
  line-height: 1.7;
}

.code-card pre {
  margin: 0;
  color: #e2e8f0;
  font-family: "JetBrains Mono", monospace;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}
</style>
