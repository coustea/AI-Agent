<template>
  <div class="hierarchy-diagram">
    <div class="root-node">{{ payload.root }}</div>
    <div class="branches">
      <div v-for="branch in payload.branches" :key="branch.title" class="branch">
        <div class="branch-title">{{ branch.title }}</div>
        <ul class="branch-children">
          <li v-for="child in branch.children" :key="child">{{ child }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { HierarchyPayload } from '@/chat/types/chat'

defineProps<{
  payload: HierarchyPayload
}>()
</script>

<style scoped>
.hierarchy-diagram {
  display: grid;
  gap: 16px;
}

.root-node {
  justify-self: center;
  padding: 12px 28px;
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.9) 0%, rgba(219, 234, 254, 0.5) 100%);
  border: 2px solid rgba(59, 130, 246, 0.5);
  border-radius: 999px;
  font-size: 16px;
  font-weight: 800;
  color: #1d4ed8;
  box-shadow: 0 4px 10px rgba(59, 130, 246, 0.15);
  position: relative;
  z-index: 2;
}

.branches {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.branch {
  padding: 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-top: 4px solid #0d9488;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  transition: transform 0.3s ease, box-shadow 0.3s ease, border-top-color 0.3s ease;
}

.branch:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
  border-top-color: #14b8a6;
}

.branch-title {
  margin-bottom: 10px;
  font-size: 15px;
  font-weight: 800;
  color: #0f766e;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
  overflow-wrap: break-words;
  word-break: break-all;
}

.branch-children {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 4px;
}

.branch-children li {
  padding: 4px 0 4px 16px;
  font-size: 13px;
  color: var(--c-muted, #64748b);
  line-height: 1.5;
  position: relative;
  overflow-wrap: break-words;
  word-break: break-all;
}

.branch-children li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 9px;
  width: 6px;
  height: 6px;
  background: #99f6e4;
  border: 1px solid #0f766e;
  border-radius: 50%;
}
</style>
