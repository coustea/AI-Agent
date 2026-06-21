<template>
  <div class="phase-view generating-view workflow-stage-page workflow-stage-page-v4">
    <header class="stage-topbar stage-topbar-v4">
      <div class="stage-title-area">
        <div class="stage-route-progress">
          <span class="route-step done">1 需求解析</span>
          <span class="route-line done"></span>
          <span class="route-step" :class="planReady ? 'done' : 'active'">2 计划生成</span>
          <span class="route-line" :class="{ active: planReady }"></span>
          <span class="route-step" :class="{ active: planReady }">3 任务调度</span>
          <span class="route-line"></span>
          <span class="route-step">4 资源生成</span>
          <span class="route-line"></span>
          <span class="route-step">5 质量校验</span>
          <span class="route-line"></span>
          <span class="route-step">6 打包交付</span>
        </div>
        <h2>多智能体资源生成</h2>
        <p>{{ dagHeroMessage }}</p>
      </div>

      <div class="stage-stat-group stage-stat-group-v4">
        <div class="stage-stat-card progress-stat-card">
          <span>生成进度</span>
          <strong>{{ overallProgress }}%</strong>
          <div class="mini-progress-track"><i :style="{ width: `${overallProgress}%` }"></i></div>
        </div>
        <div class="stage-stat-card">
          <span>活跃 Agent</span>
          <strong>{{ runningAgentCount }}<small>/{{ dagSelectedAgentIds.length }}</small></strong>
        </div>
        <div class="stage-stat-card wide">
          <span>产物坞</span>
          <strong>{{ generatedResources.length }}<small> 项</small></strong>
        </div>
        <el-button round class="stage-log-btn" @click="workflowLogDrawerVisible = true">
          运行日志
          <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
      </div>
    </header>

    <el-alert
      v-if="generationError"
      class="stage-generation-error"
      type="error"
      :closable="false"
      show-icon
      :title="generationError"
    />

    <main class="agent-stage-shell-v4">
      <section class="dispatch-workbench-panel dispatch-workbench-panel-v4">
        <div class="workbench-header workbench-header-v4">
          <div>
            <span class="panel-eyebrow">DISPATCH WORKBENCH</span>
            <h3>多智能体协作流程</h3>
            <p>点击任意 Agent 工位查看详情；详情面板默认隐藏，不占用主舞台空间。</p>
          </div>
          <div class="workbench-actions">
            <span class="control-pill active"><span class="live-dot"></span> SSE 实时流追踪</span>
            <span class="control-pill muted">计划 {{ planReady ? '已生成' : '生成中' }}</span>
            <el-button round size="small" @click="workflowLogDrawerVisible = true">查看日志</el-button>
          </div>
        </div>

        <div ref="flowCanvasRef" class="agent-flow-canvas agent-flow-canvas-v4">
          <div class="flow-grid-bg"></div>
          <div class="flow-orbit orbit-one"></div>
          <div class="flow-orbit orbit-two"></div>
          <div class="flow-orbit orbit-three"></div>

          <div class="learning-demand-float">
            <span>学习需求</span>
            <strong>{{ naturalInput || '等待学习需求' }}</strong>
            <p>{{ latestWorkflowMessage || 'PlanningAgent 正在解析目标、画像与资源需求' }}</p>
          </div>

          <div class="master-plan-float">
            <div>
              <span class="panel-eyebrow">MASTER PLAN</span>
              <strong>{{ planReady ? '计划已生成' : '计划生成中' }}</strong>
            </div>
            <div class="master-plan-track"><b :style="{ width: `${getStageNode('planning').progress}%` }"></b></div>
          </div>

          <div class="flow-core-stack flow-core-stack-v4">
            <article
              class="core-agent-node planning-core"
              :class="['status-' + getStageNode('planning').status, { 'is-selected': selectedDagNodeId === 'planning' }]"
              @click="handleAgentClick('planning')"
            >
              <div class="core-icon">🤖</div>
              <div>
                <strong>PlanningAgent</strong>
                <span>{{ getNodeStageLabel(getStageNode('planning')) }}</span>
              </div>
              <div class="core-progress">{{ getStageNode('planning').progress }}%</div>
            </article>

            <div class="core-link-line"><i></i></div>

            <article
              ref="coordinatorNodeRef"
              class="core-agent-node coordinator-core"
              :class="['status-' + getStageNode(COORDINATOR_AGENT_ID).status, { 'is-selected': selectedDagNodeId === COORDINATOR_AGENT_ID }]"
              @click="handleAgentClick(COORDINATOR_AGENT_ID)"
            >
              <div class="core-icon">⚙️</div>
              <div>
                <strong>Coordinator</strong>
                <span>{{ getNodeStageLabel(getStageNode(COORDINATOR_AGENT_ID)) }}</span>
              </div>
              <div class="core-progress">{{ getStageNode(COORDINATOR_AGENT_ID).progress }}%</div>
            </article>
          </div>

          <svg class="agent-link-svg" :viewBox="'0 0 ' + linkCanvasSize.width + ' ' + linkCanvasSize.height" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <linearGradient id="agentLinkGradient" x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stop-color="#3B82F6" stop-opacity="0.22" />
                <stop offset="52%" stop-color="#06B6D4" stop-opacity="0.8" />
                <stop offset="100%" stop-color="#8B5CF6" stop-opacity="0.28" />
              </linearGradient>
              <filter id="agentLinkGlow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            <path
              v-for="link in agentLinkPaths"
              :key="link.id"
              class="agent-link-path"
              :class="`status-${link.status}`"
              :d="link.d"
            />
            <circle
              v-for="link in agentLinkPaths"
              :key="`${link.id}-dot`"
              class="agent-link-dot"
              :class="`status-${link.status}`"
              :cx="link.x"
              :cy="link.y"
              r="4"
            />
          </svg>

          <transition-group name="agent-station" tag="div" class="agent-station-row agent-station-row-v4">
            <article
              v-for="node in parallelPoolNodes"
              :key="node.id"
              class="agent-station-card agent-station-card-v4"
              :ref="el => setStationCardRef(node.id, el)"
              :class="['status-' + node.status, { 'is-selected': selectedDagNodeId === node.id, 'has-artifact': hasGeneratedResource(node.id) }]"
              @click="handleAgentClick(node.id)"
            >
              <div class="station-header">
                <div class="station-icon">{{ node.icon }}</div>
                <div>
                  <strong>{{ node.label }}</strong>
                  <span>Agent</span>
                </div>
                <em>{{ getNodeStatusLabel(node) }}</em>
              </div>
              <div class="station-live-log" :class="[`is-${node.status}`, { 'is-empty': !getNodeLiveLogs(node).length }]">
                <template v-if="getNodeLiveLogs(node).length">
                  <div class="station-live-current">
                    <span class="station-live-dot"></span>
                    <div>
                      <strong>{{ getNodePhaseLabel(node) }}</strong>
                      <p>{{ getNodeDisplayMessage(node) }}</p>
                    </div>
                  </div>

                  <div class="station-live-lines">
                    <p
                      v-for="log in getNodeLiveLogs(node, 3)"
                      :key="log.id"
                      class="station-live-line"
                      :class="`is-${log.status || node.status}`"
                    >
                      <span>{{ getLogPhaseLabel(log.phase) }}</span>
                      <em>{{ log.message }}</em>
                    </p>
                  </div>
                </template>

                <div v-else class="station-live-empty">
                  <span class="station-live-dot muted"></span>
                  <p>等待该智能体接收调度指令</p>
                </div>
              </div>
              <div class="station-footer">
                <span>{{ getNodeStageLabel(node) }}</span>
                <i :style="{ width: `${node.progress}%` }"></i>
              </div>
            </article>
          </transition-group>

          <div class="review-station-row review-station-row-v4">
            <article
              v-for="node in trailingStageNodes"
              :key="node.id"
              class="review-station-card review-station-card-v4"
              :class="['status-' + node.status, { 'is-selected': selectedDagNodeId === node.id }]"
              @click="handleAgentClick(node.id)"
            >
              <div class="review-icon">{{ node.icon }}</div>
              <div>
                <strong>{{ node.label }}</strong>
                <span>{{ getNodeStageLabel(node) }}</span>
              </div>
              <em>{{ node.progress }}%</em>
            </article>
          </div>
        </div>
      </section>

      <transition name="detail-float">
        <aside v-if="detailPanelVisible && selectedDagNode" class="agent-detail-floating-panel">
          <button class="detail-close-btn" type="button" @click="closeAgentDetail">×</button>

          <div class="detail-panel-title">
            <div>
              <span class="panel-eyebrow">AGENT DETAIL</span>
              <h3>Agent 详情</h3>
            </div>
            <span class="control-pill muted">点击后显示</span>
          </div>

          <div class="selected-agent-detail-card">
            <div class="detail-agent-head">
              <div class="focus-agent-icon">{{ selectedDagNode.icon }}</div>
              <div>
                <h4>{{ selectedDagNode.label }}</h4>
                <p>{{ getNodeStageLabel(selectedDagNode) }}</p>
              </div>
              <span class="detail-status-dot" :class="`status-${selectedDagNode.status}`"></span>
            </div>

            <div class="detail-current-task">
              <span>当前任务</span>
              <strong>{{ getNodeDisplayMessage(selectedDagNode) }}</strong>
              <div class="detail-progress-line">
                <i :style="{ width: `${selectedDagNode.progress}%` }"></i>
              </div>
              <em>{{ selectedDagNode.progress }}%</em>
            </div>

            <dl class="focus-metrics detail-metrics-v3">
              <div>
                <dt>当前阶段</dt>
                <dd>{{ getNodePhaseLabel(selectedDagNode) }}</dd>
              </div>
              <div>
                <dt>运行耗时</dt>
                <dd>{{ formatElapsed(selectedDagNode.elapsedMs) }}</dd>
              </div>
              <div>
                <dt>最近更新</dt>
                <dd>{{ getNodeTimeLabel(selectedDagNode) }}</dd>
              </div>
              <div>
                <dt>产物状态</dt>
                <dd>{{ hasGeneratedResource(selectedDagNode.id) ? '已进入产物坞' : '等待生成' }}</dd>
              </div>
            </dl>

            <div class="detail-io-grid">
              <div>
                <span>输入</span>
                <p>学习需求 / 用户画像 / 教学蓝图</p>
              </div>
              <div>
                <span>输出</span>
                <p>{{ hasGeneratedResource(selectedDagNode.id) ? getAgentOutputFormat(selectedDagNode.id) : '生成中 / 等待中' }}</p>
              </div>
            </div>

            <div class="focus-metric-chips" v-if="getMetricChips(selectedDagNode).length">
              <span v-for="chip in getMetricChips(selectedDagNode)" :key="chip">{{ chip }}</span>
            </div>

            <div class="focus-history detail-history-v3">
              <span class="panel-eyebrow">SSE EVENT STREAM</span>

              <div
                v-for="log in getNodeLiveLogs(selectedDagNode, 8)"
                :key="log.id"
                class="detail-live-log-item"
                :class="`is-${log.status || selectedDagNode.status}`"
              >
                <div>
                  <span>{{ getLogPhaseLabel(log.phase) }}</span>
                  <em>{{ log.elapsedMs ? formatElapsed(log.elapsedMs) : getNodeTimeLabel(selectedDagNode) }}</em>
                </div>
                <p>{{ log.message }}</p>
              </div>

              <p v-if="!getNodeLiveLogs(selectedDagNode, 8).length">等待该智能体上报执行步骤</p>
            </div>
          </div>
        </aside>
      </transition>
    </main>

    <section class="output-dock-section output-dock-section-v4">
      <div class="output-dock-heading">
        <div>
          <span class="panel-eyebrow">OUTPUT DOCK</span>
          <strong>产物坞</strong>
        </div>
        <p>Agent 产物到达后会在这里高亮，可直接点击预览</p>
      </div>
      <div class="output-dock-list output-dock-list-v4">
        <article
          v-for="agentId in visibleOutputAgentIds"
          :key="agentId"
          class="output-dock-item output-dock-item-v4"
          :class="{ ready: hasGeneratedResource(agentId), 'just-arrived': latestArtifactAgentId === agentId }"
          @click="emit('openResource', agentId)"
        >
          <span>{{ getDagNodeIcon(agentId) }}</span>
          <div>
            <strong>{{ getResourceTypeLabel(agentId) }}</strong>
            <p>{{ hasGeneratedResource(agentId) ? '已生成，可预览' : getAgentOutputFormat(agentId) }}</p>
          </div>
          <em>{{ hasGeneratedResource(agentId) ? '刚刚完成' : getNodeStatusLabel(getStageNode(agentId)) }}</em>
        </article>
      </div>
    </section>

    <el-drawer v-model="workflowLogDrawerVisible" title="实时调度日志" direction="rtl" size="420px" class="workflow-log-drawer">
      <div class="drawer-log-list">
        <div v-for="item in workflowLogItems" :key="item.id" class="drawer-log-item" :class="`is-${item.status}`">
          <span class="drawer-log-dot"></span>
          <div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.message }}</p>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onBeforeUnmount, onMounted, watch } from 'vue'
