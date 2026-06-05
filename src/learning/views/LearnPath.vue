<template>
  <div class="learn-path-container minimalist-theme">
    <!-- Hero Section: Input Goal -->
    <section class="hero-section" v-if="!coursePath && !isGenerating">
      <div class="hero-content">
        <h1 class="hero-title">构建你的专属学习路径</h1>
        <p class="hero-subtitle">
          输入您的长远学习目标，AI 智能引擎将为您梳理出科学的知识图谱与学习计划。
        </p>
        <div class="search-box">
          <el-input
            v-model="courseGoal"
            placeholder="例如：大语言模型底层原理与部署..."
            class="course-input clean-input"
            size="large"
            @keyup.enter="handleGeneratePath"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button 
            type="primary" 
            size="large" 
            class="generate-btn"
            :loading="isGenerating"
            @click="handleGeneratePath"
          >
            生成路径
          </el-button>
        </div>
      </div>
    </section>

    <!-- Generating Skeleton -->
    <div v-if="isGenerating" class="loading-state clean-panel">
      <el-skeleton :rows="2" animated class="skeleton-header" />
      <div class="skeleton-grid">
        <el-skeleton-item variant="rect" class="skeleton-card" />
        <el-skeleton-item variant="rect" class="skeleton-card" />
        <el-skeleton-item variant="rect" class="skeleton-card" />
      </div>
      <p class="loading-text">多智能体正在深度协同，诊断画像并构建拓扑网络...</p>
    </div>

    <!-- Path Display Section -->
    <div v-else-if="coursePath" class="path-display-section">
      <header class="path-header">
        <div class="path-title-group">
          <h2>{{ coursePath.title }}</h2>
          <div class="path-meta-tags">
            <el-tag type="info" class="clean-tag" effect="plain">节点: {{ coursePath.nodes.length }}</el-tag>
            <el-tag type="info" class="clean-tag" effect="plain">预计时长: {{ coursePath.eta_days }} 天</el-tag>
            <el-tag type="success" class="clean-tag" effect="plain" v-if="coursePath.confidence">规划置信度: {{ coursePath.confidence }}%</el-tag>
          </div>
        </div>
        <div class="path-actions">
          <el-button @click="openOptimizationDialog">
            <el-icon><MagicStick /></el-icon> 诊断优化
          </el-button>
          <el-button @click="resetPath">重新规划</el-button>
        </div>
      </header>

      <!-- AI Diagnosis Report -->
      <transition name="el-zoom-in-top">
        <div class="diagnosis-report-card clean-panel" v-if="coursePath.strategy_report">
          <div class="dr-header">
            <div class="dr-title-wrap">
              <el-icon class="dr-icon"><DataAnalysis /></el-icon>
              <span class="dr-title">AI 诊断与裁剪策略</span>
            </div>
          </div>
          <div class="dr-body">
            <div class="dr-text-content" v-html="formatStrategyReport(coursePath.strategy_report)"></div>
          </div>
        </div>
      </transition>

      <section class="learning-evaluation-panel clean-panel">
        <div class="lep-main">
          <div>
            <p class="lep-eyebrow">学习效果评估</p>
            <h3>路径自适应状态</h3>
            <p class="lep-summary">
              {{ evaluationSummaryText }}
            </p>
          </div>
          <el-progress
            type="dashboard"
            :percentage="evaluationScore"
            :stroke-width="10"
            :color="evaluationColors"
          >
            <template #default="{ percentage }">
              <span class="lep-score">{{ percentage }}%</span>
            </template>
          </el-progress>
        </div>

        <div class="lep-metrics">
          <div class="lep-metric">
            <span>平均测验</span>
            <strong>{{ signalSnapshot.average_score === null ? '暂无' : `${Math.round(signalSnapshot.average_score)}分` }}</strong>
          </div>
          <div class="lep-metric">
            <span>已完成资源</span>
            <strong>{{ signalSnapshot.completed_resource_count }}</strong>
          </div>
          <div class="lep-metric">
            <span>活跃学习</span>
            <strong>{{ signalSnapshot.active_minutes }} 分钟</strong>
          </div>
        </div>

        <div class="lep-tags">
          <el-tag
            v-for="topic in signalSnapshot.weak_topics"
            :key="topic"
            type="warning"
            effect="plain"
          >
            {{ topic }}
          </el-tag>
          <el-tag v-if="!signalSnapshot.weak_topics.length" type="info" effect="plain">等待更多学习信号</el-tag>
        </div>

        <div v-if="pathEvaluation?.optimization_tips.length" class="lep-tips">
          <div v-for="tip in pathEvaluation.optimization_tips" :key="tip" class="lep-tip">
            <el-icon><DataAnalysis /></el-icon>
            <span>{{ tip }}</span>
          </div>
        </div>
      </section>

      <section v-if="shouldShowPathSummary" class="summary-card clean-panel">
        <div class="summary-header">
          <el-icon><DataAnalysis /></el-icon>
          <div class="summary-header-text">
            <span>路径学习总结</span>
            <small>{{ summaryStatusText }}</small>
          </div>
        </div>

        <div v-if="summaryLoading || pathSummary?.status === 'pending' || pathSummary?.status === 'generating'" class="summary-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在生成掌握度分析与后续建议...</span>
        </div>

        <div v-else-if="pathSummary?.status === 'failed'" class="summary-error">
          {{ pathSummary.error_message || '学习总结生成失败，请稍后刷新。' }}
        </div>

        <div v-else-if="pathSummary?.status === 'completed'" class="summary-content">
          <div v-if="masteryEntries.length" class="summary-section">
            <h4>节点掌握度</h4>
            <div class="mastery-list">
              <div v-for="item in masteryEntries" :key="item.nodeId" class="mastery-item">
                <span class="mastery-topic">{{ item.topic }}</span>
                <el-progress :percentage="item.score" :stroke-width="8" />
              </div>
            </div>
          </div>

          <div v-if="pathSummary.weak_points?.length" class="summary-section">
            <h4>薄弱点回顾</h4>
            <div class="weak-list">
              <el-tag
                v-for="weak in pathSummary.weak_points"
                :key="`${weak.topic || 'weak'}-${weak.score || 0}`"
                type="warning"
                effect="plain"
                class="weak-tag"
              >
                {{ weak.topic || '待巩固知识点' }}{{ weak.score !== undefined ? ` ${weak.score}分` : '' }}
              </el-tag>
            </div>
          </div>

          <div v-if="pathSummary.next_suggestions?.length" class="summary-section">
            <h4>后续建议</h4>
            <div class="suggestions-list">
              <div v-for="suggestion in pathSummary.next_suggestions" :key="suggestion.title || suggestion.reason" class="suggestion-item">
                <strong>{{ suggestion.title || '继续学习建议' }}</strong>
                <p>{{ suggestion.reason }}</p>
              </div>
            </div>
          </div>

          <MarkdownPreview
            v-if="pathSummary.summary_markdown"
            class="summary-markdown"
            :content="pathSummary.summary_markdown"
          />
        </div>
      </section>

      <!-- Timeline Skill Tree -->
      <div class="timeline-container">
        <div 
          v-for="(stage, index) in groupedStages" 
          :key="stage.stage_id"
          class="stage-block"
        >
          <!-- Stage Meta -->
          <div class="stage-info">
            <div class="stage-number">{{ index + 1 }}</div>
            <div class="stage-text">
              <h3 class="stage-title">{{ stage.title }}</h3>
              <p class="stage-desc">{{ stage.description }}</p>
            </div>
          </div>

          <!-- Nodes List -->
          <div class="stage-nodes">
            <div 
              v-for="node in stage.nodes" 
              :key="node.id"
              class="node-wrapper"
              :class="`status-${node.status}`"
            >
              <!-- Node Point -->
              <div class="node-indicator">
                <div class="indicator-line"></div>
                <div class="indicator-dot">
                  <el-icon v-if="node.status === 'completed'"><Check /></el-icon>
                  <el-icon v-else-if="node.status === 'locked'"><Lock /></el-icon>
                </div>
              </div>

              <!-- Node Card -->
              <div class="node-card clean-panel">
                <div class="nc-header">
                  <span class="nc-title">{{ node.title }}</span>
                  <span class="nc-status-text" :class="`text-${node.status}`">{{ getStatusText(node.status) }}</span>
                </div>
                
                <div class="nc-body">
                  <p class="nc-summary">{{ node.mastery_target || node.recommendation_reason }}</p>
                  
                  <div v-if="node.resource_status === 'generating'" class="nc-generating-state">
                    <el-progress :percentage="getNodeProgress(node)" :show-text="false" class="clean-progress" />
                    <span>AI 资料生成中... {{ getNodeProgress(node) }}%</span>
                  </div>
                </div>

                <div class="nc-footer">
                  <el-button
                    v-if="node.status === 'available' && node.resource_status === 'not_started'"
                    type="primary" class="clean-btn" :loading="generatingNodeId === node.id"
                    @click="handleGenerateResources(node)"
                  >
                    生成学习资料
                  </el-button>
                  <el-button
                    v-else-if="node.status === 'available' && node.resource_status === 'generating'"
                    type="primary" class="clean-btn" plain loading
                  >
                    生成中...
                  </el-button>
                  <el-button
                    v-else-if="node.status === 'available' && node.resource_status === 'ready'"
                    type="success" class="clean-btn"
                    @click="handleStartLearning(node)"
                  >
                    开始学习
                  </el-button>
                  <el-button
                    v-else-if="node.status === 'available' && node.resource_status === 'failed'"
                    type="warning" class="clean-btn" plain
                    @click="handleGenerateResources(node)"
                  >
                    重新生成
                  </el-button>
                  <div v-else-if="node.status === 'in_progress'" class="nc-actions-group">
                    <el-button class="clean-btn" plain @click="viewResource(node)">继续学习</el-button>
                    <div class="quiz-score-submit">
                      <el-input-number
                        v-model="quizScores[node.id]"
                        :min="0"
                        :max="100"
                        :step="5"
                        size="small"
                        controls-position="right"
                      />
                      <el-button
                        class="clean-btn"
                        plain
                        :loading="submittingQuizNodeId === node.id"
                        @click="handleSubmitQuiz(node)"
                      >
                        提交测验
                      </el-button>
                    </div>
                    <el-button type="success" class="clean-btn" :loading="completingNodeId === node.id" @click="handleCompleteNode(node)">
                      完成节点
                    </el-button>
                  </div>
                  <el-button
                    v-else-if="node.status === 'completed'"
                    class="clean-btn" plain
                    @click="viewResource(node)"
                  >
                    复习资源
                  </el-button>
                  <span v-else-if="node.status === 'locked'" class="locked-hint">
                    需完成前置节点
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Optimization Dialog -->
    <el-dialog
      v-model="showOptimizeDialog"
      title="路径诊断与重构"
      width="540px"
      class="clean-dialog"
    >
      <div class="dialog-desc">
        AI 将根据您的反馈，动态调整后续节点的难度与内容安排。
      </div>
      
      <div class="preset-section">
        <span class="section-label">快速选择：</span>
        <div class="preset-tags">
          <el-tag
            v-for="tag in presetTags" :key="tag"
            class="clean-tag-clickable" :effect="customFeedback === tag ? 'dark' : 'plain'"
            type="info"
            @click="selectPresetTag(tag)"
          >
            {{ tag }}
          </el-tag>
        </div>
      </div>
      
      <div class="feedback-input-section">
        <span class="section-label">自定义反馈：</span>
        <el-input
          v-model="customFeedback"
          type="textarea" :rows="4"
          placeholder="例如：我觉得目前的理论有点深，希望能放缓坡度..."
        />
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showOptimizeDialog = false">取消</el-button>
          <el-button type="primary" :loading="isOptimizing" @click="handleOptimizePath">
            开始重构
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Optimizing Overlay -->
    <div v-if="isOptimizing" class="clean-overlay">
      <div class="loader-box clean-panel">
        <el-icon class="loader-icon is-loading"><Loading /></el-icon>
        <h3 class="loader-title">正在重新规划路径</h3>
        <p class="loader-sub">AI 正在根据反馈重组知识拓扑...</p>
        <div class="clean-steps">
          <div v-for="(step, idx) in optimizeSteps" :key="idx" class="c-step" :class="{ active: idx <= currentOptimizeStep, done: idx < currentOptimizeStep }">
            <el-icon><Check v-if="idx < currentOptimizeStep" /><VideoPlay v-else-if="idx === currentOptimizeStep" /><More v-else /></el-icon>
            {{ step }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search, DataAnalysis,
  Lock, MagicStick, Check, Loading, VideoPlay, More
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  completeCoursePathNode, generateCoursePath, getActiveCoursePathTask,
  getCoursePathTaskStatus, generatePathNodeResources, getActiveCoursePath,
  startCoursePathNode, adjustCoursePath, getCoursePathSummary,
  type CoursePathSummaryResponse,
  type CoursePathNodeDTO, type CoursePathResponse, type PathGenerationTaskResponse,
  type PathLearningEvaluationResponse, type PathNodeResourceRequest,
} from '@/learning/api/path'
import {
  getPathLearningEvaluation,
  recordPathLearningEvent,
} from '@/learning/api/evaluation'
import { pollResourceStatus } from '@/resource/api/resource'
import type { ResourceTaskStatus } from '@/resource/types/resource'
import MarkdownPreview from '@/shared/components/MarkdownPreview.vue'

