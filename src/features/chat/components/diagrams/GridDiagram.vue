<template>
  <div class="grid-diagram">
    <!-- 1. Horizontal Layout (Array / Queue) -->
    <div v-if="payload.layout === 'horizontal'" class="grid-horizontal-container">
      <div 
        v-for="(cell, idx) in payload.cells" 
        :key="idx" 
        class="col-wrapper animate-cell"
        :style="{ '--idx': idx }"
      >
        <!-- Pointer Slot (above) -->
        <div class="pointer-slot">
          <div v-if="cell.pointer" class="pointer-badge top pulsing-badge">
            <span class="pointer-text">{{ cell.pointer }}</span>
            <span class="pointer-arrow">↓</span>
          </div>
        </div>

        <!-- Cell Card (with tooltip if detail is present) -->
        <el-tooltip
          v-if="cell.detail"
          :content="cell.detail"
          placement="top"
          effect="dark"
          :show-after="100"
        >
          <div class="cell-card" :class="[`cell-${cell.status}`, { 'has-detail': cell.detail }]">
            <span class="cell-label">{{ cell.label }}</span>
            <div class="detail-indicator"></div>
          </div>
        </el-tooltip>
        <div v-else class="cell-card" :class="`cell-${cell.status}`">
          <span class="cell-label">{{ cell.label }}</span>
        </div>

        <!-- Index Slot (below) -->
        <div class="index-slot">
          <span class="index-text">{{ cell.index }}</span>
        </div>
      </div>
    </div>

    <!-- 2. Vertical Layout (Call Stack / Register File) -->
    <div v-else-if="payload.layout === 'vertical'" class="grid-vertical-container">
      <div 
        v-for="(cell, idx) in payload.cells" 
        :key="idx" 
        class="row-wrapper animate-cell"
        :style="{ '--idx': idx }"
      >
        <!-- Left: Address / Index -->
        <div class="address-col">
          <span class="address-text">{{ cell.index }}</span>
        </div>

        <!-- Center: Cell Card (with inline detail + tooltip if detail present) -->
        <div class="cell-col">
          <el-tooltip
            v-if="cell.detail"
            :content="cell.detail"
            placement="top"
            effect="dark"
            :show-after="100"
          >
            <div class="cell-card-vertical" :class="[`cell-${cell.status}`, { 'has-detail': cell.detail }]">
              <span class="cell-label">{{ cell.label }}</span>
              <span class="cell-detail-inline">— {{ cell.detail }}</span>
            </div>
          </el-tooltip>
          <div v-else class="cell-card-vertical" :class="`cell-${cell.status}`">
            <span class="cell-label">{{ cell.label }}</span>
          </div>
        </div>

        <!-- Right: Pointer Badge -->
        <div class="pointer-col">
          <div v-if="cell.pointer" class="pointer-badge right pulsing-badge">
            <span class="pointer-arrow">←</span>
            <span class="pointer-text">{{ cell.pointer }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 3. Matrix Layout (Memory Paging / Cache Lines) -->
    <div 
      v-else-if="payload.layout === 'matrix'" 
      class="grid-matrix-container"
      :style="{ '--cols': payload.cols || 4 }"
    >
      <div 
        v-for="(cell, idx) in payload.cells" 
        :key="idx" 
        class="matrix-cell-wrapper animate-cell"
        :style="{ '--idx': idx }"
      >
        <el-tooltip
          v-if="cell.detail"
          :content="cell.detail"
          placement="top"
          effect="dark"
          :show-after="100"
        >
          <div class="cell-card-matrix" :class="[`cell-${cell.status}`, { 'has-detail': cell.detail }]">
            <span class="matrix-cell-index">{{ cell.index }}</span>
            <span class="matrix-cell-label">{{ cell.label }}</span>
            <div v-if="cell.pointer" class="matrix-cell-pointer-badge">
              {{ cell.pointer }}
            </div>
          </div>
        </el-tooltip>
        <div v-else class="cell-card-matrix" :class="`cell-${cell.status}`">
          <span class="matrix-cell-index">{{ cell.index }}</span>
          <span class="matrix-cell-label">{{ cell.label }}</span>
          <div v-if="cell.pointer" class="matrix-cell-pointer-badge">
            {{ cell.pointer }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GridPayload } from '@/features/chat/types/chat'

defineProps<{
  payload: GridPayload
}>()
</script>

<style scoped>
.grid-diagram {
  width: 100%;
  background: var(--color-bg);
  border-radius: 16px;
  padding: 16px;
  box-sizing: border-box;
}

/* Staggered entry animations */
.animate-cell {
  animation: cell-fade-in 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: calc(var(--idx) * 0.04s);
}

@keyframes cell-fade-in {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* Cell status styles with premium gradients and borders */
.cell-normal {
  background: linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-hover) 100%);
  border: 1.5px solid var(--color-border);
  color: var(--color-text-strong);
}
.cell-normal:hover {
  border-color: var(--color-primary-border);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.08);
  transform: translateY(-2px) scale(1.03);
}

