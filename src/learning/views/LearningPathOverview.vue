<template>
  <main class="path-overview-page">
    <section v-if="loading" class="state-card">正在加载学习路径...</section>
    <section v-else-if="!path" class="state-card">
      <p>还没有可用的学习路径。</p>
      <button class="primary-btn" @click="router.push('/path-planner')">去创建</button>
    </section>

    <template v-else>
      <header class="overview-header">
        <div>
          <span class="page-kicker">当前学习路径</span>
          <h1>{{ path.title }}</h1>
          <p>{{ path.goal }}</p>
        </div>

        <div class="header-actions">
          <button class="ghost-btn" @click="router.push('/path-planner/history')">路径历史</button>
          <button class="ghost-btn" @click="router.push('/path-resource-history')">路径资源记录</button>
          <button class="primary-btn" @click="router.push('/path-planner')">重新规划</button>
        </div>
      </header>

      <section class="summary-grid">
        <article class="summary-panel">
          <span>总进度</span>
          <strong>{{ path.overall_progress }}%</strong>
          <div class="progress-track">
            <i :style="{ width: `${path.overall_progress}%` }"></i>
          </div>
        </article>

        <article class="summary-panel">
          <span>预计周期</span>
          <strong>{{ path.eta_days }} 天</strong>
          <p>规划置信度 {{ path.confidence }}%</p>
        </article>

        <article class="summary-panel">
          <span>当前节点</span>
          <strong>{{ currentNode?.title || '待开始' }}</strong>
          <p>{{ currentNode?.mastery_target || '选择一个可学习节点开始' }}</p>
        </article>
      </section>

      <section class="stage-list">
        <article v-for="stage in groupedStages" :key="stage.stage_id" class="stage-panel">
          <div class="stage-head">
            <div>
              <h2>{{ stage.title }}</h2>
              <p>{{ stage.description }}</p>
            </div>
            <span>{{ completedCount(stage.nodes) }}/{{ stage.nodes.length }}</span>
          </div>

          <div class="node-list">
            <button
              v-for="node in stage.nodes"
              :key="node.id"
              class="node-card"
              :class="node.status"
              @click="openNode(node.id)"
            >
              <div class="node-card-head">
                <strong>{{ node.title }}</strong>
                <span>{{ statusText(node.status) }}</span>
              </div>
              <p>{{ node.mastery_target || node.recommendation_reason || '进入节点后生成教程并开始学习。' }}</p>
              <div class="node-meta">
                <span v-if="node.estimated_minutes">{{ node.estimated_minutes }} 分钟</span>
                <span v-if="node.difficulty">{{ node.difficulty }}</span>
                <span>第 {{ node.attempt_count }} 轮</span>
              </div>
            </button>
          </div>
        </article>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getCurrentLearningPath, getLearningPathById } from '@/learning/api/path'
import type { LearningPathNode, LearningPathOverview } from '@/learning/types/path'
import { getErrorMessage } from '@/shared/utils/http'

const router = useRouter()
const route = useRoute()

const loading = ref(false)
const path = ref<LearningPathOverview | null>(null)

const groupedStages = computed(() => {
  if (!path.value) return []
  const nodeMap = new Map(path.value.nodes.map((node) => [node.stage_id, [] as LearningPathNode[]]))
  for (const node of path.value.nodes) {
    if (!nodeMap.has(node.stage_id)) nodeMap.set(node.stage_id, [])
    nodeMap.get(node.stage_id)!.push(node)
  }
  return path.value.stages.map((stage) => ({
    ...stage,
    nodes: (nodeMap.get(stage.stage_id) || []).slice().sort((a, b) => a.priority - b.priority),
  }))
})

const currentNode = computed(() => path.value?.nodes.find((node) => node.node_id === path.value?.current_node_key) || null)