import { ArrowRight } from '@element-plus/icons-vue'
import type { ResourceAgentId } from '@/features/resource/model/resource'
import {
  COORDINATOR_AGENT_ID,
  PPT_AGENT_ID,
  VIDEO_AGENT_ID,
  BUNDLE_AGENT_ID,
  SYSTEM_AGENT_IDS,
  AGENT_DISPLAY,
  getResourceTypeLabel,
  getAgentOutputFormat,
  getDagNodeIcon,
  getNodeFallbackMessage,
  type DagNodeState,
} from '@/features/resource/model/ResourceGeneratorConstants'

type GeneratedResourceItem = Record<string, any> & {
  generatedAt?: string
  displayOrder?: number
}

type AgentLinkGeometry = {
  id: string
  x: number
  y: number
  d: string
}

const props = defineProps<{
  naturalInput: string
  dagNodeStates: Record<string, DagNodeState>
  selectedDagNodeId: string | null
  overallProgress: number
  latestWorkflowMessage: string
  generatedResources: GeneratedResourceItem[]
  dagSelectedAgentIds: ResourceAgentId[]
  generationError: string | null
  planReady: boolean
  latestArtifactAgentId: string | null
  visibleWorkflowNodes: DagNodeState[]
}>()

const emit = defineEmits<{
  selectNode: [id: string]
  openResource: [type: string]
}>()

const workflowLogDrawerVisible = ref(false)
const detailPanelVisible = ref(false)

const flowCanvasRef = ref<HTMLElement | null>(null)
const coordinatorNodeRef = ref<HTMLElement | null>(null)
const stationCardRefs = new Map<string, HTMLElement>()
const linkCanvasSize = ref({ width: 1000, height: 700 })
const measuredAgentLinks = ref<AgentLinkGeometry[]>([])
let linkMeasureFrame = 0
let canvasResizeObserver: ResizeObserver | null = null

function handleAgentClick(id: string) {
  detailPanelVisible.value = true
  emit('selectNode', id)
}

function closeAgentDetail() {
  detailPanelVisible.value = false
}

const baseGenerationAgentIds = computed(() => {
  return props.dagSelectedAgentIds.filter(id => id !== PPT_AGENT_ID && id !== VIDEO_AGENT_ID)
})

