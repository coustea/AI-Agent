<template>
  <div class="composition protocol-stack">
    <div class="info-pane">
      <div class="subtitle">{{ slide.key_message }}</div>
      <div class="details-list">
        <div v-for="el in slide.elements" :key="el.content || ''" class="detail-item">
          <span class="bullet">✦</span>
          <span class="detail-text" v-if="el.properties && !Array.isArray(el.properties)">
            <strong>{{ el.content }}:</strong> {{ el.properties.description || '' }}
          </span>
          <span class="detail-text" v-else>{{ el.content }}</span>
        </div>
      </div>
    </div>
    <div class="stack-pane">
      <div class="stack-container">
        <div
          v-for="(el, idx) in slide.elements"
          :key="el.content || ''"
          class="stack-layer ppt-card"
          :style="{
            transform: `translateY(${idx * -4}px)`,
            zIndex: slide.elements.length - idx,
            opacity: 1 - (idx * 0.08)
          }"
        >
          <span class="layer-num">L{{ slide.elements.length - idx }}</span>
          <span class="layer-name">{{ el.content }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ResolvedSlide } from '../model/resolvedSlide'
defineProps<{ slide: ResolvedSlide }>()
</script>

<style scoped>
.protocol-stack {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 40px;
  height: 100%;
  padding: 40px 60px;
  box-sizing: border-box;
  align-items: center;
}
.info-pane {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.subtitle {
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--ppt-text-secondary);
  border-left: 3px solid var(--ppt-accent);
  padding-left: 12px;
}
.details-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.detail-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.bullet {
  color: var(--ppt-accent);
  font-weight: bold;
}
.detail-text {
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--ppt-text-secondary);
}
.stack-pane {
  display: flex;
  align-items: center;
  justify-content: center;
}
.stack-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 280px;
}
.stack-layer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-left: 4px solid var(--ppt-accent);
  margin-bottom: 8px;
  transition: transform 0.2s;
}
.layer-num {
  font-size: 0.8rem;
  font-weight: 800;
  color: var(--ppt-accent);
}
.layer-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--ppt-text-primary);
}
</style>