const router = useRouter()

const courseGoal = ref('')
const isGenerating = ref(false)
const generatingNodeId = ref<number | null>(null)
const completingNodeId = ref<number | null>(null)
const coursePath = ref<CoursePathResponse | null>(null)
const pathEvaluation = ref<PathLearningEvaluationResponse | null>(null)
const pathSummary = ref<CoursePathSummaryResponse | null>(null)
const summaryLoading = ref(false)
const nodeTaskStatuses = ref<Record<number, ResourceTaskStatus>>({})
const activePathTask = ref<PathGenerationTaskResponse | null>(null)
const quizScores = ref<Record<number, number | undefined>>({})
const submittingQuizNodeId = ref<number | null>(null)

const showOptimizeDialog = ref(false)
const isOptimizing = ref(false)
const customFeedback = ref('')
const currentOptimizeStep = ref(0)
const optimizationPromptKey = ref<string | null>(null)
const presetTags = [
  '测验成绩不理想，需要强化复习',
  '概念过于抽象，增加图解和案例',
  '时间紧迫，快速突破核心要点',
  '偏好实践，多提供代码实操'
]
const optimizeSteps = [
  '读取历史学习数据与反馈...',
  '提取画像并生成新策略...',
  '重构剩余节点与难度...',
  '校验拓扑前置依赖...'
]

