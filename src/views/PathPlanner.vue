<template>
  <div class="path-planner">
    <section class="hero-panel">
      <div class="hero-copy">
        <p class="eyebrow">智能学习路径规划</p>
        <h2>{{ heroTitle }}</h2>
        <p>{{ heroSubtitle }}</p>
      </div>

      <div class="hero-actions">
        <el-button
          :icon="RefreshRight"
          :loading="rebuildLoading"
          type="primary"
          @click="handleRebuild"
        >
          重建路径
        </el-button>
      </div>
    </section>

    <el-alert
      v-if="error"
      class="state-alert"
      :title="error"
      type="error"
      show-icon
      :closable="false"
    >
      <template #default>
        <div class="alert-actions">
          <span>当前路径数据加载失败，点击重新加载可再次获取最新结果。</span>
          <el-button link type="primary" @click="loadPathPlan">重新加载</el-button>
        </div>
      </template>
    </el-alert>

    <el-skeleton v-if="loading && !plan" animated :rows="10" class="loading-shell" />

    <template v-else-if="plan">
      <el-row :gutter="24" class="content-grid">
        <el-col :xs="24" :lg="16">
          <section class="panel timeline-panel">
            <div class="panel-header">
              <div>
                <h3>路径阶段</h3>
                <p>按当前掌握情况安排学习顺序</p>
              </div>
              <el-tag size="small" type="info">v{{ plan.meta.plan_version }}</el-tag>
            </div>

            <el-empty v-if="!plan.stages.length" description="暂无阶段数据" />

            <el-steps
              v-else
              direction="vertical"
              :active="activeStageIndex"
              finish-status="success"
              process-status="process"
            >
              <el-step v-for="stage in plan.stages" :key="stage.id">
                <template #icon>
                  <el-icon v-if="stage.status === 'success'" class="stage-icon success">
                    <CircleCheckFilled />
                  </el-icon>
                  <el-icon v-else-if="stage.status === 'processing'" class="stage-icon processing">
                    <Aim />
                  </el-icon>
                  <el-icon v-else class="stage-icon wait">
                    <Flag />
                  </el-icon>
                </template>

                <template #title>
                  <div class="stage-title-row">
                    <span>{{ stage.title }}</span>
                    <el-tag size="small" :type="statusTagType(stage.status)">
                      {{ statusLabel(stage.status) }}
                    </el-tag>
                  </div>
                </template>

                <template #description>
                  <div class="stage-block">
                    <div class="stage-meta">
                      <span>完成度 {{ stage.progress }}%</span>
                      <span>{{ stage.nodes.length }} 个节点</span>
                    </div>

                    <div class="node-list">
                      <div v-for="node in stage.nodes" :key="node.id" class="node-row">
                        <div class="node-main">
                          <el-icon class="node-status" :class="node.status">
                            <CircleCheckFilled v-if="node.status === 'success'" />
                            <Aim v-else-if="node.status === 'processing'" />
                            <Flag v-else />
                          </el-icon>

                          <div class="node-copy">
                            <div class="node-title">{{ node.title }}</div>
                            <div v-if="node.desc" class="node-desc">{{ node.desc }}</div>
                          </div>
                        </div>

                        <div class="node-side">
                          <el-tag size="small" :type="statusTagType(node.status)">
                            {{ statusLabel(node.status) }}
                          </el-tag>
                          <span class="node-meta">优先级 {{ node.priority }}</span>
                          <span class="node-meta">进度 {{ node.progress }}%</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </template>
              </el-step>
            </el-steps>
          </section>
        </el-col>

        <el-col :xs="24" :lg="8">
          <section class="panel overview-panel">
            <div class="panel-header">
              <div>
                <h3>路径概览</h3>
                <p>当前计划的关键指标</p>
              </div>
            </div>

            <div class="overview-grid">
              <div class="overview-item">
                <span class="label">总体进度</span>
                <strong>{{ plan.summary.overall_progress }}%</strong>
                <el-progress :percentage="plan.summary.overall_progress" :stroke-width="10" />
              </div>

              <div class="overview-item">
                <span class="label">当前阶段</span>
                <strong>{{ plan.summary.current_stage || currentStageFallback }}</strong>
              </div>

              <div class="overview-item">
                <span class="label">知识掌握</span>
                <strong>{{ plan.summary.knowledge_level || '未识别' }}</strong>
              </div>

              <div class="overview-item split">
                <div>
                  <span class="label">预计完成</span>
                  <strong>{{ plan.summary.eta_days }} 天</strong>
                </div>
                <div>
                  <span class="label">置信度</span>
                  <strong>{{ plan.summary.confidence }}%</strong>
                </div>
              </div>
            </div>
          </section>

          <section class="panel insight-panel">
            <div class="panel-header">
              <div>
                <h3>策略洞察</h3>
                <p>根据画像、资源和反馈给出的调整方向</p>
              </div>
            </div>

            <div class="insight-text">
              <div>
                <span class="label">调整原因</span>
                <p>{{ plan.insights.adjustment_reason }}</p>
              </div>
              <div>
                <span class="label">下一步动作</span>
                <p>{{ plan.insights.next_action }}</p>
              </div>
            </div>
          </section>

          <section class="panel meta-panel">
            <div class="panel-header">
              <div>
                <h3>来源与版本</h3>
                <p>用于判断本次计划的新鲜度</p>
              </div>
            </div>

            <div class="meta-list">
              <div class="meta-item">
                <span class="label">生成时间</span>
                <strong>{{ formatDate(plan.meta.generated_at) }}</strong>
              </div>

              <div class="meta-item">
                <span class="label">数据源</span>
                <div class="tag-row">
                  <el-tag
                    v-for="source in plan.meta.data_sources"
                    :key="source"
                    size="small"
                    type="info"
                  >
                    {{ sourceLabel(source) }}
                  </el-tag>
                </div>
              </div>

              <div class="meta-item split">
                <div>
                  <span class="label">资源 ID</span>
                  <strong>{{ plan.meta.resource_id ?? '无' }}</strong>
                </div>
                <div>
                  <span class="label">计划版本</span>
                  <strong>{{ plan.meta.plan_version }}</strong>
                </div>
              </div>
            </div>
          </section>
        </el-col>
      </el-row>
    </template>

    <el-empty v-else-if="!error" description="暂无可用路径规划" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Aim,
  CircleCheckFilled,
  Flag,
  RefreshRight,
} from '@element-plus/icons-vue'
import {
  getPathPlan,
  rebuildPathPlan,
  type PathNodeStatus,
  type PathPlan,
} from '@/api/ai'
import { getErrorMessage } from '@/utils/http'