const parallelPoolNodes = computed(() => {
  const agentStatusRank: Record<DagNodeState['status'], number> = {
    failed: 0, running: 1, success: 2, waiting: 3, skipped: 4,
  }
  return baseGenerationAgentIds.value
    .map(agentId => getStageNode(agentId))
    .sort((a, b) => {
      const rankDiff = agentStatusRank[a.status] - agentStatusRank[b.status]
      if (rankDiff !== 0) return rankDiff
      return b.progress - a.progress
    })
})

const agentLinkPaths = computed(() => {
  const nodes = parallelPoolNodes.value
  const measuredMap = new Map(measuredAgentLinks.value.map(link => [link.id, link]))

  return nodes.flatMap((node) => {
    const measured = measuredMap.get(node.id)
    return measured ? [{ ...measured, status: node.status }] : []
  })
})


function setStationCardRef(id: string, el: unknown) {
  if (el instanceof HTMLElement) {
    stationCardRefs.set(id, el)
  } else {
    stationCardRefs.delete(id)
  }
  scheduleLinkMeasure()
}

function scheduleLinkMeasure() {
  if (typeof window === 'undefined') return
  if (linkMeasureFrame) window.cancelAnimationFrame(linkMeasureFrame)
  linkMeasureFrame = window.requestAnimationFrame(() => {
    linkMeasureFrame = 0
    measureAgentLinks()
  })
}

function measureAgentLinks() {
  const canvas = flowCanvasRef.value
  const coordinator = coordinatorNodeRef.value
  if (!canvas || !coordinator) return

  const canvasRect = canvas.getBoundingClientRect()
  const width = Math.max(1, Math.round(canvasRect.width))
  const height = Math.max(1, Math.round(canvasRect.height))
  if (linkCanvasSize.value.width !== width || linkCanvasSize.value.height !== height) {
    linkCanvasSize.value = { width, height }
  }

  const coordinatorRect = coordinator.getBoundingClientRect()
  const startX = Math.round(coordinatorRect.left - canvasRect.left + coordinatorRect.width / 2)
  const startY = Math.round(coordinatorRect.bottom - canvasRect.top + 8)

  const links = parallelPoolNodes.value
    .map((node) => {
      const station = stationCardRefs.get(node.id)
      if (!station) return null

      const stationRect = station.getBoundingClientRect()
      const endX = Math.round(stationRect.left - canvasRect.left + stationRect.width / 2)
      const endY = Math.round(stationRect.top - canvasRect.top - 8)
      const distanceY = Math.max(42, endY - startY)
      const distanceX = endX - startX
      const sidePull = Math.min(120, Math.max(28, Math.abs(distanceX) * 0.18))
      const c1X = Math.round(startX + (distanceX > 0 ? sidePull : -sidePull))
      const c2X = Math.round(endX - (distanceX > 0 ? sidePull : -sidePull))
      const c1Y = Math.round(startY + distanceY * 0.36)
      const c2Y = Math.round(endY - distanceY * 0.28)

      return {
        id: node.id,
        x: endX,
        y: endY,
        d: `M ${startX} ${startY} C ${c1X} ${c1Y}, ${c2X} ${c2Y}, ${endX} ${endY}`,
      }
    })
    .filter((link): link is AgentLinkGeometry => Boolean(link))

  if (!isSameLinkGeometry(measuredAgentLinks.value, links)) {
    measuredAgentLinks.value = links
  }
}

function isSameLinkGeometry(prev: AgentLinkGeometry[], next: AgentLinkGeometry[]) {
  if (prev.length !== next.length) return false
  return prev.every((item, index) => {
    const target = next[index]
    if (!target) return false
    return item.id === target.id && item.x === target.x && item.y === target.y && item.d === target.d
  })
}

onMounted(async () => {
  await nextTick()
  scheduleLinkMeasure()
  window.addEventListener('resize', scheduleLinkMeasure)

  if (typeof ResizeObserver !== 'undefined' && flowCanvasRef.value) {
    canvasResizeObserver = new ResizeObserver(scheduleLinkMeasure)
    canvasResizeObserver.observe(flowCanvasRef.value)
  }
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', scheduleLinkMeasure)
    if (linkMeasureFrame) window.cancelAnimationFrame(linkMeasureFrame)
  }
  canvasResizeObserver?.disconnect()
})

watch(
  () => [
    parallelPoolNodes.value.map(node => `${node.id}:${node.status}:${node.progress}`).join('|'),
    props.planReady,
    props.generatedResources.length,
  ],
  async () => {
    await nextTick()
    scheduleLinkMeasure()
  },
  { immediate: true },
)

const trailingStageNodes = computed(() => {
  const nodes: DagNodeState[] = []
  if (props.dagSelectedAgentIds.includes(PPT_AGENT_ID as ResourceAgentId)) {
    nodes.push(getStageNode(PPT_AGENT_ID))
  }
  if (props.dagSelectedAgentIds.includes(VIDEO_AGENT_ID as ResourceAgentId)) {
    nodes.push(getStageNode(VIDEO_AGENT_ID))
  }
  nodes.push(getStageNode(BUNDLE_AGENT_ID))
  return nodes
})

const selectedDagNode = computed(() => {
  if (!props.selectedDagNodeId) return null
  if (props.selectedDagNodeId === COORDINATOR_AGENT_ID) return getStageNode(COORDINATOR_AGENT_ID)
  return props.dagNodeStates[props.selectedDagNodeId] || getStageNode(props.selectedDagNodeId)
})

const runningAgentCount = computed(() => {
  return props.visibleWorkflowNodes.filter(node => node.status === 'running').length
})

const dagHeroMessage = computed(() => {
  const running = Object.values(props.dagNodeStates).find(n => n.status === 'running')
  if (running) return running.currentMessage || `${running.label}处理中...`
  const allDone = Object.values(props.dagNodeStates).every(n => n.status === 'success')
  if (allDone) return '所有资源生成完成'
  return props.latestWorkflowMessage || '多智能体协同生成中'
})

const visibleOutputAgentIds = computed(() => {
  return props.dagSelectedAgentIds
})

const workflowLogItems = computed(() => {
  const items: Array<{ id: string; title: string; message: string; status: DagNodeState['status'] }> = []
  props.visibleWorkflowNodes.forEach((node) => {
    const richLogs = node.eventLogs || []

    if (richLogs.length) {
      richLogs.slice(-4).forEach((log) => {
        items.push({
          id: log.id,
          title: `${node.label} · ${getLogPhaseLabel(log.phase)}`,
          message: log.message,
          status: log.status || node.status,
        })
      })
      return
    }

    if (node.stepHistory?.length) {
      node.stepHistory.slice(-3).forEach((step, index) => {
        items.push({
          id: `${node.id}-${index}-${step}`,
          title: node.label,
          message: step,
          status: node.status,
        })
      })
    }
  })
  return items
})

type AgentLiveLog = {
  id: string
  eventType?: string
  phase?: string
  message: string
  status?: DagNodeState['status']
  progress?: number
  elapsedMs?: number
  timestamp?: number
}

function getNodeLiveLogs(node: DagNodeState, limit = 4): AgentLiveLog[] {
  const richLogs = (node.eventLogs || []) as AgentLiveLog[]

  if (richLogs.length) {
    return richLogs
      .filter(log => Boolean(log.message?.trim()))
      .slice(-limit)
      .reverse()
  }

  return (node.stepHistory || [])
    .filter(Boolean)
    .slice(-limit)
    .reverse()
    .map((message, index) => ({
      id: `${node.id}-history-${index}-${message}`,
      message,
      phase: node.phase,
      status: node.status,
      elapsedMs: node.elapsedMs,
      timestamp: node.lastUpdatedAt,
    }))
}