const groupedStages = computed(() => {
  if (!coursePath.value) return []
  return coursePath.value.stages.map(stage => ({
    ...stage,
    nodes: coursePath.value!.nodes.filter(n => n.stage_id === stage.stage_id)
  }))
})

const signalSnapshot = computed(() => pathEvaluation.value?.signal_snapshot ?? {
  average_score: null,
  weak_topics: [],
  preferred_resources: [],
  negative_feedback: [],
  completed_resource_count: 0,
  viewed_resource_count: 0,
  active_minutes: 0,
  recommendations: [],
})

const evaluationScore = computed(() => {
  if (signalSnapshot.value.average_score !== null) return Math.round(signalSnapshot.value.average_score)
  if (!coursePath.value) return 0
  return Math.round(coursePath.value.overall_progress || 0)
})

const evaluationSummaryText = computed(() => {
  if (pathEvaluation.value?.needs_optimization) return '检测到薄弱点或负向反馈，建议触发诊断优化调整后续节点。'
  if (signalSnapshot.value.completed_resource_count > 0 || signalSnapshot.value.viewed_resource_count > 0) {
    return '已结合学习行为、测验表现和资源完成情况校准当前路径。'
  }
  return '开始学习资源或完成节点后，系统会生成更具体的掌握度判断。'
})

