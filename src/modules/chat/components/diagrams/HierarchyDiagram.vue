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
import type { HierarchyPayload } from '@/api/chat'

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
  padding: 10px 24px;
  background: #eff6ff;
  border: 2px solid #2563eb;
  border-radius: 999px;
  font-size: 16px;
  font-weight: 700;
  color: #1d4ed8;
}

.branches {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
}

.branch {
  padding: 14px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-top: 3px solid #0f766e;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
}

.branch-title {
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 700;
  color: #0f766e;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.branch-children {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 4px;
}

.branch-children li {
  padding: 3px 0 3px 14px;
  font-size: 13px;
  color: var(--c-muted, #64748b);
  line-height: 1.4;
  position: relative;
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