function getLogPhaseLabel(phase?: string) {
  const phaseMap: Record<string, string> = {
    planning_blueprint: '规划',
    llm_generating: '生成',
    validating: '校验',
    ppt_generating: 'PPT',
    ppt_waiting_sources: '等待',
    artifact_saved: '保存',
    bundling: '打包',
    finished: '完成',
    failed: '失败',
  }

  return phase ? phaseMap[phase] || phase : '状态'
}

function getStageNode(id: string): DagNodeState {
  return props.dagNodeStates[id] || {
    id,
    label: AGENT_DISPLAY[id]?.label || id,
    icon: AGENT_DISPLAY[id]?.icon || '✨',
    status: 'waiting',
    progress: 0,
    currentMessage: '',
    stepHistory: [],
    eventLogs: [],
    isSystem: SYSTEM_AGENT_IDS.includes(id),
  }
}

function hasGeneratedResource(type: string) {
  return props.generatedResources.some(resource => resource.type === type)
}

function getNodeStatusLabel(node: DagNodeState) {
  if (node.status === 'failed') return '失败'
  if (node.status === 'skipped') return '跳过'
  if (node.status === 'success') return '完成'
  if (node.status === 'running') return '运行中'
  return '等待'
}

function getNodeStageLabel(node: DagNodeState) {
  if (node.status === 'success') return '已就绪'
  if (node.status === 'failed') return '执行失败'
  if (node.status === 'skipped') return '已跳过'
  if (node.status === 'running') {
    if (node.phase === 'llm_generating') return '模型生成中'
    if (node.phase === 'validating') return '解析校验中'
    if (node.phase === 'artifact_saved') return '产物已保存'
    if (node.phase === 'bundling') return '资源打包中'
    return '执行中'
  }
  return '等待依赖'
}

function getNodePhaseLabel(node: DagNodeState) {
  const phaseMap: Record<string, string> = {
    planning_blueprint: '规划蓝图',
    llm_generating: '模型调用',
    validating: '解析校验',
    ppt_waiting_sources: '等待事实来源',
    artifact_saved: '产物保存',
    bundling: '资源组装',
    finished: '完成',
    failed: '失败',
  }
  if (node.phase && phaseMap[node.phase]) return phaseMap[node.phase]
  if (node.status === 'waiting') return '等待上游'
  if (node.status === 'success') return '完成'
  if (node.status === 'failed') return '失败'
  return '执行阶段'
}

function getNodeDisplayMessage(node: DagNodeState) {
  if (node.status === 'failed') return node.currentMessage || '执行失败，请检查该智能体输出'
  if (node.currentMessage) return node.currentMessage
  if (node.id === PPT_AGENT_ID) return '等待基础资源完成后生成演示文稿'
  if (node.id === VIDEO_AGENT_ID) return '等待基础资源完成后生成讲解视频'
  if (node.id === BUNDLE_AGENT_ID) return '等待资源完成后组装资源包'
  return getNodeFallbackMessage(node)
}

function formatElapsed(ms?: number | null) {
  if (!ms || ms < 0) return '未开始'
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${minutes}m ${rest}s`
}

function getNodeTimeLabel(node: DagNodeState) {
  if (node.status === 'waiting') return '等待上游'
  if (!node.lastUpdatedAt) return formatElapsed(node.elapsedMs)
  const seconds = Math.max(0, Math.floor((Date.now() - node.lastUpdatedAt) / 1000))
  if (seconds < 3) return '刚刚更新'
  if (seconds < 60) return `${seconds}s 前更新`
  return `${Math.floor(seconds / 60)}m 前更新`
}

function getMetricChips(node: DagNodeState) {
  const metrics = node.metrics || {}
  return Object.entries(metrics)
    .filter(([, value]) => value !== null && value !== undefined && value !== '')
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${String(value)}`)
}

</script>

<style scoped>
.generating-view {
  background: transparent;
  overflow-y: auto;
}

.workflow-stage-page {
  background: transparent;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 18px 16px;
  gap: 12px;
}

.workflow-stage-page-v4 {
  min-height: auto;
  padding: 18px clamp(18px, 2vw, 30px) 24px;
  background:
    radial-gradient(circle at 20% 12%, rgba(59, 130, 246, 0.12), transparent 32%),
    radial-gradient(circle at 82% 46%, rgba(45, 212, 191, 0.12), transparent 30%),
    linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(241, 245, 249, 0.86));
}

.stage-topbar {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 22px;
  padding: 14px 18px;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.055);
}

.stage-topbar-v4 {
  margin-bottom: 14px;
}

.stage-title-area {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.stage-title-area h2 {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--weight-extrabold);
  color: var(--color-text);
}

.stage-title-area p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.stage-route-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.route-step {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 var(--space-2);
  border-radius: 999px;
  background: var(--color-surface-hover);
  color: var(--color-text-faint);
  font-size: var(--text-2xs);
  font-weight: var(--weight-extrabold);
}

.route-step.done {
  background: var(--color-success-soft);
  color: var(--color-success);
}

.route-step.active {
  background: var(--cat-resource-soft);
  color: var(--cat-resource);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.16);
}

.route-line {
  width: 28px;
  height: 2px;
  border-radius: 99px;
  background: var(--color-border-hover);
}

.route-line.done {
  background: var(--color-primary);
}

.route-line.active {
  background: linear-gradient(90deg, var(--color-primary), var(--cat-resource));
}

.stage-stat-group {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.stage-stat-group-v4 .progress-stat-card {
  min-width: 148px;
}

.stage-stat-card {
  min-width: 92px;
  padding: 10px 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.8);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stage-stat-card.wide {
  min-width: 110px;
}

.stage-stat-card span {
  color: var(--color-text-muted);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
}

.stage-stat-card strong {
  color: var(--color-text);
  font-size: var(--text-xl);
  line-height: 1;
  font-weight: var(--weight-extrabold);
}

.stage-stat-card small {
  color: var(--color-text-faint);
  font-size: var(--text-xs);
  margin-left: 2px;
}

.stage-log-btn {
  height: 42px;
  border-color: rgba(16,185,129,0.3) !important;
  color: var(--color-info, #2563eb) !important;
  font-weight: 800;
  background: var(--color-surface, #fff) !important;
}

.mini-progress-track {
  width: 100%;
  height: 5px;
  background: rgba(148, 163, 184, 0.2);
  border-radius: 999px;
  overflow: hidden;
  margin-top: 6px;
}

.mini-progress-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #22C55E, #06B6D4, #3B82F6);
  box-shadow: 0 0 18px rgba(59, 130, 246, 0.42);
  transition: width 0.35s ease;
}

.stage-generation-error {
  position: relative;
  z-index: 2;
  border-radius: 16px;
}

.agent-stage-shell-v4 {
  position: relative;
  z-index: 1;
  width: 100%;
  min-height: auto;
  display: block;
}

.dispatch-workbench-panel,
.agent-detail-floating-panel,
.output-dock-section-v4 {
  position: relative;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px solid rgba(255, 255, 255, 0.86);
  box-shadow: 0 22px 60px rgba(15, 23, 42, 0.07);
  backdrop-filter: blur(22px);
  overflow: hidden;
}

.dispatch-workbench-panel-v4 {
  width: 100%;
  padding: clamp(16px, 1.4vw, 24px);
  min-width: 0;
}

.panel-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--cat-resource);
  font-size: var(--text-2xs);
  font-weight: var(--weight-extrabold);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.control-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 900;
  background: rgba(241, 245, 249, 0.78);
  color: #64748B;
  border: 1px solid rgba(226, 232, 240, 0.86);
}

.control-pill.active {
  background: rgba(224, 231, 255, 0.84);
  color: #4338ca;
  border-color: rgba(165, 180, 252, 0.78);
}

