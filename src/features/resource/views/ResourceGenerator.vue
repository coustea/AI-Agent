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

    <el-dialog v-model="previewVisible" :title="previewData ? getResourceTypeLabel(previewData.agentId) : '资源预览'" width="78%" top="6vh" destroy-on-close :class="['elegant-dialog', { 'is-ppt-dialog': previewData?.agentId === 'ppt' }]">
      <div v-if="previewData" class="preview-dialog-body" :class="{ 'is-ppt-preview': previewData.agentId === 'ppt' }">
        <MindmapView v-if="previewData.agentId === 'mindmap'" :result-data="previewData.resultData" />
        <QuizView v-else-if="previewData.agentId === 'quiz'" :result-data="previewData.resultData" />
        <CodeView v-else-if="previewData.agentId === 'code'" :result-data="previewData.resultData" />
        <ReadingView v-else-if="previewData.agentId === 'reading'" :result-data="previewData.resultData" />
        <PptView v-else-if="previewData.agentId === 'ppt'" :document-data="previewData.resultData" />
        <VideoView v-else-if="previewData.agentId === 'video'" :result-data="previewData.resultData" />
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
import { parsePptDocument } from '@/features/resource/components/ppt-engine/types/ppt'
import VideoView from '@/features/resource/components/VideoView.vue'

import {
  startResourceGeneration,
  pollResourceStatus,
  getResourceBundle,
} from '@/features/resource/api/resource'
import type { AgentEvent } from '@/shared/agent-events/model'
import { useAgentRun } from '@/shared/agent-events/useAgentRun'

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

const agentConfigs = reactive<AnyAgentConfigs>({
  content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'full_coverage', depth_level: 'standard' },
  mindmap: { map_type: 'knowledge_tree', max_depth: 3, highlight_weak: true, expand_weak_points: false, include_prerequisites: false },
  quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 50, exam_style: 'school', include_analysis: true, question_types: ['single', 'multiple', 'judge'] },
  code: { programming_language: 'python', case_type: 'basic_demo', difficulty: 'beginner' },
  reading: { reading_depth: 'course_extended', max_items: 3, language_preference: 'chinese' },
  ppt: { difficulty: 'intermediate', lesson_depth: 'standard', lesson_kind: 'auto', learning_focus: 'balanced' },
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
const agentRun = useAgentRun()

function selectDagNode(id: string) {
  selectedDagNodeId.value = id
}

function handlePlanningAnimation(event: AgentEvent) {
  if (event.status === 'completed') planReady.value = true
}

function handleArtifactReadyAnimation(event: AgentEvent) {
  if (!event.agent_id) return
  latestArtifactAgentId.value = event.agent_id
  window.setTimeout(() => {
    if (latestArtifactAgentId.value === event.agent_id) latestArtifactAgentId.value = null
  }, 1400)
}

function handleWorkflowAnimation(event: AgentEvent) {
  if (!event.agent_id) return
  if (event.agent_id === 'planning') handlePlanningAnimation(event)
  if (event.type === 'artifact.ready') handleArtifactReadyAnimation(event)
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
  if (status === 'failed') return 'failed'
  if (status === 'skipped') return 'skipped'
  if (status === 'running') return 'running'
  return undefined
}

function appendAgentEventLog(node: DagNodeState, event: AgentEvent) {
  const message = (event.summary || event.title).trim()
  if (!message) return

  const eventStatus = normalizeEventStatus(event.status)
  const logs = node.eventLogs || []
  const last = logs[logs.length - 1]
  const eventPhase = typeof event.detail.phase === 'string' ? event.detail.phase : undefined
  const eventElapsedMs = event.elapsed_ms ?? undefined

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
      id: `${event.agent_id || node.id}-${event.type}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      eventType: event.type,
      phase: eventPhase,
      message,
      status: eventStatus || node.status,
      progress: event.progress ?? undefined,
      elapsedMs: eventElapsedMs,
      timestamp: Date.now(),
    },
  ]
}

function applyAgentEvent(event: AgentEvent) {
  if (!event.agent_id) return
  const node = dagNodeStates.value[event.agent_id] || createDagNode(event.agent_id, SYSTEM_AGENT_IDS.includes(event.agent_id))
  if (event.status) {
    node.status = event.status === 'completed'
      ? 'success'
      : event.status === 'pending' ? 'waiting' : event.status
  }
  if (event.progress != null) node.progress = Math.max(node.progress, event.progress)
  if (typeof event.detail.phase === 'string') node.phase = event.detail.phase
  if (event.elapsed_ms != null) node.elapsedMs = event.elapsed_ms
  const metrics = event.detail.metrics
  if (metrics && typeof metrics === 'object' && !Array.isArray(metrics)) node.metrics = { ...(node.metrics || {}), ...metrics }
  if (typeof event.detail.artifact_id === 'string') node.artifactId = event.detail.artifact_id
  node.lastUpdatedAt = Date.now()
  const message = event.summary || event.title
  if (message) {
    node.currentMessage = message
    if (node.stepHistory[node.stepHistory.length - 1] !== message) {
      node.stepHistory = [...node.stepHistory.slice(-7), message]
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
          event_id: `snapshot-${snapshot.agent_id}-${Date.now()}`,
          run_id: '', sequence: 0, module: 'resource', business_id: String(taskStatus.resource_id),
          type: snapshot.event_type === 'agent.artifact_ready' ? 'artifact.ready' : 'agent.status',
          status: snapshot.status === 'finished' || snapshot.status === 'completed'
            ? 'completed'
            : snapshot.status === 'failed' ? 'failed' : snapshot.status === 'skipped' ? 'skipped' : 'running',
          activity_id: `agent:${snapshot.agent_id}`, agent_id: snapshot.agent_id,
          title: snapshot.message || snapshot.agent_id, summary: snapshot.message || '',
          progress: snapshot.progress ?? 0,
          detail: { phase: snapshot.phase, metrics: snapshot.metrics || {}, artifact_id: snapshot.artifact_id },
          elapsed_ms: snapshot.elapsed_ms || null, timestamp: snapshot.timestamp || Date.now() / 1000,
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

function startResourceStream(runId: string, resourceId: number) {
  stopResourceStream()
  startPollingFallback(resourceId)
  agentRun.connect(runId, {
    onEvent: (event) => {
      applyAgentEvent(event)
      if (event.summary || event.title) latestWorkflowMessage.value = event.summary || event.title
      if (event.status === 'completed') syncStatusSoon(resourceId)
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
    onConnectionError: (err) => {
      if (!isGenerating.value || generationFinalized.value) return
      console.warn('[ResourceGenerator] SSE 连接失败，切换到轮询兜底:', err)
      latestWorkflowMessage.value = '实时连接中断，已切换到状态同步模式'
      startPollingFallback(resourceId)
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
      agent_configs: {
        content: agentConfigs.content,
        mindmap: agentConfigs.mindmap,
        quiz: agentConfigs.quiz,
        code: agentConfigs.code,
        reading: agentConfigs.reading,
        ppt: agentConfigs.ppt,
        video: agentConfigs.video,
      },
    }
    const { resource_id, run_id } = (await startResourceGeneration(requestParams)).data.data
    activeResourceId.value = resource_id
    activeRunId.value = run_id
    startResourceStream(run_id, resource_id)
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
  agentRun.close()
}

const pauseLiveGenerationUpdates = () => { stopPolling(); stopResourceStream() }

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