const needsPolling = computed(() => {
  if (!coursePath.value) return false
  return coursePath.value.nodes.some(n => n.resource_status === 'generating')
})

const shouldShowPathSummary = computed(() => {
  return !!pathSummary.value || (coursePath.value?.overall_progress ?? 0) >= 100
})

const summaryStatusText = computed(() => {
  if (!pathSummary.value) return '完成整条路径后生成'
  const map: Record<string, string> = {
    pending: '排队生成中',
    generating: '生成中',
    completed: '已完成',
    failed: '生成失败',
  }
  return map[pathSummary.value.status] || pathSummary.value.status
})

const masteryEntries = computed(() => {
  const scores = pathSummary.value?.mastery_scores || {}
  return Object.entries(scores).map(([nodeId, raw]) => {
    const score = Number(raw?.score ?? 0)
    return {
      nodeId,
      topic: String(raw?.topic || nodeId),
      score: Number.isFinite(score) ? Math.max(0, Math.min(100, Math.round(score))) : 0,
    }
  })
})

const evaluationColors = [
  { color: '#f56c6c', percentage: 40 },
  { color: '#e6a23c', percentage: 65 },
  { color: '#5cb87a', percentage: 80 },
  { color: '#1989fa', percentage: 100 },
]

let pollTimer: number | null = null
let summaryPollTimer: number | null = null

onMounted(() => {
  initializePathView()
})

onUnmounted(() => {
  stopPolling()
  stopSummaryPolling()
})

async function initializePathView() {
  const hasActivePath = await fetchExistingPath()
  if (hasActivePath) return
  await resumePathGenerationTask()
}

async function fetchExistingPath() {
  try {
    const res = await getActiveCoursePath()
    if (res.data.data) {
      coursePath.value = res.data.data
      activePathTask.value = null
      isGenerating.value = false
      await refreshPathEvaluation()
      await refreshPathSummary()
      await refreshTaskStatuses()
      if (needsPolling.value) startPolling()
      else stopPolling()
      return true
    }
  } catch (error) {}
  return false
}

async function resumePathGenerationTask() {
  try {
    const res = await getActiveCoursePathTask()
    const task = res.data.data
    if (!task || task.status === 'failed') return
    if (task.status === 'completed') {
      await fetchActivePath(true)
      return
    }
    activePathTask.value = task
    isGenerating.value = true
    startPolling()
  } catch (error) {}
}

async function fetchActivePath(silent = false) {
  try {
    const res = await getActiveCoursePath()
    if (res.data.data) {
      coursePath.value = res.data.data
      activePathTask.value = null
      isGenerating.value = false
      await refreshPathEvaluation()
      await refreshPathSummary()
      await refreshTaskStatuses()
      if (needsPolling.value) startPolling()
      else stopPolling()
    } else if (!silent) {
      coursePath.value = null
    }
  } catch (error) {}
}

