<template>
  <div class="mac-light-slide mac-light-dashboard">
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
          <h2 class="slide-title">{{ data.title }}</h2>
        </header>
        
        <div class="layout-body">
          <div class="left-col">
            <div class="mac-editor">
              <div class="editor-header">
                <div class="editor-dots">
                  <span></span><span></span><span></span>
                </div>
                <div class="editor-tab">snippet.{{ data.code_snippet.language }}</div>
              </div>
              <div class="editor-body">
                <pre><code>{{ data.code_snippet.code }}</code></pre>
              </div>
            </div>
            
            <div class="mac-terminal" v-if="data.terminal_output">
              <div class="term-header">
                <span>Output / 执行日志</span>
              </div>
              <div class="term-body">
                {{ data.terminal_output }}
              </div>
            </div>
          </div>
          
          <div class="right-col">
            <div class="stats-grid" v-if="data.stat_metrics && data.stat_metrics.length">
              <div class="stat-card" v-for="(stat, idx) in data.stat_metrics" :key="idx">
                <div class="stat-value">
                  {{ stat.value }}<span class="stat-unit" v-if="stat.unit">{{ stat.unit }}</span>
                </div>
                <div class="stat-label">{{ stat.label }}</div>
              </div>
            </div>
            
            <div class="summary-card">
              <div class="card-label">KEY TAKEAWAYS / 核心要点</div>
              <ul class="summary-list">
                <li v-for="(point, idx) in data.summary_points" :key="idx">
                  <span class="check-icon">✓</span>
                  <span>{{ point }}</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TechDashboardData } from '../../types/ppt';

defineProps<{
  data: TechDashboardData
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
  padding: 30px 40px;
  display: flex;
  flex-direction: column;
}

.slide-header {
  margin-bottom: 20px;
  border-bottom: 2px solid #F3F4F6;
  padding-bottom: 10px;
}

.slide-title {
  font-size: 32px;
  color: #111827;
  margin: 0;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.layout-body {
  flex: 1;
  display: flex;
  gap: 30px;
}

.left-col {
  flex: 7;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.right-col {
  flex: 5;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Mac Editor */
.mac-editor {
  flex: 2;
  background: #1E1E1E;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 10px 20px rgba(0,0,0,0.1);
}

.editor-header {
  background: #2D2D2D;
  height: 36px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  gap: 16px;
}

.editor-dots {
  display: flex;
  gap: 6px;
}

.editor-dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #555;
}

.editor-tab {
  background: #1E1E1E;
  color: #D4D4D4;
  font-size: 13px;
  font-family: var(--font-sans);
  padding: 4px 16px;
  border-radius: 6px 6px 0 0;
  margin-top: 8px;
}

.editor-body {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.editor-body pre {
  margin: 0;
  color: #D4D4D4;
  font-family: var(--font-mono, monospace);
  font-size: 14px;
  line-height: 1.6;
}

/* Mac Terminal */
.mac-terminal {
  flex: 1;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.term-header {
  background: #F9FAFB;
  border-bottom: 1px solid #E5E7EB;
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 700;
  color: #6B7280;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.term-body {
  padding: 16px;
  font-family: var(--font-mono, monospace);
  font-size: 13px;
  color: #4B5563;
  line-height: 1.6;
  white-space: pre-wrap;
  flex: 1;
  overflow-y: auto;
}

/* Stats */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.stat-card {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);
}

.stat-value {
  font-size: 48px;
  font-weight: 800;
  color: #2563EB;
  line-height: 1;
  margin-bottom: 8px;
  font-family: var(--font-mono, monospace);
  display: flex;
  align-items: baseline;
}

.stat-unit {
  font-size: 18px;
  font-weight: 600;
  color: #6B7280;
  margin-left: 4px;
}

.stat-label {
  font-size: 14px;
  font-weight: 600;
  color: #4B5563;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Summary */
.summary-card {
  flex: 1;
  background: #EFF6FF;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid #BFDBFE;
}

.card-label {
  font-size: 13px;
  font-weight: 800;
  color: #1D4ED8;
  letter-spacing: 1px;
  margin-bottom: 16px;
}

.summary-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-list li {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  font-size: 16px;
  color: #1E3A8A;
  line-height: 1.5;
}

.check-icon {
  background: #2563EB;
  color: #FFF;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  flex-shrink: 0;
  margin-top: 2px;
}
</style>
