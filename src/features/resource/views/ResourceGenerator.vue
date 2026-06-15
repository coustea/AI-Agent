<template>
  <div class="elegant-generator-layout">
    <div class="resource-generator-ambient" aria-hidden="true">
      <span class="ambient-glow glow-blue"></span>
      <span class="ambient-glow glow-emerald"></span>
      <span class="ambient-glow glow-indigo"></span>
      <span class="resource-pattern-bg"></span>
    </div>

    <div v-show="currentPhase === 'input'" class="floating-history-btn" @click="router.push('/resource-history')">
      <el-icon><Timer /></el-icon>
      <span>历史记录</span>
    </div>

    <transition name="page-slide" mode="out-in">

      <ResourceInput
        v-if="currentPhase === 'input'"
        key="input"
        v-model="naturalInput"
        @submit="goToPersonalize"
      />

      <ResourcePersonalize
        v-else-if="currentPhase === 'personalize'"
        key="personalize"
        v-model:learningScenario="learningScenario"
        v-model:enabledAgentIds="enabledAgentIds"
        v-model:agentConfigs="agentConfigs"
        @back="currentPhase = 'input'"
        @launch="startGeneration"
      />

      <ResourceGenerating
        v-else-if="currentPhase === 'generating'"
        key="generating"
        :natural-input="naturalInput"
        :dag-node-states="dagNodeStates"
        :selected-dag-node-id="selectedDagNodeId"
        :overall-progress="overallProgress"
        :latest-workflow-message="latestWorkflowMessage"
        :generated-resources="generatedResources"
        :dag-selected-agent-ids="dagSelectedAgentIds"
        :generation-error="generationError"
        :plan-steps="planSteps"
        :plan-ready="planReady"
        :dispatch-cards="dispatchCards"
        :latest-artifact-agent-id="latestArtifactAgentId"
        :visible-workflow-nodes="visibleWorkflowNodes"
        @select-node="selectDagNode"
        @open-resource="openResourceByType"
      />

      <ResourceResult
        v-else-if="currentPhase === 'result'"
        key="result"
        :final-bundle="finalBundle"
        :generated-resources="generatedResources"
        :result-warning="resultWarning"
        @reset="resetGenerator"
        @preview="handlePreview"
      />

    </transition>

    <el-dialog v-model="previewVisible" :title="previewData ? getResourceTypeLabel(previewData.agentId) : '资源预览'" width="78%" top="6vh" destroy-on-close :class="['elegant-dialog', { 'is-ppt-dialog': previewData?.agentId === 'ppt' }]">
      <div v-if="previewData" class="preview-dialog-body" :class="{ 'is-ppt-preview': previewData.agentId === 'ppt' }">
        <MindmapView v-if="previewData.agentId === 'mindmap'" :result-data="previewData.resultData" />
        <QuizView v-else-if="previewData.agentId === 'quiz'" :result-data="previewData.resultData" />
        <CodeView v-else-if="previewData.agentId === 'code'" :result-data="previewData.resultData" />
        <ReadingView v-else-if="previewData.agentId === 'reading'" :result-data="previewData.resultData" />
        <PptView v-else-if="previewData.agentId === 'ppt'" :result-data="previewData.resultData" />
        <MarkdownView v-else :result-data="previewData.resultData" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, reactive, computed, onMounted, onBeforeUnmount, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Timer } from '@element-plus/icons-vue'

import ResourceInput from '@/features/resource/views/ResourceInput.vue'
import ResourcePersonalize from '@/features/resource/views/ResourcePersonalize.vue'
import ResourceGenerating from '@/features/resource/views/ResourceGenerating.vue'
import ResourceResult from '@/features/resource/views/ResourceResult.vue'
import './resource-generator.css'