async function handleGeneratePath() {
  if (!courseGoal.value.trim()) {
    ElMessage.warning('请输入目标')
    return
  }
  isGenerating.value = true
  coursePath.value = null
  pathEvaluation.value = null
  pathSummary.value = null
  stopPolling()
  stopSummaryPolling()
  try {
    const res = await generateCoursePath({ goal: courseGoal.value.trim(), module: 'mentor' })
    activePathTask.value = res.data.data
    startPolling()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '生成失败')
    isGenerating.value = false
  }
}

function resetPath() {
  courseGoal.value = ''
  coursePath.value = null
  pathEvaluation.value = null
  pathSummary.value = null
  activePathTask.value = null
  isGenerating.value = false
  stopPolling()
  stopSummaryPolling()
}

function startPolling() {
  if (pollTimer) return
  pollTimer = window.setInterval(async () => {
    if (activePathTask.value && isGenerating.value) {
      await refreshPathTaskStatus()
    } else {
      await fetchActivePath(true)
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function startSummaryPolling() {
  if (summaryPollTimer) return
  summaryPollTimer = window.setInterval(() => {
    void refreshPathSummary(true)
  }, 3000)
}

function stopSummaryPolling() {
  if (summaryPollTimer) {
    clearInterval(summaryPollTimer)
    summaryPollTimer = null
  }
}

async function refreshPathTaskStatus() {
  if (!activePathTask.value) return
  try {
    const res = await getCoursePathTaskStatus(activePathTask.value.task_id)
    const task = res.data.data
    activePathTask.value = task
    if (task.status === 'completed') {
      isGenerating.value = false
      await fetchActivePath(true)
      ElMessage.success('路线生成完毕！')
    } else if (task.status === 'failed') {
      isGenerating.value = false
      stopPolling()
      ElMessage.error(task.error_message || '生成失败')
    }
  } catch (error) {}
}

function getStatusText(status: string) {
  const map: Record<string, string> = {
    'completed': '已完成',
    'available': '可学习',
    'in_progress': '学习中',
    'locked': '已锁定'
  }
  return map[status] || status
}

function getNodeTaskStatus(node: CoursePathNodeDTO) {
  return node.resource_id ? nodeTaskStatuses.value[node.resource_id] : undefined
}

function getNodeProgress(node: CoursePathNodeDTO) {
  const taskStatus = getNodeTaskStatus(node)
  if (!taskStatus) return 0
  const progressMap: Record<string, number> = { pending: 0, planning: 20, generating: 60, reviewing: 80, completed: 100, partial_completed: 100, failed: 0 }
  return progressMap[taskStatus.status] ?? 0
}

async function refreshTaskStatuses() {
  const generatingNodes = coursePath.value?.nodes.filter(
    node => node.resource_status === 'generating' && node.resource_id
  ) || []
  await Promise.all(generatingNodes.map(async (node) => {
    if (!node.resource_id) return
    try {
      nodeTaskStatuses.value[node.resource_id] = (await pollResourceStatus(node.resource_id)).data.data
    } catch {}
  }))
}

async function handleGenerateResources(node: CoursePathNodeDTO) {
  if (generatingNodeId.value) return
  generatingNodeId.value = node.id
  try {
    const defaultPayload: PathNodeResourceRequest = {
      selected_agents: [
        { agent_id: 'content', enabled: true, priority: 0 },
        { agent_id: 'mindmap', enabled: true, priority: 1 },
        { agent_id: 'quiz', enabled: true, priority: 2 },
        { agent_id: 'code', enabled: true, priority: 4 },
        { agent_id: 'ppt', enabled: true, priority: 5 },
      ],
      agent_configs: {},
    }
    const res = await generatePathNodeResources(node.id, defaultPayload)
    if (coursePath.value) {
      const found = coursePath.value.nodes.find(n => n.id === node.id)
      if (found) {
        found.resource_status = res.data.data.status
        found.resource_id = res.data.data.resource_id
      }
    }
    await refreshTaskStatuses()
    startPolling()
  } catch (error: any) {
    ElMessage.error(error?.message || '生成资料失败')
  } finally {
    generatingNodeId.value = null
  }
}

async function handleStartLearning(node: CoursePathNodeDTO) {
  try {
    const res = await startCoursePathNode(node.id)
    coursePath.value = res.data.data
    viewResource(coursePath.value.nodes.find(item => item.id === node.id) || node)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '暂时无法开始学习')
  }
}

async function handleCompleteNode(node: CoursePathNodeDTO) {
  completingNodeId.value = node.id
  try {
    const res = await completeCoursePathNode(node.id)
    coursePath.value = res.data.data
    await recordNodeEvent(node, 'resource_completed')
    await refreshPathEvaluation()
    await refreshPathSummary()
    ElMessage.success(`「${node.title}」已完成，进度已更新`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '完成节点失败')
  } finally {
    completingNodeId.value = null
  }
}

async function handleSubmitQuiz(node: CoursePathNodeDTO) {
  if (!coursePath.value?.id) return
  const score = quizScores.value[node.id]
  if (score === undefined || !Number.isFinite(Number(score))) {
    ElMessage.warning('请输入 0-100 的测验分数')
    return
  }

  submittingQuizNodeId.value = node.id
  try {
    await recordPathLearningEvent(coursePath.value.id, {
      event_type: 'quiz_submitted',
      resource_id: node.resource_id,
      path_id: coursePath.value.id,
      path_node_id: node.id,
      node_id: node.node_id,
      course: coursePath.value.title,
      topic: node.title,
      score: Number(score),
      metadata: {
        source: 'learn_path_quiz_score',
      },
    })
    await refreshPathEvaluation()
    if (Number(score) < 65) {
      ElMessage.warning('已记录薄弱点，系统会在诊断优化时参考该分数')
    } else {
      ElMessage.success('测验分数已记录')
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '测验分数记录失败')
  } finally {
    submittingQuizNodeId.value = null
  }
}

function viewResource(node: CoursePathNodeDTO) {
  if (node.resource_id) {
    router.push({
      name: 'PathResourceDetail',
      params: { id: node.resource_id },
      query: {
        pathId: coursePath.value?.id,
        pathNodeId: node.id,
        nodeId: node.node_id,
      },
    })
  }
}

function openOptimizationDialog() {
  customFeedback.value = pathEvaluation.value?.optimization_tips?.join('\n') || ''
  showOptimizeDialog.value = true
}

function selectPresetTag(tag: string) {
  customFeedback.value = tag
}

async function handleOptimizePath() {
  const feedbackText = customFeedback.value.trim() || '依据画像诊断自动优化'
  showOptimizeDialog.value = false
  isOptimizing.value = true
  currentOptimizeStep.value = 0
  
  const interval = window.setInterval(() => {
    if (currentOptimizeStep.value < optimizeSteps.length - 1) {
      currentOptimizeStep.value++
    }
  }, 1200)

  try {
    await recordPathFeedback(feedbackText)
    const res = await adjustCoursePath({ feedback: feedbackText, use_learning_signals: true })
    await new Promise(resolve => setTimeout(resolve, 800))
    coursePath.value = res.data.data
    await refreshPathEvaluation()
    ElMessage.success('路径重新规划完成！')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '重构失败')
  } finally {
    clearInterval(interval)
    isOptimizing.value = false
    currentOptimizeStep.value = 0
  }
}

function formatStrategyReport(text: string) {
  if (!text) return ''
  let html = text.replace(/【(.*?)】/g, '<strong>【$1】</strong>')
  html = html.replace(/\n/g, '<br/>')
  html = html.replace(/(跳过|裁剪|无需|快速复习)/g, '<span class="text-success">$1</span>')
  html = html.replace(/(必须补充|核心短板|强相关)/g, '<span class="text-danger">$1</span>')
  return html
}

async function refreshPathEvaluation() {
  if (!coursePath.value?.id) {
    pathEvaluation.value = null
    optimizationPromptKey.value = null
    return
  }

  try {
    const res = await getPathLearningEvaluation(coursePath.value.id)
    pathEvaluation.value = res.data.data
    maybePromptOptimization()
  } catch (error) {
    console.warn('[LearnPath] load path evaluation failed:', error)
  }
}

function maybePromptOptimization() {
  if (!pathEvaluation.value?.needs_optimization) return
  const tips = pathEvaluation.value.optimization_tips || []
  const nextKey = `${coursePath.value?.id || 0}:${tips.join('|')}`
  if (!tips.length || optimizationPromptKey.value === nextKey || showOptimizeDialog.value || isOptimizing.value) {
    return
  }
  optimizationPromptKey.value = nextKey
  customFeedback.value = tips.join('\n')
  showOptimizeDialog.value = true
}

async function refreshPathSummary(silent = false) {
  if (!coursePath.value?.id || (coursePath.value.overall_progress ?? 0) < 100) {
    pathSummary.value = null
    stopSummaryPolling()
    return
  }

  summaryLoading.value = !silent
  try {
    const res = await getCoursePathSummary(coursePath.value.id)
    pathSummary.value = res.data.data
    if (pathSummary.value?.status === 'pending' || pathSummary.value?.status === 'generating') {
      startSummaryPolling()
    } else {
      stopSummaryPolling()
    }
  } catch (error) {
    console.warn('[LearnPath] load path summary failed:', error)
  } finally {
    summaryLoading.value = false
  }
}

async function recordNodeEvent(node: CoursePathNodeDTO, eventType: 'resource_viewed' | 'resource_completed') {
  if (!coursePath.value?.id) return
  try {
    await recordPathLearningEvent(coursePath.value.id, {
      event_type: eventType,
      resource_id: node.resource_id,
      path_id: coursePath.value.id,
      path_node_id: node.id,
      node_id: node.node_id,
      course: coursePath.value.title,
      topic: node.title,
      metadata: {
        source: 'learn_path_node',
        status: node.status,
      },
    })
  } catch (error) {
    console.warn('[LearnPath] record node event failed:', error)
  }
}

async function recordPathFeedback(feedback: string) {
  if (!coursePath.value?.id) return
  try {
    await recordPathLearningEvent(coursePath.value.id, {
      event_type: 'path_feedback',
      path_id: coursePath.value.id,
      course: coursePath.value.title,
      topic: coursePath.value.current_node_id,
      feedback,
      metadata: {
        source: 'learn_path_optimization',
      },
    })
  } catch (error) {
    console.warn('[LearnPath] record path feedback failed:', error)
  }
}
</script>

<style scoped>
/* 路径完成总结卡片 */
.summary-card {
  margin: 20px 0;
  padding: 24px;
}
.summary-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 600;
  color: var(--el-color-success);
  margin-bottom: 20px;
}
.summary-header-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.summary-header-text small {
  font-size: 12px;
  font-weight: 400;
  color: var(--el-text-color-secondary);
}
.summary-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
  padding: 30px 0;
  justify-content: center;
}
.summary-section {
  margin-bottom: 20px;
}
.summary-section h4 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--el-text-color-primary);
}
.mastery-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.mastery-item {
  display: flex;
  align-items: center;
  gap: 12px;
}
.mastery-topic {
  min-width: 120px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}
