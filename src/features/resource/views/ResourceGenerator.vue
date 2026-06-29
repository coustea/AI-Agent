<template>
  <div class="elegant-generator-layout">
    <div class="resource-generator-ambient" aria-hidden="true">
      <span class="ambient-glow glow-blue"></span>
      <span class="ambient-glow glow-emerald"></span>
      <span class="ambient-glow glow-indigo"></span>
      <span class="resource-pattern-bg"></span>
    </div>

    <button
      v-show="currentPhase === 'input'"
      class="floating-history-btn btn btn-outline"
      @click="router.push('/resource-history')"
    >
      <Timer class='w-4 h-4 inline-block align-middle' />
      <span>历史记录</span>
    </button>

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
        :plan-ready="planReady"
        :latest-artifact-agent-id="latestArtifactAgentId"
        :visible-workflow-nodes="visibleWorkflowNodes"
        @select-node="selectDagNode"
        @open-resource="openResourceByType"
      />

      <ResourceResult
        v-else-if="currentPhase === 'result'"
        key="result"
        :final-bundle="finalBundle"
        :result-warning="resultWarning"
        @reset="resetGenerator"
        @preview="handlePreview"
      />

    </transition>

    <Teleport to="body"><transition name="modal-fade"><div v-if="previewVisible" class="custom-modal-overlay" @click="previewVisible = false"><div class="custom-modal-content note-preview-modal max-w-[78%] w-full" @click.stop><div class="modal-header border-b border-slate-100 pb-3 mb-4 flex justify-between items-start"><div><h3 class="text-lg font-bold text-slate-900">{{ previewData ? getResourceTypeLabel(previewData.agentId) : '资源预览' }}</h3></div><button class="modal-close-btn text-slate-400 hover:text-slate-600" @click="previewVisible = false">×</button></div>>
      <div v-if="previewData" class="preview-dialog-body" :class="{ 'is-ppt-preview': previewData.agentId === 'ppt' }">
        <MindmapView v-if="previewData.agentId === 'mindmap'" :result-data="previewData.resultData" />
        <QuizView v-else-if="previewData.agentId === 'quiz'" :result-data="previewData.resultData" />
        <CodeView v-else-if="previewData.agentId === 'code'" :result-data="previewData.resultData" />
        <ReadingView v-else-if="previewData.agentId === 'reading'" :result-data="previewData.resultData" />
        <PptView v-else-if="previewData.agentId === 'ppt'" :document-data="previewData.resultData" />
        <VideoView v-else-if="previewData.agentId === 'video'" :result-data="previewData.resultData" />
        <MarkdownView v-else :result-data="previewData.resultData" />
      </div>
    </div></div></transition></Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, computed, onMounted, onBeforeUnmount, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import {
  PhClock as Timer
} from '@phosphor-icons/vue'

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
import { parsePptDocument } from '@/features/resource/components/ppt-engine/types/ppt'
import VideoView from '@/features/resource/components/VideoView.vue'

import {
  startResourceGeneration,
  pollResourceStatus,
  getResourceBundle,
} from '@/features/resource/api/resource'
import type { ResourceEvent } from '@/features/resource/model/resourceEvent'
import { useResourceEvents } from '@/features/resource/model/useResourceEvents'

import type {
  LearningScenario,
  ResourceAgentId,
  ResourceTaskStatus,
  ResourceGenerationRequest,
} from '@/features/resource/model/resource'

import {
  PPT_AGENT_ID,
  VIDEO_AGENT_ID,
  COORDINATOR_AGENT_ID,
  BUNDLE_AGENT_ID,
  SYSTEM_AGENT_IDS,
  AGENT_DISPLAY,
  getResourceTypeLabel,
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

const agentConfigs = ref<AnyAgentConfigs>({
  content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'full_coverage', depth_level: 'standard' },
  mindmap: { map_type: 'knowledge_tree', max_depth: 3, highlight_weak: true },
  quiz: { question_count: 5, difficulty_mode: 'adaptive', exam_style: 'school', include_analysis: true },
  code: { programming_language: 'python', case_type: 'basic_demo', difficulty: 'beginner' },
  reading: { reading_depth: 'course_extended', max_items: 3, language_preference: 'chinese' },
  ppt: { theme_id: 'logic-blue', explanation_style: 'conceptual', visual_emphasis: 'balanced' },
  video: { duration_seconds: 180, scene_count: 6, style: 'explainer', voice: 'teacher', aspect_ratio: '16:9' },
})

