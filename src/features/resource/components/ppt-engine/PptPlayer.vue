<template>
  <div class="ppt-player-container" :class="`theme-${documentData.theme_id}`" ref="containerRef">
    <template v-if="isExportMode">
      <div
        v-for="(slide, index) in documentData.slides"
        :key="`export-${index}`"
        class="slide-frame export-slide"
      >
        <div class="slide-shell ppt-grid-bg">
          <!-- 顶部横向进度条 -->
          <div class="slide-progress-tracker">
            <div 
              v-for="(_, idx) in documentData.slides" 
              :key="idx"
              class="tracker-dot"
              :class="{ active: idx === index, passed: idx < index }"
            ></div>
          </div>

          <div class="slide-header">
            <div>
              <div class="slide-title">{{ slide.title }}</div>
              <div v-if="slide.subtitle" class="slide-subtitle">{{ slide.subtitle }}</div>
            </div>
            <div class="slide-role-badge">
              <span class="role-icon">✦</span>
              <span class="role-text">{{ slide.role }}</span>
            </div>
          </div>

          <div class="slide-content-wrapper">
            <component
              :is="resolveLayoutComponent(slide.layout)"
              :slide="slide"
              :slots="slide.slots"
            />
          </div>

          <div class="slide-footer">
            <div class="slide-takeaway-container">
              <span class="takeaway-tag">要点</span>
              <div class="slide-takeaway">{{ slide.takeaway }}</div>
            </div>
            <div class="slide-index">{{ index + 1 }} / {{ documentData.slides.length }}</div>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="viewer-stage">
        <div class="viewer-canvas" :style="{ transform: `scale(${scale})` }">
          <div class="slide-frame preview-slide">
            <div v-if="currentSlide" class="slide-shell ppt-grid-bg">
              <!-- 顶部横向进度条 -->
              <div class="slide-progress-tracker">
                <div 
                  v-for="(_, idx) in documentData.slides" 
                  :key="idx"
                  class="tracker-dot"
                  :class="{ active: idx === currentIndex, passed: idx < currentIndex }"
                  @click="jumpToSlide(idx)"
                ></div>
              </div>

              <div class="slide-header">
                <div>
                  <div class="slide-title">{{ currentSlide.title }}</div>
                  <div v-if="currentSlide.subtitle" class="slide-subtitle">{{ currentSlide.subtitle }}</div>
                </div>
                <div class="slide-role-badge">
                  <span class="role-icon">✦</span>
                  <span class="role-text">{{ currentSlide.role }}</span>
                </div>
              </div>

              <div class="slide-content-wrapper">
                <component
                  :is="resolveLayoutComponent(currentSlide.layout)"
                  :slide="currentSlide"
                  :slots="currentSlide.slots"
                />
              </div>

              <div class="slide-footer">
                <div class="slide-takeaway-container">
                  <span class="takeaway-tag">要点</span>
                  <div class="slide-takeaway">{{ currentSlide.takeaway }}</div>
                </div>
                <div class="slide-index">{{ currentIndex + 1 }} / {{ documentData.slides.length }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="controls">
        <button @click="prevSlide" :disabled="currentIndex === 0" class="control-btn prev-btn">
          <span>上一页</span>
        </button>
        <span class="page-indicator">{{ currentIndex + 1 }} / {{ documentData.slides.length }}</span>
        <button @click="nextSlide" :disabled="currentIndex === documentData.slides.length - 1" class="control-btn next-btn">
          <span>下一页</span>
        </button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import type { PPTDocument } from './types/ppt'
import './assets/themes.css'
import { resolveLayoutComponent } from './components/layouts/registry'

const props = defineProps<{
  documentData: PPTDocument
  isExportMode?: boolean
}>()

const currentIndex = ref(0)
const containerRef = ref<HTMLElement | null>(null)
const scale = ref(1)
let resizeObserver: ResizeObserver | null = null

const currentSlide = computed(() => props.documentData.slides[currentIndex.value])

const prevSlide = () => {
  if (currentIndex.value > 0) currentIndex.value -= 1
}

const nextSlide = () => {
  if (currentIndex.value < props.documentData.slides.length - 1) currentIndex.value += 1
}

const jumpToSlide = (idx: number) => {
  currentIndex.value = idx
}

const handleKeyDown = (event: KeyboardEvent) => {
  if (!currentSlide.value) return
  if (event.key === 'ArrowRight' || event.key === 'PageDown') nextSlide()
  if (event.key === 'ArrowLeft' || event.key === 'PageUp') prevSlide()
}

const calculateScale = () => {
  if (!containerRef.value || props.isExportMode) return
  const { width, height } = containerRef.value.getBoundingClientRect()
  if (width < 200 || height < 200) return

  const horizontalPadding = 56
  const verticalPadding = 96
  const controlBarHeight = 84
  const availableWidth = Math.max(width - horizontalPadding, 1)
  const availableHeight = Math.max(height - verticalPadding - controlBarHeight, 1)

  scale.value = Math.min(availableWidth / 1280, availableHeight / 720, 1)
}

onMounted(() => {
  calculateScale()
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => calculateScale())
    resizeObserver.observe(containerRef.value)
  }
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
.ppt-player-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  background: radial-gradient(circle at top left, rgba(37, 99, 235, 0.05), transparent 35%),
              linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%);
}

