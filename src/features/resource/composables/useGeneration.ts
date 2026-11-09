// src/features/resource/composables/useGeneration.ts — 教学资源生成全流程编排
// 对齐 chat 模块架构：主 Agent 统筹驱动，基于 ResourceRunState 实时快照推流
import { ref, shallowRef, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import { getErrorMessage } from '@/shared/api/http'
import { getAuthToken } from '@/shared/auth/token'
import {
  startResourceGeneration,
  getResourceRunSnapshot,
  cancelResourceRun,
  getResourceBundle,
} from '@/features/resource/api/resource'
import type {
  ResourceAgentId,
  ResourceGenerationRequest,
  ResourceRunState,
  GeneratedResourceItem,
  ResourceContentFormat,
  ResourceContent,
} from '@/features/resource/model/resource'
import {
  PPT_AGENT_ID,
  CARTOON_AGENT_ID,
  COORDINATOR_AGENT_ID,
  BUNDLE_AGENT_ID,
  createDagNode,
  type DagNodeState,
} from '../model/catalog'

export type Phase = 'input' | 'personalize' | 'generating' | 'result'

const ACTIVE_RESOURCE_ID_KEY = 'resource-generation:active-resource:v2'
const RUN_ID_KEY_PREFIX = 'resource-generation:run-id:v2:'

const TOOL_TO_AGENT_ID: Record<string, ResourceAgentId> = {
  generate_lecture_content: 'content',
  generate_mindmap: 'mindmap',
  generate_quiz: 'quiz',
  generate_code: 'code',
  generate_reading: 'reading',
  generate_ppt_deck: 'ppt',
  generate_teaching_video: 'cartoon',
}

export function useGeneration() {
  const router = useRouter()
  const route = useRoute()

  // 阶段与表单配置
  const currentPhase = ref<Phase>('input')
  const naturalInput = ref('')
  const enabledAgentIds = ref<ResourceAgentId[]>([
    'content',
    'mindmap',
    'code',
    'quiz',
    'reading',
    'ppt',
    'cartoon',
  ])

  // 节点选择计算属性
  const dagSelectedAgentIds = computed(() => enabledAgentIds.value)
  const baseGenerationAgentIds = computed(() =>
    dagSelectedAgentIds.value.filter(id => ![PPT_AGENT_ID, CARTOON_AGENT_ID].includes(id))
  )

  // 运行与工作流状态
  const dagNodeStates = ref<Record<string, DagNodeState>>({})
  const selectedDagNodeId = ref<string | null>(null)
  const overallProgress = ref(0)
  const latestWorkflowMessage = ref('')
  const generatedResources = shallowRef<GeneratedResourceItem[]>([])
  const generationError = ref<string | null>(null)
  const planReady = ref(false)

  const isGenerating = ref(false)
  const generationFinalized = ref(false)
  const activeResourceId = ref<number | null>(null)
  const activeRunId = ref<string | null>(null)

  let eventSource: EventSource | null = null
  let pollingTimer: ReturnType<typeof setInterval> | null = null

  // 缓存工具函数
  function rememberRunId(resourceId: number, runId: string) {
    sessionStorage.setItem(`${RUN_ID_KEY_PREFIX}${resourceId}`, runId)
  }

  function readRunId(resourceId: number): string | null {
    return sessionStorage.getItem(`${RUN_ID_KEY_PREFIX}${resourceId}`)
  }

  function rememberActiveResource(resourceId: number) {
    sessionStorage.setItem(ACTIVE_RESOURCE_ID_KEY, String(resourceId))
  }

  function readActiveResourceId(): number | null {
    const raw = sessionStorage.getItem(ACTIVE_RESOURCE_ID_KEY)
    const parsed = Number(raw)
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null
  }

  function forgetActiveResource(resourceId?: number) {
    const active = readActiveResourceId()
    if (!resourceId || active === resourceId) {
      sessionStorage.removeItem(ACTIVE_RESOURCE_ID_KEY)
    }
  }

  // DAG 节点构建与展示
  const dagNodesV2 = computed<DagNodeState[]>(() => {
    const selected = dagSelectedAgentIds.value
    const nodes: DagNodeState[] = []
    nodes.push(dagNodeStates.value['planning'] || createDagNode('planning', true))
    nodes.push(dagNodeStates.value[COORDINATOR_AGENT_ID] || createDagNode(COORDINATOR_AGENT_ID, true))
    for (const agentId of baseGenerationAgentIds.value) {
      nodes.push(dagNodeStates.value[agentId] || createDagNode(agentId, false))
    }
    if (selected.includes(PPT_AGENT_ID)) {
      nodes.push(dagNodeStates.value[PPT_AGENT_ID] || createDagNode(PPT_AGENT_ID, false))
    }
    if (selected.includes(CARTOON_AGENT_ID)) {
      nodes.push(dagNodeStates.value[CARTOON_AGENT_ID] || createDagNode(CARTOON_AGENT_ID, false))
    }
    nodes.push(dagNodeStates.value[BUNDLE_AGENT_ID] || createDagNode(BUNDLE_AGENT_ID, true))
    return nodes
  })

  function hasNodeEntered(node?: DagNodeState): boolean {
    if (!node) return false
    if (node.id === 'planning') return true
    return node.status !== 'waiting' || node.progress > 0 || Boolean(node.currentMessage) || (node.stepHistory?.length || 0) > 0
  }

  const visibleWorkflowNodes = computed(() => dagNodesV2.value.filter(hasNodeEntered))

  function getStageNode(id: string): DagNodeState {
    return dagNodeStates.value[id] || createDagNode(id, ['planning', COORDINATOR_AGENT_ID, BUNDLE_AGENT_ID].includes(id))
  }

  function hasGeneratedResource(type: string): boolean {
    return generatedResources.value.some(r => r.type === type) || dagNodeStates.value[type]?.status === 'success'
  }

  const parallelPoolNodes = computed(() => {
    const rank: Record<DagNodeState['status'], number> = { failed: 0, running: 1, success: 2, waiting: 3, skipped: 4 }
    return baseGenerationAgentIds.value.map(id => getStageNode(id)).sort((a, b) => {
      const diff = rank[a.status] - rank[b.status]
      return diff !== 0 ? diff : b.progress - a.progress
    })
  })

  function selectDagNode(id: string) {
    selectedDagNodeId.value = id
  }

  function initializeWaitingNodes() {
    const nodes: Record<string, DagNodeState> = {
      planning: createDagNode('planning', true),
      [COORDINATOR_AGENT_ID]: createDagNode(COORDINATOR_AGENT_ID, true),
      [BUNDLE_AGENT_ID]: createDagNode(BUNDLE_AGENT_ID, true),
    }
    enabledAgentIds.value.forEach(id => {
      nodes[id] = createDagNode(id, false)
    })
    dagNodeStates.value = nodes
    selectedDagNodeId.value = null
    planReady.value = false
    overallProgress.value = 0
  }

  // 核心：基于全量 ResourceRunState 快照更新前端状态（与 chat 模块无缝对齐）
  function applyRunState(state: ResourceRunState) {
    // 1. 总体进度计算
    if (state.status === 'completed') {
      overallProgress.value = 100
    } else if (state.phase === 'queued') {
      overallProgress.value = 5
    } else if (state.phase === 'preparing') {
      overallProgress.value = 12
    } else if (state.phase === 'planning') {
      overallProgress.value = 25
    } else if (state.phase === 'generating') {
      const totalSteps = state.steps.length || enabledAgentIds.value.length || 1
      const totalStepProg = state.steps.reduce((sum, s) => {
        if (s.status === 'completed') return sum + 100
        if (s.status === 'running') return sum + Math.max(s.progress, 30)
        return sum
      }, 0)
      const progressFromSteps = Math.round(30 + (totalStepProg / (totalSteps * 100)) * 60)
      overallProgress.value = Math.min(92, Math.max(overallProgress.value, progressFromSteps))
    } else if (state.phase === 'saving') {
      overallProgress.value = 95
    }

    // 2. 规划完成状态
    planReady.value = !['queued', 'preparing'].includes(state.phase)

    // 3. 消息提示
    const activeStep = state.steps.find(s => s.status === 'running')
    if (activeStep) {
      latestWorkflowMessage.value = `${activeStep.title}: ${activeStep.message || '正在全力生成中...'}`
    } else if (state.phase_label) {
      latestWorkflowMessage.value = state.phase_label
    }

    // 4. DAG 节点全量同步
    const nextNodes: Record<string, DagNodeState> = { ...dagNodeStates.value }

    // 规划节点
    const planningNode: DagNodeState = nextNodes.planning || createDagNode('planning', true)
    if (state.phase === 'queued') {
      planningNode.status = 'waiting'
      planningNode.progress = 0
    } else if (state.phase === 'preparing' || state.phase === 'planning') {
      planningNode.status = 'running'
      planningNode.progress = 65
      planningNode.currentMessage = state.thought_text ? '正在统筹制定教学方案...' : '正在分析学情与方案规划...'
      if (!planningNode.stepHistory.includes(planningNode.currentMessage)) {
        planningNode.stepHistory = [...planningNode.stepHistory, planningNode.currentMessage]
      }
    } else {
      planningNode.status = 'success'
      planningNode.progress = 100
      planningNode.currentMessage = '课程设计方案已确定'
    }
    nextNodes.planning = planningNode

    // 协同中枢节点
    const coordNode: DagNodeState = nextNodes[COORDINATOR_AGENT_ID] || createDagNode(COORDINATOR_AGENT_ID, true)
    if (['queued', 'preparing', 'planning'].includes(state.phase)) {
      coordNode.status = 'waiting'
      coordNode.progress = 0
    } else if (state.phase === 'generating') {
      coordNode.status = 'running'
      coordNode.progress = 80
      coordNode.currentMessage = '正在并行协同调度子智能体'
    } else {
      coordNode.status = 'success'
      coordNode.progress = 100
      coordNode.currentMessage = '所有子智能体任务协同完毕'
    }
    nextNodes[COORDINATOR_AGENT_ID] = coordNode

    // 子智能体步骤与产物
    for (const step of state.steps) {
      const agentId = TOOL_TO_AGENT_ID[step.tool_name]
      if (!agentId) continue
      const node: DagNodeState = nextNodes[agentId] || createDagNode(agentId, false)
      if (step.status === 'completed') {
        node.status = 'success'
        node.progress = 100
      } else if (step.status === 'failed') {
        node.status = 'failed'
        node.progress = step.progress
      } else if (step.status === 'running') {
        node.status = 'running'
        node.progress = Math.max(node.progress, step.progress, 25)
      }
      if (step.message) {
        node.currentMessage = step.message
        if (!node.stepHistory.includes(step.message)) {
          node.stepHistory = [...node.stepHistory.slice(-7), step.message]
        }
      }
      if (step.elapsed_ms) node.elapsedMs = step.elapsed_ms
      nextNodes[agentId] = node
    }

    // 产物确认绑定
    for (const artifact of state.artifacts) {
      const agentId = artifact.kind
      const node: DagNodeState = nextNodes[agentId] || createDagNode(agentId, false)
      node.status = 'success'
      node.progress = 100
      node.artifactId = artifact.id
      if (artifact.title) node.currentMessage = `已交付：${artifact.title}`
      nextNodes[agentId] = node
    }

    // 汇编归档节点
    const bundleNode: DagNodeState = nextNodes[BUNDLE_AGENT_ID] || createDagNode(BUNDLE_AGENT_ID, true)
    if (['queued', 'preparing', 'planning', 'generating'].includes(state.phase)) {
      bundleNode.status = 'waiting'
      bundleNode.progress = 0
    } else if (state.phase === 'saving') {
      bundleNode.status = 'running'
      bundleNode.progress = 70
      bundleNode.currentMessage = '正在组装与持久化教学产物包...'
    } else if (state.phase === 'completed') {
      bundleNode.status = 'success'
      bundleNode.progress = 100
      bundleNode.currentMessage = '学习资源包已完成归档'
    }
    nextNodes[BUNDLE_AGENT_ID] = bundleNode

    dagNodeStates.value = nextNodes

    // 5. 产物列表映射
    generatedResources.value = state.artifacts.map(art => ({
      id: art.id,
      type: art.kind,
      title: art.title,
      format: (art.file_type === 'markdown' ? 'markdown' : 'json') as ResourceContentFormat,
      content: (art.content as ResourceContent) ?? null,
      metadata: art.metadata ?? {},
      created_at: null,
    }))
  }

  // 终态处理：拉取完整产物包并跳转到结果页
  async function completeGeneration(resourceId: number) {
    if (generationFinalized.value) return
    generationFinalized.value = true
    closeStream()
    stopPolling()
    forgetActiveResource(resourceId)

    try {
      const resp = await getResourceBundle(resourceId)
      const bundle = resp.data?.data
      if (bundle) {
        generatedResources.value = bundle.resources || []
      }
    } catch (err) {
      console.warn('获取资源包失败:', err)
    }

    isGenerating.value = false
    currentPhase.value = 'result'
  }

  // 建立 SSE 订阅连接，同时启动轮询保底
  function startResourceStream(runId: string, resourceId: number) {
    closeStream()
    stopPolling()

    const query = new URLSearchParams()
    const token = getAuthToken()
    if (token) query.set('token', token)

    const url = `/api/v1/ai/resource/runs/${runId}/events?${query}`
    const es = new EventSource(url)
    eventSource = es

    const onSnapshot = (raw: MessageEvent) => {
      try {
        const state = JSON.parse(raw.data) as ResourceRunState
        applyRunState(state)

        if (state.status === 'completed') {
          void completeGeneration(resourceId)
        } else if (state.status === 'failed') {
          generationError.value = state.error || '资源生成失败'
          isGenerating.value = false
          closeStream()
          stopPolling()
          toast.error(generationError.value)
        } else if (state.status === 'cancelled') {
          isGenerating.value = false
          closeStream()
          stopPolling()
          toast.info('生成任务已取消')
        }
      } catch (err) {
        console.warn('解析 SSE 帧失败:', err)
      }
    }

    es.addEventListener('run.state', onSnapshot)

    es.onerror = () => {
      void pollSnapshot(runId, resourceId)
    }

    startPollingFallback(runId, resourceId)
  }

  async function pollSnapshot(runId: string, resourceId: number) {
    try {
      const resp = await getResourceRunSnapshot(runId)
      const state = resp.data?.data
      if (state) {
        applyRunState(state)
        if (state.status === 'completed') {
          await completeGeneration(resourceId)
        } else if (state.status === 'failed') {
          generationError.value = state.error || '资源生成失败'
          isGenerating.value = false
          closeStream()
          stopPolling()
        }
      }
    } catch {
      // 容错处理
    }
  }

  function startPollingFallback(runId: string, resourceId: number) {
    if (pollingTimer) return
    pollingTimer = setInterval(() => {
      void pollSnapshot(runId, resourceId)
    }, 4000)
  }

  function stopPolling() {
    if (pollingTimer) {
      clearInterval(pollingTimer)
      pollingTimer = null
    }
  }

  function closeStream() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  // 提交学习需求，进入个性化配置
  function submitInput() {
    if (!naturalInput.value.trim()) return
    currentPhase.value = 'personalize'
  }

  // 启动生成任务
  async function start(options?: {
    topic?: string
    learningGoal?: string
    targetResources?: ResourceAgentId[]
    difficulty?: import('../model/resource').DifficultyLevel
    preferences?: Record<string, unknown>
  }) {
    currentPhase.value = 'generating'
    resetGenerationState()
    if (options?.targetResources && options.targetResources.length > 0) {
      enabledAgentIds.value = options.targetResources
    }
    initializeWaitingNodes()
    isGenerating.value = true

    try {
      const requestParams: ResourceGenerationRequest = {
        topic: options?.topic || naturalInput.value,
        learning_goal: options?.learningGoal || '',
        target_resources: options?.targetResources || enabledAgentIds.value,
        difficulty: options?.difficulty || 'intermediate',
        preferences: options?.preferences || {},
      }

      const res = await startResourceGeneration(requestParams)
      const { run_id, resource_id } = res.data.data

      activeResourceId.value = resource_id
      activeRunId.value = run_id
      rememberActiveResource(resource_id)
      rememberRunId(resource_id, run_id)

      await router.replace({
        query: {
          ...route.query,
          resourceId: String(resource_id),
        },
      })

      startResourceStream(run_id, resource_id)
    } catch (err: unknown) {
      generationError.value = getErrorMessage(err, '启动生成失败')
      isGenerating.value = false
      toast.error(generationError.value)
    }
  }

  // 恢复未完成的生成任务
  async function restore(resourceId: number) {
    activeResourceId.value = resourceId
    rememberActiveResource(resourceId)
    currentPhase.value = 'generating'
    resetGenerationState()
    initializeWaitingNodes()
    isGenerating.value = true

    const runId = readRunId(resourceId)

    if (runId) {
      activeRunId.value = runId
      try {
        const resp = await getResourceRunSnapshot(runId)
        const state = resp.data?.data
        if (state) {
          applyRunState(state)
          if (state.status === 'completed') {
            await completeGeneration(resourceId)
            return
          }
          startResourceStream(runId, resourceId)
          return
        }
      } catch {
        // 快照不存在时降级检查 bundle
      }
    }

    // 若无 runId 或快照失败，尝试直接读取产物包
    try {
      const bundleResp = await getResourceBundle(resourceId)
      const bundle = bundleResp.data?.data
      if (bundle && bundle.resources?.length) {
        generatedResources.value = bundle.resources
        isGenerating.value = false
        currentPhase.value = 'result'
        return
      }
    } catch {
      // 无法获取
    }

    generationError.value = '无法恢复该资源生成任务'
    isGenerating.value = false
    currentPhase.value = 'input'
    forgetActiveResource(resourceId)
    const query = { ...route.query }
    delete query.resourceId
    await router.replace({ query })
    toast.error(generationError.value)
  }

  function resetGenerationState() {
    generatedResources.value = []
    generationError.value = null
    overallProgress.value = 0
    latestWorkflowMessage.value = ''
    isGenerating.value = false
    generationFinalized.value = false
    dagNodeStates.value = {}
    selectedDagNodeId.value = null
    planReady.value = false
  }

  function pause() {
    closeStream()
    stopPolling()
  }

  async function resume() {
    if (!activeRunId.value || !activeResourceId.value || !isGenerating.value || generationFinalized.value) return
    startResourceStream(activeRunId.value, activeResourceId.value)
  }

  async function cancel() {
    if (activeRunId.value) {
      try {
        await cancelResourceRun(activeRunId.value)
      } catch (err) {
        console.warn('取消运行请求失败:', err)
      }
    }
    pause()
    isGenerating.value = false
    toast.info('生成已取消')
  }

  function reset() {
    pause()
    if (activeResourceId.value) {
      forgetActiveResource(activeResourceId.value)
    }
    naturalInput.value = ''
    resetGenerationState()
    currentPhase.value = 'input'
    const query = { ...route.query }
    delete query.resourceId
    delete query.prompt
    void router.replace({ query })
  }

  function dispose() {
    pause()
  }

  return {
    currentPhase,
    naturalInput,
    enabledAgentIds,
    dagNodeStates,
    selectedDagNodeId,
    overallProgress,
    latestWorkflowMessage,
    generatedResources,
    generationError,
    planReady,
    isGenerating,
    activeResourceId,
    activeRunId,
    visibleWorkflowNodes,
    parallelPoolNodes,
    dagSelectedAgentIds,
    baseGenerationAgentIds,
    submitInput,
    start,
    restore,
    readActiveResourceId,
    reset,
    pause,
    resume,
    cancel,
    dispose,
    selectDagNode,
    getStageNode,
    hasGeneratedResource,
  }
}