const goToPersonalize = () => {
  if (!naturalInput.value.trim()) return
  currentPhase.value = 'personalize'
}

const dagSelectedAgentIds = computed(() => {
  return enabledAgentIds.value.filter(id => !['master', 'assembler'].includes(id))
})

const dagNodeStates = ref<Record<string, DagNodeState>>({})
const selectedDagNodeId = ref<string | null>(null)
const overallProgress = ref(0)
const latestWorkflowMessage = ref('')
const generatedResources = shallowRef<Array<Record<string, any>>>([])
const finalBundle = shallowRef<any | null>(null)
const generationError = ref<string | null>(null)
const resultWarning = ref('')

const planReady = ref(false)
const latestArtifactAgentId = ref<string | null>(null)

const isGenerating = ref(false)
const generationFinalized = ref(false)
const activeResourceId = ref<number | null>(null)
const activeRunId = ref<string | null>(null)
const pollingInterval = ref<ReturnType<typeof setInterval> | null>(null)
const resourceEvents = useResourceEvents()

function selectDagNode(id: string) {
  selectedDagNodeId.value = id
}

function handlePlanningAnimation(event: ResourceEvent) {
  // 新协议：planning 完成时 event 为 agent.status，data.status === 'completed'
  if (event.agent_id === 'planning' && event.event === 'agent.status') {
    const dataStatus = event.data.status as string | undefined
    if (dataStatus === 'completed') planReady.value = true
  }
}

function handleArtifactReadyAnimation(event: ResourceEvent) {
  if (!event.agent_id) return
  latestArtifactAgentId.value = event.agent_id
  window.setTimeout(() => {
    if (latestArtifactAgentId.value === event.agent_id) latestArtifactAgentId.value = null
  }, 1400)
}

function handleWorkflowAnimation(event: ResourceEvent) {
  if (!event.agent_id) return
  if (event.agent_id === 'planning') handlePlanningAnimation(event)
  // 新协议：artifact.ready 已移除，通过 agent.status + data.artifact_id 判断
  if (typeof event.data.artifact_id === 'string' && event.data.artifact_id) handleArtifactReadyAnimation(event)
}