.cell-active {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(16, 185, 129, 0.12) 100%);
  border: 1.5px solid var(--color-success);
  color: var(--color-success);
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.1);
}
.cell-active:hover {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.18) 100%);
  box-shadow: 0 6px 16px rgba(16, 185, 129, 0.2);
  transform: translateY(-2px) scale(1.03);
}

.cell-empty {
  background: transparent;
  border: 1.5px dashed var(--color-border-hover);
  color: var(--color-text-muted);
  opacity: 0.6;
}
.cell-empty:hover {
  opacity: 1;
  border-color: var(--color-text-muted);
  transform: translateY(-1px) scale(1.02);
}

.cell-pointer {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.06) 0%, rgba(245, 158, 11, 0.15) 100%);
  border: 1.5px solid var(--color-warning);
  color: var(--color-warning);
  font-weight: 600;
}
.cell-pointer:hover {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(245, 158, 11, 0.22) 100%);
  box-shadow: 0 6px 16px rgba(245, 158, 11, 0.18);
  transform: translateY(-2px) scale(1.03);
}

/* 1. Horizontal Layout (Array / Queue) */
.grid-horizontal-container {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 12px;
  overflow-x: auto;
  padding: 16px 8px 8px;
  width: 100%;
  box-sizing: border-box;
}

/* Custom scrollbar for horizontal container */
.grid-horizontal-container::-webkit-scrollbar {
  height: 6px;
}
.grid-horizontal-container::-webkit-scrollbar-track {
  background: transparent;
}
.grid-horizontal-container::-webkit-scrollbar-thumb {
  background-color: var(--color-border-hover);
  border-radius: 3px;
}

.col-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.pointer-slot {
  height: 28px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  margin-bottom: 6px;
}

.pointer-badge {
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  line-height: 1;
  white-space: nowrap;
}

.pointer-badge.top {
  background: rgba(79, 70, 229, 0.08);
  border: 1px solid rgba(79, 70, 229, 0.2);
  color: var(--color-primary);
  gap: 2px;
}

.pointer-badge.top .pointer-arrow {
  font-size: 12px;
  margin-top: 1px;
}

.pulsing-badge {
  animation: badge-pulse 2s infinite ease-in-out;
}

@keyframes badge-pulse {
  0% { transform: scale(1); opacity: 0.95; }
  50% { transform: scale(1.04); opacity: 1; box-shadow: 0 0 8px rgba(79, 70, 229, 0.12); }
  100% { transform: scale(1); opacity: 0.95; }
}

.cell-card {
  width: 68px;
  height: 68px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease, border-color 0.2s ease;
  position: relative;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

.cell-label {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  text-align: center;
}

.detail-indicator {
  position: absolute;
  bottom: 6px;
  width: 5px;
  height: 5px;
  background-color: currentColor;
  border-radius: 50%;
  opacity: 0.6;
}

.index-slot {
  margin-top: 8px;
  display: flex;
  justify-content: center;
}

.index-text {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-muted);
}

/* 2. Vertical Layout (Call Stack / Register File) */
.grid-vertical-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 540px;
  margin: 0 auto;
  padding: 12px 8px;
}

.row-wrapper {
  display: flex;
  align-items: center;
  width: 100%;
}

.address-col {
  width: 72px;
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  padding-right: 16px;
  box-sizing: border-box;
}

.address-text {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.cell-col {
  flex-grow: 1;
}

.cell-card-vertical {
  height: 42px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  border-radius: 8px;
  box-sizing: border-box;
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease, border-color 0.2s ease;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

.cell-card-vertical:hover {
  transform: translateX(4px) scale(1.01);
}

.cell-card-vertical .cell-label {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
}

.cell-detail-inline {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-left: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 0.8;
}

.pointer-col {
  width: 110px;
  flex-shrink: 0;
  display: flex;
  justify-content: flex-start;
  padding-left: 16px;
  box-sizing: border-box;
}

.pointer-badge.right {
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.2);
  color: var(--color-warning);
  gap: 2px;
}

.pointer-badge.right .pointer-arrow {
  font-size: 12px;
}

/* 3. Matrix Layout (Memory Paging / Cache Lines) */
.grid-matrix-container {
  display: grid;
  grid-template-columns: repeat(var(--cols, 4), minmax(0, 1fr));
  gap: 12px;
  padding: 12px 8px;
  width: 100%;
  box-sizing: border-box;
}

.matrix-cell-wrapper {
  position: relative;
  width: 100%;
}

.cell-card-matrix {
  min-height: 84px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border-radius: 12px;
  position: relative;
  box-sizing: border-box;
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease, border-color 0.2s ease;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

.cell-card-matrix:hover {
  transform: translateY(-3px) scale(1.03);
}

.matrix-cell-index {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-text-muted);
  font-weight: 500;
  align-self: flex-start;
}

.matrix-cell-label {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  text-align: center;
  margin: 6px 0;
  word-break: break-all;
}

.matrix-cell-pointer-badge {
  align-self: flex-end;
  background: rgba(79, 70, 229, 0.08);
  border: 1px solid rgba(79, 70, 229, 0.2);
  color: var(--color-primary);
  font-size: 10px;
  font-weight: 600;
  padding: 1px 4px;
  border-radius: 3px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
