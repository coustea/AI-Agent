<template>
  <aside class="stage-directory">
    <header class="directory-head">
      <span>ROADMAP OUTLINE</span>
      <h2>阶段大纲</h2>
    </header>
    
    <div class="stage-cards">
      <button
        v-for="(stage, idx) in stages"
        :key="stage.stage_id"
        type="button"
        class="stage-dir-card"
        :class="{ active: activeStageId === stage.stage_id }"
        @click="$emit('select-stage', stage.stage_id)"
      >
        <div class="card-num">
          <span>{{ String(idx + 1).padStart(2, '0') }}</span>
        </div>
        <div class="card-info">
          <h4>{{ stage.title }}</h4>
          <div class="progress-bar-wrap">
            <div class="progress-bar-track">
              <i :style="{ width: `${stageProgress(stage.stage_id)}%` }"></i>
            </div>
            <span class="progress-text">{{ completedCount(stage.stage_id) }}/{{ totalCount(stage.stage_id) }} 已通关</span>
          </div>
        </div>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { LearningPathStage, LearningPathNode } from '@/features/learning-path/model/path'

const props = defineProps<{
  stages: LearningPathStage[]
  nodes: LearningPathNode[]
  activeStageId: string | null
}>()

defineEmits<{
  (e: 'select-stage', stageId: string): void
}>()

const stageNodes = (stageId: string) => {
  return props.nodes.filter(n => n.stage_id === stageId)
}

const totalCount = (stageId: string) => stageNodes(stageId).length

const completedCount = (stageId: string) => {
  return stageNodes(stageId).filter(n => ['completed', 'completed_with_gaps'].includes(n.status)).length
}

const stageProgress = (stageId: string) => {
  const total = totalCount(stageId)
  if (!total) return 0
  return Math.round((completedCount(stageId) / total) * 100)
}
</script>

<style scoped>
.stage-directory {
  padding: 18px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.015);
}
.directory-head span {
  font-size: 11px;
  font-weight: 900;
  color: #6366f1;
  letter-spacing: 0.1em;
}
.directory-head h2 {
  margin: 4px 0 16px;
  font-size: 18px;
  color: var(--color-text, #173b42);
}
.stage-cards {
  display: grid;
  gap: 10px;
}
.stage-dir-card {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
}
.stage-dir-card:hover {
  border-color: var(--color-primary, #46b8b4);
  background: var(--color-bg, #f2f8f7);
}
.stage-dir-card.active {
  border-color: #6366f1;
  box-shadow: 0 0 0 1px #6366f1;
}
.card-num {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #f1f5f9;
  font-size: 12px;
  font-weight: 800;
  color: var(--color-text-secondary, #58747a);
}
.stage-dir-card.active .card-num {
  background: #e0e7ff;
  color: #6366f1;
}
.card-info {
  flex: 1;
  min-width: 0;
}
.card-info h4 {
  margin: 0 0 6px;
  font-size: 14px;
  color: var(--color-text, #173b42);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.progress-bar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.progress-bar-track {
  flex: 1;
  height: 4px;
  background: #f1f5f9;
  border-radius: 99px;
  overflow: hidden;
}
.progress-bar-track i {
  display: block;
  height: 100%;
  background: var(--color-primary, #46b8b4);
  border-radius: inherit;
  transition: width 0.3s ease;
}
.stage-dir-card.active .progress-bar-track i {
  background: #6366f1;
}
.progress-text {
  font-size: 11px;
  color: var(--color-text-secondary, #58747a);
  font-weight: 600;
}
</style>