const baseGenerationAgentIds = computed(() => (
  dagSelectedAgentIds.value.filter(id => id !== PPT_AGENT_ID && id !== VIDEO_AGENT_ID)
))

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
  if (selected.includes(PPT_AGENT_ID)) {
    nodes.push(dagNodeStates.value[PPT_AGENT_ID] || { id: PPT_AGENT_ID, label: '演示文稿助手', icon: '📊', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: false })
  }
  if (selected.includes(VIDEO_AGENT_ID)) {
    nodes.push(dagNodeStates.value[VIDEO_AGENT_ID] || { id: VIDEO_AGENT_ID, label: '讲解视频助手', icon: '🎬', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: false })
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
    { weight: 55, progress: parallelPoolNodes.value.length ? parallelPoolNodes.value.reduce((sum, node) => sum + node.progress, 0) / parallelPoolNodes.value.length : 0 },
    ...(dagSelectedAgentIds.value.includes(PPT_AGENT_ID as ResourceAgentId) ? [
      { weight: 20, progress: getStageNode(PPT_AGENT_ID).progress },
    ] : []),
    ...(dagSelectedAgentIds.value.includes(VIDEO_AGENT_ID as ResourceAgentId) ? [
      { weight: 20, progress: getStageNode(VIDEO_AGENT_ID).progress },
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
    [BUNDLE_AGENT_ID]: createDagNode(BUNDLE_AGENT_ID, true),
  }
  enabledAgentIds.value.forEach((agentId) => { nodes[agentId] = createDagNode(agentId, false) })
  dagNodeStates.value = nodes
  selectedDagNodeId.value = null
  planReady.value = false
  latestArtifactAgentId.value = null
  updateOverallProgressFromDag()
}

function normalizeEventStatus(status?: string | null): DagNodeState['status'] | undefined {
  if (!status) return undefined
  if (status === 'finished' || status === 'completed') return 'success'
  if (status === 'failed' || status === 'interrupted') return 'failed'
  if (status === 'skipped') return 'skipped'
  if (status === 'running') return 'running'
  return undefined
}

function appendResourceEventLog(node: DagNodeState, event: ResourceEvent) {
  const message = event.message.trim()
  if (!message) return

  // 新协议：从 data.status 读取状态
  const dataStatus = event.data.status as string | undefined
  const eventStatus = normalizeEventStatus(dataStatus)
  const logs = node.eventLogs || []
  const last = logs[logs.length - 1]
  const eventPhase = typeof event.data.phase === 'string' ? event.data.phase : undefined
  const eventElapsedMs = event.data.elapsed_ms as number | undefined

  const sameMessage = last && last.message === message && last.phase === eventPhase

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
      id: `${event.agent_id || node.id}-${event.event}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      eventType: event.event,
      phase: eventPhase,
      message,
      status: eventStatus || node.status,
      progress: event.progress ?? undefined,
      elapsedMs: eventElapsedMs,
      timestamp: Date.now(),
    },
  ]
}

function applyResourceEvent(event: ResourceEvent) {
  // 全局事件处理（agent_id 为空）
  if (!event.agent_id) {
    if (event.event === 'generation.started') {
      latestWorkflowMessage.value = event.message
    } else if (event.event === 'generation.completed') {
      latestWorkflowMessage.value = event.message
    } else if (event.event === 'generation.failed') {
      latestWorkflowMessage.value = event.message
      generationError.value = event.message
    }
    return
  }

  // 创建新节点对象以触发 Vue 响应式
  const existing = dagNodeStates.value[event.agent_id] || createDagNode(event.agent_id, SYSTEM_AGENT_IDS.includes(event.agent_id))
  const node = { ...existing }

  // 新协议：agent.status 事件，状态在 data.status 中
  if (event.event === 'agent.status') {
    const dataStatus = event.data.status as string | undefined
    if (dataStatus === 'completed') node.status = 'success'
    else if (dataStatus === 'failed') node.status = 'failed'
    else if (dataStatus === 'pending') node.status = 'waiting'
    else if (dataStatus === 'running') node.status = 'running'
  }

  if (event.progress != null) node.progress = Math.max(node.progress, event.progress)
  if (typeof event.data.phase === 'string') node.phase = event.data.phase
  const elapsedMs = event.data.elapsed_ms as number | undefined
  if (elapsedMs != null) node.elapsedMs = elapsedMs
  const metrics = event.data.metrics as Record<string, unknown> | undefined
  if (metrics && typeof metrics === 'object' && !Array.isArray(metrics)) node.metrics = { ...(node.metrics || {}), ...metrics }
  const artifactId = event.data.artifact_id as string | undefined
  if (typeof artifactId === 'string') node.artifactId = artifactId
  node.lastUpdatedAt = Date.now()
  const message = event.message
  if (message) {
    node.currentMessage = message
    if (node.stepHistory[node.stepHistory.length - 1] !== message) {
      node.stepHistory = [...node.stepHistory.slice(-7), message]
    }
    appendResourceEventLog(node, event)
  }

  // 触发 Vue 响应式更新
  dagNodeStates.value = {
    ...dagNodeStates.value,
    [event.agent_id]: node,
  }
  handleWorkflowAnimation(event)
  updateOverallProgressFromDag()
}

function applyTaskStatus(taskStatus: ResourceTaskStatus) {
  if (taskStatus.run_id) activeRunId.value = taskStatus.run_id
  if (taskStatus.learning_need) naturalInput.value = taskStatus.learning_need
  if (Array.isArray(taskStatus.selected_agents) && taskStatus.selected_agents.length) {
    enabledAgentIds.value = taskStatus.selected_agents.filter(id => AGENT_DISPLAY[id]) as ResourceAgentId[]
  }
  if (Array.isArray(taskStatus.resources)) generatedResources.value = taskStatus.resources
  if (taskStatus.current_message) latestWorkflowMessage.value = taskStatus.current_message
  if (taskStatus.agent_snapshots) {
    Object.values(taskStatus.agent_snapshots).forEach((snapshot) => {
      if (snapshot.agent_id) {
        // 新协议：统一为 agent.status，状态放入 data.status
        let dataStatus = 'running'
        if (snapshot.status === 'finished' || snapshot.status === 'completed') dataStatus = 'completed'
        else if (snapshot.status === 'failed' || snapshot.status === 'interrupted') dataStatus = 'failed'
        else if (snapshot.status === 'skipped') dataStatus = 'completed'
        else if (snapshot.status === 'pending') dataStatus = 'pending'

        applyResourceEvent({
          sequence: 0,
          run_id: '',
          resource_id: taskStatus.resource_id,
          event: 'agent.status',
          agent_id: snapshot.agent_id,
          message: snapshot.message || snapshot.agent_id,
          progress: snapshot.progress ?? 0,
          data: {
            status: dataStatus,
            phase: snapshot.phase,
            metrics: snapshot.metrics || {},
            artifact_id: snapshot.artifact_id,
            elapsed_ms: snapshot.elapsed_ms,
          },
          timestamp: snapshot.timestamp || Date.now() / 1000,
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
    generatedResources.value = Array.isArray(bundle.resources) ? bundle.resources : []
    resultWarning.value = taskStatus.status === 'partial_completed' ? '部分资源生成失败，以下已完成内容仍可查看。' : ''
    isGenerating.value = false
    currentPhase.value = 'result'
    return
  }
  generationError.value = '资源生成失败，暂无可展示内容'
  isGenerating.value = false
  toast.error(generationError.value || '资源生成失败，暂无可展示内容')
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
      toast.error(generationError.value || '生成中断，请稍后重试')
    })
  }, 4000)
}

function syncStatusSoon(resourceId: number) {
  void checkStatusOnce(resourceId).catch((err: any) => { console.warn('[ResourceGenerator] 状态同步失败:', err) })
}

function startResourceStream(runId: string, resourceId: number) {
  stopResourceStream()
  startPollingFallback(resourceId)
  resourceEvents.connect(resourceId, runId, {
    onEvent: (event) => {
      applyResourceEvent(event)
      if (event.message) latestWorkflowMessage.value = event.message
      if (event.event === 'generation.completed') syncStatusSoon(resourceId)
    },
    onCompleted: () => {
      void checkStatusOnce(resourceId).catch(() => {
        void completeGeneration(resourceId, { resource_id: resourceId, status: 'completed' })
      })
    },
    onFailed: () => {
      void checkStatusOnce(resourceId).catch(() => {
        void completeGeneration(resourceId, { resource_id: resourceId, status: 'failed' })
      })
    },
  })
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
      agent_configs: agentConfigs.value,
    }
    const { resource_id, run_id } = (await startResourceGeneration(requestParams)).data.data
    activeResourceId.value = resource_id
    activeRunId.value = run_id
    await router.replace({
      query: {
        ...route.query,
        resourceId: String(resource_id),
      },
    })
    startResourceStream(run_id, resource_id)
  } catch (err: any) {
    generationError.value = err.message || '生成请求失败'
    isGenerating.value = false
    toast.error(generationError.value || '生成请求失败')
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
  activeRunId.value = null
  dagNodeStates.value = {}
  selectedDagNodeId.value = null
  planReady.value = false
  latestArtifactAgentId.value = null
}

const stopPolling = () => {
  if (pollingInterval.value) { clearInterval(pollingInterval.value); pollingInterval.value = null }
}

const stopResourceStream = () => {
  resourceEvents.close()
}

const pauseLiveGenerationUpdates = () => { stopPolling(); stopResourceStream() }

const restoreGeneration = async (resourceId: number) => {
  currentPhase.value = 'generating'
  resetGenerationState()
  initializeWaitingNodes()
  activeResourceId.value = resourceId
  isGenerating.value = true

  try {
    const taskStatus = (await pollResourceStatus(resourceId)).data.data
    applyTaskStatus(taskStatus)
    if (['completed', 'partial_completed', 'failed'].includes(taskStatus.status)) {
      await completeGeneration(resourceId, taskStatus)
      return
    }
    if (taskStatus.run_id) {
      startResourceStream(taskStatus.run_id, resourceId)
    } else {
      startPollingFallback(resourceId)
    }
  } catch (err: any) {
    generationError.value = err.message || '无法恢复资源生成任务'
    isGenerating.value = false
    currentPhase.value = 'input'
    const query = { ...route.query }
    delete query.resourceId
    await router.replace({ query })
    toast.error(generationError.value || '无法恢复资源生成任务')
  }
}

const resumeLiveGenerationUpdates = async () => {
  const resourceId = activeResourceId.value
  const runId = activeRunId.value
  if (!resourceId || !runId || !isGenerating.value || generationFinalized.value) return
  try { await checkStatusOnce(resourceId) } catch { latestWorkflowMessage.value = '状态同步失败，正在重试实时连接' }
  if (activeResourceId.value === resourceId && isGenerating.value && !generationFinalized.value) startResourceStream(runId, resourceId)
}

const previewVisible = ref(false)
const previewData = ref<any>(null)
const handlePreview = (data: any) => {
  if (data?.agentId === 'ppt') {
    const parsed = parsePptDocument(data.resultData)
    if (!parsed.ok) {
      console.error('Invalid persisted PPT artifact omitted', {
        reason: parsed.reason,
        details: parsed.details,
      })
      return
    }
    previewData.value = { ...data, resultData: parsed.document }
  } else {
    previewData.value = data
  }
  previewVisible.value = true
}

const resetGenerator = () => {
  stopPolling()
  stopResourceStream()
  naturalInput.value = ''
  resetGenerationState()
  currentPhase.value = 'input'
  const query = { ...route.query }
  delete query.resourceId
  delete query.prompt
  void router.replace({ query })
}

onMounted(() => {
  const prompt = route.query.prompt
  if (prompt) naturalInput.value = String(prompt)
  const resourceId = Number(route.query.resourceId)
  if (Number.isInteger(resourceId) && resourceId > 0) {
    void restoreGeneration(resourceId)
  }
})

onActivated(() => { void resumeLiveGenerationUpdates() })
onDeactivated(() => { stopResourceStream() })
onBeforeUnmount(() => { pauseLiveGenerationUpdates() })
</script>

<style scoped>
.elegant-generator-layout {
  --color-primary: var(--cat-resource);
  --color-primary-hover: #4f46e5;
  --color-primary-soft: var(--cat-resource-soft);
  --color-primary-border: #a5b4fc;
  --color-primary-text: #4338ca;
  --gradient-primary: var(--gradient-resource);
  min-height: calc(100vh - 64px);
  position: relative;
  background: #f4f7fb;
  overflow-x: hidden;
  font-family: var(--font-sans);
}

.resource-generator-ambient {
  display: none;
}

.floating-history-btn {
  position: absolute; top: 24px; right: 24px; z-index: 50;
  height: 36px;
  display: flex; align-items: center; gap: 8px;
  padding: 0 14px;
  background: #fff;
  border: 1px solid #d9e1ec;
  border-radius: 8px;
  color: var(--color-primary); font-weight: 600; font-size: 0.9rem;
  box-shadow: 0 2px 8px rgba(23, 32, 51, 0.05);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.floating-history-btn:hover {
  background: #fff;
  border-color: #a5b4fc;
  box-shadow: 0 4px 12px rgba(23, 32, 51, 0.08);
}

.phase-view { position: relative; width: 100%; min-height: calc(100vh - 64px); display: flex; flex-direction: column; background: transparent; backdrop-filter: blur(20px); }
.page-slide-enter-active, .page-slide-leave-active { transition: opacity 0.4s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.page-slide-enter-from { opacity: 0; transform: translateY(30px) scale(0.98); }
.page-slide-leave-to { opacity: 0; transform: translateY(-30px) scale(1.02); }

.elegant-dialog :deep(.resource-card-wrapper) { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; border-radius: 0 !important; }
.elegant-dialog :deep(.resource-card-wrapper:hover) { background: transparent !important; box-shadow: none !important; border: none !important; }
.preview-dialog-body.is-ppt-preview { padding: 0 !important; background: transparent !important; border: none !important; box-shadow: none !important; }
.preview-dialog-body.is-ppt-preview :deep(.player-wrapper) { margin-top: 0 !important; border: none !important; border-radius: 0 !important; }

h1, h2, h3, h4 { letter-spacing: 0; color: var(--color-text); font-weight: var(--weight-bold); }
p, .card-summary, .s-desc { line-height: 1.65; letter-spacing: 0; color: var(--color-text-secondary); }
</style>
