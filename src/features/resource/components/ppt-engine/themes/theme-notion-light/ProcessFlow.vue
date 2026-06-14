<template>
  <div class="notion-light-slide notion-process">
    <div class="notion-page">
      <h2 class="slide-title">{{ data.flow_title }}</h2>
      
      <div class="content-body">
        <!-- Notion Table for Timeline -->
        <div class="notion-table-view">
          <div class="table-header">
            <div class="table-cell col-time">Time / Seq</div>
            <div class="table-cell col-action">Action</div>
            <div class="table-cell col-state">Internal State</div>
          </div>
          
          <div class="table-row" v-for="(step, idx) in data.timeline_steps" :key="idx">
            <div class="table-cell col-time">
              <span class="notion-tag blue">{{ step.time_seq }}</span>
            </div>
            <div class="table-cell col-action">
              <strong>{{ step.from }}</strong> ➔ <strong>{{ step.to }}</strong><br/>
              <span class="action-desc">{{ step.action }}</span>
            </div>
            <div class="table-cell col-state">
              <div class="code-block">{{ step.internal_state }}</div>
            </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ProcessFlowData } from '../../types/ppt';

defineProps<{
  data: ProcessFlowData
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
.table-row:last-child {
  border-bottom: none;
}

.table-cell {
  padding: 12px 16px;
  font-size: 14px;
  border-right: 1px solid rgba(55, 53, 47, 0.09);
}
.table-cell:last-child {
  border-right: none;
}

.table-header .table-cell {
  color: rgba(55, 53, 47, 0.65);
  font-weight: 500;
}

.col-time { width: 120px; flex-shrink: 0; }
.col-action { width: 250px; flex-shrink: 0; }
.col-state { flex: 1; }

.notion-tag.blue {
  background: rgba(225, 242, 254, 1);
  color: rgba(11, 110, 153, 1);
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 14px;
  font-family: SFMono-Regular, Consolas, monospace;
}

.action-desc {
  color: rgba(55, 53, 47, 0.8);
  display: block;
  margin-top: 4px;
}

.code-block {
  background: rgba(247, 246, 243, 1);
  padding: 12px;
  border-radius: 4px;
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, Courier, monospace;
  font-size: 13px;
  color: #EB5757;
  white-space: pre-wrap;
}
</style>
