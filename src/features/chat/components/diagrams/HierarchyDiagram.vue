<template>
  <div class="hierarchy-diagram">
    <div class="tree-container">
      <!-- Root Node -->
      <div class="root-wrapper">
        <div class="root-node">
          <div class="root-glow"></div>
          <span>{{ payload.root }}</span>
        </div>
      </div>
      
      <!-- Connecting Trunk -->
      <div class="tree-trunk"></div>
      
      <!-- Branches Row -->
      <div class="branches-container">
        <!-- Horizontal Top Connector spanning all branches -->
        <div class="branches-connector"></div>
        
        <div class="branches-row">
          <div v-for="(branch, idx) in payload.branches" :key="branch.title" class="branch-col" :class="`theme-${idx % 4}`">
            <!-- Vertical Drop to Branch -->
            <div class="branch-drop"></div>
            
            <div class="branch-card">
              <div class="branch-title">
                <span class="branch-dot"></span>
                {{ branch.title }}
              </div>
              <ul class="branch-children">
                <li v-for="child in branch.children" :key="child">{{ child }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { HierarchyPayload } from '@/features/chat/types/chat'

defineProps<{
  payload: HierarchyPayload
}>()
</script>

<style scoped>
.hierarchy-diagram {
  padding: 32px 16px;
  background: linear-gradient(180deg, var(--color-bg) 0%, var(--color-surface) 100%);
  border-radius: 16px;
  overflow-x: auto;
}

.tree-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: max-content;
}

/* Root Node */
.root-wrapper {
  position: relative;
  z-index: 2;
}

.root-node {
  padding: 16px 40px;
  background: linear-gradient(135deg, #0ea5e9, var(--color-info));
  border-radius: 999px;
  font-size: 18px;
  font-weight: 800;
  color: var(--color-surface);
  position: relative;
  box-shadow: 0 10px 25px -5px rgba(14, 165, 233, 0.4), inset 0 2px 4px rgba(255, 255, 255, 0.3);
  border: 2px solid #7dd3fc;
  text-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

.root-glow {
  position: absolute;
  inset: -8px;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(14, 165, 233, 0.3) 0%, transparent 70%);
  z-index: -1;
  animation: root-pulse 3s infinite;
}

@keyframes root-pulse {
  0%, 100% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.1); opacity: 0.4; }
}

/* Connectors */
.tree-trunk {
  width: 3px;
  height: 32px;
  background: linear-gradient(to bottom, #7dd3fc, var(--color-border-hover));
  position: relative;
  z-index: 1;
}

.branches-container {
  position: relative;
  width: 100%;
}

.branches-connector {
  position: absolute;
  top: 0;
  /* Span from center of first to center of last */
  left: calc(50% / var(--branch-count, 1));
  right: calc(50% / var(--branch-count, 1));
  height: 3px;
  background: var(--color-border-hover);
  border-radius: 999px;
}

.branches-row {
  display: flex;
  justify-content: center;
  gap: 24px;
  position: relative;
  padding-top: 0;
}

/* Dynamic CSS variable for branch count */
.branches-row > * {
  --branch-count: 3; /* Fallback */
}
.branches-row:has(> :nth-child(1)) > * { --branch-count: 1; }
.branches-row:has(> :nth-child(2)) > * { --branch-count: 2; }
.branches-row:has(> :nth-child(3)) > * { --branch-count: 3; }
.branches-row:has(> :nth-child(4)) > * { --branch-count: 4; }
.branches-row:has(> :nth-child(5)) > * { --branch-count: 5; }
.branches-row:has(> :nth-child(6)) > * { --branch-count: 6; }

.branch-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  min-width: 160px;
  max-width: 240px;
}

.branch-drop {
  width: 3px;
  height: 24px;
  background: var(--color-border-hover);
}

/* For single child, hide the horizontal connector and just use trunk */
.branches-row:has(> :nth-child(1):last-child) .branches-connector {
  display: none;
}

/* Branch Cards */
.branch-card {
  width: 100%;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  position: relative;
  overflow: hidden;
}

.branch-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 20px -5px rgba(0, 0, 0, 0.08);
}

.branch-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
}

.theme-0 .branch-card::before { background: #3b82f6; }
.theme-1 .branch-card::before { background: var(--color-success); }
.theme-2 .branch-card::before { background: var(--color-warning); }
.theme-3 .branch-card::before { background: #8b5cf6; }

.branch-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 15px;
  font-weight: 800;
  color: var(--color-text-strong);
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--color-border);
}

.branch-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.theme-0 .branch-dot { background: #3b82f6; box-shadow: 0 0 6px #3b82f6; }
.theme-1 .branch-dot { background: var(--color-success); box-shadow: 0 0 6px var(--color-success); }
.theme-2 .branch-dot { background: var(--color-warning); box-shadow: 0 0 6px var(--color-warning); }
.theme-3 .branch-dot { background: #8b5cf6; box-shadow: 0 0 6px #8b5cf6; }

.branch-children {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.branch-children li {
  padding: 6px 12px;
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.4;
  background: var(--color-bg);
  border-radius: 6px;
  border: 1px solid var(--color-surface-hover);
  transition: background 0.2s ease;
}

.branch-children li:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-border);
}
</style>
