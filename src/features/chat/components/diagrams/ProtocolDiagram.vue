<template>
  <div class="protocol-diagram-container">
    <!-- 1. Vertical Stack Orientation (OSI/TCP-IP Stack) -->
    <div v-if="payload.orientation === 'vertical'" class="vertical-stack">
      <div class="stack-backbone"></div>
      
      <div 
        v-for="(field, idx) in payload.fields" 
        :key="idx" 
        class="layer-row animate-layer"
        :style="{ '--layer-idx': idx }"
      >
        <!-- Connector node dot -->
        <div class="connector-dot" :class="{ 'is-active': field.highlight }"></div>

        <!-- Layer box (wrapped in tooltip if detail exists) -->
        <div 
          class="layer-card" 
          :class="{ 'is-highlighted': field.highlight }"
          :title="field.detail ? field.detail : undefined"
        >
          <div class="layer-badge" :class="{ 'is-highlighted': field.highlight }">
            {{ getLayerBadge(idx, payload.fields.length) }}
          </div>
          <div class="layer-content">
            <strong class="layer-name">{{ field.name }}</strong>
            <span v-if="field.detail" class="layer-detail-inline">{{ field.detail }}</span>
          </div>
          <div v-if="field.highlight && field.detail" class="pulse-indicator">
            <span class="pulse-dot"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. Horizontal Split Orientation (Packet Header Structure) -->
    <div v-else class="horizontal-split">
      <!-- Bit Ruler -->
      <div class="bit-ruler-container">
        <div class="ruler-offset-placeholder"></div>
        <div class="bit-ruler">
          <div 
            v-for="bit in [0, 8, 16, 24, 31]" 
            :key="bit" 
            class="bit-marker"
            :style="{ 
              left: `${(bit / 32) * 100}%`,
              transform: bit === 31 ? 'translateX(-100%)' : (bit === 0 ? 'none' : 'translateX(-50%)')
            }"
          >
            {{ bit }}
          </div>
        </div>
      </div>

      <!-- Packet Rows -->
      <div class="packet-rows">
        <div 
          v-for="(row, rowIdx) in rowMeta" 
          :key="rowIdx" 
          class="packet-row animate-row"
          :style="{ '--row-idx': rowIdx }"
        >
          <!-- Left side bit range / offset label -->
          <div class="row-offset-label">
            {{ row.startBit }}
          </div>

          <!-- Flex field container -->
          <div class="row-fields">
            <template v-for="(field, fIdx) in row.fields" :key="fIdx">
              <div 
                class="field-card" 
                :class="{ 'is-highlighted': field.highlight }"
                :style="{ 
                  flex: `0 0 ${((field.width_ratio ?? 32) / 32 * 100)}%`,
                  maxWidth: `${((field.width_ratio ?? 32) / 32 * 100)}%`
                }"
                :title="field.detail ? `${field.name}: ${field.detail} (${field.width_ratio ?? 32} ${ (field.width_ratio ?? 32) === 1 ? 'bit' : 'bits' })` : undefined"
              >
                <div class="field-card-content">
                  <span class="field-name">{{ field.name }}</span>
                  <span v-if="(field.width_ratio ?? 32) >= 4" class="field-bits">
                    {{ field.width_ratio ?? 32 }} {{ (field.width_ratio ?? 32) === 1 ? 'bit' : 'bits' }}
                  </span>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ProtocolPayload, ProtocolField } from '@/features/chat/types/chat'

const props = defineProps<{
  payload: ProtocolPayload
}>()

// Dynamic layer badge helper for vertical stacks
const getLayerBadge = (idx: number, total: number) => {
  return `L${total - idx}`
}

// Group fields into 32-bit rows for packet header diagrams
const rows = computed(() => {
  const result: ProtocolField[][] = []
  let currentRow: ProtocolField[] = []
  let currentWidth = 0

  for (const field of props.payload.fields) {
    const fieldWidth = field.width_ratio ?? 32
    const clampedWidth = Math.max(1, Math.min(fieldWidth, 32))
    
    if (currentWidth + clampedWidth > 32) {
      if (currentRow.length > 0) {
        result.push(currentRow)
      }
      currentRow = [field]
      currentWidth = clampedWidth
    } else {
      currentRow.push(field)
      currentWidth += clampedWidth
    }
  }
  if (currentRow.length > 0) {
    result.push(currentRow)
  }
  return result
})

// Calculate bit offsets for each row
const rowMeta = computed(() => {
  const result: { fields: ProtocolField[]; startBit: number; endBit: number }[] = []
  let currentStartBit = 0
  
  for (const row of rows.value) {
    result.push({
      fields: row,
      startBit: currentStartBit,
      endBit: currentStartBit + 32 - 1
    })
    currentStartBit += 32
  }
  return result
})
</script>