const route = useRoute()
const plan = ref<PathPlan | null>(null)
const loading = ref(true)
const rebuildLoading = ref(false)
const error = ref('')

function parseResourceId(value: unknown): number | undefined {
  const raw = Array.isArray(value) ? value[0] : value
  if (raw == null || raw === '') return undefined
  const parsed = Number(raw)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : undefined
}

const resourceId = computed(() => parseResourceId(route.query.resource_id ?? route.query.resourceId))

const currentStageFallback = computed(() => {
  const stages = plan.value?.stages ?? []
  const current = stages.find((stage) => stage.status === 'processing')
    ?? stages.find((stage) => stage.status === 'wait')
    ?? stages[stages.length - 1]
  return current?.title ?? '等待生成'
})

const heroTitle = computed(() => {
  if (plan.value) {
    return `${plan.value.summary.overall_progress}% · ${currentStageFallback.value}`
  }
  return loading.value ? '正在加载最新路径' : '等待拉取路径数据'
})

const heroSubtitle = computed(() => {
  if (plan.value) {
    return plan.value.insights.adjustment_reason
  }
  return '系统会根据画像、资源和反馈生成当前学习安排。'
})

const activeStageIndex = computed(() => {
  const stages = plan.value?.stages ?? []
  if (!stages.length) return 0
  const processingIndex = stages.findIndex((stage) => stage.status === 'processing')
  if (processingIndex >= 0) return processingIndex
  const waitIndex = stages.findIndex((stage) => stage.status === 'wait')
  if (waitIndex >= 0) return waitIndex
  return stages.length - 1
})

function statusLabel(status: PathNodeStatus) {
  switch (status) {
    case 'success':
      return '已完成'
    case 'processing':
      return '进行中'
    default:
      return '待开始'
  }
}

function statusTagType(status: PathNodeStatus) {
  switch (status) {
    case 'success':
      return 'success'
    case 'processing':
      return 'warning'
    default:
      return 'info'
  }
}

function sourceLabel(source: string) {
  const labels: Record<string, string> = {
    profile: '用户画像',
    resource: '学习资源',
    plan_result: '已有计划',
    cold_start: '冷启动',
  }
  return labels[source] || source
}

function formatDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

