<template>
  <div class="ppt-player-container" :class="documentData.template_id" ref="containerRef">
    <template v-if="isExportMode">
      <div
        v-for="(slide, index) in documentData.slides"
        :key="`export-${index}`"
        class="slide-frame export-slide"
      >
        <div
          class="slide-shell"
          :style="slide.metadata?.background_override ? { background: slide.metadata.background_override } : undefined"
        >
          <component
            :is="resolveLayoutComponent(slide.layout)"
            v-if="resolveLayoutComponent(slide.layout)"
            :slots="slide.slots"
            :config="slide.layoutConfig"
          />
          <div v-else class="fallback-slide">
            <h3>布局组件缺失</h3>
            <p>{{ documentData.template_id }} / {{ slide.layout }}</p>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="viewer-stage">
        <div class="viewer-canvas" :style="{ transform: `scale(${scale})` }">
          <transition :name="`ppt-${currentSlide?.metadata?.transition || 'fade'}`" mode="out-in">
            <div
              :key="currentIndex"
              class="slide-frame preview-slide"
            >
              <div
                class="slide-shell"
                :style="currentSlide?.metadata?.background_override ? { background: currentSlide.metadata.background_override } : undefined"
              >
                <component
                  :is="resolveLayoutComponent(currentSlide?.layout)"
                  v-if="currentSlide && resolveLayoutComponent(currentSlide.layout)"
                  :slots="currentSlide.slots"
                  :config="currentSlide.layoutConfig"
                />
                <div v-else class="fallback-slide">
                  <h3>布局组件缺失</h3>
                  <p>{{ documentData.template_id }} / {{ currentSlide?.layout }}</p>
                </div>
              </div>
            </div>
          </transition>
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
  background: #fff;
  box-shadow:
    0 30px 60px rgba(15, 23, 42, 0.16),
    0 10px 24px rgba(15, 23, 42, 0.08);
}

.fallback-slide {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #fff1f2, #ffe4e6);
  color: #9f1239;
  text-align: center;
  gap: 12px;
}

.fallback-slide h3 {
  margin: 0;
  font-size: 34px;
  font-weight: 800;
}

.fallback-slide p {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
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

/* Transitions */
.ppt-fade-enter-active,
.ppt-fade-leave-active {
  transition: opacity 0.3s ease;
}
.ppt-fade-enter-from,
.ppt-fade-leave-to {
  opacity: 0;
}

.ppt-slide-enter-active,
.ppt-slide-leave-active {
  transition: all 0.4s ease;
}
.ppt-slide-enter-from {
  opacity: 0;
  transform: translateX(50px);
}
.ppt-slide-leave-to {
  opacity: 0;
  transform: translateX(-50px);
}

.ppt-zoom-enter-active,
.ppt-zoom-leave-active {
  transition: all 0.4s ease;
}
.ppt-zoom-enter-from {
  opacity: 0;
  transform: scale(0.95);
}
.ppt-zoom-leave-to {
  opacity: 0;
  transform: scale(1.05);
}
</style>