import MindmapView from '@/features/resource/components/MindmapView.vue'
import MarkdownView from '@/features/resource/components/MarkdownView.vue'
import QuizView from '@/features/resource/components/QuizView.vue'
import CodeView from '@/features/resource/components/CodeView.vue'
import ReadingView from '@/features/resource/components/ReadingView.vue'
import PptView from '@/features/resource/components/PptView.vue'

import {
  startResourceGeneration,
  pollResourceStatus,
  getResourceBundle,
  streamResourceEvents,
} from '@/features/resource/api/resource'

import type {
  LearningScenario,
  ResourceAgentId,
  ResourceTaskStatus,
  ResourceGenerationRequest,
  ResourceStreamEvent,
} from '@/features/resource/model/resource'

import {
  PPT_AGENT_ID,
  PRE_REVIEW_AGENT_ID,
  PPT_REVIEW_AGENT_ID,
  COORDINATOR_AGENT_ID,
  BUNDLE_AGENT_ID,
  SYSTEM_AGENT_IDS,
  AGENT_DISPLAY,
  getResourceTypeLabel,
  getAgentOutputFormat,
  createDagNode,
  type AnyAgentConfigs,
  type DagNodeState,
} from '@/features/resource/model/ResourceGeneratorConstants'

defineOptions({ name: 'ResourceGenerator' })

const route = useRoute()
const router = useRouter()

type Phase = 'input' | 'personalize' | 'generating' | 'result'
const currentPhase = ref<Phase>('input')

const naturalInput = ref('')
const learningScenario = ref<LearningScenario>('daily_review')
const enabledAgentIds = ref<ResourceAgentId[]>(['content', 'mindmap', 'code', 'quiz', 'reading', 'ppt'])

const agentConfigs = reactive<AnyAgentConfigs>({
  content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'full_coverage', depth_level: 'standard' },
  mindmap: { map_type: 'knowledge_tree', max_depth: 3, highlight_weak: true, expand_weak_points: false, include_prerequisites: false },
  quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 50, exam_style: 'school', include_analysis: true, question_types: ['single', 'multiple', 'judge'] },
  code: { programming_language: 'python', case_type: 'basic_demo', difficulty: 'beginner' },
  reading: { reading_depth: 'course_extended', max_items: 3, language_preference: 'chinese' },
  ppt: { page_count: 6, difficulty: 'intermediate', output_format: 'preview' },
})

const goToPersonalize = () => {
  if (!naturalInput.value.trim()) return
  currentPhase.value = 'personalize'
}

const dagSelectedAgentIds = computed(() => {
  return enabledAgentIds.value.filter(id => !['master', 'reviewer', 'assembler'].includes(id))
})

const dagNodeStates = ref<Record<string, DagNodeState>>({})
const selectedDagNodeId = ref<string | null>(null)
const overallProgress = ref(0)
const latestWorkflowMessage = ref('')
const generatedResources = shallowRef<Array<Record<string, any>>>([])
const finalBundle = shallowRef<any | null>(null)
const generationError = ref<string | null>(null)
const resultWarning = ref('')

type PlanStepStatus = 'pending' | 'created' | 'dispatching' | 'running' | 'finished'
type PlanStepState = {
  id: string; agentId: ResourceAgentId; title: string; summary: string;
  input: string; output: string; status: PlanStepStatus
}
type DispatchCardState = {
  id: string; stepId: string; from: 'planning' | 'coordinator';
  to: string; title: string; active: boolean
}

const planReady = ref(false)
const planSteps = ref<PlanStepState[]>([])
const dispatchCards = ref<DispatchCardState[]>([])
const latestArtifactAgentId = ref<string | null>(null)

const isGenerating = ref(false)
const generationFinalized = ref(false)
const activeResourceId = ref<number | null>(null)
const pollingInterval = ref<ReturnType<typeof setInterval> | null>(null)
const resourceStreamController = ref<EventSource | null>(null)

const planRevealStarted = ref(false)
const planRevealTimers: ReturnType<typeof setTimeout>[] = []
const dispatchStarted = ref(false)

