<template>
  <div class="notion-light-slide notion-theory">
    <div class="notion-page">
      <h2 class="slide-title">{{ data.theorem_name }}</h2>
      
      <div class="content-body">
        
        <!-- Formula Callout -->
        <div class="notion-callout">
          <div class="callout-icon">∑</div>
          <div class="callout-text">
            <div class="latex-render">{{ data.formula_latex }}</div>
          </div>
        </div>
        
        <!-- Constraints -->
        <div class="notion-block" v-if="data.constraints && data.constraints.length">
          <h3 class="block-heading">Constraints</h3>
          <ul class="notion-bullet-list">
            <li v-for="(item, idx) in data.constraints" :key="idx">{{ item }}</li>
          </ul>
        </div>
        
        <!-- Proof Steps -->
        <div class="notion-block">
          <h3 class="block-heading">Proof Steps</h3>
          <div class="notion-numbered-list">
            <div 
              class="list-item" 
              v-for="(step, index) in data.proof_steps" 
              :key="index"
            >
              <div class="item-number">{{ index + 1 }}.</div>
              <div class="item-content">
                <strong>{{ step.step_title }}</strong>
                <p>{{ step.detail }}</p>
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
.notion-light-slide {
  width: 100%;
  height: 100%;
  background: #FFFFFF;
  display: flex;
  justify-content: center;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, "Apple Color Emoji", Arial, sans-serif, "Segoe UI Emoji", "Segoe UI Symbol";
  color: #37352f;
  padding: 80px;
  box-sizing: border-box;
}

.notion-page {
  width: 100%;
  max-width: 900px;
  display: flex;
  flex-direction: column;
}

.slide-title {
  font-size: 40px;
  font-weight: 700;
  margin: 0 0 30px 0;
}

.content-body {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.notion-callout {
  display: flex;
  padding: 16px;
  background: rgba(241, 241, 239, 1);
  border-radius: 4px;
  gap: 12px;
}

.callout-icon {
  font-size: 24px;
}

.callout-text {
  flex: 1;
  display: flex;
  align-items: center;
}

.latex-render {
  font-family: 'Cambria Math', 'Times New Roman', serif;
  font-size: 24px;
  font-style: italic;
}

.notion-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.block-heading {
  font-size: 20px;
  font-weight: 600;
  margin: 16px 0 8px 0;
}

.notion-bullet-list {
  list-style: disc;
  padding-left: 24px;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.notion-bullet-list li {
  font-size: 16px;
  line-height: 1.5;
}

.notion-numbered-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.list-item {
  display: flex;
  gap: 8px;
}

.item-number {
  min-width: 24px;
  font-size: 16px;
}

.item-content {
  flex: 1;
  font-size: 16px;
  line-height: 1.5;
}

.item-content strong {
  display: block;
  font-weight: 600;
  margin-bottom: 4px;
}

.item-content p {
  margin: 0;
  color: rgba(55, 53, 47, 0.8);
}
</style>