async function loadPathPlan() {
  loading.value = true
  error.value = ''
  try {
    const response = await getPathPlan(resourceId.value)
    plan.value = response.data.data
  } catch (err) {
    error.value = getErrorMessage(err, '路径规划加载失败')
  } finally {
    loading.value = false
  }
}

async function handleRebuild() {
  rebuildLoading.value = true
  error.value = ''
  try {
    const response = await rebuildPathPlan(resourceId.value)
    plan.value = response.data.data
    ElMessage.success('路径已重建')
  } catch (err) {
    error.value = getErrorMessage(err, '路径重建失败')
    ElMessage.error(error.value)
  } finally {
    rebuildLoading.value = false
  }
}

watch(resourceId, () => {
  void loadPathPlan()
}, { immediate: true })
</script>

<style scoped>
.path-planner {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.hero-panel,
.panel {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--border-default);
  border-radius: 20px;
  box-shadow: var(--shadow-md);
}

.hero-panel {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.5rem;
}

.hero-copy {
  min-width: 0;
}

.eyebrow {
  margin: 0 0 0.35rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  color: var(--primary);
  text-transform: uppercase;
}

.hero-copy h2 {
  margin: 0;
  font-size: 1.6rem;
  line-height: 1.25;
  color: var(--text-main);
}

.hero-copy p {
  margin: 0.6rem 0 0;
  color: var(--text-muted);
  line-height: 1.6;
}

.hero-actions {
  flex-shrink: 0;
}

.state-alert {
  border-radius: 14px;
}

.alert-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.loading-shell {
  padding: 1rem 0;
}

.content-grid {
  align-items: flex-start;
}

.panel {
  padding: 1.25rem;
}

.timeline-panel {
  min-height: 100%;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.02rem;
  color: var(--text-main);
}

.panel-header p {
  margin: 0.25rem 0 0;
  font-size: 0.86rem;
  color: var(--text-muted);
}

.stage-title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.stage-block {
  padding: 0.5rem 0 1.25rem;
}

.stage-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 0.9rem;
  color: var(--text-muted);
  font-size: 0.84rem;
}

.node-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.node-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.95rem 1rem;
  border-radius: 14px;
  background: var(--bg-subtle);
  border: 1px solid var(--border-light);
}

.node-main {
  display: flex;
  gap: 0.75rem;
  min-width: 0;
  flex: 1;
}

.node-status {
  margin-top: 0.15rem;
  font-size: 1rem;
}

.node-status.success {
  color: #16a34a;
}

.node-status.processing {
  color: #d97706;
}

.node-status.wait {
  color: #94a3b8;
}

.node-copy {
  min-width: 0;
}

.node-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-main);
}

.node-desc {
  margin-top: 0.25rem;
  color: var(--text-muted);
  font-size: 0.84rem;
  line-height: 1.5;
}

.node-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.35rem;
  flex-shrink: 0;
  font-size: 0.8rem;
}

.node-meta {
  color: var(--text-muted);
}

.overview-grid,
.meta-list {
  display: grid;
  gap: 0.9rem;
}

.overview-item,
.meta-item {
  padding: 0.9rem 1rem;
  border-radius: 14px;
  background: var(--bg-subtle);
  border: 1px solid var(--border-light);
}

.overview-item strong,
.meta-item strong {
  display: block;
  margin-top: 0.35rem;
  color: var(--text-main);
  font-size: 1rem;
}

.label {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.split {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.4rem;
}

.insight-text {
  display: grid;
  gap: 1rem;
}

.insight-text p {
  margin: 0.35rem 0 0;
  color: var(--text-main);
  line-height: 1.6;
}

:deep(.el-steps--vertical) {
  margin-top: 0.75rem;
}

:deep(.el-step__title) {
  color: var(--text-main);
}

:deep(.el-step__description) {
  padding-bottom: 0;
}

:deep(.el-step__icon) {
  background: transparent !important;
}

.stage-icon {
  font-size: 1rem;
}

.stage-icon.success {
  color: #16a34a;
}

.stage-icon.processing {
  color: #d97706;
}

.stage-icon.wait {
  color: #94a3b8;
}

@media (max-width: 991px) {
  .hero-panel {
    flex-direction: column;
  }

  .hero-actions {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .panel {
    padding: 1rem;
  }

  .node-row {
    flex-direction: column;
  }

  .node-side {
    align-items: flex-start;
  }

  .split {
    flex-direction: column;
  }
}
</style>
