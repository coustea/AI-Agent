<template>
  <div class="composition worked-example">
    <div class="subtitle">{{ slide.key_message }}</div>
    <div class="example-content">
      <div class="code-pane ppt-card">
        <div class="pane-label">CODE WALKTHROUGH / FORMULA</div>
        <div v-for="el in slide.slots.code || []" :key="el.content || ''" class="code-wrapper">
          <pre v-if="el.type === 'code'" class="code-block"><code>{{ el.content }}</code></pre>
          <div v-else-if="el.type === 'formula'" class="formula-block">
            $${{ el.content }}$$
          </div>
          <div v-else class="fallback-code">{{ el.content }}</div>
        </div>
      </div>
      <div class="explanation-pane">
        <div class="pane-label">EXPLANATION & ANALYSIS</div>
        <div class="explanation-list">
          <div v-for="el in slide.slots.explanation || []" :key="el.content || ''" class="explanation-item">
            <span class="bullet">✦</span>
            <div class="exp-text">
              <div v-if="el.label" class="exp-label">{{ el.label }}</div>
              <div class="exp-content">{{ el.content }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import type { ResolvedSlide } from '../model/resolvedSlide'

defineProps<{ slide: ResolvedSlide }>()

onMounted(() => {
  if (typeof (window as any).renderMathInElement === 'function') {
    try {
      (window as any).renderMathInElement(document.body)
    } catch (e) {
      console.warn('MathJax/KaTeX rendering failed:', e)
    }
  }
})
</script>

<style scoped>
.worked-example {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 40px 60px;
  box-sizing: border-box;
}
.subtitle {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--ppt-text-secondary);
  margin-bottom: 24px;
  border-left: 3px solid var(--ppt-accent);
  padding-left: 12px;
}
.example-content {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 30px;
  flex: 1;
  min-height: 0;
}
.code-pane {
  background: var(--ppt-code-block-bg, #1e293b);
  color: var(--ppt-code-block-text, #f1f5f9);
  padding: 24px;
  overflow: auto;
  display: flex;
  flex-direction: column;
}
.pane-label {
  font-size: 0.75rem;
  font-weight: 800;
  color: var(--ppt-accent);
  letter-spacing: 0.1em;
  margin-bottom: 12px;
  text-transform: uppercase;
}
.code-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.code-block {
  margin: 0;
  font-family: 'Fira Code', 'Courier New', Courier, monospace;
  font-size: 0.95rem;
  line-height: 1.5;
  white-space: pre-wrap;
}
.formula-block {
  font-size: 1.5rem;
  text-align: center;
  padding: 20px;
  color: var(--ppt-accent);
}
.fallback-code {
  font-size: 1.1rem;
  font-family: monospace;
}
.explanation-pane {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.explanation-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.explanation-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.bullet {
  color: var(--ppt-accent);
  font-weight: bold;
}
.exp-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.exp-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--ppt-accent);
}
.exp-content {
  font-size: 0.95rem;
  color: var(--ppt-text-secondary);
  line-height: 1.4;
}
</style>