const loadPath = async () => {
  loading.value = true
  try {
    const rawId = String(route.params.id || '')
    const paramId = Number(rawId || 0)
    const shouldLoadSpecificPath = Boolean(rawId && rawId !== 'latest' && Number.isFinite(paramId) && paramId > 0)

    if (shouldLoadSpecificPath) {
      const res = await getLearningPathById(paramId)
      path.value = res.data.data
      return
    }

    const res = await getCurrentLearningPath()
    const current = res.data.data
    if (!current) {
      path.value = null
      return
    }

    path.value = current
    if (rawId === 'latest') {
      router.replace(`/path-planner/overview/${current.id}`)
    }
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '加载学习路径失败'))
  } finally {
    loading.value = false
  }
}

const openNode = (nodeId: number) => {
  router.push(`/path-planner/node/${nodeId}`)
}

const completedCount = (nodes: LearningPathNode[]) => nodes.filter((node) => ['completed', 'completed_with_gaps'].includes(node.status)).length

const statusText = (status: string) => {
  switch (status) {
    case 'available': return '可学习'
    case 'locked': return '未解锁'
    case 'completed': return '已通过'
    case 'completed_with_gaps': return '带缺口完成'
    default: return status
  }
}

onMounted(loadPath)
</script>

<style scoped>
.path-overview-page {
  min-height: calc(100vh - 64px);
  padding: 28px 32px 48px;
  background: #f8fafc;
}

.overview-header,
.summary-panel,
.stage-panel,
.state-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.overview-header {
  max-width: 1200px;
  margin: 0 auto 20px;
  padding: 24px 28px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.page-kicker {
  display: inline-block;
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.overview-header h1 {
  margin: 0 0 8px;
  font-size: 30px;
  color: #0f172a;
}

.overview-header p {
  margin: 0;
  color: #475569;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: start;
}

.summary-grid {
  max-width: 1200px;
  margin: 0 auto 20px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.summary-panel {
  padding: 20px;
}

.summary-panel span {
  display: block;
  color: #64748b;
  font-size: 13px;
  margin-bottom: 8px;
}

.summary-panel strong {
  display: block;
  color: #0f172a;
  font-size: 28px;
  margin-bottom: 8px;
}

.summary-panel p {
  margin: 0;
  color: #475569;
}

.progress-track {
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.progress-track i {
  display: block;
  height: 100%;
  background: #2563eb;
}

.stage-list {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  gap: 16px;
}

.stage-panel {
  padding: 20px;
}

.stage-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.stage-head h2 {
  margin: 0 0 6px;
  font-size: 20px;
  color: #0f172a;
}

.stage-head p {
  margin: 0;
  color: #64748b;
}

.stage-head span {
  color: #2563eb;
  font-weight: 700;
}

.node-list {
  display: grid;
  gap: 12px;
}

.node-card {
  width: 100%;
  text-align: left;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
}

.node-card.available {
  border-color: #93c5fd;
  background: #eff6ff;
}

.node-card.completed,
.node-card.completed_with_gaps {
  border-color: #86efac;
  background: #f0fdf4;
}

.node-card.locked {
  opacity: 0.75;
}

.node-card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.node-card-head strong {
  color: #0f172a;
}

.node-card-head span,
.node-meta span,
.node-card p {
  color: #475569;
}

.node-card p {
  margin: 0 0 10px;
  line-height: 1.6;
}

.node-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 13px;
}

.state-card {
  max-width: 880px;
  margin: 40px auto 0;
  padding: 32px;
  text-align: center;
}

.primary-btn,
.ghost-btn {
  border-radius: 8px;
  font: inherit;
  cursor: pointer;
  padding: 10px 16px;
}

.primary-btn {
  border: none;
  background: #2563eb;
  color: #fff;
}

.ghost-btn {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
}

@media (max-width: 900px) {
  .overview-header,
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .overview-header {
    flex-direction: column;
  }

  .header-actions {
    flex-wrap: wrap;
  }
}

@media (max-width: 640px) {
  .path-overview-page {
    padding: 16px;
  }
}
</style>