.mastery-item :deep(.el-progress) {
  flex: 1;
}
.weak-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.weak-tag {
  font-size: 14px;
}
.suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.suggestion-item strong {
  font-size: 15px;
  color: var(--el-text-color-primary);
}
.suggestion-item p {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin: 4px 0 0;
}
.summary-markdown {
  font-size: 14px;
  line-height: 1.8;
  color: var(--el-text-color-regular);
}
.summary-markdown :deep(h1),
.summary-markdown :deep(h2),
.summary-markdown :deep(h3) {
  margin-top: 16px;
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
}
.summary-markdown :deep(ul),
.summary-markdown :deep(ol) {
  padding-left: 20px;
}
.summary-error {
  text-align: center;
  padding: 20px;
  color: var(--el-color-danger);
}

.learning-evaluation-panel {
  margin: 22px 0 28px;
  padding: 24px;
  border: 1px solid rgba(59, 130, 246, 0.16);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(239, 246, 255, 0.88));
}

.lep-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.lep-eyebrow {
  margin: 0 0 8px;
  color: #2563EB;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.lep-main h3 {
  margin: 0 0 8px;
  color: #0F172A;
  font-size: 22px;
}

.lep-summary {
  max-width: 640px;
  margin: 0;
  color: #64748B;
  line-height: 1.8;
}

