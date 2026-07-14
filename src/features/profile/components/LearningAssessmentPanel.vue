<template>
  <section class="assessment-panel">
    <div class="panel-shell">
      <header class="panel-header">
        <div class="header-title">
          <span class="header-label">学习评估</span>
          <h1>学习记录如何改变当前辅导策略</h1>
        </div>
        <div class="header-actions">
          <div class="range-tabs" role="group" aria-label="评估时间范围">
            <button
              v-for="days in rangeOptions"
              :key="days"
              type="button"
              :class="{ active: selectedRange === days }"
              @click="selectedRange = days"
            >
              {{ days }} 天
            </button>
          </div>
          <Button class="generate-btn" :disabled="generating" @click="triggerReportGeneration">
            <Sparkles :size="15" />
            {{ generating ? '生成中' : '重新评估' }}
          </Button>
        </div>
      </header>

      <!-- 生成进度 -->
      <section v-if="generating" class="generation-strip">
        <span
          v-for="(step, index) in generationSteps"
          :key="step"
          :class="{ done: index < currentStepIdx, current: index === currentStepIdx }"
        >
          {{ step }}
        </span>
      </section>

      <!-- 加载状态 -->
      <section v-if="initialLoading" class="loading-state">
        <div class="loading-spinner" />
        <p>加载中...</p>
      </section>

      <!-- 无报告 -->
      <section v-else-if="!activeReport" class="empty-state">
        <FileCheck :size="28" />
        <h2>暂无评估报告</h2>
        <p>点击「重新评估」生成第一份报告</p>
      </section>

      <!-- 失败状态 -->
      <section v-else-if="activeReport.status === 'failed'" class="error-state">
        <AlertCircle :size="22" />
        <h2>生成失败</h2>
        <p>{{ activeReport.failure_code || '未知错误' }}</p>
        <Button variant="outline" size="sm" @click="triggerReportGeneration">重试</Button>
      </section>

      <!-- 生成中 -->
      <section v-else-if="activeReport.status !== 'ready'" class="loading-state">
        <div class="loading-spinner" />
        <p>报告生成中...</p>
      </section>

      <!-- 主内容 -->
      <template v-else-if="facts">
        <!-- 本期结论 -->
        <section class="conclusion-block">
          <div class="conclusion-header">
            <ShieldCheck :size="16" />
            <h2>本期结论</h2>
            <span class="window-badge">{{ activeReport.range_days }} 天</span>
          </div>
          <p class="conclusion-text">{{ guidanceStrategy?.conclusion || defaultConclusion }}</p>
          <div v-if="guidanceStrategy" class="strategy-row">
            <div class="strategy-item">
              <span class="strategy-label">重点主题</span>
              <strong>{{ guidanceStrategy.focus_topics?.length ? guidanceStrategy.focus_topics.slice(0, 2).join('、') : '暂无' }}</strong>
            </div>
            <div class="strategy-item">
              <span class="strategy-label">建议时长</span>
              <strong>{{ guidanceStrategy.recommended_session_minutes }} 分钟</strong>
            </div>
            <div class="strategy-item">
              <span class="strategy-label">辅导方式</span>
              <strong>{{ guidanceStrategy.tutoring_style?.slice(0, 10) || '暂无' }}{{ guidanceStrategy.tutoring_style?.length > 10 ? '...' : '' }}</strong>
            </div>
          </div>
        </section>

        <!-- 核心指标 -->
        <section class="metrics-row">
          <div class="metric-cell">
            <Clock :size="15" />
            <strong>{{ facts.activity.total_minutes }}</strong>
            <span>分钟</span>
          </div>
          <div class="metric-cell">
            <ListChecks :size="15" />
            <strong>{{ percentLabel(facts.practice.accuracy) }}</strong>
            <span>正确率</span>
          </div>
          <div class="metric-cell">
            <Route :size="15" />
            <strong>{{ percentLabel(facts.learning_path.completion_rate) }}</strong>
            <span>路径完成</span>
          </div>
          <div class="metric-cell">
            <Target :size="15" />
            <strong>{{ facts.topics.encountered.length }}</strong>
            <span>个主题</span>
          </div>
        </section>

        <!-- 行动计划 -->
        <section v-if="actionPlan.length" class="action-section">
          <h3>下一阶段计划</h3>
          <div class="action-list">
            <div
              v-for="(action, index) in actionPlan.slice(0, 3)"
              :key="index"
              class="action-row"
            >
              <span class="action-num">{{ index + 1 }}</span>
              <span class="action-desc">{{ action.description }}</span>
              <RouterLink :to="action.link" class="action-link">
                {{ actionTypeLabel(action.action_type) }}
              </RouterLink>
            </div>
          </div>
        </section>

        <!-- 历史报告 -->
        <section class="history-section">
          <h3>历史报告</h3>
          <div v-if="reportsHistory.length" class="history-chips">
            <button
              v-for="report in reportsHistory.slice(0, 3)"
              :key="report.id"
              type="button"
              :class="{ active: activeReport?.id === report.id }"
              @click="selectReport(report.id)"
            >
              {{ report.range_days }} 天
            </button>
          </div>
          <p v-else class="history-empty">暂无历史</p>
        </section>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { toast } from 'vue-sonner'
