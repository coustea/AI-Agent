<template>
  <div class="notion-light-slide notion-dashboard">
    <div class="notion-page">
      <h2 class="slide-title">{{ data.title }}</h2>
      
      <div class="content-body">
        
        <!-- Metrics / Gallery View -->
        <div class="notion-gallery" v-if="data.stat_metrics && data.stat_metrics.length">
          <div class="gallery-card" v-for="(stat, idx) in data.stat_metrics" :key="idx">
            <div class="stat-val">{{ stat.value }}<span class="stat-unit" v-if="stat.unit">{{ stat.unit }}</span></div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>

        <div class="columns-wrapper">
          <div class="column-left">
            <div class="notion-code-block">
              <div class="code-header">{{ data.code_snippet.language }}</div>
              <pre><code>{{ data.code_snippet.code }}</code></pre>
            </div>
            
            <div class="notion-code-block terminal" v-if="data.terminal_output">
              <div class="code-header">Terminal / Shell</div>
              <pre><code>{{ data.terminal_output }}</code></pre>
            </div>
          </div>
          
          <div class="column-right">
            <div class="notion-callout highlight">
              <div class="callout-icon">💡</div>
              <div class="callout-text">
                <strong>Key Takeaways</strong>
                <ul class="notion-bullet-list">
                  <li v-for="(point, idx) in data.summary_points" :key="idx">{{ point }}</li>
                </ul>
              </div>
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

.notion-gallery {
  display: flex;
  gap: 16px;
}

.gallery-card {
  flex: 1;
  border: 1px solid rgba(55, 53, 47, 0.09);
  border-radius: 4px;
  padding: 16px;
  background: #FFFFFF;
  box-shadow: rgba(15, 15, 15, 0.05) 0px 0px 0px 1px, rgba(15, 15, 15, 0.1) 0px 2px 4px;
}

.stat-val {
  font-size: 32px;
  font-weight: 700;
  color: #37352f;
  margin-bottom: 4px;
}

.stat-unit {
  font-size: 14px;
  font-weight: 500;
  color: rgba(55, 53, 47, 0.65);
  margin-left: 4px;
}

.stat-label {
  font-size: 14px;
  color: rgba(55, 53, 47, 0.65);
}

.columns-wrapper {
  display: flex;
  gap: 32px;
}

.column-left {
  flex: 7;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.column-right {
  flex: 5;
}

.notion-code-block {
  background: rgba(247, 246, 243, 1);
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid rgba(55, 53, 47, 0.09);
}

.code-header {
  font-size: 12px;
  color: rgba(55, 53, 47, 0.65);
  padding: 8px 12px;
  border-bottom: 1px solid rgba(55, 53, 47, 0.09);
  text-transform: uppercase;
}

.notion-code-block pre {
  margin: 0;
  padding: 16px;
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, Courier, monospace;
  font-size: 14px;
  color: #EB5757;
  overflow-x: auto;
}

.notion-code-block.terminal pre {
  color: #37352f;
}

.notion-callout.highlight {
  display: flex;
  padding: 16px;
  background: rgba(235, 241, 237, 1); /* Greenish background for takeaway */
  border-radius: 4px;
  gap: 12px;
}

.callout-icon { font-size: 24px; }
.callout-text { flex: 1; }

.callout-text strong {
  display: block;
  margin-bottom: 12px;
  font-size: 16px;
}

.notion-bullet-list {
  list-style: disc;
  padding-left: 20px;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notion-bullet-list li {
  font-size: 15px;
  line-height: 1.5;
}
</style>
