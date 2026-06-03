<template>
  <div class="framework-diagram">
    <div class="center-node">{{ payload.center }}</div>
    <div class="modules-grid">
      <div v-for="mod in payload.modules" :key="mod.title" class="module-card">
        <strong class="module-title">{{ mod.title }}</strong>
        <ul class="module-items">
          <li v-for="item in mod.items" :key="item">{{ item }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { FrameworkPayload } from '@/api/chat'

defineProps<{
  payload: FrameworkPayload
}>()
</script>

<style scoped>
.framework-diagram {
  display: grid;
  gap: 16px;
}

.center-node {
  justify-self: center;
  padding: 12px 24px;
  background: #eff6ff;
  border: 2px solid #2563eb;
  border-radius: 999px;
  font-size: 18px;
  font-weight: 700;
  color: #1d4ed8;
}

.modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.module-card {
  padding: 14px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.module-title {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--c-ink, #111827);
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.module-items {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 4px;
}

.module-items li {
  padding: 3px 0;
  font-size: 13px;
  color: var(--c-muted, #64748b);
  line-height: 1.4;
}

.module-items li::before {
  content: '\00B7';
  margin-right: 6px;
  color: #94a3b8;
  font-weight: 700;
}
</style>
