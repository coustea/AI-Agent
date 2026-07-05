import { ref, shallowRef, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import {
  startResourceGeneration,
  pollResourceStatus,
  getResourceBundle,
} from '@/features/resource/api/resource'
import type {
  LearningScenario,
  ResourceAgentId,
  ResourceTaskStatus,
  ResourceGenerationRequest,
} from '@/features/resource/model/resource'
import type { ResourceEvent } from '@/features/resource/model/resourceEvent'
import { useResourceEvents } from './useResourceEvents'
import {
  PPT_AGENT_ID,
  CARTOON_AGENT_ID,
  VIDEO_AGENT_ID,
  COORDINATOR_AGENT_ID,
  BUNDLE_AGENT_ID,
  SYSTEM_AGENT_IDS,
  AGENT_DISPLAY,
  createDagNode,
  type AnyAgentConfigs,
  type DagNodeState,
} from '../model/catalog'

export type Phase = 'input' | 'personalize' | 'generating' | 'result'

export function useGeneration() {
  const router = useRouter()
  const route = useRoute()

  const currentPhase = ref<Phase>('input')
  const naturalInput = ref('')
  const learningScenario = ref<LearningScenario>('daily_review')
  const enabledAgentIds = ref<ResourceAgentId[]>(['content', 'mindmap', 'code', 'quiz', 'reading', 'ppt', 'cartoon', 'video'])

  const agentConfigs = ref<AnyAgentConfigs>({
    content: { structure: 'progressive', depth_level: 'standard', focus_mode: 'full_coverage', include_examples: true },
    mindmap: { map_type: 'knowledge_tree', max_depth: 3, leaf_detail: 'brief_note', show_relations: true },
    quiz: { question_count: 5, difficulty_mode: 'adaptive', exam_style: 'school', question_types: ['single', 'multiple', 'judge', 'fill'] },
    code: { programming_language: 'python', case_type: 'basic_demo', difficulty: 'beginner', focus: 'syntax' },
    reading: { reading_depth: 'course_extended', max_items: 3, language_preference: 'chinese', focus: 'textbook' },
    ppt: { template: 'auto', explanation_style: 'concept', density: 'standard', focus: ['core_concepts'] },
    cartoon: { style: 'diagram', depth: 'standard', pace: 'normal', visuals: 'balanced' },
    video: { style: 'precision_light', focus: 'concept', voice: 'teacher', aspect_ratio: '16:9' },
  })

  const dagSelectedAgentIds = computed(() => {
    return enabledAgentIds.value.filter(id => !['master', 'assembler'].includes(id))
  })

  const baseGenerationAgentIds = computed(() => (
    dagSelectedAgentIds.value.filter(id => ![PPT_AGENT_ID, CARTOON_AGENT_ID, VIDEO_AGENT_ID].includes(id))
  ))

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
  const pollingInterval = ref<ReturnType<typeof setInterval> | null>(null)
  const resourceEvents = useResourceEvents()

  function selectDagNode(id: string) {
    selectedDagNodeId.value = id
  }

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
    if (selected.includes(CARTOON_AGENT_ID)) {
      nodes.push(dagNodeStates.value[CARTOON_AGENT_ID] || { id: CARTOON_AGENT_ID, label: '动画讲解助手', icon: '🎬', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: false })
    }
    if (selected.includes(VIDEO_AGENT_ID)) {
      nodes.push(dagNodeStates.value[VIDEO_AGENT_ID] || { id: VIDEO_AGENT_ID, label: '讲解视频助手', icon: '🎥', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: false })
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
    const isReadyInResources = generatedResources.value.some(resource => resource.type === type)
    const isReadyInDag = dagNodeStates.value[type]?.status === 'success'
    return isReadyInResources || isReadyInDag
  }

  const parallelPoolNodes = computed(() => {
    const agentStatusRank: Record<DagNodeState['status'], number> = { failed: 0, running: 1, success: 2, waiting: 3, skipped: 4 }
    return baseGenerationAgentIds.value.map(agentId => getStageNode(agentId)).sort((a, b) => {
      const rankDiff = agentStatusRank[a.status] - agentStatusRank[b.status]
      if (rankDiff !== 0) return rankDiff
      return b.progress - a.progress
    })
  })

  function updateOverallProgressFromDag() {
    const stages = [
      { weight: 15, progress: getStageNode('planning').progress },
      { weight: 55, progress: parallelPoolNodes.value.length ? parallelPoolNodes.value.reduce((sum, node) => sum + node.progress, 0) / parallelPoolNodes.value.length : 0 },
      ...(dagSelectedAgentIds.value.includes(PPT_AGENT_ID as ResourceAgentId) ? [
        { weight: 15, progress: getStageNode(PPT_AGENT_ID).progress },
      ] : []),
      ...(dagSelectedAgentIds.value.includes(CARTOON_AGENT_ID as ResourceAgentId) ? [
        { weight: 15, progress: getStageNode(CARTOON_AGENT_ID).progress },
      ] : []),
      ...(dagSelectedAgentIds.value.includes(VIDEO_AGENT_ID as ResourceAgentId) ? [
        { weight: 15, progress: getStageNode(VIDEO_AGENT_ID).progress },
      ] : []),
      { weight: 10, progress: getStageNode(BUNDLE_AGENT_ID).progress },
    ]
    const weightTotal = stages.reduce((sum, item) => sum + item.weight, 0)
    const weighted = stages.reduce((sum, item) => sum + item.progress * item.weight, 0)
    overallProgress.value = Math.round(weighted / weightTotal)
  }

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

  function handlePlanningAnimation(event: ResourceEvent) {
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
    if (typeof event.data.artifact_id === 'string' && event.data.artifact_id) handleArtifactReadyAnimation(event)
  }

  function applyResourceEvent(event: ResourceEvent) {
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

    const existing = dagNodeStates.value[event.agent_id] || createDagNode(event.agent_id, SYSTEM_AGENT_IDS.includes(event.agent_id))
    const node = { ...existing }

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

    dagNodeStates.value = {
      ...dagNodeStates.value,
      [event.agent_id]: node,
    }
    handleWorkflowAnimation(event)
    updateOverallProgressFromDag()
  }

  function applyTaskStatus(taskStatus: ResourceTaskStatus) {
    if (taskStatus.learning_need) naturalInput.value = taskStatus.learning_need
    if (Array.isArray(taskStatus.selected_agents) && taskStatus.selected_agents.length) {
      enabledAgentIds.value = taskStatus.selected_agents.filter(id => AGENT_DISPLAY[id]) as ResourceAgentId[]
    }
    if (Array.isArray(taskStatus.resources)) {
      const existingMap = new Map(
        generatedResources.value.map(r => [r.type, r] as [string, any])
      )
      generatedResources.value = taskStatus.resources.map((summary: any) => {
        const existing = existingMap.get(summary.type)
        if (existing && existing.content) {
          return { ...existing, ...summary, content: existing.content }
        }
        return summary
      })
    }
    if (taskStatus.current_message) latestWorkflowMessage.value = taskStatus.current_message
    if (taskStatus.agent_snapshots) {
      Object.values(taskStatus.agent_snapshots).forEach((snapshot) => {
        if (snapshot.agent_id) {
          let dataStatus = 'running'
          if (snapshot.status === 'finished' || snapshot.status === 'completed') dataStatus = 'completed'
          else if (snapshot.status === 'failed' || snapshot.status === 'interrupted') dataStatus = 'failed'
          else if (snapshot.status === 'skipped') dataStatus = 'completed'
          else if (snapshot.status === 'pending') dataStatus = 'pending'

          applyResourceEvent({
            sequence: 0,
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

    let bundle: any = null
    try {
      bundle = (await getResourceBundle(resourceId)).data?.data
    } catch {
      // bundle 获取失败不影响后续流程
    }

    const hasResources = Array.isArray(bundle?.resources) && bundle.resources.length > 0

    if (hasResources) {
      finalBundle.value = bundle
      generatedResources.value = bundle.resources
      resultWarning.value = taskStatus.status === 'partial_completed'
        ? '部分资源生成失败，以下已完成内容仍可查看。'
        : taskStatus.status === 'failed'
          ? '资源生成未完全成功，以下已完成内容仍可查看。'
          : ''
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

  function startResourceStream(resourceId: number) {
    stopResourceStream()
    startPollingFallback(resourceId)
    resourceEvents.connect(resourceId, {
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

  const start = async () => {
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
      const { resource_id } = (await startResourceGeneration(requestParams)).data.data
      activeResourceId.value = resource_id
      await router.replace({
        query: {
          ...route.query,
          resourceId: String(resource_id),
        },
      })
      startResourceStream(resource_id)
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

  const submitInput = () => {
    if (!naturalInput.value.trim()) return
    currentPhase.value = 'personalize'
  }

  const restore = async (resourceId: number) => {
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
      startResourceStream(resourceId)
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

  const pause = () => {
    stopPolling()
    stopResourceStream()
  }

  const resume = async () => {
    const resourceId = activeResourceId.value
    if (!resourceId || !isGenerating.value || generationFinalized.value) return
    try { await checkStatusOnce(resourceId) } catch { latestWorkflowMessage.value = '状态同步失败，正在重试实时连接' }
    if (activeResourceId.value === resourceId && isGenerating.value && !generationFinalized.value) startResourceStream(resourceId)
  }

  const reset = () => {
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

  const dispose = () => {
    pause()
  }

  return {
    currentPhase,
    naturalInput,
    learningScenario,
    enabledAgentIds,
    agentConfigs,
    dagNodeStates,
    selectedDagNodeId,
    overallProgress,
    latestWorkflowMessage,
    generatedResources,
    finalBundle,
    generationError,
    resultWarning,
    planReady,
    latestArtifactAgentId,
    isGenerating,
    activeResourceId,
    visibleWorkflowNodes,
    parallelPoolNodes,
    dagSelectedAgentIds,
    baseGenerationAgentIds,
    submitInput,
    start,
    restore,
    reset,
    pause,
    resume,
    dispose,
    selectDagNode,
    getStageNode,
    hasGeneratedResource,
    applyResourceEvent,
  }
}
