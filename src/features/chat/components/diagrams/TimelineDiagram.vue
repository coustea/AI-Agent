<template>
  <div class="timeline-diagram">
    <!-- Horizontal Scroll Wrapper -->
    <div class="timeline-scroll-wrapper">
      <div 
        class="timeline-interactive-wrapper" 
        :style="{ minWidth: `${timelineMinWidth}px` }"
      >
        <!-- Time Ruler Row -->
        <div class="ruler-row">
          <div class="ruler-meta-spacer"></div>
          <div class="ruler-container">
            <div class="time-ruler">
              <div 
                v-for="tick in maxTime + 1" 
                :key="tick" 
                class="ruler-tick"
                :style="{ left: `${((tick - 1) / maxTime) * 100}%` }"
              >
                <span class="tick-label">{{ tick - 1 }}</span>
                <span class="tick-line"></span>
              </div>
            </div>
          </div>
        </div>

        <!-- Tracks Container -->
        <div class="tracks-outer">
          <!-- Grid Overlay (Background grid lines and Playhead) -->
          <div class="tracks-grid-overlay">
            <!-- Background vertical dashed lines -->
            <div class="grid-background">
              <div 
                v-for="tick in maxTime + 1" 
                :key="tick" 
                class="grid-bg-line"
                :style="{ left: `${((tick - 1) / maxTime) * 100}%` }"
              ></div>
            </div>

            <!-- Scanning Playhead -->
            <div 
              class="playhead" 
              :style="{ left: `${(currentStep / maxTime) * 100}%` }"
            >
              <div class="playhead-line"></div>
              <div class="playhead-badge">{{ currentStep }}</div>
            </div>
          </div>

          <!-- Track Rows -->
          <div 
            v-for="(track, tIdx) in payload.tracks" 
            :key="tIdx" 
            class="track-row"
          >
            <div class="track-meta">
              <span class="track-name" :title="track.track_name">
                {{ track.track_name }}
              </span>
            </div>
            <div 
              class="track-grid-container" 
              :style="{ '--max-time': maxTime }"
            >
              <div 
                v-for="(block, bIdx) in track.blocks" 
                :key="bIdx" 
                class="timeline-block"
                :class="[
                  `status-${block.status}`, 
                  { 
                    'state-future': block.start > currentStep,
                    'state-active': block.start <= currentStep && (block.start + block.duration) > currentStep,
                    'state-past': (block.start + block.duration) <= currentStep 
                  }
                ]"
                :style="{ 
                  gridColumn: `${block.start + 1} / span ${block.duration}`,
                  '--active-color-rgb': getActiveColorRgb(block.status)
                }"
              >
                <el-tooltip 
                  :content="`${block.label} | 开始: ${block.start}, 持续: ${block.duration} (${block.status})`" 
                  placement="top" 
                  effect="dark"
                >
                  <div class="block-content">
                    <span class="block-label">{{ block.label }}</span>
                  </div>
                </el-tooltip>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Beautiful Controls Bar -->
    <div class="timeline-controls-bar">
      <div class="step-info">
        <span class="step-label">当前步骤:</span>
        <span class="step-value">{{ currentStep }}</span>
        <span class="step-divider">/</span>
        <span class="step-max">{{ maxTime }}</span>
      </div>

      <div class="control-buttons">
        <el-button 
          type="info" 
          plain 
          circle
          @click="resetPlayback"
          title="重置 (Reset)"
          class="control-btn"
        >
          <svg class="control-icon" viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
          </svg>
        </el-button>

        <el-button 
          :type="isPlaying ? 'warning' : 'primary'"
          circle 
          @click="togglePlay"
          :title="isPlaying ? '暂停 (Pause)' : '播放 (Play)'"
          class="control-btn play-btn"
        >
          <svg v-if="!isPlaying" class="control-icon" viewBox="0 0 24 24" width="20" height="20">
            <path fill="currentColor" d="M8 5v14l11-7z"/>
          </svg>
          <svg v-else class="control-icon" viewBox="0 0 24 24" width="20" height="20">
            <path fill="currentColor" d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
          </svg>
        </el-button>

        <el-button 
          type="primary" 
          plain 
          circle
          @click="nextStep"
          :disabled="currentStep >= maxTime"
          title="下一步 (Next)"
          class="control-btn"
        >
          <svg class="control-icon" viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M6 18l8.5-6L6 6v12zM16 6v12h2V6h-2z"/>
          </svg>
        </el-button>
      </div>

      <div v-if="payload.axis_label" class="axis-label-display">
        <span class="axis-badge">{{ payload.axis_label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue'
import type { TimelinePayload } from '@/features/chat/types/chat'

const props = defineProps<{
  payload: TimelinePayload
}>()

const currentStep = ref(0)
const isPlaying = ref(false)
let timerInterval: any = null

const maxTime = computed(() => {
  let maxVal = 0
  props.payload.tracks.forEach(track => {
    track.blocks.forEach(block => {
      const endVal = block.start + block.duration
      if (endVal > maxVal) {
        maxVal = endVal
      }
    })
  })
  return Math.max(1, maxVal)
})

const timelineMinWidth = computed(() => {
  return 140 + maxTime.value * 60
})

const getActiveColorRgb = (status: 'normal' | 'active' | 'idle' | 'stall') => {
  switch (status) {
    case 'normal':
      return '59, 130, 246'
    case 'active':
      return '16, 185, 129'
    case 'idle':
      return '148, 163, 184'
    case 'stall':
      return '245, 158, 11'
    default:
      return '59, 130, 246'
  }
}

const startPlayback = () => {
  if (isPlaying.value) return
  isPlaying.value = true
  timerInterval = setInterval(() => {
    if (currentStep.value >= maxTime.value) {
      pausePlayback()
    } else {
      currentStep.value++
    }
  }, 1000)
}

const pausePlayback = () => {
  isPlaying.value = false
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

const togglePlay = () => {
  if (isPlaying.value) {
    pausePlayback()
  } else {
    if (currentStep.value >= maxTime.value) {
      currentStep.value = 0
    }
    startPlayback()
  }
}

const resetPlayback = () => {
  pausePlayback()
  currentStep.value = 0
}

const nextStep = () => {
  pausePlayback()
  if (currentStep.value < maxTime.value) {
    currentStep.value++
  }
}

watch(() => props.payload, () => {
  resetPlayback()
}, { deep: true })

onUnmounted(() => {
  if (timerInterval) {
    clearInterval(timerInterval)
  }
})
</script>

<style scoped>
.timeline-diagram {
  width: 100%;
  background: var(--color-bg);
  border-radius: 16px;
  padding: 24px;
  box-sizing: border-box;
  border: 1px solid var(--color-border);
}

.timeline-scroll-wrapper {
  width: 100%;
  overflow-x: auto;
  padding-bottom: 8px;
}

/* Custom Scrollbar for premium feel */
.timeline-scroll-wrapper::-webkit-scrollbar {
  height: 6px;
}
.timeline-scroll-wrapper::-webkit-scrollbar-track {
  background: transparent;
}
.timeline-scroll-wrapper::-webkit-scrollbar-thumb {
  background: var(--color-border-hover);
  border-radius: 3px;
}
.timeline-scroll-wrapper::-webkit-scrollbar-thumb:hover {
  background: var(--color-text-muted);
}

.timeline-interactive-wrapper {
  position: relative;
  width: 100%;
}

/* Ruler Styling */
.ruler-row {
  display: flex;
  align-items: center;
  height: 32px;
  margin-bottom: 8px;
}

.ruler-meta-spacer {
  width: 140px;
  min-width: 140px;
}

.ruler-container {
  flex: 1;
  position: relative;
  height: 100%;
}

.time-ruler {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.ruler-tick {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.tick-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 700;
  color: var(--color-text-muted);
  line-height: 1;
}

.tick-line {
  width: 1px;
  height: 6px;
  background: var(--color-border-hover);
  margin-top: 6px;
}

/* Tracks Area */
.tracks-outer {
  position: relative;
  width: 100%;
}

.tracks-grid-overlay {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 140px;
  right: 0;
  pointer-events: none;
  z-index: 5;
}

/* Vertical Grid Background lines */
.grid-background {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
}

.grid-bg-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  border-left: 1px dashed var(--color-border);
  opacity: 0.6;
}

/* Scanning Playhead */
.playhead {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  transform: translateX(-50%);
  z-index: 10;
  transition: left 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.playhead-line {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 2px;
  border-left: 2px dashed #ff007f;
  filter: drop-shadow(0 0 4px #ff007f);
}

.playhead-badge {
  position: absolute;
  top: -26px;
  left: 50%;
  transform: translateX(-50%);
  background: #ff007f;
  color: white;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
  box-shadow: 0 2px 6px rgba(255, 0, 127, 0.4);
}

/* Track Rows */
.track-row {
  display: flex;
  align-items: stretch;
  margin-bottom: 12px;
  min-height: 44px;
}

.track-row:last-child {
  margin-bottom: 0;
}

.track-meta {
  width: 140px;
  min-width: 140px;
  display: flex;
  align-items: center;
  padding-right: 16px;
  box-sizing: border-box;
}

.track-name {
  font-family: var(--font-display);
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-grid-container {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(var(--max-time), 1fr);
  gap: 0; /* Contiguous columns to align perfectly with ruler & playhead */
  background: rgba(241, 245, 249, 0.4);
  border-radius: 8px;
  padding: 4px;
  border: 1px solid var(--color-border-light);
  box-sizing: border-box;
  align-items: center;
  position: relative;
}

/* Timeline Block */
.timeline-block {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  margin: 2px; /* slight margin to create spacing between adjacent blocks */
  padding: 6px 8px;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 700;
  color: white;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
  min-height: 32px;
  box-sizing: border-box;
  cursor: pointer;
}

.block-content {
  width: 100%;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.block-label {
  letter-spacing: 0.02em;
}

/* Status Colors & Gradients */
.status-normal {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border: 1.5px solid rgba(59, 130, 246, 0.3);
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.15);
}

.status-active {
  background: linear-gradient(135deg, #10b981 0%, #047857 100%);
  border: 1.5px solid rgba(16, 185, 129, 0.3);
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.15);
}

.status-idle {
  background: linear-gradient(135deg, #f1f5f9 0%, #cbd5e1 100%);
  border: 1.5px solid rgba(148, 163, 184, 0.3);
  color: var(--color-text-secondary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.status-stall {
  background: repeating-linear-gradient(
    -45deg,
    #f59e0b,
    #f59e0b 6px,
    #d97706 6px,
    #d97706 12px
  );
  border: 1.5px solid rgba(245, 158, 11, 0.4);
  box-shadow: 0 2px 4px rgba(245, 158, 11, 0.15);
}

/* Playhead State Adjustments */
.state-future {
  opacity: 0.12;
  border: 1.5px dashed currentColor;
  background: transparent !important;
  box-shadow: none;
  color: var(--color-text-muted);
}

.state-active {
  transform: scale(1.03);
  z-index: 2;
  animation: pulse-glow 1.5s infinite alternate ease-in-out;
}

@keyframes pulse-glow {
  from {
    box-shadow: 0 0 6px rgba(var(--active-color-rgb), 0.4), inset 0 0 3px rgba(var(--active-color-rgb), 0.2);
    transform: scale(1.01);
  }
  to {
    box-shadow: 0 0 16px rgba(var(--active-color-rgb), 0.8), inset 0 0 6px rgba(var(--active-color-rgb), 0.4);
    transform: scale(1.04);
  }
}

.state-past {
  opacity: 0.9;
}

/* Control Bar Styling */
.timeline-controls-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--color-surface);
  border-radius: 12px;
  padding: 12px 20px;
  border: 1px solid var(--color-border);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
  margin-top: 20px;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-display);
}

.step-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: 500;
}

.step-value {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-primary);
  line-height: 1;
}

.step-divider {
  color: var(--color-border-hover);
}

.step-max {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  line-height: 1;
}

.control-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
}

.control-btn {
  transition: all 0.2s ease;
}

.control-btn:hover {
  transform: translateY(-1px);
}

.play-btn {
  transform: scale(1.1);
}

.play-btn:hover {
  transform: scale(1.15) translateY(-1px);
}

.control-icon {
  display: block;
}

.axis-label-display {
  display: flex;
  align-items: center;
}

.axis-badge {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  border: 1px solid var(--color-primary-border);
  padding: 4px 10px;
  border-radius: 99px;
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.02em;
}
</style>
