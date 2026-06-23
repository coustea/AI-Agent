<template>
  <div class="composition concept-breakdown">
    <div class="subtitle">{{ slide.key_message }}</div>
    <div class="grid-container" :style="gridStyle">
      <div v-for="el in slide.elements" :key="el.content || ''" class="breakdown-card ppt-card">
        <div v-if="el.label" class="card-label">{{ el.label }}</div>
        <div class="card-title">{{ el.content }}</div>
        <div v-if="el.properties && typeof el.properties === 'object' && !Array.isArray(el.properties)" class="card-properties">
          <div v-for="(val, key) in el.properties" :key="key" class="prop-row">
            <span class="prop-key">{{ key }}:</span>
            <span class="prop-val">{{ val }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ResolvedSlide } from '../model/resolvedSlide'

const props = defineProps<{ slide: ResolvedSlide }>()

const gridStyle = computed(() => {
  const count = props.slide.elements.length
  if (count <= 3) {
    return { gridTemplateColumns: `repeat(${count}, 1fr)` }
  }
  const cols = Math.ceil(count / 2)
  return { gridTemplateColumns: `repeat(${cols}, 1fr)` }
})
</script>

<style scoped>
.concept-breakdown {
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
.grid-container {
  display: grid;
  gap: 20px;
  flex: 1;
}
.breakdown-card {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 20px;
}
.card-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--ppt-accent);
  text-transform: uppercase;
  margin-bottom: 8px;
}
.card-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--ppt-text-primary);
  line-height: 1.4;
}
.card-properties {
  margin-top: 12px;
  font-size: 0.85rem;
  border-top: 1px solid var(--ppt-border);
  padding-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.prop-row {
  display: flex;
  justify-content: space-between;
}
.prop-key {
  color: var(--ppt-text-secondary);
}
.prop-val {
  font-weight: 600;
  color: var(--ppt-text-primary);
}
</style>