.control-pill.muted {
  background: rgba(248, 250, 252, 0.9);
  color: #64748B;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #6366F1;
  box-shadow: 0 0 0 5px rgba(99, 102, 241, 0.14);
}

.workbench-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.workbench-header h3 {
  margin: 6px 0 0;
  color: var(--color-text);
  font-size: var(--text-xl);
  font-weight: var(--weight-bold);
}

.workbench-header p {
  margin: 6px 0 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.workbench-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.workbench-actions .el-button {
  background: rgba(255, 255, 255, 0.72) !important;
  border-color: rgba(191, 219, 254, 0.86) !important;
  color: #2563EB !important;
  font-weight: 800;
}

.agent-flow-canvas {
  position: relative;
  border-radius: 28px;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 20%, rgba(59, 130, 246, 0.12), transparent 34%),
    radial-gradient(circle at 48% 74%, rgba(45, 212, 191, 0.12), transparent 38%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(248, 250, 252, 0.68));
  border: 1px solid rgba(226, 232, 240, 0.78);
}

.agent-flow-canvas-v4 {
  min-height: clamp(660px, 70vh, 840px);
  padding: clamp(20px, 2.2vw, 32px) clamp(18px, 2.4vw, 34px) clamp(24px, 2.4vw, 34px);
}


.agent-flow-canvas-v4::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 96px;
  width: 1px;
  height: 240px;
  transform: translateX(-50%);
  background: linear-gradient(180deg, rgba(59,130,246,0), rgba(59,130,246,0.28), rgba(45,212,191,0.18), rgba(59,130,246,0));
  pointer-events: none;
}
.flow-grid-bg {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: radial-gradient(circle at 50% 48%, #000, transparent 74%);
  pointer-events: none;
}

.flow-orbit {
  position: absolute;
  left: 6%;
  right: 6%;
  border-radius: 999px;
  pointer-events: none;
  border: 1px dashed rgba(59, 130, 246, 0.18);
  filter: drop-shadow(0 0 18px rgba(59, 130, 246, 0.18));
}

.orbit-one {
  top: 112px;
  height: 220px;
  transform: rotate(-4deg);
}

.orbit-two {
  top: 176px;
  height: 250px;
  transform: rotate(5deg);
  border-color: rgba(45, 212, 191, 0.2);
}

.orbit-three {
  top: 236px;
  height: 220px;
  transform: rotate(-2deg);
  border-color: rgba(139, 92, 246, 0.16);
}

.learning-demand-float,
.master-plan-float {
  position: absolute;
  z-index: 6;
  top: 22px;
  width: min(280px, 24vw);
  min-height: 72px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow: 0 16px 42px rgba(15, 23, 42, 0.075);
  padding: 14px 16px;
}

.learning-demand-float {
  left: 20px;
}

.master-plan-float {
  right: 20px;
}

.learning-demand-float span,
.master-plan-float strong {
  display: block;
  color: #2563EB;
  font-size: 0.72rem;
  font-weight: 900;
}

.learning-demand-float strong {
  display: block;
  margin-top: 6px;
  color: #0F172A;
  font-size: 0.88rem;
  line-height: 1.45;
}

.learning-demand-float p {
  margin: 6px 0 0;
  color: #64748B;
  font-size: 0.76rem;
  line-height: 1.45;
}

.master-plan-float > div:first-child {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.master-plan-track {
  margin-top: 12px;
  height: 5px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.16);
  overflow: hidden;
}

.master-plan-track b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #6366F1, #22D3EE, #3B82F6);
}

.flow-core-stack {
  position: relative;
  z-index: 4;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  margin-top: 80px;
}

.flow-core-stack-v4 {
  margin-top: 44px;
}

.core-agent-node {
  width: min(300px, 44vw);
  min-height: 78px;
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 14px 16px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(191, 219, 254, 0.82);
  box-shadow: 0 18px 48px rgba(37, 99, 235, 0.12);
  cursor: pointer;
  transition: all 0.24s ease;
}

.core-agent-node:hover,
.core-agent-node.is-selected {
  transform: translateY(-2px);
  border-color: rgba(37, 99, 235, 0.46);
  box-shadow: 0 20px 56px rgba(37, 99, 235, 0.18);
}

.core-icon {
  width: 46px;
  height: 46px;
  border-radius: 16px;
  background: rgba(219, 234, 254, 0.82);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.35rem;
}

.core-agent-node strong {
  display: block;
  color: var(--color-text);
  font-size: var(--text-base);
}

.core-agent-node span {
  color: var(--cat-resource);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
}

.core-progress {
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
  color: var(--color-text);
}

.core-link-line {
  width: 2px;
  height: 22px;
  background: linear-gradient(180deg, #60A5FA, #22D3EE);
  border-radius: 99px;
  position: relative;
}

.core-link-line i {
  position: absolute;
  left: 50%;
  bottom: -4px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #06B6D4;
  transform: translateX(-50%);
  box-shadow: 0 0 0 6px rgba(6, 182, 212, 0.12);
}

.agent-connection-field {
  position: absolute;
  left: 10%;
  right: 10%;
  top: 188px;
  height: 120px;
  pointer-events: none;
  z-index: 2;
}

.agent-connection-field .arc {
  position: absolute;
  top: 0;
  border-top: 2px solid rgba(59, 130, 246, 0.42);
  border-radius: 50% 50% 0 0;
  height: 88px;
  animation: flowPulse 1.4s ease-in-out infinite;
}

.arc-a { left: 0; right: 50%; transform: rotate(-8deg); }
.arc-b { left: 14%; right: 34%; transform: rotate(-3deg); border-color: rgba(45, 212, 191, 0.48) !important; }
.arc-c { left: 34%; right: 14%; transform: rotate(3deg); border-color: rgba(139, 92, 246, 0.42) !important; }
.arc-d { left: 50%; right: 0; transform: rotate(8deg); }

@keyframes flowPulse {
  0%, 100% {
    opacity: 0.46;
    filter: drop-shadow(0 0 0 rgba(59, 130, 246, 0));
  }
  50% {
    opacity: 1;
    filter: drop-shadow(0 0 12px rgba(59, 130, 246, 0.26));
  }
}

.agent-station-row {
  position: relative;
  z-index: 5;
  display: grid;
  gap: 14px;
}

.agent-station-row-v4 {
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  max-width: 1320px;
  margin: 108px auto 0;
  align-items: stretch;
}

.agent-station-card {
  border-radius: 24px;
  padding: 13px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(226, 232, 240, 0.92);
  cursor: pointer;
  transition: all 0.26s ease;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.055);
}

.agent-station-card-v4 {
  min-height: 210px;
  display: flex;
  flex-direction: column;
}

.agent-station-card:hover,
.agent-station-card.is-selected {
  transform: translateY(-5px);
  border-color: rgba(59, 130, 246, 0.52);
  box-shadow: 0 24px 54px rgba(37, 99, 235, 0.16);
}

.agent-station-card.status-running {
  border-color: rgba(59, 130, 246, 0.48);
  box-shadow: 0 20px 48px rgba(59, 130, 246, 0.13);
}

.agent-station-card.status-success,
.agent-station-card.has-artifact {
  border-color: rgba(16, 185, 129, 0.42);
  background: rgba(240, 253, 250, 0.72);
}

.agent-station-card.status-failed {
  border-color: rgba(239, 68, 68, 0.42);
  background: rgba(254, 242, 242, 0.82);
}

.station-header {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
}

.station-icon {
  width: 36px;
  height: 36px;
  border-radius: 13px;
  background: rgba(219, 234, 254, 0.82);
  display: flex;
  align-items: center;
  justify-content: center;
}

.station-header strong {
  display: block;
  color: var(--color-text);
  font-size: var(--text-sm);
}