.theme-logic-blue.ppt-player-container {
  background: radial-gradient(circle at top left, rgba(56, 189, 248, 0.08), transparent 35%),
              linear-gradient(180deg, #020617 0%, #0b1329 100%);
}

.viewer-stage {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 24px 88px;
}

.viewer-canvas {
  width: 1280px;
  height: 720px;
  position: relative;
  transform-origin: center center;
}

.slide-frame {
  width: 1280px;
  height: 720px;
}

.preview-slide {
  position: absolute;
  inset: 0;
}

.export-slide {
  position: relative;
  page-break-after: always;
  margin-bottom: 24px;
}

.slide-shell {
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: var(--ppt-radius-lg);
  background: var(--ppt-bg-primary);
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.1),
              0 1px 3px rgba(15, 23, 42, 0.05);
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  position: relative;
  border: 1px solid var(--ppt-border);
}

/* 顶部进度条 */
.slide-progress-tracker {
  display: flex;
  width: 100%;
  padding: 10px 36px 0;
  gap: 6px;
  z-index: 10;
}

.tracker-dot {
  flex: 1;
  height: 4px;
  border-radius: 99px;
  background: var(--ppt-border);
  cursor: pointer;
  transition: all 0.25s ease;
}

.tracker-dot.active {
  background: var(--ppt-accent);
  box-shadow: 0 0 8px rgba(37, 99, 235, 0.3);
}

.tracker-dot.passed {
  background: var(--ppt-accent);
  opacity: 0.4;
}

.slide-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 36px 8px;
  border-bottom: 1px dashed var(--ppt-border);
  z-index: 5;
}

.slide-title {
  font-size: 2.1rem;
  font-weight: 800;
  line-height: 1.2;
  color: var(--ppt-text-primary);
  letter-spacing: -0.02em;
}

.slide-subtitle {
  margin-top: 6px;
  font-size: 1.05rem;
  line-height: 1.5;
  color: var(--ppt-text-secondary);
}

.slide-role-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  background: var(--ppt-badge-bg);
  border: 1px solid var(--ppt-border);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02);
}

.role-icon {
  color: var(--ppt-accent);
  font-size: 0.9rem;
}

.role-text {
  font-size: 0.75rem;
  font-weight: 800;
  color: var(--ppt-badge-text);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.slide-content-wrapper {
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.slide-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 8px 36px 20px;
  border-top: 1px dashed var(--ppt-border);
  z-index: 5;
}

.slide-takeaway-container {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.takeaway-tag {
  font-size: 0.7rem;
  font-weight: 800;
  color: #ffffff;
  background: var(--ppt-accent-gradient);
  padding: 3px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.slide-takeaway {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--ppt-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.slide-index {
  flex-shrink: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--ppt-text-secondary);
  font-family: var(--ppt-font-mono);
}

.controls {
  position: absolute;
  left: 50%;
  bottom: 18px;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 10px 18px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(12px);
  z-index: 100;
  border: 1px solid rgba(255, 255, 255, 0.4);
}

.theme-logic-blue .controls {
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.control-btn {
  border: none;
  background: transparent;
  color: #334155;
  font-size: 14px;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.theme-logic-blue .control-btn {
  color: #94a3b8;
}

.control-btn:hover:not(:disabled) {
  background: rgba(37, 99, 235, 0.08);
  color: #1c52d5;
}

.theme-logic-blue .control-btn:hover:not(:disabled) {
  background: rgba(56, 189, 248, 0.12);
  color: #38bdf8;
}

.control-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.page-indicator {
  min-width: 60px;
  text-align: center;
  font-size: 14px;
  font-weight: 800;
  color: #0f172a;
  font-family: var(--ppt-font-mono);
}

.theme-logic-blue .page-indicator {
  color: #f8fafc;
}
</style>