import { RouterLink } from 'vue-router'
import { Button } from '@/components/ui/button'
import {
  AlertCircle,
  Clock,
  FileCheck,
  ListChecks,
  Route,
  ShieldCheck,
  Sparkles,
  Target,
} from 'lucide-vue-next'
import {
  generateAssessmentReport,
  getGuidanceStrategy,
  getLatestReport,
  getReportDetail,
  getReportsHistory,
} from '@/features/learning-assessment/api/assessment'
import type {
  ActionPlanItem,
  AssessmentFacts,
  GuidanceStrategy,
  LearningAssessmentReport,
} from '@/features/learning-assessment/model/assessment'
import { normalizeGuidanceStrategy } from '@/features/learning-assessment/model/assessment'

const rangeOptions = [3, 7, 14] as const
const selectedRange = ref<3 | 7 | 14>(7)
const reportsHistory = ref<Omit<LearningAssessmentReport, 'facts_snapshot' | 'report_markdown'>[]>([])
const activeReport = ref<LearningAssessmentReport | null>(null)
const guidanceStrategy = ref<GuidanceStrategy | null>(null)
const generating = ref(false)
const initialLoading = ref(true)
const currentStepIdx = ref(0)
const generationSteps = ['聚合事实', '校验质量', '生成报告', '更新策略']

const facts = computed<AssessmentFacts | null>(() => activeReport.value?.facts_snapshot ?? null)

const actionPlan = computed<ActionPlanItem[]>(() => guidanceStrategy.value?.action_plan ?? [])

const defaultConclusion = computed(() => {
  if (!facts.value) return '暂无学习数据'
  if (!facts.value.data_quality.has_activity) return '当前窗口暂无学习活动'
  return '学习证据已形成'
})

async function loadGuidanceStrategy(): Promise<void> {
  try {
    const response = await getGuidanceStrategy()
    guidanceStrategy.value = normalizeGuidanceStrategy(response.data.data.guidance_strategy)
  } catch (error) {
    console.error('加载辅导策略失败', error)
  }
}

async function loadReportsHistory(): Promise<void> {
  try {
    const response = await getReportsHistory(1, 5)
    reportsHistory.value = response.data.data.items
  } catch (error) {
    console.error('加载历史报告失败', error)
  }
}

async function selectReport(reportId: number): Promise<void> {
  try {
    const response = await getReportDetail(reportId)
    activeReport.value = response.data.data
  } catch (error) {
    console.error('加载报告详情失败', error)
  }
}

async function triggerReportGeneration(): Promise<void> {
  generating.value = true
  currentStepIdx.value = 0
  const timer = window.setInterval(() => {
    currentStepIdx.value = Math.min(currentStepIdx.value + 1, generationSteps.length - 1)
  }, 800)

  try {
    const response = await generateAssessmentReport(selectedRange.value)
    activeReport.value = response.data.data
    toast.success('评估报告已生成')
    await Promise.all([loadReportsHistory(), loadGuidanceStrategy()])
  } catch (error: any) {
    if (error?.response?.status === 409) {
      toast.warning('已有报告生成中')
    } else {
      console.error('生成报告失败', error)
      toast.error('生成失败')
    }
  } finally {
    window.clearInterval(timer)
    generating.value = false
    currentStepIdx.value = 0
  }
}

function percentLabel(value: number): string {
  return `${Math.round(value * 100)}%`
}

function actionTypeLabel(type: ActionPlanItem['action_type']): string {
  const labels: Record<string, string> = {
    review: '复习',
    practice: '练习',
    quiz: '测验',
  }
  return labels[type] || '开始'
}

