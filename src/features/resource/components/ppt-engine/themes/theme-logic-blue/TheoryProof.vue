<template>
  <div class="logic-blue-slide">
    <header class="slide-header">
      <div>
        <div class="eyebrow">THEORY FRAME</div>
        <h2 class="slide-title">{{ data.theorem_name }}</h2>
      </div>
    </header>

    <div class="layout-grid">
      <section class="formula-card">
        <div class="card-label">Formula</div>
        <div class="formula-box">{{ data.formula_latex }}</div>
        <div v-if="data.constraints.length" class="constraints">
          <div class="card-label">Constraints</div>
          <div class="constraint-list">
            <div v-for="constraint in data.constraints" :key="constraint" class="constraint-item">{{ constraint }}</div>
          </div>
        </div>
      </section>

      <section class="steps-panel">
        <article v-for="(step, index) in data.proof_steps" :key="step.step_title" class="step-card">
          <div class="step-index">{{ index + 1 }}</div>
          <div class="step-body">
            <h3 class="step-title">{{ step.step_title }}</h3>
            <p class="step-detail">{{ step.detail }}</p>
          </div>
        </article>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TheoryProofData } from '../../types/ppt'

defineProps<{
  data: TheoryProofData
}>()
</script>

<style scoped>
.logic-blue-slide {
  width: 100%;
  height: 100%;
  padding: 56px 64px;
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
  font-size: 40px;
  line-height: 1.08;
  font-weight: 800;
}

.layout-grid {
  height: calc(100% - 92px);
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: 26px;
}

.formula-card {
  border-radius: 28px;
  padding: 28px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.97), rgba(226, 232, 240, 0.92));
  color: #0f172a;
  box-shadow: 0 24px 44px rgba(2, 6, 23, 0.2);
}

.card-label {
  margin-bottom: 12px;
  color: #2563eb;
  font-size: 13px;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  font-weight: 800;
}

.formula-box {
  padding: 28px 24px;
  border-radius: 20px;
  background: #f8fbff;
  font-family: "Cambria Math", "Times New Roman", serif;
  font-size: 28px;
  line-height: 1.55;
  color: #0f172a;
}

.constraints {
  margin-top: 24px;
}

.constraint-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.constraint-item {
  padding: 12px 14px;
  border-radius: 16px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 15px;
  font-weight: 700;
}

.steps-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.step-card {
  flex: 1;
  display: flex;
  gap: 16px;
  border-radius: 24px;
  padding: 20px 22px;
  background: rgba(15, 23, 42, 0.44);
  border: 1px solid rgba(125, 211, 252, 0.12);
  box-shadow: 0 18px 34px rgba(2, 6, 23, 0.18);
}

.step-index {
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border-radius: 14px;
  background: linear-gradient(180deg, #38bdf8, #2563eb);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #eff6ff;
  font-weight: 800;
  font-family: "JetBrains Mono", monospace;
}

.step-body {
  min-width: 0;
}

.step-title {
  margin: 0 0 10px;
  font-size: 22px;
  font-weight: 800;
}

.step-detail {
  margin: 0;
  color: rgba(226, 232, 240, 0.88);
  font-size: 16px;
  line-height: 1.65;
}
</style>