<style scoped>
.protocol-diagram-container {
  width: 100%;
  background: var(--color-bg);
  border-radius: 16px;
  padding: 24px;
  box-sizing: border-box;
}

/* ============================================================
   1. Vertical Stack (OSI/TCP-IP Stack)
   ============================================================ */
.vertical-stack {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-left: 36px;
  width: 100%;
  box-sizing: border-box;
}

.stack-backbone {
  position: absolute;
  left: 17px;
  top: 12px;
  bottom: 12px;
  width: 2px;
  background: var(--color-border);
  z-index: 1;
}

.layer-row {
  position: relative;
  width: 100%;
}

.connector-dot {
  position: absolute;
  left: -24px;
  top: 50%;
  transform: translateY(-50%);
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 2px solid var(--color-border-hover);
  z-index: 2;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.connector-dot.is-active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: 0 0 10px var(--color-primary);
}

.connector-dot.is-active::after {
  content: '';
  position: absolute;
  top: -4px;
  left: -4px;
  right: -4px;
  bottom: -4px;
  border-radius: 50%;
  border: 1px solid var(--color-primary);
  animation: dot-pulse 1.8s infinite ease-in-out;
}

@keyframes dot-pulse {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.6); opacity: 0; }
}

.layer-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-hover) 100%);
  border: 1.5px solid var(--color-border);
  border-radius: 12px;
  padding: 14px 18px;
  cursor: pointer;
  position: relative;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.layer-card:hover {
  transform: translateY(-2px) scale(1.01);
  border-color: var(--color-border-hover);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.05);
}

.layer-card.is-highlighted {
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.06) 0%, rgba(79, 70, 229, 0.12) 100%);
  border-color: var(--color-primary);
  border-left: 4px solid var(--color-primary);
  box-shadow: 0 4px 15px rgba(79, 70, 229, 0.15), inset 0 0 8px rgba(79, 70, 229, 0.04);
}

.layer-card.is-highlighted:hover {
  box-shadow: 0 8px 25px rgba(79, 70, 229, 0.25), inset 0 0 12px rgba(79, 70, 229, 0.08);
}

.layer-badge {
  background: var(--color-bg);
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  min-width: 32px;
  text-align: center;
  transition: all 0.3s ease;
}

.layer-badge.is-highlighted {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  border-color: var(--color-primary-border);
}

.layer-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.layer-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-strong);
}

.layer-detail-inline {
  font-size: 13px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pulse-indicator {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  box-shadow: 0 0 8px var(--color-primary);
}

/* ============================================================
   2. Horizontal Split (Packet Header structure)
   ============================================================ */
.horizontal-split {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  box-sizing: border-box;
}

.bit-ruler-container {
  display: flex;
  align-items: center;
  width: 100%;
}

.ruler-offset-placeholder {
  width: 48px;
  flex: 0 0 48px;
}

.bit-ruler {
  position: relative;
  flex: 1;
  height: 16px;
  margin-bottom: 2px;
}

.bit-marker {
  position: absolute;
  top: 0;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--color-text-muted);
}

.packet-rows {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.packet-row {
  display: flex;
  align-items: stretch;
  width: 100%;
}

.row-offset-label {
  width: 48px;
  flex: 0 0 48px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-faint);
  user-select: none;
}

.row-fields {
  display: flex;
  flex: 1;
  gap: 4px;
}

.field-card {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 48px;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.06) 0%, rgba(37, 99, 235, 0.12) 100%);
  border: 1px solid rgba(59, 130, 246, 0.2);
  color: var(--color-text-strong);
  padding: 6px 8px;
  box-sizing: border-box;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
}

.field-card:hover {
  transform: translateY(-2px) scale(1.02);
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.12);
  z-index: 5;
}

.field-card.is-highlighted {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(245, 158, 11, 0.18) 100%);
  border-color: var(--color-warning);
  color: var(--color-warning);
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.1);
}

.field-card.is-highlighted:hover {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.14) 0%, rgba(245, 158, 11, 0.24) 100%);
  box-shadow: 0 6px 18px rgba(245, 158, 11, 0.25);
  border-color: var(--color-warning);
}

.field-card-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-width: 0;
}

.field-name {
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  width: 100%;
}

.field-bits {
  font-size: 9px;
  opacity: 0.75;
  white-space: nowrap;
  margin-top: 2px;
  font-family: var(--font-mono);
}

/* ============================================================
   3. Staggered Animations
   ============================================================ */
.animate-layer {
  animation: slide-in-left 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: calc(var(--layer-idx) * 0.05s);
}

.animate-row {
  animation: slide-in-bottom 0.45s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: calc(var(--row-idx) * 0.06s);
}

@keyframes slide-in-left {
  from {
    opacity: 0;
    transform: translateX(-16px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slide-in-bottom {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