function clearPlanRevealTimers() {
  while (planRevealTimers.length) {
    const timer = planRevealTimers.pop()
    if (timer) clearTimeout(timer)
  }
}

function getPlanStepTitle(agentId: string) {
  const map: Record<string, string> = {
    content: '生成课程讲解文档', mindmap: '生成知识结构思维导图',
    quiz: '生成个性化练习题', code: '生成代码实操案例',
    reading: '生成拓展阅读材料', ppt: '生成 PPT 文稿',
  }
  return map[agentId] || `${agentId} 资源生成`
}

function getPlanStepSummary(agentId: string) {
  const map: Record<string, string> = {
    content: '包含概念、原理、示例与易错点讲解',
    mindmap: '构建知识结构、前置概念与关联关系',
    quiz: '按难度生成练习题，并附答案与解析',
    code: '提供可运行代码、注释和实操步骤',
    reading: '推荐拓展文章与延伸知识点',
    ppt: '汇总知识结构并生成可视化课件文稿',
  }
  return map[agentId] || '根据教学蓝图生成个性化学习资源'
}

function buildFallbackPlanSteps(): PlanStepState[] {
  return dagSelectedAgentIds.value.map((agentId) => ({
    id: `plan-${agentId}`, agentId,
    title: getPlanStepTitle(agentId), summary: getPlanStepSummary(agentId),
    input: '学习需求 / 用户画像 / 教学蓝图', output: getAgentOutputFormat(agentId),
    status: 'pending',
  }))
}

function ensurePlanSteps() {
  if (!planSteps.value.length) planSteps.value = buildFallbackPlanSteps()
}

function revealPlanStepsStaggered() {
  ensurePlanSteps()
  if (planRevealStarted.value) return
  planRevealStarted.value = true
  clearPlanRevealTimers()
  planSteps.value.forEach((step, index) => {
    const timer = setTimeout(() => {
      planSteps.value = planSteps.value.map(item => (
        item.id === step.id && item.status === 'pending'
          ? { ...item, status: 'created' }
          : item
      ))
    }, 180 + index * 220)
    planRevealTimers.push(timer)
  })
}

function markPlanStep(agentId: string, status: PlanStepStatus) {
  ensurePlanSteps()
  planSteps.value = planSteps.value.map(step => (
    step.agentId === agentId ? { ...step, status } : step
  ))
}

function selectDagNode(id: string) {
  selectedDagNodeId.value = id
}

function triggerDispatchCards(agentIds: string[]) {
  ensurePlanSteps()
  dispatchCards.value = agentIds.map((agentId, index) => {
    const step = planSteps.value.find(item => item.agentId === agentId)
    return {
      id: `dispatch-${agentId}-${Date.now()}-${index}`,
      stepId: step?.id || `plan-${agentId}`,
      from: 'coordinator', to: agentId,
      title: step?.title || getPlanStepTitle(agentId),
      active: true,
    }
  })
  window.setTimeout(() => { dispatchCards.value = [] }, 1400)
}

function handlePlanningAnimation(event: ResourceStreamEvent) {
  ensurePlanSteps()
  if (event.status === 'running') revealPlanStepsStaggered()
  if (event.status === 'finished') {
    planReady.value = true
    planSteps.value = planSteps.value.map(step => (
      step.status === 'pending' ? { ...step, status: 'created' } : step
    ))
  }
}

function handleCoordinatorAnimation(event: ResourceStreamEvent) {
  if (event.status !== 'running' || dispatchStarted.value) return
  dispatchStarted.value = true
  const workerIds = baseGenerationAgentIds.value
  workerIds.forEach(agentId => markPlanStep(agentId, 'dispatching'))
  triggerDispatchCards(workerIds)
  window.setTimeout(() => { workerIds.forEach(agentId => markPlanStep(agentId, 'running')) }, 900)
}

