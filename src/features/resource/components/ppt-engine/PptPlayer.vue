<template>
  <div class="ppt-player-wrapper" :class="`theme-${documentData.theme_id}`">
    <!-- Export Mode: Render all slides vertically -->
    <template v-if="isExportMode">
      <div
        v-for="(slide, index) in documentData.slides"
        :key="`export-${index}`"
        class="slide-frame export-slide"
      >
        <div class="slide-shell ppt-grid-bg">
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
            <DynamicSlotLayout :layout="slide.layout" :slots="slide.slots" />
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

    <!-- Normal Mode: Interactive Reveal.js presentation -->
    <template v-else>
      <div class="reveal" ref="deckRef">
        <div class="slides">
          <section
            v-for="(slide, index) in documentData.slides"
            :key="slide.id"
            class="slide-frame"
          >
            <div class="slide-shell ppt-grid-bg">
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
                <DynamicSlotLayout :layout="slide.layout" :slots="slide.slots" />
              </div>

              <div class="slide-footer">
                <div class="slide-takeaway-container">
                  <span class="takeaway-tag">要点</span>
                  <div class="slide-takeaway">{{ slide.takeaway }}</div>
                </div>
                <div class="slide-index">{{ index + 1 }} / {{ documentData.slides.length }}</div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import Reveal from 'reveal.js'
import 'reveal.js/dist/reveal.css'
import type { PPTDocument } from './types/ppt'
import './assets/themes.css'
import DynamicSlotLayout from './components/layouts/DynamicSlotLayout.vue'

const props = defineProps<{
  documentData: PPTDocument
  isExportMode?: boolean
}>()

const deckRef = ref<HTMLElement | null>(null)
let deckInstance: any = null

onMounted(() => {
  if (props.isExportMode || !deckRef.value) return

  deckInstance = new Reveal(deckRef.value, {
    embedded: true,
    keyboard: true,
    controls: true,
    progress: true,
    center: true,
    hash: false,
    respondToHashChanges: false,
    history: false,
    transition: 'slide',
    width: 1280,
    height: 720,
    margin: 0.05,
    minScale: 0.2,
    maxScale: 2.0,
  })

  deckInstance.initialize()
})

onBeforeUnmount(() => {
  if (deckInstance) {
    try {
      deckInstance.destroy()
    } catch (e) {
      console.warn('[Reveal.js] Destroy error:', e)
    }
    deckInstance = null
  }
})
</script>

<style scoped>
.ppt-player-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

/* Reveal.js Container Styling overrides */
.reveal {
  width: 100%;
  height: 100%;
  background: radial-gradient(circle at top left, rgba(37, 99, 235, 0.05), transparent 35%),
              linear-gradient(180deg, #f1f5f9 0%, #e2e8f0 100%);
  color: var(--ppt-text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}

.theme-logic-blue .reveal {
  background: radial-gradient(circle at top left, rgba(14, 165, 233, 0.06), transparent 40%),
              linear-gradient(180deg, #f0f7ff 0%, #e0f2fe 100%);
}

.reveal :deep(.slides) {
  text-align: left;
}

/* Ensure Reveal.js sections are sized exactly to slide dimensions and have no padding */
.reveal :deep(section) {
  padding: 0 !important;
  margin: 0 !important;
  box-sizing: border-box;
}

.slide-frame {
  width: 1280px;
  height: 720px;
  box-sizing: border-box;
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
  grid-template-rows: auto 1fr auto;
  position: relative;
  border: 1px solid var(--ppt-border);
  box-sizing: border-box;
}

.slide-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 36px 8px;
  border-bottom: 1px dashed var(--ppt-border);
  z-index: 5;
  box-sizing: border-box;
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
  box-sizing: border-box;
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

/* Custom styling for Reveal.js progress and controls to fit our brand */
.reveal :deep(.progress) {
  height: 6px !important;
  color: var(--ppt-accent) !important;
}

.reveal :deep(.progress span) {
  background: var(--ppt-accent-gradient) !important;
}

.reveal :deep(.controls-arrow) {
  color: var(--ppt-accent) !important;
}

/* Grid texture background */
.ppt-grid-bg {
  background-image: radial-gradient(rgba(148, 163, 184, 0.12) 1px, transparent 1px);
  background-size: 20px 20px;
}
</style>
