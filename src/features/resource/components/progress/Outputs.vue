<template>
  <section class="output-dock-section output-dock-section-v4">
    <div class="output-dock-heading">
      <div>
        <span>READY RESOURCES</span>
        <strong>已交付资源</strong>
      </div>
      <p>这里仅展示已经完成并可预览的资源，不改变主流水线的阅读顺序。</p>
    </div>

    <div class="output-dock-list">
      <button
        v-for="agentId in agentIds"
        :key="agentId"
        type="button"
        class="output-dock-item"
        :class="[
          isReady(agentId) ? 'ready' : isRunning(agentId) ? 'running' : 'waiting',
          { 'just-arrived': latestId === agentId }
        ]"
        :disabled="!isReady(agentId)"
        @click="isReady(agentId) && emit('open', agentId)"
      >
        <span class="output-icon"><component :is="getIcon(agentId)" class="h-4 w-4" /></span>
        <span class="output-copy">
          <strong>{{ getArtifactLabel(agentId) }}</strong>
          <small>{{ getAgentOutputFormat(agentId) }}</small>
        </span>
        <em class="output-status">
          <template v-if="isReady(agentId)">刚刚完成 ▶</template>
          <template v-else-if="isRunning(agentId)">执行中<span class="loading-dots">...</span></template>
          <template v-else>就绪待命</template>
        </em>
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Component } from 'vue'
import {
  PhChartBar as SlidesIcon,
  PhCpu as CodeIcon,
  PhFileText as ArticleIcon,
  PhFilmStrip as VideoIcon,
  PhNotePencil as QuizIcon,
  PhBookOpen as ReadingIcon,
  PhShareNetwork as MindMapIcon,
} from '@phosphor-icons/vue'
import type { ResourceAgentId } from '../../model/resource'
import type { DagNodeState } from '../../model/catalog'
import { getAgentOutputFormat } from '../../model/catalog'
import { getArtifactLabel } from '@/shared/content/kind'

const props = defineProps<{
  agentIds: ResourceAgentId[]
  generatedTypes: string[]
  nodeStates: Record<string, DagNodeState>
  latestId: string | null
}>()

const emit = defineEmits<{
  open: [type: string]
}>()

const icons: Record<string, Component> = {
  content: ArticleIcon,
  mindmap: MindMapIcon,
  quiz: QuizIcon,
  code: CodeIcon,
  reading: ReadingIcon,
  ppt: SlidesIcon,
  cartoon: VideoIcon,
}

function getIcon(id: string) {
  return icons[id] || ArticleIcon
}

function isReady(id: string) {
  return props.generatedTypes.includes(id) || props.nodeStates[id]?.status === 'success'
}

function isRunning(id: string) {
  return props.nodeStates[id]?.status === 'running'
}
</script>

<style scoped>
.output-dock-section {
  padding: 18px 24px 24px;
  border-top: 1px solid #e3e8ef;
  background: #f6f8fb;
}

.output-dock-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.output-dock-heading > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.output-dock-heading span {
  color: #98a2b3;
  font-size: 8px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.output-dock-heading strong {
  color: #263246;
  font-size: 14px;
}

.output-dock-heading p {
  margin: 0;
  color: #7a8494;
  font-size: 10px;
}

.output-dock-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 8px;
}

/* 三种状态样式 */

/* 已生成 ✅ (ready) */
.output-dock-item {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-left: 3px solid transparent;
  border-radius: 10px;
  background: #f4f6f9;
  color: #94a3b8;
  text-align: left;
  opacity: 0.65;
  cursor: default;
  transition: opacity 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.output-dock-item.ready {
  opacity: 1;
  background: #ffffff;
  border-left-color: #20b986;
  border-color: rgba(16, 185, 129, 0.18);
  color: #344054;
  cursor: pointer;
}

.output-dock-item.ready:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgb(15 23 42 / 6%), 0 0 0 1px rgba(16, 185, 129, 0.12);
  border-left-color: #10b981;
}

.output-dock-item.running {
  opacity: 1;
  background: #ffffff;
  border-left-color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.18);
  color: #344054;
  cursor: default;
  animation: border-shimmer 2s infinite ease-in-out;
}

@keyframes border-shimmer {
  0%, 100% { border-left-color: rgba(59, 130, 246, 0.48); }
  50% { border-left-color: rgba(59, 130, 246, 0.9); }
}

.output-dock-icon {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 8px;
  background: #edf4fc;
  color: #2c5f9f;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.output-dock-item.running .output-icon {
  background: #dbeafe;
  color: #3b82f6;
}

.output-dock-item.waiting .output-icon {
  background: #f1f5f9;
  color: #cbd5e1;
}

.output-copy {
  min-width: 0;
}

.output-copy strong,
.output-copy small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.output-copy strong {
  font-size: 11px;
  transition: color 0.2s ease;
}

.output-dock-item.waiting .output-copy strong {
  color: #94a3b8;
}

.output-copy small {
  font-size: 9px;
  color: #98a2b3;
  font-style: normal;
}

.output-dock-item.waiting .output-copy small {
  color: #cbd5e1;
}

.output-status {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 700;
  font-style: normal;
  white-space: nowrap;
  transition: color 0.2s ease, background-color 0.2s ease;
}

.output-dock-item.ready .output-status {
  color: #16a34a;
  background: rgba(16, 185, 129, 0.08);
}

.output-dock-item.running .output-status {
  color: #2563eb;
  background: rgba(59, 130, 246, 0.08);
}

.output-dock-item.waiting .output-status {
  color: #94a3b8;
  background: transparent;
}

.loading-dots {
  display: inline-block;
  animation: dots-pulse 1.2s infinite;
}

@keyframes dots-pulse {
  0%, 20% { opacity: 0.2; }
  50% { opacity: 1; }
  80%, 100% { opacity: 0.2; }
}

/* 到达动画 */
.output-dock-item.just-arrived {
  animation: artifact-arrive 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes artifact-arrive {
  0% {
    transform: scale(0.9);
    opacity: 0;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
  60% {
    transform: scale(1.02);
    opacity: 1;
    box-shadow: 0 0 0 8px rgba(16, 185, 129, 0.25);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .output-dock-item.just-arrived,
  .output-dock-item.running,
  .loading-dots {
    animation: none !important;
  }
  .output-dock-item.ready:hover {
    transform: none;
  }
}
</style>
