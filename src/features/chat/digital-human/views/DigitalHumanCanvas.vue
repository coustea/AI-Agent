<template>
  <div class="digital-human-canvas">
    <div class="avatar-background"></div>
    <div ref="videoContainer" :class="['video-container', { 'is-chroma-active': chromaReady }]"></div>
    <canvas ref="chromaCanvas" :class="['chroma-canvas', { active: chromaReady }]"></canvas>

    <!-- Not ready states (connecting / disconnected) -->
    <div v-if="!isReady" class="placeholder">
      <template v-if="state === 'error'">
        <Avatar class="placeholder-icon error-icon" />
        <p class="error-message">{{ errorMessage || '数字人服务连接失败' }}</p>
        <button class="reconnect-btn" @click="$emit('reconnect')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          重新连接
        </button>
      </template>
      <template v-else-if="isConnected">
        <div class="spinner"></div>
        <p>等待数字人上线...</p>
      </template>
      <template v-else>
        <Avatar class="placeholder-icon" />
        <p>数字人未连接</p>
        <button class="reconnect-btn" @click="$emit('reconnect')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          重新连接
        </button>
      </template>
    </div>

    <!-- Audio enable button -->
    <div v-if="isReady && !audioEnabled" class="audio-enable-overlay">
      <button class="audio-enable-btn" @click="$emit('enable-audio')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
        </svg>
        点击启用音频
      </button>
    </div>

    <!-- Disconnect button + idle countdown -->
    <div v-if="isConnected" class="disconnect-bar">
      <span v-if="idleCountdown > 0 && idleCountdown <= 10" class="idle-hint">
        {{ idleCountdown }}s 后自动断开
      </span>
      <button class="disconnect-btn" @click="$emit('disconnect')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
        断开连接
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { PhUser as Avatar } from '@phosphor-icons/vue'
import { applyGreenScreenAlpha } from '../model/chromaKey'
import type { DigitalHumanStateType } from '../model/digital-human'

const props = defineProps<{
  isReady: boolean
  isConnected: boolean
  state: DigitalHumanStateType
  errorMessage?: string | null
  audioEnabled: boolean
  idleCountdown: number
}>()

// 事件：启用音频 / 断开 / 重连
defineEmits<{
  'enable-audio': []
  'disconnect': []
  'reconnect': []
}>()

const videoContainer = ref<HTMLElement | null>(null)
const chromaCanvas = ref<HTMLCanvasElement | null>(null)
const chromaReady = ref(false)
let chromaObserver: MutationObserver | null = null
let chromaFrameId: number | null = null
let sourceVideo: HTMLVideoElement | null = null
let workCanvas: HTMLCanvasElement | null = null
let workContext: CanvasRenderingContext2D | null = null

// 确保绿幕抠像用的离屏 Canvas 已创建
const ensureWorkCanvas = () => {
  if (!workCanvas) {
    workCanvas = document.createElement('canvas')
    workContext = workCanvas.getContext('2d', { willReadFrequently: true })
  }
  return workContext
}

const resizeCanvas = (canvas: HTMLCanvasElement, width: number, height: number) => {
  if (canvas.width !== width) canvas.width = width
  if (canvas.height !== height) canvas.height = height
  if (workCanvas && workCanvas.width !== width) workCanvas.width = width
  if (workCanvas && workCanvas.height !== height) workCanvas.height = height
}

// 逐帧渲染绿幕抠像：读取视频帧 → 去绿 → 绘制到输出 Canvas
const renderChromaFrame = () => {
  const video = sourceVideo
  const canvas = chromaCanvas.value
  const context = canvas?.getContext('2d')
  const work = ensureWorkCanvas()

  if (video && canvas && context && work && video.readyState >= 2) {
    const width = video.videoWidth || 720
    const height = video.videoHeight || 1280
    resizeCanvas(canvas, width, height)

    try {
      work.drawImage(video, 0, 0, width, height)
      const frame = work.getImageData(0, 0, width, height)
      applyGreenScreenAlpha(frame.data)
      work.putImageData(frame, 0, 0)
      context.clearRect(0, 0, width, height)
      context.drawImage(work.canvas, 0, 0)
      chromaReady.value = true
    } catch (error) {
      chromaReady.value = false
      console.warn('[DH] chroma key rendering failed:', error)
    }
  }

  chromaFrameId = window.requestAnimationFrame(renderChromaFrame)
}