.station-header span {
  color: var(--color-text-muted);
  font-size: var(--text-2xs);
  font-weight: var(--weight-extrabold);
}

.station-header em {
  font-size: var(--text-2xs);
  font-style: normal;
  color: var(--cat-resource);
  font-weight: var(--weight-extrabold);
  white-space: nowrap;
}

.station-live-log {
  min-height: 92px;
  margin: 16px 0 14px;
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.9));
  border: 1px solid rgba(226, 232, 240, 0.86);
  padding: 11px 12px;
  display: flex;
  flex-direction: column;
  gap: 9px;
  overflow: hidden;
  flex: 1;
}

.station-live-log.is-running {
  border-color: rgba(59, 130, 246, 0.34);
  background:
    radial-gradient(circle at 12% 0%, rgba(59, 130, 246, 0.08), transparent 42%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(239, 246, 255, 0.82));
}

.station-live-log.is-success {
  border-color: rgba(16, 185, 129, 0.34);
  background:
    radial-gradient(circle at 12% 0%, rgba(16, 185, 129, 0.08), transparent 42%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(240, 253, 250, 0.84));
}

.station-live-log.is-failed {
  border-color: rgba(239, 68, 68, 0.28);
  background:
    radial-gradient(circle at 12% 0%, rgba(239, 68, 68, 0.08), transparent 42%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(254, 242, 242, 0.86));
}

.station-live-current {
  display: grid;
  grid-template-columns: 9px minmax(0, 1fr);
  gap: 9px;
  align-items: flex-start;
  min-width: 0;
}

.station-live-dot {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 999px;
  background: #3B82F6;
  box-shadow: 0 0 0 5px rgba(59, 130, 246, 0.12);
  flex-shrink: 0;
}

.station-live-dot.muted {
  background: #CBD5E1;
  box-shadow: 0 0 0 5px rgba(148, 163, 184, 0.12);
}

.station-live-current strong {
  display: block;
  color: var(--cat-resource);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  line-height: 1.2;
}

.station-live-current p {
  margin: 3px 0 0;
  color: var(--color-text);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
  line-height: 1.36;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.station-live-lines {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.station-live-line {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 7px;
  align-items: center;
  margin: 0;
  min-width: 0;
}

.station-live-line span {
  padding: 2px var(--space-2);
  border-radius: 999px;
  background: var(--cat-resource-soft);
  color: var(--cat-resource);
  font-size: var(--text-2xs);
  font-weight: var(--weight-extrabold);
  white-space: nowrap;
}

.station-live-line em {
  min-width: 0;
  color: var(--color-text-muted);
  font-size: var(--text-2xs);
  font-style: normal;
  font-weight: var(--weight-bold);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.station-live-line.is-success span {
  background: var(--color-success-soft);
  color: var(--color-success);
}

.station-live-line.is-failed span {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.station-live-empty {
  height: 100%;
  min-height: 68px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  color: var(--color-text-faint);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
}

.station-live-empty p {
  margin: 0;
  color: var(--color-text-faint);
}

.detail-live-log-item {
  margin-top: 9px;
  padding: 9px 10px;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.86);
}

.detail-live-log-item > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.detail-live-log-item span {
  color: var(--cat-resource);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
}

.detail-live-log-item em {
  color: var(--color-text-faint);
  font-size: var(--text-2xs);
  font-style: normal;
  font-weight: var(--weight-extrabold);
}

.detail-live-log-item p {
  margin: 6px 0 0;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: 1.45;
}

.detail-live-log-item.is-success {
  border-color: rgba(16, 185, 129, 0.28);
  background: rgba(240, 253, 250, 0.82);
}

.detail-live-log-item.is-failed {
  border-color: rgba(239, 68, 68, 0.26);
  background: rgba(254, 242, 242, 0.82);
}

.station-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  color: var(--color-success);
  font-size: var(--text-2xs);
  font-weight: var(--weight-extrabold);
}

.station-footer i {
  width: min(64px, 28%);
  max-width: 64px;
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, #22C55E, #3B82F6);
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.25);
  transition: width 0.32s ease;
}

.agent-station-enter-active,
.agent-station-leave-active {
  transition: all 0.3s ease;
}

.agent-station-enter-from,
.agent-station-leave-to {
  opacity: 0;
  transform: translateY(18px) scale(0.96);
}

.review-station-row {
  position: relative;
  z-index: 5;
  display: grid;
  gap: 14px;
}

.review-station-row-v4 {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  width: min(1100px, 92%);
  margin: 28px auto 0;
}

.review-station-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 16px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(226, 232, 240, 0.88);
  cursor: pointer;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.055);
  transition: all 0.24s ease;
}

.review-station-card-v4 {
  min-height: 92px;
}

.review-station-card:hover,
.review-station-card.is-selected {
  transform: translateY(-3px);
  border-color: rgba(59, 130, 246, 0.48);
  box-shadow: 0 18px 42px rgba(37, 99, 235, 0.14);
}

.review-icon {
  width: 42px;
  height: 42px;
  border-radius: 15px;
  background: rgba(219, 234, 254, 0.82);
  display: flex;
  align-items: center;
  justify-content: center;
}

.review-station-card strong {
  color: var(--color-text);
  font-size: var(--text-sm);
  display: block;
}

.review-station-card span {
  color: var(--color-text-muted);
  font-size: var(--text-2xs);
  font-weight: var(--weight-extrabold);
}

.review-station-card em {
  font-style: normal;
  color: var(--cat-resource);
  font-weight: var(--weight-extrabold);
  font-size: var(--text-xs);
}

.agent-detail-floating-panel {
  position: fixed;
  top: calc(var(--navbar-height, 64px) + 82px);
  right: clamp(18px, 2.4vw, 34px);
  z-index: 80;
  width: min(420px, calc(100vw - 36px));
  max-height: calc(100vh - var(--navbar-height, 64px) - 112px);
  overflow-y: auto;
  padding: 18px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(191, 219, 254, 0.9);
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.18);
}

.detail-close-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 12px;
  background: rgba(241, 245, 249, 0.95);
  color: #475569;
  font-size: 1.35rem;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s ease;
}

.detail-close-btn:hover {
  background: #DBEAFE;
  color: #2563EB;
}

.detail-panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  padding-right: 36px;
}

.detail-panel-title h3 {
  margin: 6px 0 0;
  color: var(--color-text);
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
}

.selected-agent-detail-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.detail-agent-head {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) 12px;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border-radius: 20px;
  background: rgba(248, 250, 252, 0.76);
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.detail-agent-head h4 {
  margin: 0;
  color: var(--color-text);
  font-size: var(--text-lg);
}

.detail-agent-head p {
  margin: 4px 0 0;
  color: var(--color-success);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
}

.detail-status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #94A3B8;
}

.detail-status-dot.status-running {
  background: #3B82F6;
  box-shadow: 0 0 0 6px rgba(59, 130, 246, 0.14);
}

.detail-status-dot.status-success {
  background: #6366F1;
}

.detail-status-dot.status-failed {
  background: #EF4444;
}

.focus-agent-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: var(--cat-resource-soft, #dbeafe);
  border: 1px solid rgba(99,102,241,0.3);
  font-size: 1.25rem;
}

.detail-current-task {
  padding: 14px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.detail-current-task span {
  display: block;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
  margin-bottom: 7px;
}

.detail-current-task strong {
  display: block;
  color: var(--color-text);
  font-size: var(--text-sm);
  line-height: 1.5;
}

.detail-progress-line {
  height: 7px;
  margin-top: 12px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.18);
  overflow: hidden;
}

.detail-progress-line i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #3B82F6, #22D3EE);
  transition: width 0.3s ease;
}

