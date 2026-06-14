<template>
  <div class="notion-light-slide notion-mixed">
    <div class="notion-page">
      <h2 class="slide-title">{{ data.title }}</h2>
      
      <div class="content-body">
        
        <div class="notion-columns">
          <div class="column-left">
            
            <!-- Board View Mock for Architecture -->
            <div class="notion-board" v-if="data.architecture_nodes && data.architecture_nodes.length">
              <div class="board-header">Architecture Topology</div>
              <div class="board-body">
                <div class="board-card" v-for="node in data.architecture_nodes" :key="node.id">
                  <div class="card-title">{{ node.label }}</div>
                  <div class="card-prop">
                    <span class="notion-tag" :class="node.type === 'client' ? 'orange' : 'green'">{{ node.type }}</span>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- Table View Mock for Comparison -->
            <div class="notion-table-view" v-else-if="data.comparison_table">
              <div class="table-header">
                <div class="table-cell empty"></div>
                <div class="table-cell">A</div>
                <div class="table-cell">B</div>
              </div>
              <div class="table-row" v-for="(dim, idx) in data.comparison_table.dimensions" :key="idx">
                <div class="table-cell dim">{{ dim }}</div>
                <div class="table-cell">{{ data.comparison_table.left_features[idx] }}</div>
                <div class="table-cell">{{ data.comparison_table.right_features[idx] }}</div>
              </div>
            </div>
          </div>
          
          <div class="column-right">
            <!-- Text Block -->
            <div class="notion-block text-block">
              <h3 class="block-heading">Deep Dive</h3>
              <p>{{ data.deep_dive_text }}</p>
            </div>
            
            <!-- Code Block -->
            <div class="notion-block code-block-wrap">
              <h3 class="block-heading">Implementation</h3>
              <div class="notion-code-block">
                <pre><code>{{ data.inline_code }}</code></pre>
              </div>
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
}

.notion-columns {
  display: flex;
  gap: 40px;
}

.column-left { flex: 1; }
.column-right { flex: 1; display: flex; flex-direction: column; gap: 24px; }

/* Board */
.notion-board {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.board-header {
  font-weight: 600;
  color: rgba(55, 53, 47, 0.65);
  font-size: 14px;
}

.board-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.board-card {
  border: 1px solid rgba(55, 53, 47, 0.09);
  border-radius: 4px;
  padding: 10px 14px;
  box-shadow: rgba(15, 15, 15, 0.05) 0px 0px 0px 1px, rgba(15, 15, 15, 0.1) 0px 2px 4px;
  background: #FFFFFF;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-title {
  font-weight: 500;
  font-size: 14px;
}

.notion-tag {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
}
.notion-tag.orange { background: rgba(253, 236, 200, 1); color: rgba(147, 47, 8, 1); }
.notion-tag.green { background: rgba(219, 237, 219, 1); color: rgba(28, 56, 41, 1); }

/* Table */
.notion-table-view {
  border: 1px solid rgba(55, 53, 47, 0.09);
  border-radius: 4px;
  overflow: hidden;
}

.table-header {
  display: flex;
  background: rgba(247, 246, 243, 1);
  border-bottom: 1px solid rgba(55, 53, 47, 0.09);
}

.table-row {
  display: flex;
  border-bottom: 1px solid rgba(55, 53, 47, 0.09);
}
.table-row:last-child { border-bottom: none; }

.table-cell {
  flex: 1;
  padding: 8px 12px;
  font-size: 14px;
  border-right: 1px solid rgba(55, 53, 47, 0.09);
}
.table-cell:last-child { border-right: none; }
.table-header .table-cell { font-weight: 500; color: rgba(55, 53, 47, 0.65); }
.table-cell.dim { font-weight: 600; background: rgba(250, 250, 250, 1); }

/* Blocks */
.block-heading {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.text-block p {
  margin: 0;
  line-height: 1.6;
  font-size: 16px;
  color: rgba(55, 53, 47, 0.8);
}

.notion-code-block {
  background: rgba(247, 246, 243, 1);
  border-radius: 4px;
  padding: 16px;
  overflow-x: auto;
  border: 1px solid rgba(55, 53, 47, 0.09);
}

.notion-code-block pre {
  margin: 0;
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, Courier, monospace;
  font-size: 13px;
  color: #EB5757;
}
</style>