function handleWorkerAnimation(event: ResourceStreamEvent) {
  if (!event.agent_id) return
  const agentId = event.agent_id
  if (!dagSelectedAgentIds.value.includes(agentId as ResourceAgentId)) return
  if (!dispatchStarted.value && (baseGenerationAgentIds.value as string[]).includes(agentId)) {
    dispatchStarted.value = true
    triggerDispatchCards(baseGenerationAgentIds.value)
  }
  if (event.status === 'finished') markPlanStep(agentId, 'finished')
  else if (event.status === 'running') markPlanStep(agentId, 'running')
}

function handleArtifactReadyAnimation(event: ResourceStreamEvent) {
  if (!event.agent_id) return
  markPlanStep(event.agent_id, 'finished')
  latestArtifactAgentId.value = event.agent_id
  window.setTimeout(() => {
    if (latestArtifactAgentId.value === event.agent_id) latestArtifactAgentId.value = null
  }, 1400)
}

function handleWorkflowAnimation(event: ResourceStreamEvent) {
  if (!event.agent_id) return
  if (event.agent_id === 'planning') handlePlanningAnimation(event)
  if (event.agent_id === COORDINATOR_AGENT_ID) handleCoordinatorAnimation(event)
  if (event.event_type === 'agent.artifact_ready') handleArtifactReadyAnimation(event)
  handleWorkerAnimation(event)
}

const baseGenerationAgentIds = computed(() => dagSelectedAgentIds.value.filter(id => id !== PPT_AGENT_ID))

const dagNodesV2 = computed<DagNodeState[]>(() => {
  const selected = dagSelectedAgentIds.value
  const nodes: DagNodeState[] = []
  nodes.push(dagNodeStates.value['planning'] || { id: 'planning', label: '规划任务', icon: '🎯', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: true })
  nodes.push(dagNodeStates.value[COORDINATOR_AGENT_ID] || { id: COORDINATOR_AGENT_ID, label: '并行调度中枢', icon: '⚙️', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: true })
  for (const agentId of baseGenerationAgentIds.value) {
    const display = AGENT_DISPLAY[agentId]
    if (!display) continue
    nodes.push(dagNodeStates.value[agentId] || { id: agentId, label: display.label, icon: display.icon, status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: false })
  }
  nodes.push(dagNodeStates.value[PRE_REVIEW_AGENT_ID] || { id: PRE_REVIEW_AGENT_ID, label: '前置安全审核', icon: '🛡️', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: true })
  if (selected.includes(PPT_AGENT_ID)) {
    nodes.push(dagNodeStates.value[PPT_AGENT_ID] || { id: PPT_AGENT_ID, label: '演示文稿助手', icon: '📊', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: false })
    nodes.push(dagNodeStates.value[PPT_REVIEW_AGENT_ID] || { id: PPT_REVIEW_AGENT_ID, label: 'PPT 安全审核', icon: '🔍', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: true })
  }
  nodes.push(dagNodeStates.value[BUNDLE_AGENT_ID] || { id: BUNDLE_AGENT_ID, label: '资源组装', icon: '📦', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: true })
  return nodes
})

function hasNodeEntered(node?: DagNodeState) {
  if (!node) return false
  if (node.id === 'planning') return true
  return node.status !== 'waiting' || node.progress > 0 || Boolean(node.currentMessage) || (node.stepHistory?.length || 0) > 0 || hasGeneratedResource(node.id)
}

const visibleWorkflowNodes = computed(() => dagNodesV2.value.filter(node => hasNodeEntered(node)))

function getStageNode(id: string) {
  return dagNodeStates.value[id] || createDagNode(id, SYSTEM_AGENT_IDS.includes(id))
}

function hasGeneratedResource(type: string) {
  return generatedResources.value.some(resource => resource.type === type)
}

function openResourceByType(type: string) {
  const resource = generatedResources.value.find(item => item.type === type)
  if (resource) previewGeneratedResource(resource)
}