.lep-score {
  color: #0F172A;
  font-size: 22px;
  font-weight: 800;
}

.lep-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 18px;
}

.lep-metric {
  min-height: 82px;
  padding: 16px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
}

.lep-metric span {
  display: block;
  margin-bottom: 8px;
  color: #64748B;
  font-size: 13px;
}

.lep-metric strong {
  color: #0F172A;
  font-size: 20px;
}

.lep-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.lep-tips {
  display: grid;
  gap: 10px;
  margin-top: 16px;
}

.lep-tip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 12px;
  color: #1E3A8A;
  background: rgba(219, 234, 254, 0.72);
}
/* ==================== 
   Minimalist Clean Theme 
   ==================== */
.learn-path-container.minimalist-theme {
  --bg-main: #FAFAFA;
  --panel-bg: #FFFFFF;
  --border-color: #E5E7EB;
  --text-primary: #111827;
  --text-secondary: #4B5563;
  --text-muted: #9CA3AF;
  --primary-color: #2563EB;
  --success-color: #10B981;
  --warning-color: #F59E0B;
  --danger-color: #EF4444;
  --radius-md: 8px;
  --radius-lg: 12px;
  
  background-color: var(--bg-main);
  min-height: calc(100vh - 64px);
  padding: 40px;
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* Base Panel Style */
.clean-panel {
  background: var(--panel-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

/* Utilities */
.text-success { color: var(--success-color); font-weight: 600; }
.text-danger { color: var(--danger-color); font-weight: 600; }

/* ------------------ Hero Section ------------------ */
.hero-section {
  text-align: center;
  padding: 60px 40px;
  margin-bottom: 40px;
}
.hero-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 16px;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}
.hero-subtitle {
  color: var(--text-secondary);
  font-size: 16px;
  margin-bottom: 40px;
}
.search-box {
  display: flex;
  gap: 12px;
  justify-content: center;
  max-width: 600px;
  margin: 0 auto;
}
:deep(.clean-input .el-input__wrapper) {
  box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

/* ------------------ Loading State ------------------ */
.loading-state {
  padding: 60px 40px;
  text-align: center;
  margin-bottom: 40px;
}
.skeleton-header { max-width: 500px; margin: 0 auto 30px; }
.skeleton-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
.skeleton-card { height: 120px; border-radius: var(--radius-md); }
.loading-text { color: var(--text-secondary); font-size: 14px; }

/* ------------------ Path Display ------------------ */
.path-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border-color);
}
.path-title-group h2 {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 12px;
  letter-spacing: -0.5px;
}
.path-meta-tags {
  display: flex;
  gap: 8px;
}

/* ------------------ Diagnosis Report ------------------ */
.diagnosis-report-card {
  padding: 24px 32px;
  margin-bottom: 40px;
  border-left: 4px solid var(--primary-color);
}
.dr-header {
  margin-bottom: 16px;
}
.dr-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
  font-weight: 600;
  font-size: 16px;
}
.dr-icon {
  color: var(--primary-color);
  font-size: 18px;
}
.dr-text-content {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-secondary);
}

