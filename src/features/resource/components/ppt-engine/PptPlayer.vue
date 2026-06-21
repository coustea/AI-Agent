<template>
  <div class="ppt-player-container" :class="`theme-${documentData.theme_id}`" ref="containerRef">
    <template v-if="isExportMode">
      <div
        v-for="(slide, index) in documentData.slides"
        :key="`export-${index}`"
        class="slide-frame export-slide"
      >
        <div class="slide-shell">
          <div class="slide-header">
            <div>
              <div class="slide-title">{{ slide.title }}</div>
              <div v-if="slide.subtitle" class="slide-subtitle">{{ slide.subtitle }}</div>
            </div>
            <div class="slide-role">{{ slide.role }}</div>
          </div>
          <component
            :is="resolveLayoutComponent(slide.layout)"
            :slide="slide"
            :slots="slide.slots"
          />
          <div class="slide-footer">
            <div class="slide-takeaway">{{ slide.takeaway }}</div>
            <div class="slide-index">{{ index + 1 }} / {{ documentData.slides.length }}</div>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="viewer-stage">
        <div class="viewer-canvas" :style="{ transform: `scale(${scale})` }">
          <div class="slide-frame preview-slide">
            <div v-if="currentSlide" class="slide-shell">
              <div class="slide-header">
                <div>
                  <div class="slide-title">{{ currentSlide.title }}</div>
                  <div v-if="currentSlide.subtitle" class="slide-subtitle">{{ currentSlide.subtitle }}</div>
                </div>
                <div class="slide-role">{{ currentSlide.role }}</div>
              </div>
              <component
                :is="resolveLayoutComponent(currentSlide.layout)"
                :slide="currentSlide"
                :slots="currentSlide.slots"
              />
              <div class="slide-footer">
                <div class="slide-takeaway">{{ currentSlide.takeaway }}</div>
                <div class="slide-index">{{ currentIndex + 1 }} / {{ documentData.slides.length }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="controls">
        <button @click="prevSlide" :disabled="currentIndex === 0" class="control-btn">上一页</button>
        <span class="page-indicator">{{ currentIndex + 1 }} / {{ documentData.slides.length }}</span>
        <button @click="nextSlide" :disabled="currentIndex === documentData.slides.length - 1" class="control-btn">下一页</button>
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
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.1), transparent 28%),
    radial-gradient(circle at bottom right, rgba(15, 23, 42, 0.08), transparent 30%),
    linear-gradient(180deg, #e7edf7 0%, #d8dde6 100%);
}

.viewer-stage {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px 28px 96px;
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
  border-radius: 28px;
  background: var(--ppt-bg-primary);
  box-shadow:
    0 30px 60px rgba(15, 23, 42, 0.16),
    0 10px 24px rgba(15, 23, 42, 0.08);
  display: grid;
  grid-template-rows: auto 1fr auto;
}

.slide-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 36px 0;
}

.slide-title {
  font-size: 2rem;
  font-weight: 800;
  line-height: 1.15;
  color: var(--ppt-text-primary);
}

.slide-subtitle {
  margin-top: 8px;
  font-size: 1rem;
  line-height: 1.5;
  color: var(--ppt-text-secondary);
}

.slide-role {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  background: var(--ppt-badge-bg);
  color: var(--ppt-badge-text);
  border: 1px solid var(--ppt-border);
}

.slide-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 0 36px 24px;
}

.slide-takeaway {
  flex: 1;
  min-width: 0;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.5;
  color: var(--ppt-text-secondary);
}

.slide-index {
  flex-shrink: 0;
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--ppt-text-secondary);
}

.controls {
  position: absolute;
  left: 50%;
  bottom: 18px;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 12px 20px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.14);
  backdrop-filter: blur(14px);
  z-index: 10;
}

.control-btn {
  border: none;
  background: transparent;
  color: #334155;
  font-size: 15px;
  font-weight: 600;
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.control-btn:hover:not(:disabled) {
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
}

.control-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.page-indicator {
  min-width: 64px;
  text-align: center;
  font-size: 15px;
  font-weight: 800;
  color: #0f172a;
}
</style>