const previewGeneratedResource = (resource: any) => {
  handlePreview({ agentId: resource.type, resultData: resource.content, title: resource.title || getResourceTypeLabel(resource.type) })
}

function updateOverallProgressFromDag() {
  const stages = [
    { weight: 15, progress: getStageNode('planning').progress },
    { weight: 45, progress: parallelPoolNodes.value.length ? parallelPoolNodes.value.reduce((sum, node) => sum + node.progress, 0) / parallelPoolNodes.value.length : 0 },
    { weight: 10, progress: getStageNode(PRE_REVIEW_AGENT_ID).progress },
    ...(dagSelectedAgentIds.value.includes(PPT_AGENT_ID as ResourceAgentId) ? [
      { weight: 15, progress: getStageNode(PPT_AGENT_ID).progress },
      { weight: 5, progress: getStageNode(PPT_REVIEW_AGENT_ID).progress },
    ] : []),
    { weight: 10, progress: getStageNode(BUNDLE_AGENT_ID).progress },
  ]
  const weightTotal = stages.reduce((sum, item) => sum + item.weight, 0)
  const weighted = stages.reduce((sum, item) => sum + item.progress * item.weight, 0)
  overallProgress.value = Math.round(weighted / weightTotal)
}

const parallelPoolNodes = computed(() => {
  const agentStatusRank: Record<DagNodeState['status'], number> = { failed: 0, running: 1, success: 2, waiting: 3, skipped: 4 }
  return baseGenerationAgentIds.value.map(agentId => getStageNode(agentId)).sort((a, b) => {
    const rankDiff = agentStatusRank[a.status] - agentStatusRank[b.status]
    if (rankDiff !== 0) return rankDiff
    return b.progress - a.progress
  })
})

function initializeWaitingNodes() {
  const nodes: Record<string, DagNodeState> = {
    planning: createDagNode('planning', true),
    [COORDINATOR_AGENT_ID]: createDagNode(COORDINATOR_AGENT_ID, true),
    [PRE_REVIEW_AGENT_ID]: createDagNode(PRE_REVIEW_AGENT_ID, true),
    [BUNDLE_AGENT_ID]: createDagNode(BUNDLE_AGENT_ID, true),
  }
  if (enabledAgentIds.value.includes(PPT_AGENT_ID as ResourceAgentId)) {
    nodes[PPT_REVIEW_AGENT_ID] = createDagNode(PPT_REVIEW_AGENT_ID, true)
  }
  enabledAgentIds.value.forEach((agentId) => { nodes[agentId] = createDagNode(agentId, false) })
  dagNodeStates.value = nodes
  selectedDagNodeId.value = null
  planSteps.value = buildFallbackPlanSteps()
  planReady.value = false
  dispatchStarted.value = false
  planRevealStarted.value = false
  latestArtifactAgentId.value = null
  updateOverallProgressFromDag()
}

function normalizeEventStatus(status?: string | null): DagNodeState['status'] | undefined {
  if (!status) return undefined
  if (status === 'finished') return 'success'
  if (status === 'failed') return 'failed'
  if (status === 'skipped') return 'skipped'
  if (status === 'running') return 'running'
  return undefined
}