onMounted(async () => {
  initialLoading.value = true
  await Promise.all([loadReportsHistory(), loadGuidanceStrategy()])
  try {
    const response = await getLatestReport()
    if (response.data.data) {
      activeReport.value = response.data.data
    } else if (reportsHistory.value[0]?.id !== undefined) {
      await selectReport(reportsHistory.value[0].id)
    }
  } catch (error) {
    console.error('获取最新报告失败', error)
  } finally {
    initialLoading.value = false
  }
})
</script>

<style scoped>
.assessment-panel {
  height: 100%;
  overflow: auto;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
}

.panel-shell {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

h1, h2, h3, p {
  margin: 0;
}

/* Header */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.header-label {
  font-size: var(--text-xs);
  color: var(--color-primary-text);
  font-weight: var(--weight-extrabold);
}

.header-title h1 {
  margin-top: var(--space-1);
  font-size: var(--text-base);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
  line-height: var(--leading-tight);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.range-tabs {
  display: inline-flex;
  gap: 1px;
  padding: 2px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
}

.range-tabs button {
  min-width: 2.5rem;
  min-height: 1.75rem;
  border: 0;
  border-radius: 2px;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  cursor: pointer;
}

.range-tabs button.active {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
}

.generate-btn {
  min-height: 1.75rem;
  font-size: var(--text-xs);
  gap: var(--space-1);
}

/* Generation Strip */
.generation-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-1);
}

.generation-strip span {
  min-height: 1.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.generation-strip span.done {
  background: var(--color-success-soft);
  color: var(--color-success);
}

.generation-strip span.current {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
}

/* Loading & Empty */
.loading-state,
.empty-state,
.error-state {
  min-height: 10rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  text-align: center;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state h2,
.error-state h2 {
  font-size: var(--text-sm);
  color: var(--color-text-strong);
}

.empty-state p,
.loading-state p {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.error-state {
  color: var(--color-danger);
}

.error-state h2 {
  color: var(--color-danger);
}

/* Conclusion */
.conclusion-block {
  padding: var(--space-3);
  background: linear-gradient(135deg, var(--color-primary-soft) 0%, var(--color-surface) 50%);
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-md);
}

.conclusion-header {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
  color: var(--color-primary-text);
}

.conclusion-header h2 {
  font-size: var(--text-sm);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
}

.window-badge {
  margin-left: auto;
  padding: 2px 6px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
}

.conclusion-text {
  font-size: var(--text-sm);
  color: var(--color-text-strong);
  line-height: var(--leading-relaxed);
  margin-bottom: var(--space-3);
}

.strategy-row {
  display: flex;
  gap: var(--space-2);
}

.strategy-item {
  flex: 1;
  padding: var(--space-2);
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.strategy-label {
  display: block;
  font-size: 10px;
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
}

.strategy-item strong {
  display: block;
  margin-top: 2px;
  font-size: var(--text-xs);
  color: var(--color-text-strong);
}

/* Metrics */
.metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-2);
}

.metric-cell {
  padding: var(--space-2);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.metric-cell svg {
  color: var(--color-primary-text);
}

.metric-cell strong {
  font-size: var(--text-lg);
  color: var(--color-text-strong);
  line-height: 1;
}

.metric-cell span {
  font-size: 10px;
  color: var(--color-text-muted);
}

/* Actions */
.action-section h3 {
  font-size: var(--text-sm);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
  margin-bottom: var(--space-2);
}

.action-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.action-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.action-num {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  border-radius: 50%;
  font-size: 10px;
  font-weight: var(--weight-extrabold);
}

.action-desc {
  flex: 1;
  font-size: var(--text-xs);
  color: var(--color-text-strong);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-link {
  padding: 2px 8px;
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: var(--weight-bold);
  text-decoration: none;
}

.action-link:hover {
  background: var(--color-primary-hover);
}

/* History */
.history-section h3 {
  font-size: var(--text-sm);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
  margin-bottom: var(--space-2);
}

.history-chips {
  display: flex;
  gap: var(--space-1);
}

.history-chips button {
  padding: var(--space-1) var(--space-2);
  background: var(--color-bg);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-pill);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.history-chips button.active {
  background: var(--color-primary-soft);
  border-color: var(--color-primary);
  color: var(--color-primary-text);
}

.history-empty {
  font-size: var(--text-xs);
  color: var(--color-text-faint);
}

/* Responsive */
@media (max-width: 480px) {
  .panel-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    justify-content: space-between;
  }

  .metrics-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .strategy-row {
    flex-direction: column;
  }
}
</style>