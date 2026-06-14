<template>
  <div class="mac-light-slide mac-light-theory">
    <div class="mac-window">
      <div class="mac-titlebar">
        <div class="mac-buttons">
          <span class="mac-btn close"></span>
          <span class="mac-btn minimize"></span>
          <span class="mac-btn maximize"></span>
        </div>
      </div>
      <div class="mac-content">
        <header class="slide-header">
          <h2 class="slide-title">{{ data.theorem_name }}</h2>
        </header>
        
        <div class="layout-body">
          <div class="left-col">
            <div class="math-card">
              <div class="card-label">FORMULA / 定理公式</div>
              <!-- 简单的模拟 LaTeX 渲染或直接展示 -->
              <div class="formula-box">
                <span class="latex-text">{{ data.formula_latex }}</span>
              </div>
            </div>
            
            <div class="constraints-card" v-if="data.constraints && data.constraints.length">
              <div class="card-label">CONSTRAINTS / 边界条件</div>
              <ul class="constraint-list">
                <li v-for="(item, idx) in data.constraints" :key="idx">
                  <span class="bullet-icon"></span>
                  {{ item }}
                </li>
              </ul>
            </div>
          </div>
          
          <div class="right-col">
            <div class="card-label">PROOF STEPS / 推演步骤</div>
            <div class="steps-container">
              <div 
                v-for="(step, index) in data.proof_steps" 
                :key="index"
                class="proof-step"
                :style="{ animationDelay: `${index * 0.2}s` }"
              >
                <div class="step-marker">{{ index + 1 }}</div>
                <div class="step-content">
                  <h4 class="step-title">{{ step.step_title }}</h4>
                  <p class="step-detail">{{ step.detail }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TheoryProofData } from '../../types/ppt';

defineProps<{
  data: TheoryProofData
}>();
</script>

<style scoped>
.mac-light-slide {
  width: 100%;
  height: 100%;
  background: #F9FAFB;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
  padding: 60px 80px;
  box-sizing: border-box;
}

.mac-window {
  width: 100%;
  height: 100%;
  background: #FFFFFF;
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.mac-titlebar {
  height: 38px;
  background: #F3F4F6;
  border-bottom: 1px solid #E5E7EB;
  display: flex;
  align-items: center;
  padding: 0 16px;
}

.mac-buttons { display: flex; gap: 8px; }
.mac-btn { width: 12px; height: 12px; border-radius: 50%; }
.mac-btn.close { background: #FF5F56; border: 1px solid #E0443E; }
.mac-btn.minimize { background: #FFBD2E; border: 1px solid #DEA123; }
.mac-btn.maximize { background: #27C93F; border: 1px solid #1AAB29; }

.mac-content {
  flex: 1;
  padding: 40px 60px;
  display: flex;
  flex-direction: column;
}

.slide-header {
  margin-bottom: 30px;
  border-bottom: 2px solid #F3F4F6;
  padding-bottom: 20px;
}

.slide-title {
  font-size: 36px;
  color: #111827;
  margin: 0;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.layout-body {
  flex: 1;
  display: flex;
  gap: 40px;
}

.left-col {
  flex: 5;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.right-col {
  flex: 7;
  display: flex;
  flex-direction: column;
}

.card-label {
  font-size: 13px;
  font-weight: 700;
  color: #6B7280;
  letter-spacing: 1px;
  margin-bottom: 16px;
}

.math-card {
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 24px;
}

.formula-box {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 30px 0;
}

.latex-text {
  font-family: 'Cambria Math', 'Times New Roman', serif;
  font-size: 32px;
  font-style: italic;
  color: #111827;
}

.constraints-card {
  background: #FFFBEB;
  border: 1px solid #FDE68A;
  border-radius: 12px;
  padding: 24px;
  flex: 1;
}

.constraint-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.constraint-list li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 16px;
  color: #92400E;
  line-height: 1.5;
}

.bullet-icon {
  width: 6px;
  height: 6px;
  background: #F59E0B;
  border-radius: 50%;
  margin-top: 8px;
  flex-shrink: 0;
}

.steps-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  padding-right: 10px;
}

.proof-step {
  display: flex;
  gap: 20px;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);
  opacity: 0;
  animation: slideLeft 0.5s ease-out forwards;
}

.step-marker {
  width: 40px;
  height: 40px;
  background: #EFF6FF;
  color: #2563EB;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 18px;
  flex-shrink: 0;
}

.step-content {
  flex: 1;
}

.step-title {
  font-size: 18px;
  color: #111827;
  margin: 0 0 8px 0;
  font-weight: 700;
}

.step-detail {
  font-size: 15px;
  color: #4B5563;
  margin: 0;
  line-height: 1.6;
}

@keyframes slideLeft {
  0% { opacity: 0; transform: translateX(20px); }
  100% { opacity: 1; transform: translateX(0); }
}
</style>
