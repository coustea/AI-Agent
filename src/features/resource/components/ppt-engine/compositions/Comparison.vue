<template>
  <div class="composition comparison">
    <div class="subtitle">{{ slide.key_message }}</div>
    <div class="comp-panes">
      <div class="comp-pane left-pane ppt-card">
        <div class="pane-title">COMPARAND A</div>
        <div class="elements-list">
          <div v-for="el in slide.slots.left || []" :key="el.content || ''" class="comp-item">
            <div class="item-title">{{ el.content }}</div>
            <p v-if="el.properties && !Array.isArray(el.properties)" class="item-desc">{{ el.properties.description || '' }}</p>
          </div>
        </div>
      </div>
      <div class="vs-divider">VS</div>
      <div class="comp-pane right-pane ppt-card">
        <div class="pane-title">COMPARAND B</div>
        <div class="elements-list">
          <div v-for="el in slide.slots.right || []" :key="el.content || ''" class="comp-item">
            <div class="item-title">{{ el.content }}</div>
            <p v-if="el.properties && !Array.isArray(el.properties)" class="item-desc">{{ el.properties.description || '' }}</p>
          </div>
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
.comparison {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 40px 60px;
  box-sizing: border-box;
}
.subtitle {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--ppt-text-secondary);
  margin-bottom: 24px;
  border-left: 3px solid var(--ppt-accent);
  padding-left: 12px;
}
.comp-panes {
  display: flex;
  align-items: stretch;
  gap: 20px;
  flex: 1;
  position: relative;
}
.comp-pane {
  flex: 1;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.pane-title {
  font-size: 0.8rem;
  font-weight: 800;
  color: var(--ppt-accent);
  letter-spacing: 0.1em;
  border-bottom: 2px solid var(--ppt-border);
  padding-bottom: 8px;
}
.elements-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.comp-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.item-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--ppt-text-primary);
}
.item-desc {
  font-size: 0.85rem;
  color: var(--ppt-text-secondary);
  line-height: 1.4;
  margin: 0;
}
.vs-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--ppt-accent-gradient);
  color: #fff;
  font-weight: 800;
  font-size: 0.85rem;
  align-self: center;
  box-shadow: 0 4px 10px rgba(0,0,0,0.1);
  z-index: 10;
}
</style>
