<template>
  <section class="visualizer-control-bar">
    <button class="control-btn primary" :disabled="disabled" @click="handlePrimaryAction">
      <component :is="primaryIcon" class="btn-icon" />
      <span>{{ primaryLabel }}</span>
    </button>

    <button class="control-btn" :disabled="disabled || currentStepIndex === 0" @click="$emit('prev')">
      <StepBack class="btn-icon" />
      <span>上一步</span>
    </button>

    <button class="control-btn" :disabled="disabled || currentStepIndex >= events.length - 1" @click="$emit('next')">
      <StepForward class="btn-icon" />
      <span>下一步</span>
    </button>

    <button class="control-btn" :disabled="disabled" @click="$emit('reset')">
      <RotateCcw class="btn-icon" />
      <span>重置</span>
    </button>

    <div class="progress-group">
      <div class="progress-topline">
        <span class="step-count">{{ countLabel }}</span>
        <label class="speed-group">
          <span>速度</span>
          <select :value="speed" class="speed-select" @change="handleSpeedChange">
            <option :value="0.75">0.75x</option>
            <option :value="1">1x</option>
            <option :value="1.5">1.5x</option>
            <option :value="2">2x</option>
          </select>
        </label>
      </div>

      <input
        class="timeline-input"
        type="range"
        min="0"
        :max="Math.max(0, events.length - 1)"
        :value="currentStepIndex"
        :disabled="disabled"
        @input="handleSeek"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Pause, Play, RotateCcw, StepBack, StepForward } from 'lucide-vue-next'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  events: TraceEvent[]
  playing: boolean
  currentStepIndex: number
  speed: number
  finished: boolean
}>()

const emit = defineEmits<{
  play: []
  pause: []
  next: []
  prev: []
  reset: []
  'speed-change': [value: number]
  seek: [value: number]
}>()

const disabled = computed(() => props.events.length === 0)

const primaryLabel = computed(() => {
  if (props.playing) {
    return '暂停'
  }

  if (props.finished) {
    return '重新播放'
  }

  return '开始播放'
})

const primaryIcon = computed(() => (props.playing ? Pause : Play))

const countLabel = computed(() => {
  if (!props.events.length) {
    return '还没有可播放的步骤'
  }

  return `${props.currentStepIndex + 1} / ${props.events.length}`
})

function handlePrimaryAction() {
  if (disabled.value) {
    return
  }

  if (props.playing) {
    emit('pause')
    return
  }

  emit('play')
}

function handleSpeedChange(event: Event) {
  const target = event.target as HTMLSelectElement
  emit('speed-change', Number(target.value))
}

function handleSeek(event: Event) {
  const target = event.target as HTMLInputElement
  emit('seek', Number(target.value))
}
</script>

<style scoped>
.visualizer-control-bar {
  flex: 0 0 auto;
  height: 66px;
  padding: 0 20px;
  display: grid;
  grid-template-columns: auto auto auto auto minmax(280px, 1fr);
  gap: 12px;
  align-items: center;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 22px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(14px);
}

.control-btn {
  height: 36px;
  min-width: 36px;
  border-radius: 11px;
  border: 1px solid #dbe3ef;
  background: #ffffff;
  color: #334155;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 12px;
}

.control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.control-btn.primary {
  min-width: 102px;
  background: #0f172a;
  color: #ffffff;
  border-color: #0f172a;
}

.btn-icon {
  width: 15px;
  height: 15px;
}

.progress-group {
  min-width: 0;
  display: grid;
  gap: 8px;
}

.progress-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.step-count {
  font-size: 13px;
  color: #64748b;
}

.speed-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #475569;
}

.speed-select {
  height: 32px;
  padding: 0 10px;
  border-radius: 10px;
  border: 1px solid #dbe3ef;
  background: #f8fafc;
}

.timeline-input {
  width: 100%;
  accent-color: #2563eb;
}

@media (max-width: 1100px) {
  .visualizer-control-bar {
    height: auto;
    padding: 14px 20px;
    grid-template-columns: repeat(4, auto);
  }

  .progress-group {
    grid-column: 1 / -1;
  }
}

@media (max-width: 640px) {
  .visualizer-control-bar {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .control-btn {
    width: 100%;
  }

  .progress-topline {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