.detail-current-task em {
  display: block;
  text-align: right;
  margin-top: 5px;
  font-style: normal;
  color: var(--cat-resource);
  font-size: var(--text-2xs);
  font-weight: var(--weight-extrabold);
}

.focus-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.focus-metrics div {
  padding: 9px 10px;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.84);
  border: 1px solid var(--color-border, #e2e8f0);
}

.focus-metrics dt {
  color: var(--color-text-muted);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
}

.focus-metrics dd {
  margin: 4px 0 0;
  color: var(--color-text);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
}

.detail-metrics-v3 {
  grid-template-columns: 1fr 1fr;
}

.detail-io-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.detail-io-grid div {
  padding: 12px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.72);
  border: 1px solid rgba(226, 232, 240, 0.86);
}

.detail-io-grid span {
  display: block;
  color: var(--cat-resource);
  font-size: var(--text-2xs);
  font-weight: var(--weight-extrabold);
}

.detail-io-grid p {
  margin: 5px 0 0;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: 1.45;
}

.focus-metric-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 2px;
}

.focus-metric-chips span {
  padding: 5px var(--space-2);
  border-radius: 999px;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  font-size: var(--text-2xs);
  font-weight: var(--weight-extrabold);
}

.focus-history {
  margin-top: 4px;
}

.detail-history-v3 {
  max-height: 160px;
  overflow-y: auto;
}

.focus-history p {
  margin: var(--space-2) 0 0;
  padding-left: var(--space-2);
  border-left: 2px solid var(--color-success-border);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  line-height: 1.45;
}

.detail-float-enter-active,
.detail-float-leave-active {
  transition: opacity 0.24s ease, transform 0.28s cubic-bezier(0.16, 1, 0.3, 1);
}

.detail-float-enter-from,
.detail-float-leave-to {
  opacity: 0;
  transform: translateX(24px) scale(0.98);
}

