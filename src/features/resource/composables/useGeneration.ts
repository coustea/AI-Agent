import { ref, shallowRef, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
// 资源生成相关 API：启动生成、轮询状态、获取最终资源包
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
// DAG 节点常量、展示信息与节点工厂方法
import {
  PPT_AGENT_ID,
  CARTOON_AGENT_ID,
  COORDINATOR_AGENT_ID,
  BUNDLE_AGENT_ID,
  SYSTEM_AGENT_IDS,
  AGENT_DISPLAY,
  createDagNode,
  type AnyAgentConfigs,
  type DagNodeState,
} from '../model/catalog'

// 资源生成向导的四个阶段：输入需求 → 个性化配置 → 生成中 → 结果展示
export type Phase = 'input' | 'personalize' | 'generating' | 'result'

// 资源生成编排核心组合式函数：管理全流程状态、DAG 节点、SSE 事件流与轮询兜底
export function useGeneration() {
  const router = useRouter()
  const route = useRoute()

  // 当前所处阶段
  const currentPhase = ref<Phase>('input')
  // 用户自然语言输入的学习需求
  const naturalInput = ref('')
  // 学习场景预设
  const learningScenario = ref<LearningScenario>('daily_review')
  // 已启用的智能体 id 列表，默认全部启用
  const enabledAgentIds = ref<ResourceAgentId[]>(['content', 'mindmap', 'code', 'quiz', 'reading', 'ppt', 'cartoon'])

  // 各智能体的默认配置参数
  const agentConfigs = ref<AnyAgentConfigs>({
    content: { structure: 'progressive', depth_level: 'standard', focus_mode: 'full_coverage', include_examples: true },
    mindmap: { map_type: 'knowledge_tree', max_depth: 3, leaf_detail: 'brief_note', show_relations: true },
    quiz: { question_count: 5, difficulty_mode: 'adaptive', emphasis: 'foundations', question_types: ['single', 'multiple', 'judge', 'fill'] },
    code: { programming_language: 'python', output_style: 'tutorial', focus: 'syntax', include_tests: false },
    reading: { coverage: 'extended', max_items: 3, language_preference: 'chinese', focus: 'textbook' },
    ppt: { template: 'auto', narrative_style: 'concept', density: 'standard', emphasis: ['core_concepts'] },
    cartoon: { depth: 'standard', pace: 'normal' },
  })

  // DAG 选中的智能体 id 列表（直接使用 enabledAgentIds）
  const dagSelectedAgentIds = computed(() => enabledAgentIds.value)

  // 基础并行生成智能体 id：排除需要单独流水线阶段的 PPT/动画
  const baseGenerationAgentIds = computed(() => (
    dagSelectedAgentIds.value.filter(id => ![PPT_AGENT_ID, CARTOON_AGENT_ID].includes(id))
  ))

  // 所有 DAG 节点的状态映射表，key 为节点 id
  const dagNodeStates = ref<Record<string, DagNodeState>>({})
  // 当前被用户选中的 DAG 节点 id（用于展开详情面板）
  const selectedDagNodeId = ref<string | null>(null)
  // 全局加权的整体进度百分比 0-100
  const overallProgress = ref(0)
  // 最新一条工作流消息，显示在顶部状态栏
  const latestWorkflowMessage = ref('')
  // 已生成的资源摘要列表（shallowRef 避免深度监听大对象）
  const generatedResources = shallowRef<Array<Record<string, any>>>([])
  // 最终资源包数据
  const finalBundle = shallowRef<any | null>(null)
  // 生成错误信息
  const generationError = ref<string | null>(null)
  // 结果页面的警告提示（部分失败时展示）
  const resultWarning = ref('')

  // 规划阶段是否完成
  const planReady = ref(false)
  // 最近产生产物的智能体 id，用于触发产物就绪动画高亮
  const latestArtifactAgentId = ref<string | null>(null)

  // 是否正在生成中
  const isGenerating = ref(false)
  // 生成是否已最终收尾（防止重复执行完成逻辑）
  const generationFinalized = ref(false)
  // 当前生成任务的资源 id
  const activeResourceId = ref<number | null>(null)
  // 轮询兜底的定时器句柄
  const pollingInterval = ref<ReturnType<typeof setInterval> | null>(null)
  // SSE 事件流连接管理
  const resourceEvents = useResourceEvents()
  // 任务选择集在创建时已由后端持久化；这里保留本次页面会话缓存，防止首次
  // 轮询早于后端写入快照时用不完整数据覆盖用户刚刚选择的 Agent。
  const selectedAgentsHydrated = ref(false)

  function selectedAgentsCacheKey(resourceId: number) {
    return `resource-generation:selected-agents:v2:${resourceId}`
  }

  function generationStateCacheKey(resourceId: number) {
    return `resource-generation:state:v2:${resourceId}`
  }

  function cacheSelectedAgents(resourceId: number, agentIds: ResourceAgentId[]) {
    sessionStorage.setItem(selectedAgentsCacheKey(resourceId), JSON.stringify(agentIds))
  }

  function readCachedSelectedAgents(resourceId: number): ResourceAgentId[] {
    try {
      const parsed = JSON.parse(sessionStorage.getItem(selectedAgentsCacheKey(resourceId)) || '[]')
      return Array.isArray(parsed)
        ? parsed.filter(id => typeof id === 'string' && AGENT_DISPLAY[id]) as ResourceAgentId[]
        : []
    } catch {
      return []
    }
  }

  // 缓存生成状态，支持刷新页面后恢复
  interface CachedGenerationState {
    naturalInput: string
    learningScenario: LearningScenario
    enabledAgentIds: ResourceAgentId[]
    agentConfigs: AnyAgentConfigs
    timestamp: number
  }

  function cacheGenerationState(resourceId: number) {
    const state: CachedGenerationState = {
      naturalInput: naturalInput.value,
      learningScenario: learningScenario.value,
      enabledAgentIds: enabledAgentIds.value,
      agentConfigs: agentConfigs.value,
      timestamp: Date.now(),
    }
    sessionStorage.setItem(generationStateCacheKey(resourceId), JSON.stringify(state))
  }

  function readCachedGenerationState(resourceId: number): CachedGenerationState | null {
    try {
      const raw = sessionStorage.getItem(generationStateCacheKey(resourceId))
      if (!raw) return null
      const state = JSON.parse(raw) as CachedGenerationState
      // 缓存超过 24 小时则失效
      if (Date.now() - state.timestamp > 24 * 60 * 60 * 1000) {
        sessionStorage.removeItem(generationStateCacheKey(resourceId))
        return null
      }
      return state
    } catch {
      return null
    }
  }

  function clearGenerationCache(resourceId: number) {
    sessionStorage.removeItem(selectedAgentsCacheKey(resourceId))
    sessionStorage.removeItem(generationStateCacheKey(resourceId))
  }

  function hydrateSelectedAgents(resourceId: number, selectedAgents: string[]) {
    const fromStatus = selectedAgents.filter(id => AGENT_DISPLAY[id]) as ResourceAgentId[]
    const cached = readCachedSelectedAgents(resourceId)
    // 首次恢复优先使用任务快照；旧任务的快照若尚不完整，则以会话缓存补齐，
    // 后续轮询只补全，绝不移除已进入本次任务的卡片。
    const authoritative = fromStatus.length ? fromStatus : cached
    const merged = selectedAgentsHydrated.value
      ? [...new Set([...enabledAgentIds.value, ...authoritative])]
      : [...new Set([...authoritative, ...cached])]
    if (merged.length) {
      enabledAgentIds.value = merged
      cacheSelectedAgents(resourceId, merged)
    }
    selectedAgentsHydrated.value = true
  }

  // 选中某个 DAG 节点，展开其详情
  function selectDagNode(id: string) {
    selectedDagNodeId.value = id
  }

  // 按固定顺序构建 DAG 节点列表：规划 → 调度中枢 → 并行池 → PPT/动画/视频 → 组装
  const dagNodesV2 = computed<DagNodeState[]>(() => {
    const selected = dagSelectedAgentIds.value
    const nodes: DagNodeState[] = []
    // 规划任务节点始终排在最前
    nodes.push(dagNodeStates.value['planning'] || { id: 'planning', label: '规划任务', icon: '🎯', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: true })
    // 并行调度中枢节点
    nodes.push(dagNodeStates.value[COORDINATOR_AGENT_ID] || { id: COORDINATOR_AGENT_ID, label: '并行调度中枢', icon: '⚙️', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: true })
    // 基础并行生成智能体节点
    for (const agentId of baseGenerationAgentIds.value) {
      const display = AGENT_DISPLAY[agentId]
      if (!display) continue
      nodes.push(dagNodeStates.value[agentId] || { id: agentId, label: display.label, icon: display.icon, status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: false })
    }
    // PPT 智能体仅在用户启用时出现
    if (selected.includes(PPT_AGENT_ID)) {
      nodes.push(dagNodeStates.value[PPT_AGENT_ID] || { id: PPT_AGENT_ID, label: '演示文稿助手', icon: '📊', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: false })
    }
    // 动画讲解智能体仅在用户启用时出现
    if (selected.includes(CARTOON_AGENT_ID)) {
      nodes.push(dagNodeStates.value[CARTOON_AGENT_ID] || { id: CARTOON_AGENT_ID, label: '动画讲解助手', icon: '🎬', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: false })
    }
    // 资源组装节点始终排在最后
    nodes.push(dagNodeStates.value[BUNDLE_AGENT_ID] || { id: BUNDLE_AGENT_ID, label: '资源组装', icon: '📦', status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], eventLogs: [], isSystem: true })
    return nodes
  })

  // 判断节点是否已"进入"工作流（开始或已完成），用于决定是否在界面显示
  function hasNodeEntered(node?: DagNodeState) {
    if (!node) return false
    // 规划节点始终可见
    if (node.id === 'planning') return true
    return node.status !== 'waiting' || node.progress > 0 || Boolean(node.currentMessage) || (node.stepHistory?.length || 0) > 0 || hasGeneratedResource(node.id)
  }

  // 仅保留已进入工作流的节点，供工作流面板渲染
  const visibleWorkflowNodes = computed(() => dagNodesV2.value.filter(node => hasNodeEntered(node)))

  // 按 id 获取某节点状态，若不存在则创建默认等待节点
  function getStageNode(id: string) {
    return dagNodeStates.value[id] || createDagNode(id, SYSTEM_AGENT_IDS.includes(id))
  }

  // 判断某类型资源是否已生成成功
  function hasGeneratedResource(type: string) {
    const isReadyInResources = generatedResources.value.some(resource => resource.type === type)
    const isReadyInDag = dagNodeStates.value[type]?.status === 'success'
    return isReadyInResources || isReadyInDag
  }

  // 并行池节点列表，按状态优先级（失败 > 运行中 > 成功 > 等待 > 跳过）和进度降序排序
  const parallelPoolNodes = computed(() => {
    const agentStatusRank: Record<DagNodeState['status'], number> = { failed: 0, running: 1, success: 2, waiting: 3, skipped: 4 }
    return baseGenerationAgentIds.value.map(agentId => getStageNode(agentId)).sort((a, b) => {
      const rankDiff = agentStatusRank[a.status] - agentStatusRank[b.status]
      if (rankDiff !== 0) return rankDiff
      return b.progress - a.progress
    })
  })

  // 根据各阶段加权进度计算全局整体进度
  function updateOverallProgressFromDag() {
    // 各阶段权重：规划 15%、并行池 55%、PPT/动画各 15%、组装 10%
    const stages = [
      { weight: 15, progress: getStageNode('planning').progress },
      { weight: 55, progress: parallelPoolNodes.value.length ? parallelPoolNodes.value.reduce((sum, node) => sum + node.progress, 0) / parallelPoolNodes.value.length : 0 },
      ...(dagSelectedAgentIds.value.includes(PPT_AGENT_ID as ResourceAgentId) ? [
        { weight: 15, progress: getStageNode(PPT_AGENT_ID).progress },
      ] : []),
      ...(dagSelectedAgentIds.value.includes(CARTOON_AGENT_ID as ResourceAgentId) ? [
        { weight: 15, progress: getStageNode(CARTOON_AGENT_ID).progress },
      ] : []),
      { weight: 10, progress: getStageNode(BUNDLE_AGENT_ID).progress },
    ]
    const weightTotal = stages.reduce((sum, item) => sum + item.weight, 0)
    const weighted = stages.reduce((sum, item) => sum + item.progress * item.weight, 0)
    overallProgress.value = Math.round(weighted / weightTotal)
  }

  // 生成开始前初始化所有 DAG 节点为等待状态
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

  // 将后端事件状态映射为前端 DAG 节点状态枚举
  function normalizeEventStatus(status?: string | null): DagNodeState['status'] | undefined {
    if (!status) return undefined
    if (status === 'finished' || status === 'completed') return 'success'
    if (status === 'failed' || status === 'interrupted') return 'failed'
    if (status === 'skipped') return 'skipped'
    if (status === 'running') return 'running'
    return undefined
  }

  function normalizeEventTimestamp(timestamp?: number | null) {
    if (!timestamp || !Number.isFinite(timestamp)) return Date.now()
    // 兼容历史任务曾以秒为单位保存的事件；当前后端统一返回毫秒。
    return timestamp < 10_000_000_000 ? timestamp * 1000 : timestamp
  }

  // 将一条资源事件追加到节点的日志列表，相同消息做合并更新
  function appendResourceEventLog(node: DagNodeState, event: ResourceEvent) {
    const message = event.message.trim()
    if (!message) return

    const dataStatus = event.data.status as string | undefined
    const eventStatus = normalizeEventStatus(dataStatus)
    const logs = node.eventLogs || []
    const last = logs[logs.length - 1]
    const eventPhase = typeof event.data.phase === 'string' ? event.data.phase : undefined
    const eventElapsedMs = event.data.elapsed_ms as number | undefined

    // 若最新日志与当前消息及阶段相同，则就地更新而非新增
    const sameMessage = last && last.message === message && last.phase === eventPhase

    if (sameMessage) {
      node.eventLogs = [
        ...logs.slice(0, -1),
        {
          ...last,
          status: eventStatus || last.status,
          progress: event.progress ?? last.progress,
          elapsedMs: eventElapsedMs ?? last.elapsedMs,
          timestamp: normalizeEventTimestamp(event.timestamp),
        },
      ]
      return
    }

    // 新增一条日志，仅保留最近 12 条避免列表无限增长
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
        timestamp: normalizeEventTimestamp(event.timestamp),
      },
    ]
  }

  // 处理规划阶段完成事件，标记规划阶段就绪
  function handlePlanningAnimation(event: ResourceEvent) {
    if (event.agent_id === 'planning' && event.event === 'agent.status') {
      const dataStatus = event.data.status as string | undefined
      if (dataStatus === 'completed') planReady.value = true
    }
  }

  // 处理产物就绪事件，短暂高亮对应智能体节点
  function handleArtifactReadyAnimation(event: ResourceEvent) {
    if (!event.agent_id) return
    latestArtifactAgentId.value = event.agent_id
    // 1.4 秒后清除高亮（若未被后续事件覆盖）
    window.setTimeout(() => {
      if (latestArtifactAgentId.value === event.agent_id) latestArtifactAgentId.value = null
    }, 1400)
  }

  // 工作流动画总调度：根据事件类型分发到规划或产物高亮处理
  function handleWorkflowAnimation(event: ResourceEvent) {
    if (!event.agent_id) return
    if (event.agent_id === 'planning') handlePlanningAnimation(event)
    if (typeof event.data.artifact_id === 'string' && event.data.artifact_id) handleArtifactReadyAnimation(event)
  }

  // 核心函数：将一条 SSE 事件应用到对应 DAG 节点，更新状态/进度/消息/产物等
  function applyResourceEvent(event: ResourceEvent) {
    // 无 agent_id 的事件属于全局生成级事件
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

    // 取出或创建对应节点，做浅拷贝后修改再整体替换以触发响应式
    const existing = dagNodeStates.value[event.agent_id] || createDagNode(event.agent_id, SYSTEM_AGENT_IDS.includes(event.agent_id))
    const node = { ...existing }

    // 根据 agent.status 事件更新节点运行状态
    if (event.event === 'agent.status') {
      const dataStatus = event.data.status as string | undefined
      if (dataStatus === 'completed') node.status = 'success'
      else if (dataStatus === 'failed') node.status = 'failed'
      else if (dataStatus === 'pending') node.status = 'waiting'
      else if (dataStatus === 'running') node.status = 'running'
    }

    // 进度只增不减
    if (event.progress != null) node.progress = Math.max(node.progress, event.progress)
    if (typeof event.data.phase === 'string') node.phase = event.data.phase
    const elapsedMs = event.data.elapsed_ms as number | undefined
    if (elapsedMs != null) node.elapsedMs = elapsedMs
    // 合并指标数据
    const metrics = event.data.metrics as Record<string, unknown> | undefined
    if (metrics && typeof metrics === 'object' && !Array.isArray(metrics)) node.metrics = { ...(node.metrics || {}), ...metrics }
    const eventMetrics = Object.fromEntries(
      Object.entries(event.data).filter(([key, value]) => (
        !['status', 'phase', 'artifact_id', 'elapsed_ms', 'heartbeat', 'metrics'].includes(key)
        && value !== null
        && value !== undefined
      )),
    )
    if (Object.keys(eventMetrics).length) node.metrics = { ...(node.metrics || {}), ...eventMetrics }
    const artifactId = event.data.artifact_id as string | undefined
    if (typeof artifactId === 'string') node.artifactId = artifactId
    node.lastUpdatedAt = normalizeEventTimestamp(event.timestamp)
    // 更新当前消息并追加到步骤历史（保留最近 8 条）
    const message = event.message
    if (message) {
      node.currentMessage = message
      if (node.stepHistory[node.stepHistory.length - 1] !== message) {
        node.stepHistory = [...node.stepHistory.slice(-7), message]
      }
      appendResourceEventLog(node, event)
    }

    // 将更新后的节点写回状态表
    dagNodeStates.value = {
      ...dagNodeStates.value,
      [event.agent_id]: node,
    }
    handleWorkflowAnimation(event)
    updateOverallProgressFromDag()
  }

  // 将轮询返回的任务状态同步到前端状态（用于 SSE 中断后的全量恢复）
  function applyTaskStatus(taskStatus: ResourceTaskStatus) {
    if (taskStatus.learning_need) naturalInput.value = taskStatus.learning_need
    // 恢复已选智能体列表
    if (Array.isArray(taskStatus.selected_agents)) {
      hydrateSelectedAgents(taskStatus.resource_id, taskStatus.selected_agents)
    }
    // 合并资源摘要，保留已有的详细 content 避免覆盖
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
    // 将各智能体快照转为事件逐条应用，恢复节点完整状态
    if (taskStatus.agent_snapshots) {
      Object.values(taskStatus.agent_snapshots).forEach((snapshot) => {
        if (snapshot.agent_id) {
          let dataStatus = 'running'
          if (snapshot.status === 'completed') dataStatus = 'completed'
          else if (snapshot.status === 'failed' || snapshot.status === 'interrupted') dataStatus = 'failed'
          else if (snapshot.status === 'pending') dataStatus = 'pending'

          applyResourceEvent({
            sequence: 0,
            resource_id: taskStatus.resource_id,
            event: 'agent.status',
            agent_id: snapshot.agent_id,
            message: snapshot.message || '',
            progress: snapshot.progress ?? 0,
            data: {
              status: dataStatus,
              phase: snapshot.phase,
              metrics: snapshot.metrics || {},
              artifact_id: snapshot.artifact_id,
              elapsed_ms: snapshot.elapsed_ms,
            },
            timestamp: snapshot.timestamp || Date.now(),
          })
        }
      })
    }
    // 整体进度通过 DAG 加权计算
    updateOverallProgressFromDag()
  }

  // 生成完成后的收尾：拉取资源包、更新结果状态、清理连接
  async function completeGeneration(resourceId: number, taskStatus: ResourceTaskStatus) {
    // 防止重复收尾
    if (generationFinalized.value) return
    generationFinalized.value = true
    stopPolling()
    stopResourceStream()

    // 拉取最终资源包，失败不阻断流程
    let bundle: any = null
    try {
      bundle = (await getResourceBundle(resourceId)).data?.data
    } catch {
      // bundle 获取失败不影响后续流程
    }

    const hasResources = Array.isArray(bundle?.resources) && bundle.resources.length > 0

    // 有可用资源则进入结果展示阶段
    if (hasResources) {
      finalBundle.value = bundle
      generatedResources.value = bundle.resources
      // 根据任务状态设置相应的警告提示文案
      resultWarning.value = taskStatus.status === 'partial_completed'
        ? '部分资源生成失败，以下已完成内容仍可查看。'
        : taskStatus.status === 'failed'
          ? '资源生成未完全成功，以下已完成内容仍可查看。'
          : ''
      isGenerating.value = false
      currentPhase.value = 'result'
      return
    }

    // 无任何资源可展示则报错
    generationError.value = '资源生成失败，暂无可展示内容'
    isGenerating.value = false
    toast.error(generationError.value || '资源生成失败，暂无可展示内容')
  }

  // 单次轮询任务状态并处理完成逻辑
  async function checkStatusOnce(resourceId: number) {
    const taskStatus = (await pollResourceStatus(resourceId)).data.data
    applyTaskStatus(taskStatus)
    // 终态状态触发完成收尾
    const status = taskStatus.status || ''
    if (['completed', 'partial_completed', 'failed'].includes(status)) {
      await completeGeneration(resourceId, taskStatus)
    }
  }

  // 启动轮询兜底：SSE 不稳定时每 4 秒轮询一次状态作为保底
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

  // 生成完成后尽快同步一次完整状态（确保资源列表与后端一致）
  function syncStatusSoon(resourceId: number) {
    void checkStatusOnce(resourceId).catch((err: any) => { console.warn('[ResourceGenerator] 状态同步失败:', err) })
  }

  // 启动资源事件流：同时建立 SSE 连接和轮询兜底，监听生成进度
  function startResourceStream(resourceId: number) {
    stopResourceStream()
    startPollingFallback(resourceId)
    resourceEvents.connect(resourceId, {
      // 每条事件应用到 DAG 并更新工作流消息
      onEvent: (event) => {
        applyResourceEvent(event)
        if (event.message) latestWorkflowMessage.value = event.message
        // 生成完成事件触发一次状态同步确保资源一致
        if (event.event === 'generation.completed') syncStatusSoon(resourceId)
      },
      // SSE 连接完成回调：拉取最终状态
      onCompleted: () => {
        void checkStatusOnce(resourceId).catch(() => {
          void completeGeneration(resourceId, { resource_id: resourceId, status: 'completed' })
        })
      },
      // SSE 连接失败回调：尝试拉取状态，失败则按失败处理
      onFailed: () => {
        void checkStatusOnce(resourceId).catch(() => {
          void completeGeneration(resourceId, { resource_id: resourceId, status: 'failed' })
        })
      },
    })
  }

  // 启动新一轮资源生成：重置状态、发起请求、建立事件流
  const start = async () => {
    currentPhase.value = 'generating'
    resetGenerationState()
    initializeWaitingNodes()
    isGenerating.value = true

    try {
      // 构建生成请求参数
      const requestParams: ResourceGenerationRequest = {
        learning_need: naturalInput.value,
        learning_scenario: learningScenario.value,
        selected_agents: enabledAgentIds.value.map((id) => ({ agent_id: id, enabled: true })).filter(a => a.enabled),
        agent_configs: agentConfigs.value,
      }
      // 发起生成请求并获取资源 id
      const { resource_id } = (await startResourceGeneration(requestParams)).data.data
      activeResourceId.value = resource_id
      selectedAgentsHydrated.value = true
      // 缓存选中的智能体和生成状态，支持刷新恢复
      cacheSelectedAgents(resource_id, enabledAgentIds.value)
      cacheGenerationState(resource_id)
      // 将资源 id 写入 URL query，支持刷新后恢复
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

  // 重置所有生成相关状态到初始值
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
    selectedAgentsHydrated.value = false
  }

  // 停止轮询定时器
  const stopPolling = () => {
    if (pollingInterval.value) { clearInterval(pollingInterval.value); pollingInterval.value = null }
  }

  // 关闭 SSE 事件流连接
  const stopResourceStream = () => {
    resourceEvents.close()
  }

  // 提交输入需求，进入个性化配置阶段
  const submitInput = () => {
    if (!naturalInput.value.trim()) return
    currentPhase.value = 'personalize'
  }

  // 从已有资源 id 恢复生成状态（页面刷新后通过 URL resourceId 恢复）
  const restore = async (resourceId: number) => {
    currentPhase.value = 'generating'
    resetGenerationState()
    initializeWaitingNodes()
    activeResourceId.value = resourceId
    isGenerating.value = true

    // 先尝试从缓存恢复生成状态
    const cachedState = readCachedGenerationState(resourceId)
    if (cachedState) {
      naturalInput.value = cachedState.naturalInput
      learningScenario.value = cachedState.learningScenario
      enabledAgentIds.value = cachedState.enabledAgentIds
      agentConfigs.value = cachedState.agentConfigs
      selectedAgentsHydrated.value = true
    } else {
      // 无缓存时尝试从 selected_agents 缓存恢复
      const cachedSelection = readCachedSelectedAgents(resourceId)
      if (cachedSelection.length) {
        enabledAgentIds.value = cachedSelection
        selectedAgentsHydrated.value = true
      }
    }

    try {
      // 拉取当前任务状态并应用
      const taskStatus = (await pollResourceStatus(resourceId)).data.data
      applyTaskStatus(taskStatus)
      // 若任务已结束则直接完成收尾
      const status = taskStatus.status || ''
      if (['completed', 'partial_completed', 'failed'].includes(status)) {
        await completeGeneration(resourceId, taskStatus)
        return
      }
      // 任务仍在进行则恢复事件流监听
      startResourceStream(resourceId)
    } catch (err: any) {
      generationError.value = err.message || '无法恢复资源生成任务'
      isGenerating.value = false
      currentPhase.value = 'input'
      // 恢复失败则清除 URL 中的 resourceId 参数和缓存
      clearGenerationCache(resourceId)
      const query = { ...route.query }
      delete query.resourceId
      await router.replace({ query })
      toast.error(generationError.value || '无法恢复资源生成任务')
    }
  }

  // 暂停生成：停止轮询和 SSE 连接
  const pause = () => {
    stopPolling()
    stopResourceStream()
  }

  // 恢复生成：先同步一次状态再重新建立事件流
  const resume = async () => {
    const resourceId = activeResourceId.value
    if (!resourceId || !isGenerating.value || generationFinalized.value) return
    try { await checkStatusOnce(resourceId) } catch { latestWorkflowMessage.value = '状态同步失败，正在重试实时连接' }
    if (activeResourceId.value === resourceId && isGenerating.value && !generationFinalized.value) startResourceStream(resourceId)
  }

  // 完全重置：回到输入阶段并清理 URL 参数和缓存
  const reset = () => {
    stopPolling()
    stopResourceStream()
    // 清理当前任务的缓存
    if (activeResourceId.value) {
      clearGenerationCache(activeResourceId.value)
    }
    naturalInput.value = ''
    resetGenerationState()
    currentPhase.value = 'input'
    const query = { ...route.query }
    delete query.resourceId
    delete query.prompt
    void router.replace({ query })
  }

  // 销毁时暂停所有连接，释放资源
  const dispose = () => {
    pause()
  }

  // 暴露给组件使用的全部响应式状态和操作函数
  return {
    // 阶段与用户输入状态
    currentPhase,
    naturalInput,
    learningScenario,
    enabledAgentIds,
    agentConfigs,
    // DAG 节点状态与选择
    dagNodeStates,
    selectedDagNodeId,
    // 进度与消息
    overallProgress,
    latestWorkflowMessage,
    // 生成结果
    generatedResources,
    finalBundle,
    generationError,
    resultWarning,
    // 动画控制状态
    planReady,
    latestArtifactAgentId,
    // 生成任务运行状态
    isGenerating,
    activeResourceId,
    // 计算派生的节点列表
    visibleWorkflowNodes,
    parallelPoolNodes,
    dagSelectedAgentIds,
    baseGenerationAgentIds,
    // 用户操作函数
    submitInput,
    start,
    restore,
    reset,
    pause,
    resume,
    dispose,
    // DAG 节点操作
    selectDagNode,
    getStageNode,
    hasGeneratedResource,
    applyResourceEvent,
  }
}
