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
        :class="{ ready: isReady(agentId), 'just-arrived': latestId === agentId }"
        @click="emit('open', agentId)"
      >
        <span class="output-icon"><component :is="getIcon(agentId)" class="h-4 w-4" /></span>
        <span class="output-copy">
          <strong>{{ getArtifactLabel(agentId) }}</strong>
          <small>{{ isReady(agentId) ? '已生成，可预览' : getAgentOutputFormat(agentId) }}</small>
        </span>
        <em>{{ isReady(agentId) ? '刚刚完成' : getStatus(agentId) }}</em>
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

function getStatus(id: string) {
  const status = props.nodeStates[id]?.status
  if (status === 'failed') return '受阻'
  if (status === 'skipped') return '已跳过'
  if (status === 'running') return '执行中'
  return '就绪待命'
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

.output-dock-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
  min-width: 0;
  padding: 10px;
  border: 1px solid #dde3eb;
  border-radius: 10px;
  color: #667085;
  background: #fff;
  text-align: left;
}

.output-dock-item.ready {
  border-color: #b7d8c8;
  cursor: pointer;
}

.output-dock-item.ready:hover {
  border-color: #74b397;
  box-shadow: 0 4px 12px rgb(15 23 42 / 6%);
}

.output-icon {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 8px;
  color: #2c5f9f;
  background: #edf4fc;
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
  color: #344054;
  font-size: 11px;
}

.output-copy small,
.output-dock-item em {
  color: #98a2b3;
  font-size: 9px;
  font-style: normal;
}

.output-dock-item.just-arrived {
  animation: arrive 0.8s ease-out;
}

@keyframes arrive {
  0% { box-shadow: 0 0 0 0 rgb(22 131 87 / 30%); }
  100% { box-shadow: 0 0 0 10px transparent; }
}
</style>
