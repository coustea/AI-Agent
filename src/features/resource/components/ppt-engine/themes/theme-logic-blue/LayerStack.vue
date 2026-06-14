<template>
  <div class="logic-blue-slide">
    <header class="slide-header">
      <div>
        <div class="eyebrow">STACK MODEL</div>
        <h2 class="slide-title">{{ data.title }}</h2>
      </div>
      <div class="header-chip">{{ data.layers.length }} Layers</div>
    </header>

    <div class="content-grid">
      <div class="stack-panel">
        <div
          v-for="(layer, index) in data.layers"
          :key="layer.level_name"
          class="stack-card"
          :class="{ active: activeIndex === index }"
          :style="{ top: `${index * 76}px`, zIndex: `${data.layers.length - index}` }"
          @mouseenter="activeIndex = index"
        >
          <div class="stack-index">{{ String(index + 1).padStart(2, '0') }}</div>
          <div class="stack-name">{{ layer.level_name }}</div>
        </div>
      </div>

      <div class="detail-panel" v-if="activeLayer">
        <div class="detail-card">
          <div class="detail-title-row">
            <h3 class="detail-title">{{ activeLayer.level_name }}</h3>
            <div class="detail-dot"></div>
          </div>
          <p class="detail-description">{{ activeLayer.description }}</p>

          <div v-if="activeLayer.protocols?.length" class="tag-block">
            <div class="tag-label">Protocols</div>
            <div class="tag-list">
              <span v-for="protocol in activeLayer.protocols" :key="protocol" class="tag">{{ protocol }}</span>
            </div>
          </div>

          <div v-if="activeLayer.components?.length" class="tag-block">
            <div class="tag-label">Components</div>
            <div class="tag-list">
              <span v-for="component in activeLayer.components" :key="component" class="tag">{{ component }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { LayerStackData } from '../../types/ppt'

const props = defineProps<{
  data: LayerStackData
}>()

const activeIndex = ref(0)
const activeLayer = computed(() => props.data.layers[activeIndex.value] ?? props.data.layers[0])
</script>

<style scoped>
.logic-blue-slide {
  width: 100%;
  height: 100%;
  padding: 56px 64px;
  box-sizing: border-box;
  color: #eff6ff;
  background:
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.16), transparent 28%),
    linear-gradient(180deg, #091527 0%, #0f1d35 100%);
  font-family: "Avenir Next", "Segoe UI", sans-serif;
}

.slide-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 28px;
}

.eyebrow {
  color: #7dd3fc;
  font-size: 12px;
  letter-spacing: 2px;
  font-weight: 800;
  margin-bottom: 10px;
}

.slide-title {
  margin: 0;
  font-size: 40px;
  line-height: 1.1;
  font-weight: 800;
}

.header-chip {
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(125, 211, 252, 0.12);
  color: #bae6fd;
  font-size: 13px;
  font-weight: 700;
}

.content-grid {
  height: calc(100% - 110px);
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: 28px;
}

.stack-panel {
  position: relative;
  border-radius: 28px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.66), rgba(15, 23, 42, 0.32));
  border: 1px solid rgba(125, 211, 252, 0.12);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.stack-card {
  position: absolute;
  left: 42px;
  right: 42px;
  height: 108px;
  border-radius: 22px;
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 0 26px;
  border: 1px solid rgba(125, 211, 252, 0.12);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.24), rgba(14, 165, 233, 0.14));
  box-shadow: 0 18px 32px rgba(2, 6, 23, 0.22);
  transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}

.stack-card.active {
  transform: translateX(12px);
  border-color: rgba(125, 211, 252, 0.36);
  box-shadow: 0 22px 38px rgba(14, 165, 233, 0.18);
}

.stack-index {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #7dd3fc;
  font-weight: 800;
  font-family: "JetBrains Mono", monospace;
}

.stack-name {
  font-size: 24px;
  font-weight: 700;
  color: #f8fbff;
}

.detail-panel {
  min-width: 0;
}

.detail-card {
  height: 100%;
  border-radius: 28px;
  padding: 32px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(226, 232, 240, 0.92));
  color: #0f172a;
  box-shadow: 0 24px 44px rgba(2, 6, 23, 0.2);
}

.detail-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.detail-title {
  margin: 0;
  font-size: 30px;
  line-height: 1.1;
  font-weight: 800;
}

.detail-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: linear-gradient(180deg, #38bdf8, #2563eb);
}

.detail-description {
  margin: 0 0 24px;
  font-size: 18px;
  line-height: 1.65;
  color: #334155;
}

.tag-block + .tag-block {
  margin-top: 18px;
}

.tag-label {
  margin-bottom: 10px;
  font-size: 13px;
  letter-spacing: 1.6px;
  color: #2563eb;
  text-transform: uppercase;
  font-weight: 800;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tag {
  padding: 8px 12px;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 14px;
  font-weight: 700;
}
</style>