.output-dock-section {
  position: relative;
  z-index: 4;
  flex-shrink: 0;
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 16px;
  align-items: center;
  min-height: 56px;
  padding: 8px 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.output-dock-section-v4 {
  margin-top: 14px;
  padding: 14px 16px 16px;
}

.output-dock-heading {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.output-dock-heading > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.output-dock-heading strong {
  color: var(--color-text);
  font-size: var(--text-base);
  font-weight: var(--weight-extrabold);
  line-height: 1.2;
}

.output-dock-heading p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  line-height: 1.5;
}

.output-dock-list {
  display: grid;
  min-width: 0;
}

.output-dock-list-v4 {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.output-dock-item {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 16px;
  background: var(--color-bg, #fff);
  opacity: 0.72;
  transition: opacity 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
  cursor: default;
}

.output-dock-item-v4 {
  min-height: 82px;
  position: relative;
  padding-right: 90px;
}

.output-dock-item.ready {
  opacity: 1;
  background: #F0FDF4;
  border-color: #A7F3D0;
  cursor: pointer;
}

.output-dock-item.ready:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 28px rgba(16, 185, 129, 0.10);
}

.output-dock-item > span {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: var(--color-surface, #f8fafc);
  display: grid;
  place-items: center;
  flex-shrink: 0;
  font-size: 0.95rem;
}

.output-dock-item strong {
  display: block;
  color: var(--color-text);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.output-dock-item p {
  margin: 2px 0 0;
  color: var(--color-text-muted);
  font-size: var(--text-2xs);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.output-dock-item-v4 em {
  position: absolute;
  right: var(--space-3);
  top: var(--space-3);
  font-style: normal;
  font-size: var(--text-2xs);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-muted);
  background: var(--color-surface-hover);
  border-radius: 999px;
  padding: 3px var(--space-2);
}

.output-dock-item-v4.ready em {
  color: var(--color-success);
  background: var(--color-success-soft);
}

.output-dock-item-v4.just-arrived {
  animation: artifactArrive 1.35s ease both;
}

@keyframes artifactArrive {
  0% {
    transform: translateY(-14px) scale(0.96);
    box-shadow: 0 0 0 rgba(16, 185, 129, 0);
  }
  45% {
    transform: translateY(0) scale(1.04);
    box-shadow: 0 22px 48px rgba(16, 185, 129, 0.22);
  }
  100% {
    transform: translateY(0) scale(1);
  }
}

.workflow-log-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 20px 22px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  font-weight: 900;
  color: var(--color-text, #0f172a);
}

.drawer-log-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 4px;
}

.drawer-log-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 12px;
  border-radius: 16px;
  background: var(--color-bg, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
}

.drawer-log-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--color-border-hover, #cbd5e1);
  margin-top: 5px;
  flex-shrink: 0;
}

.drawer-log-item.is-running .drawer-log-dot {
  background: #F97316;
  box-shadow: 0 0 0 5px rgba(249, 115, 22, 0.12);
}

.drawer-log-item.is-success .drawer-log-dot {
  background: var(--color-success, #22c55e);
}

.drawer-log-item.is-failed .drawer-log-dot {
  background: var(--color-danger, #ef4444);
}

.drawer-log-item strong {
  color: var(--color-text);
  font-size: var(--text-sm);
  font-weight: var(--weight-extrabold);
}

.drawer-log-item p {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  line-height: 1.45;
}

@media (max-width: 1280px) {
  .learning-demand-float,
  .master-plan-float {
    position: relative;
    top: auto;
    left: auto;
    right: auto;
    width: 100%;
    margin-bottom: 14px;
  }

  .master-plan-float {
    margin-top: 0;
  }

  .flow-core-stack-v4 {
    margin-top: 24px;
  }

  .agent-connection-field {
    top: 280px;
  }

  .agent-station-row-v4 {
    grid-template-columns: repeat(3, minmax(190px, 1fr));
    margin-top: 150px;
  }

  .review-station-row-v4 {
    width: 100%;
    grid-template-columns: repeat(2, minmax(200px, 1fr));
  }
}

@media (max-width: 1024px) {
  .stage-topbar-v4,
  .stage-stat-group-v4,
  .workbench-header-v4 {
    flex-direction: column;
    align-items: stretch;
  }

  .stage-stat-group-v4 {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .agent-flow-canvas-v4 {
    min-height: auto;
    padding: 20px;
  }

  .core-agent-node {
    width: min(300px, 100%);
  }

  .agent-connection-field {
    display: none;
  }

  .agent-station-row-v4 {
    grid-template-columns: repeat(2, minmax(180px, 1fr));
    margin-top: 42px;
  }

  .review-station-row-v4 {
    grid-template-columns: 1fr 1fr;
    margin-top: 24px;
  }

  .output-dock-section {
    grid-template-columns: 1fr;
  }

  .agent-detail-floating-panel {
    top: calc(var(--navbar-height, 64px) + 70px);
  }
}

@media (max-width: 760px) {
  .workflow-stage-page-v4 {
    padding: 12px;
  }

  .stage-stat-group-v4,
  .agent-station-row-v4,
  .review-station-row-v4,
  .output-dock-list-v4 {
    grid-template-columns: 1fr;
  }

  .dispatch-workbench-panel-v4,
  .agent-flow-canvas-v4 {
    border-radius: 20px;
  }

  .agent-detail-floating-panel {
    right: 12px;
    left: 12px;
    width: auto;
  }
}


/* =========================
   v5 overflow-safe layout patch
   目标：所有内容只能在组件容器内部自适应，不能把页面撑出右侧。
   这段放在最后，用于覆盖前面的舞台布局规则。
   ========================= */
.workflow-stage-page-v4,
.workflow-stage-page-v4 * {
  box-sizing: border-box;
}

.workflow-stage-page-v4 {
  width: 100%;
  max-width: 100%;
  overflow-x: hidden;
  padding-inline: clamp(12px, 1.6vw, 24px);
}

.stage-topbar-v4,
.agent-stage-shell-v4,
.dispatch-workbench-panel-v4,
.agent-flow-canvas-v4,
.output-dock-section-v4 {
  width: 100%;
  max-width: 100%;
  min-width: 0;
}

.stage-topbar-v4 {
  flex-wrap: wrap;
}

.stage-title-area {
  flex: 1 1 420px;
  min-width: 0;
}

.stage-stat-group-v4 {
  flex: 1 1 420px;
  min-width: 0;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.stage-stat-group-v4 .stage-stat-card {
  flex: 1 1 118px;
  min-width: 0;
  max-width: 178px;
}

.stage-stat-group-v4 .progress-stat-card {
  max-width: 220px;
}

.stage-log-btn {
  flex: 0 0 auto;
}

.workbench-header-v4 {
  flex-wrap: wrap;
}

.workbench-header-v4 > div:first-child {
  flex: 1 1 420px;
  min-width: 0;
}

.workbench-actions {
  flex: 1 1 360px;
  min-width: 0;
  max-width: 100%;
}

.workbench-actions .control-pill,
.workbench-actions .el-button {
  max-width: 100%;
}

.agent-flow-canvas-v4 {
  min-height: auto;
  display: flex;
  flex-direction: column;
  gap: clamp(18px, 2.2vw, 34px);
  padding: clamp(18px, 2.4vw, 36px);
  overflow: hidden;
}

.learning-demand-float,
.master-plan-float {
  position: relative;
  top: auto;
  left: auto;
  right: auto;
  width: min(560px, 100%);
  max-width: 100%;
  min-height: auto;
}

.learning-demand-float {
  align-self: flex-start;
}

.master-plan-float {
  align-self: flex-end;
}

.flow-core-stack-v4 {
  margin-top: 0;
}

.core-agent-node {
  width: min(340px, 100%);
  max-width: 100%;
}

.agent-connection-field {
  top: clamp(360px, 40vw, 430px);
  left: clamp(18px, 4vw, 72px);
  right: clamp(18px, 4vw, 72px);
  max-width: calc(100% - 36px);
}

.agent-station-row-v4 {
  width: 100%;
  max-width: 100%;
  grid-template-columns: repeat(auto-fit, minmax(min(210px, 100%), 1fr));
  margin-top: clamp(72px, 10vw, 140px);
}

.review-station-row-v4 {
  width: 100%;
  max-width: 100%;
  grid-template-columns: repeat(auto-fit, minmax(min(230px, 100%), 1fr));
}

.output-dock-section {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  grid-template-columns: minmax(180px, 220px) minmax(0, 1fr);
}

.output-dock-list-v4 {
  width: 100%;
  max-width: 100%;
  grid-template-columns: repeat(auto-fit, minmax(min(220px, 100%), 1fr));
}

.output-dock-item-v4 {
  min-width: 0;
  padding-right: 86px;
}

.agent-detail-floating-panel {
  right: max(12px, env(safe-area-inset-right));
  width: min(420px, calc(100vw - 24px));
  max-width: calc(100vw - 24px);
}

@media (max-width: 1120px) {
  .agent-connection-field {
    display: none;
  }

  .agent-station-row-v4 {
    margin-top: 16px;
  }
}

@media (max-width: 720px) {
  .stage-stat-group-v4,
  .output-dock-section {
    grid-template-columns: 1fr;
  }

  .stage-stat-group-v4 {
    display: grid;
  }

  .stage-stat-group-v4 .stage-stat-card,
  .stage-stat-group-v4 .progress-stat-card {
    max-width: none;
  }

  .workbench-actions {
    justify-content: flex-start;
  }

  .master-plan-float,
  .learning-demand-float {
    align-self: stretch;
    width: 100%;
  }

}


/* ===== 更紧凑的中枢调度布局：用 SVG 精准连接 Coordinator 与子 Agent 卡片 ===== */
.agent-flow-canvas-v4 {
  min-height: clamp(620px, 68vh, 800px);
  padding: clamp(18px, 2vw, 28px) clamp(20px, 2.4vw, 36px) clamp(24px, 2.4vw, 36px);
}

.learning-demand-float,
.master-plan-float {
  top: 20px;
  width: min(300px, 25vw);
}

.learning-demand-float {
  left: 20px;
}

.master-plan-float {
  right: 20px;
}

.flow-core-stack-v4 {
  margin-top: 116px;
  gap: 8px;
}

.core-link-line {
  height: 18px;
}

.core-agent-node {
  width: min(300px, 34vw);
  min-height: 70px;
  padding: 12px 15px;
}

.agent-connection-field {
  display: none;
}

.agent-link-svg {
  position: absolute;
  left: clamp(42px, 4vw, 72px);
  right: clamp(42px, 4vw, 72px);
  top: 292px;
  height: 172px;
  z-index: 4;
  pointer-events: none;
  overflow: visible;
}

.agent-link-path {
  fill: none;
  stroke: url(#agentLinkGradient);
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-dasharray: 8 8;
  opacity: 0.52;
  filter: url(#agentLinkGlow);
  animation: agentLinkFlow 1.8s linear infinite;
}

.agent-link-path.status-running {
  opacity: 0.95;
  stroke-width: 3;
  stroke-dasharray: 10 7;
}

.agent-link-path.status-success {
  opacity: 0.78;
  stroke: #6366F1;
  stroke-dasharray: 0;
}

.agent-link-dot {
  fill: #38BDF8;
  opacity: 0.8;
  filter: drop-shadow(0 0 8px rgba(14, 165, 233, 0.55));
}

.agent-link-dot.status-success {
  fill: #6366F1;
}

.agent-link-dot.status-running {
  fill: #3B82F6;
  animation: linkDotPulse 1.4s ease-in-out infinite;
}

@keyframes agentLinkFlow {
  to {
    stroke-dashoffset: -32;
  }
}

@keyframes linkDotPulse {
  0%, 100% {
    r: 4;
    opacity: 0.75;
  }
  50% {
    r: 6;
    opacity: 1;
  }
}

.agent-station-row-v4 {
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  max-width: 1420px;
  margin: 74px auto 0;
  align-items: stretch;
}

.agent-station-card-v4 {
  min-height: 196px;
}

.station-live-log {
  min-height: 78px;
  margin: 12px 0 12px;
}

.review-station-row-v4 {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  width: min(1120px, 88%);
  margin: 24px auto 0;
}

.orbit-one {
  top: 116px;
  height: 210px;
}

.orbit-two {
  top: 176px;
  height: 244px;
}

.orbit-three {
  top: 232px;
  height: 220px;
}

@media (max-width: 1180px) {
  .agent-link-svg {
    display: none;
  }

  .agent-station-row-v4 {
    margin-top: 42px;
  }

  .flow-core-stack-v4 {
    margin-top: 150px;
  }

  .learning-demand-float,
  .master-plan-float {
    width: calc(50% - 34px);
  }
}

@media (max-width: 760px) {
  .learning-demand-float,
  .master-plan-float {
    position: relative;
    top: auto;
    left: auto;
    right: auto;
    width: 100%;
    margin-bottom: 12px;
  }

  .flow-core-stack-v4 {
    margin-top: 16px;
  }

  .agent-station-row-v4 {
    margin-top: 28px;
  }
}


/* ===== v6 precise connector patch：连线不再使用固定 top/viewBox，改为 DOM 实测坐标 ===== */
.agent-link-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 3;
  pointer-events: none;
  overflow: visible;
}

.agent-link-path {
  vector-effect: non-scaling-stroke;
}

.agent-link-dot {
  transform-box: fill-box;
  transform-origin: center;
}

@media (max-width: 1180px) {
  .agent-link-svg {
    display: block;
  }
}

@media (max-width: 760px) {
  .agent-link-svg {
    display: none;
  }
}

</style>