/* ------------------ Timeline Layout ------------------ */
.timeline-container {
  padding: 20px 0;
}
.stage-block {
  margin-bottom: 48px;
}
.stage-info {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 24px;
}
.stage-number {
  width: 32px;
  height: 32px;
  background: var(--text-primary);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}
.stage-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 6px;
}
.stage-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
}

.stage-nodes {
  padding-left: 16px;
}
.node-wrapper {
  display: flex;
  gap: 24px;
  position: relative;
  margin-bottom: 24px;
}
.node-wrapper:last-child {
  margin-bottom: 0;
}

/* Indicator */
.node-indicator {
  position: relative;
  width: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.indicator-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--panel-bg);
  border: 2px solid var(--border-color);
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 24px; /* Align with card header */
  font-size: 10px;
  color: white;
}
.indicator-line {
  position: absolute;
  top: 40px;
  bottom: -24px; /* Extend to next node */
  left: 50%;
  transform: translateX(-50%);
  width: 2px;
  background: var(--border-color);
  z-index: 0;
}
.node-wrapper:last-child .indicator-line {
  display: none;
}

/* Status colors */
.status-completed .indicator-dot { background: var(--success-color); border-color: var(--success-color); }
.status-available .indicator-dot { border-color: var(--primary-color); }
.status-in_progress .indicator-dot { border-color: var(--primary-color); background: var(--primary-color); }
.status-locked .indicator-dot { background: var(--border-color); border-color: var(--border-color); }

/* Node Card */
.node-card {
  flex: 1;
  padding: 20px 24px;
  transition: box-shadow 0.2s;
}
.node-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}
.status-locked .node-card {
  background: var(--bg-main);
  border-style: dashed;
  opacity: 0.7;
}

.nc-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}
.nc-title {
  font-weight: 600;
  font-size: 16px;
}
.nc-status-text {
  font-size: 12px;
  font-weight: 500;
}
.text-completed { color: var(--success-color); }
.text-available { color: var(--primary-color); }
.text-in_progress { color: var(--primary-color); }
.text-locked { color: var(--text-muted); }

.nc-body {
  margin-bottom: 16px;
}
.nc-summary {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
}
.nc-generating-state {
  margin-top: 12px;
  font-size: 12px;
  color: var(--primary-color);
  display: flex;
  align-items: center;
  gap: 12px;
}
.clean-progress {
  flex: 1;
}

.nc-footer {
  display: flex;
  gap: 12px;
  align-items: center;
}
.nc-actions-group {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.quiz-score-submit {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.quiz-score-submit :deep(.el-input-number) {
  width: 116px;
}
.locked-hint {
  font-size: 12px;
  color: var(--text-muted);
}

/* ------------------ Overlays & Dialogs ------------------ */
.preset-section, .feedback-input-section { margin-bottom: 20px; }
.section-label { font-size: 13px; font-weight: 600; margin-bottom: 8px; display: block; }
.preset-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.clean-tag-clickable { cursor: pointer; border-radius: var(--radius-md); }

.clean-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  z-index: 9999; display: flex; align-items: center; justify-content: center;
}
.loader-box {
  padding: 40px; text-align: center; width: 400px;
}
.loader-icon { font-size: 40px; color: var(--primary-color); margin-bottom: 20px; }
.loader-title { font-size: 18px; font-weight: 600; margin: 0 0 8px; }
.loader-sub { font-size: 13px; color: var(--text-secondary); margin: 0 0 24px; }
.clean-steps { display: flex; flex-direction: column; gap: 12px; text-align: left; }
.c-step { font-size: 13px; color: var(--text-muted); display: flex; align-items: center; gap: 8px; }
.c-step.active { color: var(--text-primary); font-weight: 500; }
.c-step.done { color: var(--success-color); }

@media (max-width: 768px) {
  .learning-evaluation-panel {
    padding: 18px;
  }

  .lep-main {
    align-items: flex-start;
    flex-direction: column;
  }

  .lep-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