function appendAgentEventLog(node: DagNodeState, event: ResourceStreamEvent) {
  if (!event.message?.trim()) return

  const eventStatus = normalizeEventStatus(event.status)
  const logs = node.eventLogs || []
  const last = logs[logs.length - 1]
  const eventPhase = event.phase ?? undefined
  const eventElapsedMs = event.elapsed_ms ?? undefined

  const sameMessage = last && last.message === event.message && last.phase === eventPhase

  if (sameMessage) {
    node.eventLogs = [
      ...logs.slice(0, -1),
      {
        ...last,
        status: eventStatus || last.status,
        progress: event.progress ?? last.progress,
        elapsedMs: eventElapsedMs ?? last.elapsedMs,
        timestamp: Date.now(),
      },
    ]
    return
  }

  node.eventLogs = [
    ...logs.slice(-11),
    {
      id: `${event.agent_id || node.id}-${event.event_type || 'event'}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      eventType: event.event_type,
      phase: eventPhase,
      message: event.message,
      status: eventStatus || node.status,
      progress: event.progress,
      elapsedMs: eventElapsedMs,
      timestamp: Date.now(),
    },
  ]
}

function applyAgentEvent(event: ResourceStreamEvent) {
  if (!event.agent_id) return
  const node = dagNodeStates.value[event.agent_id] || createDagNode(event.agent_id, SYSTEM_AGENT_IDS.includes(event.agent_id))
  if (event.status) node.status = event.status === 'finished' ? 'success' : event.status
  if (event.progress != null) node.progress = Math.max(node.progress, event.progress)
  if (event.phase) node.phase = event.phase
  if (event.elapsed_ms != null) node.elapsedMs = event.elapsed_ms
  if (event.metrics) node.metrics = { ...(node.metrics || {}), ...event.metrics }
  if (event.artifact_id) node.artifactId = event.artifact_id
  if (event.metrics?.review_warning) node.reviewWarning = true
  node.lastUpdatedAt = Date.now()
  if (event.message) {
    node.currentMessage = event.message
    if (node.stepHistory[node.stepHistory.length - 1] !== event.message) {
      node.stepHistory = [...node.stepHistory.slice(-7), event.message]
    }
    appendAgentEventLog(node, event)
  }
  dagNodeStates.value[event.agent_id] = node
  handleWorkflowAnimation(event)
  updateOverallProgressFromDag()
}

function applyTaskStatus(taskStatus: ResourceTaskStatus) {
  if (Array.isArray(taskStatus.selected_agents) && taskStatus.selected_agents.length) {
    enabledAgentIds.value = taskStatus.selected_agents.filter(id => AGENT_DISPLAY[id]) as ResourceAgentId[]
  }
  if (Array.isArray(taskStatus.resources)) generatedResources.value = taskStatus.resources
  if (taskStatus.current_message) latestWorkflowMessage.value = taskStatus.current_message
  if (taskStatus.agent_snapshots) {
    Object.values(taskStatus.agent_snapshots).forEach((snapshot) => {
      if (snapshot.agent_id) {
        applyAgentEvent({
          event_type: snapshot.event_type || 'agent.snapshot', agent_id: snapshot.agent_id,
          status: snapshot.status || null, message: snapshot.message || null,
          progress: snapshot.progress ?? 0, run_id: snapshot.run_id || null,
          span_id: snapshot.span_id || null, phase: snapshot.phase || null,
          elapsed_ms: snapshot.elapsed_ms || null, metrics: snapshot.metrics || {},
          dependency: snapshot.dependency || null, artifact_id: snapshot.artifact_id || null,
          success: snapshot.success || null, timestamp: snapshot.timestamp || Date.now() / 1000,
        })
      }
    })
  }
  if (typeof taskStatus.overall_progress === 'number') {
    overallProgress.value = Math.max(0, Math.min(100, Math.round(taskStatus.overall_progress)))
  } else {
    updateOverallProgressFromDag()
  }
}

async function completeGeneration(resourceId: number, taskStatus: ResourceTaskStatus) {
  if (generationFinalized.value) return
  generationFinalized.value = true
  stopPolling()
  stopResourceStream()
  if (taskStatus.status === 'completed' || taskStatus.status === 'partial_completed') {
    const bundle = (await getResourceBundle(resourceId)).data.data
    finalBundle.value = bundle
    generatedResources.value = bundle.resources || taskStatus.resources || []
    resultWarning.value = taskStatus.status === 'partial_completed' ? '部分资源生成失败或质量审查未通过，以下已完成内容仍可查看。' : ''
    isGenerating.value = false
    currentPhase.value = 'result'
    return
  }
  generationError.value = '资源生成失败，暂无可展示内容'
  isGenerating.value = false
  ElMessage.error(generationError.value || '资源生成失败，暂无可展示内容')
}

async function checkStatusOnce(resourceId: number) {
  const taskStatus = (await pollResourceStatus(resourceId)).data.data
  applyTaskStatus(taskStatus)
  if (['completed', 'partial_completed', 'failed'].includes(taskStatus.status)) {
    await completeGeneration(resourceId, taskStatus)
  }
}

function startPollingFallback(resourceId: number) {
  if (pollingInterval.value) return
  void checkStatusOnce(resourceId)
  pollingInterval.value = setInterval(() => {
    void checkStatusOnce(resourceId).catch((err: any) => {
      stopPolling()
      generationError.value = err.message || '生成中断，请稍后重试'
      isGenerating.value = false
      ElMessage.error(generationError.value || '生成中断，请稍后重试')
    })
  }, 1500)
}

function syncStatusSoon(resourceId: number) {
  void checkStatusOnce(resourceId).catch((err: any) => { console.warn('[ResourceGenerator] 状态同步失败:', err) })
}

function startResourceStream(resourceId: number) {
  stopResourceStream()
  startPollingFallback(resourceId)
  resourceStreamController.value = streamResourceEvents(
    resourceId,
    (event) => {
      applyAgentEvent(event)
      if (event.message) latestWorkflowMessage.value = event.message
      if (event.status === 'finished') syncStatusSoon(resourceId)
    },
    (event) => {
      if (isGenerating.value && !generationFinalized.value) {
        void checkStatusOnce(resourceId).catch(() => {
          void completeGeneration(resourceId, { resource_id: resourceId, status: event.success ? 'completed' : 'failed' })
        })
      }
    },
    (err) => {
      if (!isGenerating.value || generationFinalized.value) return
      console.warn('[ResourceGenerator] SSE 连接失败，切换到轮询兜底:', err)
      latestWorkflowMessage.value = '实时连接中断，已切换到状态同步模式'
      startPollingFallback(resourceId)
    },
  )
}

const startGeneration = async () => {
  currentPhase.value = 'generating'
  resetGenerationState()
  initializeWaitingNodes()
  isGenerating.value = true

  try {
    const requestParams: ResourceGenerationRequest = {
      learning_need: naturalInput.value,
      learning_scenario: learningScenario.value,
      selected_agents: enabledAgentIds.value.map((id, index) => ({ agent_id: id, enabled: true, priority: index })).filter(a => a.enabled),
      agent_configs: { content: agentConfigs.content, mindmap: agentConfigs.mindmap, quiz: agentConfigs.quiz, code: agentConfigs.code, reading: agentConfigs.reading, ppt: agentConfigs.ppt } as any,
    }
    const { resource_id } = (await startResourceGeneration(requestParams)).data.data
    activeResourceId.value = resource_id
    startResourceStream(resource_id)
  } catch (err: any) {
    generationError.value = err.message || '生成请求失败'
    isGenerating.value = false
    ElMessage.error(generationError.value || '生成请求失败')
  }
}

const resetGenerationState = () => {
  generatedResources.value = []
  finalBundle.value = null
  generationError.value = null
  resultWarning.value = ''
  overallProgress.value = 0
  latestWorkflowMessage.value = ''
  isGenerating.value = false
  generationFinalized.value = false
  activeResourceId.value = null
  dagNodeStates.value = {}
  selectedDagNodeId.value = null
  planSteps.value = []
  dispatchCards.value = []
  planReady.value = false
  dispatchStarted.value = false
  planRevealStarted.value = false
  latestArtifactAgentId.value = null
  clearPlanRevealTimers()
}

const stopPolling = () => {
  if (pollingInterval.value) { clearInterval(pollingInterval.value); pollingInterval.value = null }
}

const stopResourceStream = () => {
  if (resourceStreamController.value) { resourceStreamController.value.close(); resourceStreamController.value = null }
}

const pauseLiveGenerationUpdates = () => { stopPolling(); stopResourceStream() }

const resumeLiveGenerationUpdates = async () => {
  const resourceId = activeResourceId.value
  if (!resourceId || !isGenerating.value || generationFinalized.value) return
  try { await checkStatusOnce(resourceId) } catch { latestWorkflowMessage.value = '状态同步失败，正在重试实时连接' }
  if (activeResourceId.value === resourceId && isGenerating.value && !generationFinalized.value) startResourceStream(resourceId)
}

const previewVisible = ref(false)
const previewData = ref<any>(null)
const handlePreview = (data: any) => { previewData.value = data; previewVisible.value = true }

const resetGenerator = () => {
  stopPolling(); stopResourceStream(); naturalInput.value = ''; resetGenerationState(); currentPhase.value = 'input'
}

onMounted(() => {
  const prompt = route.query.prompt
  if (prompt) naturalInput.value = String(prompt)
})

onActivated(() => { void resumeLiveGenerationUpdates() })
onDeactivated(() => { stopResourceStream() })
onBeforeUnmount(() => { pauseLiveGenerationUpdates() })
</script>

<style scoped>
.elegant-generator-layout {
  --color-primary: var(--cat-resource);
  --color-primary-hover: #059669;
  --color-primary-soft: var(--cat-resource-soft);
  --color-primary-border: #6EE7B7;
  --color-primary-text: #047857;
  --gradient-primary: var(--gradient-resource);
  min-height: calc(100vh - 64px);
  position: relative;
  background: var(--color-bg);
  overflow-x: hidden;
  font-family: var(--font-sans);
}

.floating-history-btn {
  position: absolute; top: 24px; right: 24px; z-index: 50;
  display: flex; align-items: center; gap: 8px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 20px;
  color: var(--color-primary); font-weight: 600; font-size: 0.9rem;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.floating-history-btn:hover {
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.phase-view { position: relative; width: 100%; min-height: calc(100vh - 64px); display: flex; flex-direction: column; background: transparent; backdrop-filter: blur(20px); }
.page-slide-enter-active, .page-slide-leave-active { transition: opacity 0.4s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.page-slide-enter-from { opacity: 0; transform: translateY(30px) scale(0.98); }
.page-slide-leave-to { opacity: 0; transform: translateY(-30px) scale(1.02); }

.elegant-dialog :deep(.el-dialog) { border-radius: var(--radius-2xl); overflow: hidden; box-shadow: 0 12px 48px rgba(0, 0, 0, 0.08); background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.5); }
.elegant-dialog :deep(.el-dialog__header) { padding: var(--space-6) var(--space-8) var(--space-5); margin-right: 0; border-bottom: 1px solid rgba(0, 0, 0, 0.05); }
.elegant-dialog :deep(.el-dialog__title) { font-weight: var(--weight-extrabold); font-size: 1.2rem; color: var(--color-text); }
.elegant-dialog :deep(.el-dialog__body) { padding: var(--space-8); background: transparent; }
.elegant-dialog :deep(.resource-card-wrapper) { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; border-radius: 0 !important; }
.elegant-dialog :deep(.resource-card-wrapper:hover) { background: transparent !important; box-shadow: none !important; border: none !important; }
.is-ppt-dialog :deep(.el-dialog__body) { padding: 0 !important; background: transparent !important; }
.preview-dialog-body.is-ppt-preview { padding: 0 !important; background: transparent !important; border: none !important; box-shadow: none !important; }
.preview-dialog-body.is-ppt-preview :deep(.player-wrapper) { margin-top: 0 !important; border: none !important; border-radius: 0 !important; }

h1, h2, h3, h4 { letter-spacing: -0.025em; color: var(--color-text); font-weight: var(--weight-bold); }
p, .card-summary, .s-desc { line-height: 1.65; letter-spacing: 0.01em; color: var(--color-text-secondary); }
</style>
