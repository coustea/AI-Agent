<template>
  <div class="mac-light-slide mac-light-mixed">
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
            <!-- Architecture Graph Mock -->
            <div class="arch-canvas" v-if="data.architecture_nodes && data.architecture_nodes.length">
              <div class="canvas-label">Architecture Topology</div>
              <div class="arch-nodes">
                <div class="arch-node" v-for="node in data.architecture_nodes" :key="node.id" :class="`type-${node.type}`">
                  <div class="node-icon"></div>
                  <div class="node-label">{{ node.label }}</div>
                </div>
              </div>
            </div>
            
            <!-- Comparison Table Mock -->
            <div class="comparison-view" v-else-if="data.comparison_table">
              <div class="comp-header">
                <div class="comp-cell empty"></div>
                <div class="comp-cell">方案 A</div>
                <div class="comp-cell">方案 B</div>
              </div>
              <div class="comp-row" v-for="(dim, idx) in data.comparison_table.dimensions" :key="idx">
                <div class="comp-cell dim">{{ dim }}</div>
                <div class="comp-cell">{{ data.comparison_table.left_features[idx] }}</div>
                <div class="comp-cell">{{ data.comparison_table.right_features[idx] }}</div>
              </div>
            </div>
          </div>
          
          <div class="right-col">
            <div class="deep-dive-card">
              <div class="card-label">DEEP DIVE / 原理解析</div>
              <p class="dive-text">{{ data.deep_dive_text }}</p>
            </div>
            
            <div class="inline-code-card">
              <div class="card-label">CORE IMPLEMENTATION / 核心代码</div>
              <pre><code>{{ data.inline_code }}</code></pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { MixedTwoColumnData } from '../../types/ppt';

defineProps<{
  data: MixedTwoColumnData
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
  gap: 40px;
}

.left-col {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.right-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Architecture Canvas */
.arch-canvas {
  flex: 1;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 24px;
  position: relative;
  display: flex;
  flex-direction: column;
  background-image: radial-gradient(#D1D5DB 1px, transparent 1px);
  background-size: 20px 20px;
}

.canvas-label {
  position: absolute;
  top: 16px;
  left: 20px;
  font-size: 12px;
  font-weight: 800;
  color: #9CA3AF;
  text-transform: uppercase;
}

.arch-nodes {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  align-items: center;
  justify-content: center;
  margin-top: 30px;
}

.arch-node {
  background: #FFFFFF;
  border: 2px solid #3B82F6;
  border-radius: 8px;
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.1);
}

.arch-node.type-database { border-color: #10B981; }
.arch-node.type-client { border-color: #F59E0B; }

.node-icon {
  width: 24px;
  height: 24px;
  background: #E5E7EB;
  border-radius: 4px;
}

.node-label {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
}

/* Comparison View */
.comparison-view {
  flex: 1;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.comp-header {
  display: flex;
  background: #F9FAFB;
  border-bottom: 2px solid #E5E7EB;
}

.comp-row {
  display: flex;
  border-bottom: 1px solid #F3F4F6;
}

.comp-cell {
  flex: 1;
  padding: 16px;
  font-size: 14px;
  color: #4B5563;
  display: flex;
  align-items: center;
  border-right: 1px solid #F3F4F6;
}
.comp-cell:last-child { border-right: none; }
.comp-cell.dim { font-weight: 700; color: #111827; background: #FDFDFD; }

/* Right Col Elements */
.card-label {
  font-size: 12px;
  font-weight: 800;
  color: #6B7280;
  letter-spacing: 1px;
  margin-bottom: 12px;
}

.deep-dive-card {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.dive-text {
  font-size: 16px;
  color: #374151;
  line-height: 1.6;
  margin: 0;
}

.inline-code-card {
  flex: 1;
  background: #1E1E1E;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.inline-code-card .card-label {
  color: #9CA3AF;
}

.inline-code-card pre {
  margin: 0;
  color: #D4D4D4;
  font-family: var(--font-mono, monospace);
  font-size: 14px;
  line-height: 1.6;
  overflow-x: auto;
}
</style>