// 查找 video 元素并启动绿幕渲染循环
const startChromaKey = () => {
  const video = videoContainer.value?.querySelector('video')
  if (!(video instanceof HTMLVideoElement)) return
  if (sourceVideo !== video) {
    sourceVideo = video
    sourceVideo.playsInline = true
  }
  if (chromaFrameId === null) {
    chromaFrameId = window.requestAnimationFrame(renderChromaFrame)
  }
}

// Expose the container ref so parent can pass it to composable.setPlayerContainer
defineExpose({
  getContainer: () => videoContainer.value,
})

// 组件挂载后：启动绿幕 + 监听 DOM 变化
onMounted(() => {
  nextTick(() => {
    startChromaKey()
    if (videoContainer.value) {
      chromaObserver = new MutationObserver(startChromaKey)
      chromaObserver.observe(videoContainer.value, { childList: true, subtree: true })
    }
  })
})

// 组件卸载前：取消动画帧、断开 MutationObserver、销毁子元素
onBeforeUnmount(() => {
  if (chromaFrameId !== null) {
    window.cancelAnimationFrame(chromaFrameId)
    chromaFrameId = null
  }
  chromaObserver?.disconnect()
  chromaObserver = null
  sourceVideo = null
  if (videoContainer.value) {
    while (videoContainer.value.firstChild) {
      videoContainer.value.removeChild(videoContainer.value.firstChild)
    }
  }
})
</script>

<style scoped>
.digital-human-canvas {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.avatar-background {
  position: absolute;
  inset: 0;
  background: url('/static/avatar-background-bookshelf.jpg') center / cover no-repeat;
  z-index: 0;
}

.video-container {
  width: 100%;
  height: 100%;
  position: absolute;
  inset: 0;
  z-index: 1;
}

.video-container.is-chroma-active {
  opacity: 0;
  pointer-events: none;
}

.video-container :deep(video) {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain !important;
}

.chroma-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  opacity: 0;
  pointer-events: none;
  z-index: 2;
}

.chroma-canvas.active {
  opacity: 1;
}

.placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: var(--color-text-faint);
  font-size: var(--text-sm);
  z-index: 3;
}

.placeholder-icon {
  font-size: 3rem;
  opacity: 0.4;
}

.error-icon {
  color: var(--color-danger);
  opacity: 0.75;
}

.error-message {
  max-width: min(520px, 78vw);
  margin: 0;
  color: var(--color-danger);
  text-align: center;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid rgba(79, 70, 229, 0.2);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.reconnect-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: var(--space-2) var(--space-5);
  background: var(--color-primary);
  color: var(--color-surface);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  transition: all var(--transition-base);
}

.reconnect-btn:hover {
  background: var(--color-primary-hover);
  transform: scale(1.05);
}

.audio-enable-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
}

.audio-enable-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  background: rgba(79, 70, 229, 0.9);
  color: var(--color-surface);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.4);
  transition: all var(--transition-base);
  animation: pulse-btn 2s infinite;
}

.audio-enable-btn:hover {
  background: rgba(79, 70, 229, 1);
  transform: scale(1.05);
}

@keyframes pulse-btn {
  0%, 100% { box-shadow: 0 4px 16px rgba(79, 70, 229, 0.4); }
  50% { box-shadow: 0 4px 24px rgba(79, 70, 229, 0.8); }
}

.disconnect-bar {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  z-index: 10;
}

.idle-hint {
  font-size: var(--text-xs);
  color: var(--color-warning);
  background: var(--color-warning-soft);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  font-weight: var(--weight-medium);
  animation: idle-pulse 1s infinite;
}

@keyframes idle-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.disconnect-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  background: rgba(239, 68, 68, 0.85);
  color: var(--color-surface);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  transition: all var(--transition-base);
  backdrop-filter: blur(4px);
}

.disconnect-btn:hover {
  background: rgba(239, 68, 68, 1);
  transform: scale(1.05);
}
</style>
