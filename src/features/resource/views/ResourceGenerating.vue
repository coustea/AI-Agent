<template>
  <div class="phase-view generating-view workflow-stage-page workflow-stage-page-v4">
    <header class="stage-topbar stage-topbar-v4">
      <div class="stage-title-area">
        <div class="stage-title-copy">
          <h2>资源生成工作流</h2>
          <p>{{ dagHeroMessage }}</p>
        </div>
        <div class="stage-route-progress">
          <template v-for="(step, index) in routeSteps" :key="step.key">
            <span class="route-step" :class="step.state">{{ step.label }}</span>
            <span
              v-if="index < routeSteps.length - 1"
              class="route-line"
              :class="step.lineState"
            ></span>
          </template>
        </div>
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
          <span>已交付资源</span>
          <strong>{{ generatedResources.length }}<small> 项</small></strong>
        </div>
        <button class="btn btn-outline rounded-full stage-log-btn" @click="workflowLogDrawerVisible = true">
          运行日志
          <ArrowRight class='w-4 h-4 inline-block align-middle' />
        </button>
      </div>
    </header>
    <main class="agent-stage-shell-v4">
      <section class="dispatch-workbench-panel dispatch-workbench-panel-v4">
        <div class="workbench-header workbench-header-v4">
          <div>
            <span class="panel-eyebrow">执行流程</span>
            <h3>资源生成进度</h3>
            <p>教学计划完成后生成基础资源，再生成教学课件，最后完成资源整合。</p>
          </div>
          <div class="workbench-actions">
            <button
              v-if="generationError"
              class="workflow-error-status"
              type="button"
              :title="generationError"
              @click="workflowLogDrawerVisible = true"
            >
              <span></span>
              <strong>生成中断</strong>
              <em>查看详情</em>
              <ArrowRight class='w-4 h-4 inline-block align-middle' />
            </button>
            <span v-else class="control-pill active"><span class="live-dot"></span> SSE 实时流追踪</span>
            <span class="control-pill muted">计划 {{ planReady ? '已生成' : '生成中' }}</span>
            <button v-if="!generationError" class="btn btn-outline btn-sm rounded-full" @click="workflowLogDrawerVisible = true">查看日志</button>
          </div>
        </div>

        <div ref="flowCanvasRef" class="agent-flow-canvas agent-flow-canvas-v4">
          <div class="flow-grid-bg"></div>
          <div class="flow-orbit orbit-one"></div>
          <div class="flow-orbit orbit-two"></div>
          <div class="flow-orbit orbit-three"></div>

          <div class="flow-core-stack flow-core-stack-v4">
            <article
              ref="planningNodeRef"
              class="agent-station-card agent-station-card-v4 planning-core"
              :class="['status-' + getStageNode('planning').status, { 'is-selected': selectedDagNodeId === 'planning' }]"
              @click="handleAgentClick('planning', $event)"
            >
              <div class="station-header">
                <div class="station-icon">
                  <component :is="getWorkflowIcon('planning')"  class='w-4 h-4' />
                </div>
                <div>
                  <strong>教学计划</strong>
                  <span>Planning Agent</span>
                </div>
                <em>{{ getNodeStatusLabel(getStageNode('planning')) }}</em>
              </div>
              <div class="station-live-log" :class="[`is-${getStageNode('planning').status}`]">
                <TransitionGroup name="msg-queue" tag="div" class="msg-queue-shell">
                  <div v-for="(msg, i) in getNodeMessages(getStageNode('planning'))" :key="msg" class="station-live-current message-queue-item" :class="{ 'is-head': i === 0 && getNodeMessages(getStageNode('planning')).length > 1 }">
                    <span class="station-live-dot" :class="i === 0 && getNodeMessages(getStageNode('planning')).length > 1 ? 'muted' : getStageNode('planning').status"></span>
                    <p class="live-message-only">{{ msg }}</p>
                  </div>
                </TransitionGroup>
                <div v-if="!getNodeMessages(getStageNode('planning')).length" class="station-live-current message-only-layout">
                  <span class="station-live-dot" :class="getStageNode('planning').status"></span>
                  <p class="live-message-only">{{ getNodeDisplayMessage(getStageNode('planning')) }}</p>
                </div>
              </div>
              <div class="station-footer">
                <span>{{ getNodeStageLabel(getStageNode('planning')) }}</span>
                <div class="station-progress-track">
                  <i :style="{ width: `${getStageNode('planning').progress}%` }"></i>
                </div>
              </div>
            </article>
          </div>

          <svg class="agent-link-svg" :viewBox="'0 0 ' + linkCanvasSize.width + ' ' + linkCanvasSize.height" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <linearGradient id="agentLinkGradient" x1="0" x2="1" y1="0" y2="1">
                <stop offset="0%" stop-color="#3B82F6" stop-opacity="0.22" />
                <stop offset="52%" stop-color="#2563EB" stop-opacity="0.8" />
                <stop offset="100%" stop-color="#1D4ED8" stop-opacity="0.28" />
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

          <transition-group name="agent-station" tag="div" class="agent-station-row agent-station-row-v4 base-agent-row">
            <article
              v-for="node in parallelPoolNodes"
              :key="node.id"
              class="agent-station-card agent-station-card-v4"
              :ref="el => setStationCardRef(node.id, el)"
              :class="['status-' + node.status, { 'is-selected': selectedDagNodeId === node.id, 'has-artifact': hasGeneratedResource(node.id) }]"
              @click="handleAgentClick(node.id, $event)"
            >
              <div class="station-header">
                <div class="station-icon">
                  <component :is="getWorkflowIcon(node.id)"  class='w-4 h-4' />
                </div>
                <div>
                  <strong>{{ getWorkflowTitle(node.id) }}</strong>
                  <span>基础资源</span>
                </div>
                <em>{{ getNodeStatusLabel(node) }}</em>
              </div>
              <div class="station-live-log" :class="[`is-${node.status}`]">
                <TransitionGroup name="msg-queue" tag="div" class="msg-queue-shell">
                  <div v-for="(msg, i) in getNodeMessages(node)" :key="msg" class="station-live-current message-queue-item" :class="{ 'is-head': i === 0 && getNodeMessages(node).length > 1 }">
                    <span class="station-live-dot" :class="i === 0 && getNodeMessages(node).length > 1 ? 'muted' : node.status"></span>
                    <p class="live-message-only">{{ msg }}</p>
                  </div>
                </TransitionGroup>
                <div v-if="!getNodeMessages(node).length" class="station-live-current message-only-layout">
                  <span class="station-live-dot" :class="node.status"></span>
                  <p class="live-message-only">{{ getNodeDisplayMessage(node) }}</p>
                </div>
              </div>
              <div class="station-footer">
                <span>{{ getNodeStageLabel(node) }}</span>
                <div class="station-progress-track">
                  <i :style="{ width: `${node.progress}%` }"></i>
                </div>
              </div>
            </article>
          </transition-group>

          <div v-if="showAggregationStage" class="dual-flow-connector" aria-hidden="true">
            <span></span><i></i><i></i>
          </div>

          <div v-if="showAggregationStage" class="agent-station-row agent-station-row-v4 aggregation-agent-row">
            <article
              class="agent-station-card agent-station-card-v4"
              :class="['status-' + pptNode.status, { 'is-selected': selectedDagNodeId === pptNode.id, 'has-artifact': hasGeneratedResource(pptNode.id), 'is-unselected': !showPptNode }]"
              @click="showPptNode && handleAgentClick(pptNode.id, $event)"
            >
              <div class="station-header">
                <div class="station-icon">
                  <component :is="getWorkflowIcon(pptNode.id)"  class='w-4 h-4' />
                </div>
                <div>
                  <strong>教学课件</strong>
                  <span>PPT Agent</span>
                </div>
                <em>{{ showPptNode ? getNodeStatusLabel(pptNode) : '未选择' }}</em>
              </div>
              <div class="station-live-log" :class="[`is-${pptNode.status}`]">
                <template v-if="showPptNode">
                  <TransitionGroup name="msg-queue" tag="div" class="msg-queue-shell">
                    <div v-for="(msg, i) in getNodeMessages(pptNode)" :key="msg" class="station-live-current message-queue-item" :class="{ 'is-head': i === 0 && getNodeMessages(pptNode).length > 1 }">
                      <span class="station-live-dot" :class="i === 0 && getNodeMessages(pptNode).length > 1 ? 'muted' : pptNode.status"></span>
                      <p class="live-message-only">{{ msg }}</p>
                    </div>
                  </TransitionGroup>
                  <div v-if="!getNodeMessages(pptNode).length" class="station-live-current message-only-layout">
                    <span class="station-live-dot" :class="pptNode.status"></span>
                    <p class="live-message-only">{{ getNodeDisplayMessage(pptNode) }}</p>
                  </div>
                </template>
                <div v-else class="station-live-current message-only-layout">
                  <span class="station-live-dot waiting"></span>
                  <p class="live-message-only">当前任务未选择 PPT Agent</p>
                </div>
              </div>
              <div class="station-footer">
                <span>{{ showPptNode ? getNodeStageLabel(pptNode) : '未加入本次任务' }}</span>
                <div class="station-progress-track">
                  <i :style="{ width: `${pptNode.progress}%` }"></i>
                </div>
              </div>
            </article>

          </div>

          <div v-if="showAggregationStage" class="dual-flow-connector is-merge" aria-hidden="true">
            <span></span><i></i><i></i>
          </div>

          <div class="bundle-stage-shell">
            <article
              class="review-station-card review-station-card-v4 bundle-stage-card"
              :class="['status-' + bundleNode.status, { 'is-selected': selectedDagNodeId === bundleNode.id }]"
              @click="handleAgentClick(bundleNode.id, $event)"
            >
              <div class="review-icon">
                <component :is="getWorkflowIcon(bundleNode.id)"  class='w-4 h-4' />
              </div>
              <div>
                <strong>资源整合</strong>
                <span>{{ getNodeStageLabel(bundleNode) }}</span>
              </div>
              <em>{{ bundleNode.progress }}%</em>
            </article>
          </div>
        </div>
      </section>

      <transition name="detail-float">
        <aside
          v-if="detailPanelVisible && selectedDagNode"
          class="agent-detail-floating-panel"
          :style="detailPanelStyle"
          role="dialog"
          aria-label="Agent 运行详情"
        >
          <span class="detail-anchor-caret" aria-hidden="true"></span>

          <div class="detail-panel-title">
            <div class="focus-agent-icon">
              <component :is="getWorkflowIcon(selectedDagNode.id)"  class='w-4 h-4' />
            </div>
            <div class="detail-title-copy">
              <span>运行详情</span>
              <h3>{{ getWorkflowTitle(selectedDagNode.id) }}</h3>
              <p>{{ getNodeStageLabel(selectedDagNode) }}</p>
            </div>
            <span class="detail-status-dot" :class="`status-${selectedDagNode.status}`"></span>
            <button class="detail-close-btn" type="button" aria-label="关闭 Agent 详情" @click="closeAgentDetail">×</button>
          </div>

          <div class="selected-agent-detail-card">
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
                <dt>成果状态</dt>
                <dd>{{ getNodeArtifactStatus(selectedDagNode) }}</dd>
              </div>
            </dl>

            <div class="detail-io-grid">
              <div>
                <span>输入</span>
                <p>{{ getNodeInputSummary(selectedDagNode) }}</p>
              </div>
              <div>
                <span>输出</span>
                <p>{{ getNodeOutputSummary(selectedDagNode) }}</p>
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
          <span class="panel-eyebrow">READY RESOURCES</span>
          <strong>已交付资源</strong>
        </div>
        <p>这里仅展示已经完成并可预览的资源，不改变主流水线的阅读顺序。</p>
      </div>
      <div class="output-dock-list output-dock-list-v4">
        <article
          v-for="agentId in visibleOutputAgentIds"
          :key="agentId"
          class="output-dock-item output-dock-item-v4"
          :class="{ ready: hasGeneratedResource(agentId), 'just-arrived': latestArtifactAgentId === agentId }"
          @click="emit('openResource', agentId)"
        >
          <span><component :is="getWorkflowIcon(agentId)"  class='w-4 h-4' /></span>
          <div>
            <strong>{{ getResourceTypeLabel(agentId) }}</strong>
            <p>{{ hasGeneratedResource(agentId) ? '已生成，可预览' : getAgentOutputFormat(agentId) }}</p>
          </div>
          <em>{{ hasGeneratedResource(agentId) ? '刚刚完成' : getNodeStatusLabel(getStageNode(agentId)) }}</em>
        </article>
      </div>
    </section>

    <Teleport to="body"><transition name="slide-over"><div v-if="workflowLogDrawerVisible" class="custom-modal-overlay" @click="workflowLogDrawerVisible = false"><div class="custom-drawer-content max-w-[420px] w-full bg-white h-full absolute right-0 shadow-2xl p-6 flex flex-col z-50" @click.stop><div class="drawer-header border-b border-slate-100 pb-3 mb-4 flex justify-between items-center"><h3 class="text-sm font-bold text-slate-900">实时调度日志</h3><button class="modal-close-btn text-slate-400 hover:text-slate-600" @click="workflowLogDrawerVisible = false">×</button></div><div class="drawer-body flex-1 overflow-y-auto">
      <div class="drawer-log-list">
        <div v-for="item in workflowLogItems" :key="item.id" class="drawer-log-item" :class="`is-${item.status}`">
          <span class="drawer-log-dot"></span>
          <div>
            <strong>{{ item.title }}</strong>
            <p>{{ item.message }}</p>
          </div>
        </div>
      </div>
    </div></div></div></transition></Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onBeforeUnmount, onMounted, watch, type Component } from 'vue'
import {
  PhTarget as Aim,
  PhArrowRight as ArrowRight,
  PhArchive as Box,
  PhCompass as Connection,
  PhCpu as Cpu,
  PhChartBar as DataBoard,
  PhFileText as Document,
  PhNotePencil as EditPen,
  PhBookOpen as Reading,
  PhShareNetwork as Share
} from '@phosphor-icons/vue'
import type { ResourceAgentId } from '@/features/resource/model/resource'
import {
  COORDINATOR_AGENT_ID,
  PPT_AGENT_ID,
  BUNDLE_AGENT_ID,
  SYSTEM_AGENT_IDS,
  AGENT_DISPLAY,
  getResourceTypeLabel,
  getAgentOutputFormat,
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
const detailPanelStyle = ref<Record<string, string>>({})
const detailAnchorElement = ref<HTMLElement | null>(null)

const workflowIconMap: Record<string, Component> = {
  planning: Aim,
  coordinator: Connection,
  content: Document,
  mindmap: Share,
  quiz: EditPen,
  code: Cpu,
  reading: Reading,
  ppt: DataBoard,
  bundle: Box,
}

const workflowTitleMap: Record<string, string> = {
  planning: '教学计划',
  coordinator: '结果汇总',
  content: '课程讲解',
  mindmap: '思维导图',
  quiz: '练习题',
  code: '代码示例',
  reading: '拓展阅读',
  ppt: '教学课件',
  bundle: '资源包交付',
}

function getWorkflowIcon(id: string) {
  return workflowIconMap[id] || Document
}

function getWorkflowTitle(id: string) {
  return workflowTitleMap[id] || AGENT_DISPLAY[id]?.label || id
}

const flowCanvasRef = ref<HTMLElement | null>(null)
const planningNodeRef = ref<HTMLElement | null>(null)
const stationCardRefs = new Map<string, HTMLElement>()
const linkCanvasSize = ref({ width: 1000, height: 700 })
const measuredAgentLinks = ref<AgentLinkGeometry[]>([])
let linkMeasureFrame = 0
let detailPositionFrame = 0
let canvasResizeObserver: ResizeObserver | null = null

function handleAgentClick(id: string, event: MouseEvent) {
  const target = event.currentTarget
  detailAnchorElement.value = target instanceof HTMLElement ? target : null
  detailPanelVisible.value = true
  emit('selectNode', id)
  nextTick(scheduleDetailPanelPosition)
}

function closeAgentDetail() {
  detailPanelVisible.value = false
  detailAnchorElement.value = null
}

function scheduleDetailPanelPosition() {
  if (typeof window === 'undefined' || !detailPanelVisible.value) return
  if (detailPositionFrame) window.cancelAnimationFrame(detailPositionFrame)
  detailPositionFrame = window.requestAnimationFrame(() => {
    detailPositionFrame = 0
    updateDetailPanelPosition()
  })
}

function updateDetailPanelPosition() {
  const anchor = detailAnchorElement.value
  if (!anchor || typeof window === 'undefined') return

  const anchorRect = anchor.getBoundingClientRect()
  const viewportGap = 12
  const anchorGap = 14
  const panelWidth = Math.min(380, window.innerWidth - viewportGap * 2)
  const preferredLeft = anchorRect.right + anchorGap
  const left = Math.max(viewportGap, Math.min(preferredLeft, window.innerWidth - panelWidth - viewportGap))
  const top = Math.max(viewportGap, anchorRect.top)
  const maxHeight = Math.max(120, window.innerHeight - top - viewportGap)

  detailPanelStyle.value = {
    top: `${Math.round(top)}px`,
    left: `${Math.round(left)}px`,
    width: `${Math.round(panelWidth)}px`,
    maxHeight: `${Math.round(maxHeight)}px`,
  }
}

const baseGenerationAgentIds = computed(() => {
  return props.dagSelectedAgentIds.filter(id => id !== PPT_AGENT_ID)
})

const parallelPoolNodes = computed(() => {
  return baseGenerationAgentIds.value.map(agentId => getStageNode(agentId))
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
  const planning = planningNodeRef.value
  if (!canvas || !planning) return

  const canvasRect = canvas.getBoundingClientRect()
  const width = Math.max(1, Math.round(canvasRect.width))
  const height = Math.max(1, Math.round(canvasRect.height))
  if (linkCanvasSize.value.width !== width || linkCanvasSize.value.height !== height) {
    linkCanvasSize.value = { width, height }
  }

  const planningRect = planning.getBoundingClientRect()
  const startX = Math.round(planningRect.left - canvasRect.left + planningRect.width / 2)
  const startY = Math.round(planningRect.bottom - canvasRect.top + 8)

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
  window.addEventListener('resize', scheduleDetailPanelPosition)
  window.addEventListener('scroll', scheduleDetailPanelPosition, true)

  if (typeof ResizeObserver !== 'undefined' && flowCanvasRef.value) {
    canvasResizeObserver = new ResizeObserver(scheduleLinkMeasure)
    canvasResizeObserver.observe(flowCanvasRef.value)
  }
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', scheduleLinkMeasure)
    window.removeEventListener('resize', scheduleDetailPanelPosition)
    window.removeEventListener('scroll', scheduleDetailPanelPosition, true)
    if (linkMeasureFrame) window.cancelAnimationFrame(linkMeasureFrame)
    if (detailPositionFrame) window.cancelAnimationFrame(detailPositionFrame)
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
  return nodes
})

const aggregationNodes = computed(() => trailingStageNodes.value)

const showPptNode = computed(() => props.dagSelectedAgentIds.includes(PPT_AGENT_ID as ResourceAgentId))

const showAggregationStage = computed(() => showPptNode.value)

const pptNode = computed(() => getStageNode(PPT_AGENT_ID))

const bundleNode = computed(() => getStageNode(BUNDLE_AGENT_ID))

const selectedDagNode = computed(() => {
  if (!props.selectedDagNodeId) return null
  if (props.selectedDagNodeId === COORDINATOR_AGENT_ID) return getStageNode(COORDINATOR_AGENT_ID)
  return props.dagNodeStates[props.selectedDagNodeId] || getStageNode(props.selectedDagNodeId)
})

const runningAgentCount = computed(() => {
  return props.visibleWorkflowNodes.filter(node => node.id !== COORDINATOR_AGENT_ID && node.status === 'running').length
})

const dagHeroMessage = computed(() => {
  const running = Object.values(props.dagNodeStates).find(n => n.id !== COORDINATOR_AGENT_ID && n.status === 'running')
  if (running) return running.currentMessage || `${running.label}处理中...`
  if (getStageNode(COORDINATOR_AGENT_ID).status === 'running') return '正在准备教学课件...'
  const allDone = Object.values(props.dagNodeStates).every(n => n.status === 'success')
  if (allDone) return '所有资源生成完成'
  return props.latestWorkflowMessage || '多智能体协同生成中'
})

const routeSteps = computed(() => {
  const planning = getStageNode('planning')
  const coordinator = getStageNode(COORDINATOR_AGENT_ID)
  const baseDone = parallelPoolNodes.value.length > 0 && parallelPoolNodes.value.every(node => ['success', 'failed', 'skipped'].includes(node.status))
  const baseRunning = parallelPoolNodes.value.some(node => node.status === 'running')
  const aggregationRunning = aggregationNodes.value.some(node => node.status === 'running')
  const aggregationDone = aggregationNodes.value.length === 0 || aggregationNodes.value.every(node => ['success', 'failed', 'skipped'].includes(node.status))
  const bundle = bundleNode.value

  return [
    {
      key: 'plan',
      label: '教学计划',
      state: planning.status === 'success' ? 'done' : 'active',
      lineState: planning.status === 'success' ? 'done' : 'active',
    },
    {
      key: 'base',
      label: '基础资源',
      state: baseDone ? 'done' : baseRunning ? 'active' : '',
      lineState: coordinator.status === 'success' ? 'done' : baseDone || coordinator.status === 'running' ? 'active' : '',
    },
    {
      key: 'aggregation',
      label: '教学课件',
      state: aggregationDone && aggregationNodes.value.length ? 'done' : aggregationRunning || coordinator.status === 'running' ? 'active' : '',
      lineState: aggregationDone || bundle.status === 'running' || bundle.status === 'success' ? 'done' : aggregationRunning ? 'active' : '',
    },
    {
      key: 'bundle',
      label: '资源整合',
      state: bundle.status === 'success' ? 'done' : bundle.status === 'running' ? 'active' : '',
      lineState: '',
    },
  ]
})

const visibleOutputAgentIds = computed(() => {
  return props.dagSelectedAgentIds
})

const workflowLogItems = computed(() => {
  const items: Array<{ id: string; title: string; message: string; status: DagNodeState['status'] }> = []

  if (props.generationError) {
    items.push({
      id: 'global-generation-error',
      title: '资源生成任务',
      message: props.generationError,
      status: 'failed',
    })
  }

  props.visibleWorkflowNodes.forEach((node) => {
    if (node.id === COORDINATOR_AGENT_ID) return
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
    research: '资料研究',
    research_delegate: '研究委托',
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
  const isReadyInResources = props.generatedResources.some(resource => resource.type === type)
  const isReadyInDag = props.dagNodeStates[type]?.status === 'success'
  return isReadyInResources || isReadyInDag
}

function getNodeStatusLabel(node: DagNodeState) {
  if (node.status === 'failed') return '受阻'
  if (node.status === 'skipped') return '已跳过'
  if (node.status === 'success') return '就绪'
  if (node.status === 'running') return '执行中'
  return '就绪待命'
}

function getNodeStageLabel(node: DagNodeState) {
  if (node.status === 'success') return node.id === BUNDLE_AGENT_ID ? '整合完成' : '已完成'
  if (node.status === 'failed') return '协作中断'
  if (node.status === 'skipped') return '已跳过'
  if (node.status === 'running') {
    if (node.id === 'planning') return '计划生成中'
    if (node.id === COORDINATOR_AGENT_ID) return '结果汇总中'
    if (node.id === PPT_AGENT_ID) return '生成中'
    if (node.phase === 'llm_generating') return '核心推演中'
    if (node.phase === 'research' || node.phase === 'research_delegate') return '资料研究中'
    if (node.phase === 'validating') return '一致性校验中'
    if (node.phase === 'artifact_saved') return '资源已保存'
    if (node.phase === 'bundling') return '资源整合中'
    return '工位执行中'
  }
  if (node.id === BUNDLE_AGENT_ID) return '等待基础资源与课件'
  if (node.id === PPT_AGENT_ID) return '等待基础资源'
  return '等待上游协同'
}

function getNodePhaseLabel(node: DagNodeState) {
  const phaseMap: Record<string, string> = {
    planning_blueprint: '蓝图构建',
    coverage_gap_warning: '覆盖校验',
    llm_generating: '深度推演',
    validating: '一致性校验',
    ppt_generating: 'PPT 聚合',
    ppt_waiting_sources: '等待讲义要义',
    artifact_saved: '成果移交',
    research: '资料研究',
    research_delegate: '研究委托',
    aggregation_done: '聚合完成',
    bundling: '资源打包',
    finished: '已完成',
    failed: '受阻',
  }
  if (node.phase && phaseMap[node.phase]) return phaseMap[node.phase]
  if (node.id === 'planning' && node.status === 'running') return '计划生成'
  if (node.id === COORDINATOR_AGENT_ID && node.status === 'running') return '任务调度'
  if (node.id === PPT_AGENT_ID && node.status === 'running') return '聚合生成'
  if (node.id === BUNDLE_AGENT_ID && node.status === 'running') return '打包交付'
  if (node.status === 'waiting') return '等待上游'
  if (node.status === 'success') return '已完成'
  if (node.status === 'failed') return '受阻'
  return '工位状态'
}

function getNodeMessages(node: DagNodeState): string[] {
  const history = node.stepHistory || []
  if (history.length === 0) return []
  return history.slice(-2)
}

function getNodeDisplayMessage(node: DagNodeState) {
  if (node.status === 'failed') return node.currentMessage || '工位执行受阻，请检查协同日志'
  if (node.currentMessage) return node.currentMessage
  if (node.id === 'planning') return '正在根据学习需求与画像生成教学计划'
  if (node.id === COORDINATOR_AGENT_ID) return '等待基础资源完成后汇总成功、失败与大纲覆盖情况'
  if (node.id === PPT_AGENT_ID) return '等待讲义要义就绪以重排宣讲幻灯'
  if (node.id === BUNDLE_AGENT_ID) return '等待基础资源与聚合结果就绪后打包交付'
  return getNodeFallbackMessage(node)
}

function getNodeArtifactStatus(node: DagNodeState) {
  if (node.id === 'planning') {
    return node.status === 'success' ? '教学计划已生成' : '正在生成教学计划'
  }
  if (node.id === COORDINATOR_AGENT_ID) {
    return node.status === 'success' ? '调度与汇总已完成' : '正在分发并汇总执行状态'
  }
  if (node.id === BUNDLE_AGENT_ID) {
    if (node.status === 'success') return '资源包已交付'
    if (node.status === 'running') return '正在汇总并打包资源'
    return '等待上游资源就绪'
  }
  if (node.id === PPT_AGENT_ID) {
    return hasGeneratedResource(node.id) ? '聚合资源已交付' : '等待基础资源后生成'
  }
  return hasGeneratedResource(node.id) ? '基础资源已交付' : '工位响应中'
}

function getNodeInputSummary(node: DagNodeState) {
  if (node.id === 'planning') return '学习需求 / 学习场景 / 用户画像 / 已选 Agent'
  if (node.id === COORDINATOR_AGENT_ID) return '教学计划 / 基础资源执行结果 / 当前执行快照'
  if (node.id === BUNDLE_AGENT_ID) return '基础资源结果 / 聚合资源结果 / 已持久化产物'
  if (node.id === PPT_AGENT_ID) return '教学计划 / 基础资源 handoff / 上游已完成内容'
  return '学习需求 / 用户画像 / 教学计划'
}

function getNodeOutputSummary(node: DagNodeState) {
  if (node.id === 'planning') return '教学计划 / 大纲 / Agent 分工'
  if (node.id === COORDINATOR_AGENT_ID) return '成功失败统计 / 覆盖情况 / 基础资源 handoff'
  if (node.id === BUNDLE_AGENT_ID) return node.status === 'success' ? '最终资源包 / 可预览结果' : '等待汇总后生成资源包'
  if (hasGeneratedResource(node.id)) return getAgentOutputFormat(node.id)
  if (node.id === PPT_AGENT_ID) return '聚合资源生成中 / 等待中'
  return '基础资源生成中 / 等待中'
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
  --font-sans: var(--font-ui);
  --agent-body-font: var(--font-body);

  min-height: auto;
  padding: clamp(24px, 3vw, 36px) var(--resource-page-inset) 80px;
  background: transparent; /* allow parent background glow to show */
  font-family: var(--font-sans);
}

.stage-topbar {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  background: var(--generator-card-bg);
  backdrop-filter: var(--generator-card-blur);
  -webkit-backdrop-filter: var(--generator-card-blur);
  border: var(--generator-card-border);
  border-radius: var(--radius-outer);
  padding: 14px 18px;
  box-shadow: var(--generator-card-shadow);
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
  font-family: var(--agent-body-font);
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

.route-step:not(.done):not(.active) {
  background: rgba(241, 245, 249, 0.92);
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
  border-radius: var(--radius-inner);
  background: rgba(255, 255, 255, 0.52);
  border: var(--generator-card-border);
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
  font-family: var(--agent-body-font);
}

.workbench-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
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

.planning-core {
  width: min(280px, 90vw) !important;
  min-height: 196px !important;
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
  font-size: 0.95rem;
  line-height: 1.2;
}

.core-agent-node span {
  color: var(--cat-resource);
  font-size: 0.72rem;
  font-weight: var(--weight-extrabold);
}

.core-progress {
  font-size: 0.72rem;
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

.aggregation-agent-row {
  max-width: 920px;
  margin-top: 30px;
}

.agent-station-card {
  border-radius: var(--radius-card);
  padding: 13px;
  background: var(--generator-card-bg);
  border: var(--generator-card-border);
  cursor: pointer;
  transition: all 0.26s ease;
  box-shadow: var(--generator-card-shadow);
}

.agent-station-card-v4 {
  min-height: 196px;
  display: flex;
  flex-direction: column;
}

.agent-station-card:hover,
.agent-station-card.is-selected {
  transform: translateY(-5px);
  border-color: var(--cat-resource);
  box-shadow: 0 16px 36px var(--cat-resource-glow);
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
  font-size: 0.8rem;
  line-height: 1.2;
}

.station-header span {
  color: var(--color-text-muted);
  font-size: 0.68rem;
  font-weight: var(--weight-extrabold);
  line-height: 1.15;
}

.station-header em {
  font-size: 0.7rem;
  font-style: normal;
  color: var(--cat-resource);
  font-weight: var(--weight-extrabold);
  white-space: nowrap;
}

.station-live-log {
  min-height: 78px;
  margin: 12px 0 12px;
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
  font-size: 0.68rem;
  font-weight: var(--weight-bold);
  line-height: 1.2;
}

.station-live-current p {
  margin: 3px 0 0;
  color: var(--color-text);
  font-size: 0.74rem;
  font-weight: var(--weight-extrabold);
  line-height: 1.32;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-family: var(--agent-body-font);
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
  font-size: 0.66rem;
  font-weight: var(--weight-extrabold);
  white-space: nowrap;
}

.station-live-line em {
  min-width: 0;
  color: var(--color-text-muted);
  font-size: 0.67rem;
  font-style: normal;
  font-weight: var(--weight-bold);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: var(--agent-body-font);
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
  font-size: 0.72rem;
  font-weight: var(--weight-extrabold);
}

.station-live-empty p {
  margin: 0;
  color: var(--color-text-faint);
  font-family: var(--agent-body-font);
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
  font-family: var(--agent-body-font);
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
  font-size: 0.68rem;
  font-weight: var(--weight-extrabold);
}

.station-progress-track {
  width: 64px;
  height: 4px;
  background: rgba(148, 163, 184, 0.16);
  border-radius: 999px;
  overflow: hidden;
  display: block;
}

.station-progress-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
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
  margin: 30px auto 0;
}

.bundle-stage-shell {
  position: relative;
  z-index: 5;
  width: min(420px, 100%);
  margin: 30px auto 0;
}

.bundle-stage-card {
  position: relative;
  min-height: 102px;
  border-color: rgba(99, 102, 241, 0.26);
  background:
    radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.08), transparent 54%),
    rgba(255, 255, 255, 0.9);
}

.bundle-stage-card::before {
  content: '';
  position: absolute;
  left: 50%;
  top: -18px;
  width: 2px;
  height: 18px;
  transform: translateX(-50%);
  background: linear-gradient(180deg, rgba(99, 102, 241, 0), rgba(99, 102, 241, 0.55));
  border-radius: 999px;
}

.bundle-stage-card.status-running {
  border-color: rgba(59, 130, 246, 0.42);
  box-shadow: 0 20px 48px rgba(37, 99, 235, 0.12);
}

.bundle-stage-card.status-success {
  border-color: rgba(16, 185, 129, 0.4);
  background:
    radial-gradient(circle at 50% 0%, rgba(16, 185, 129, 0.08), transparent 54%),
    rgba(240, 253, 250, 0.9);
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
  font-size: 0.82rem;
  line-height: 1.2;
  display: block;
}

.review-station-card span {
  color: var(--color-text-muted);
  font-size: 0.68rem;
  font-weight: var(--weight-extrabold);
}

.review-station-card em {
  font-style: normal;
  color: var(--cat-resource);
  font-weight: var(--weight-extrabold);
  font-size: 0.72rem;
}

.agent-detail-floating-panel {
  position: fixed;
  top: calc(var(--navbar-height, 64px) + 82px);
  right: clamp(18px, 2.4vw, 34px);
  z-index: 80;
  width: min(420px, calc(100vw - 36px));
  max-height: calc(100vh - var(--navbar-height, 64px) - 112px);
  overflow-y: auto;
  padding: 24px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: var(--generator-card-border);
  border-radius: var(--radius-outer); /* unified round corners */
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.12);
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
  font-family: var(--agent-body-font);
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
  font-family: var(--agent-body-font);
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
  font-family: var(--agent-body-font);
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
  font-family: var(--agent-body-font);
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

.output-dock-section-v4 .panel-eyebrow {
  color: #0f766e;
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
  font-family: var(--agent-body-font);
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
  font-family: var(--agent-body-font);
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
  font-family: var(--agent-body-font);
}

@media (max-width: 1280px) {
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

  .bundle-stage-shell {
    width: 100%;
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

.workbench-actions .control-pill {
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

}


/* ===== 更紧凑的中枢调度布局：用 SVG 精准连接 Coordinator 与子 Agent 卡片 ===== */
.agent-flow-canvas-v4 {
  min-height: clamp(620px, 68vh, 800px);
  padding: clamp(18px, 2vw, 28px) clamp(20px, 2.4vw, 36px) clamp(24px, 2.4vw, 36px);
}

.flow-core-stack-v4 {
  margin-top: 52px;
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
  stroke: var(--cat-resource);
  stroke-dasharray: 0;
}

.agent-link-dot {
  fill: #38BDF8;
  opacity: 0.8;
  filter: drop-shadow(0 0 8px rgba(14, 165, 233, 0.55));
}

.agent-link-dot.status-success {
  fill: var(--cat-resource);
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
    margin-top: 52px;
  }
}

@media (max-width: 760px) {
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

/* ===== v7 incremental visual polish: preserve the original component behavior ===== */
.workflow-stage-page-v4 {
  --workflow-border: #dfe3e8;
  --workflow-border-strong: #c8ced6;
  --workflow-surface: #ffffff;
  --workflow-surface-subtle: #f7f8fa;
  --workflow-text: #172033;
  --workflow-muted: #667085;

  background: transparent;
}

.dispatch-workbench-panel,
.output-dock-section-v4 {
  border-color: var(--workflow-border);
  border-radius: 16px;
  background: var(--workflow-surface);
  box-shadow: 0 8px 24px rgba(23, 32, 51, 0.06);
  backdrop-filter: none;
}

.stage-stat-card {
  background: rgba(255, 255, 255, 0.52);
  border: var(--generator-card-border);
  border-radius: var(--radius-inner);
}

.route-step,
.control-pill {
  border-radius: 7px;
}

.panel-eyebrow {
  color: var(--workflow-muted);
  letter-spacing: 0.04em;
  text-transform: none;
}

.live-dot {
  box-shadow: none;
}

.mini-progress-track i {
  background: #2563eb;
  box-shadow: none;
}

.agent-flow-canvas,
.agent-flow-canvas-v4 {
  min-height: auto;
  border-color: var(--workflow-border);
  border-radius: 14px;
  background: var(--workflow-surface-subtle);
}

.agent-flow-canvas-v4::before,
.flow-grid-bg,
.flow-orbit {
  display: none !important;
}

.agent-link-svg {
  z-index: 2;
}

.agent-link-path,
.agent-link-path.status-running,
.agent-link-path.status-success {
  stroke: #aebccc;
  stroke-width: 1.5;
  stroke-dasharray: 5 5;
  filter: none;
  opacity: 0.8;
  animation: none;
}

.agent-link-dot,
.agent-link-dot.status-running,
.agent-link-dot.status-success {
  fill: #7c8da3;
  filter: none;
  opacity: 0.85;
  animation: none;
}

.flow-core-stack-v4 {
  margin-top: 0;
}

.core-agent-node {
  min-height: 70px;
  border-color: var(--workflow-border-strong);
  border-radius: 12px;
  background: var(--workflow-surface);
  box-shadow: 0 5px 14px rgba(23, 32, 51, 0.06);
}

.core-agent-node:hover,
.core-agent-node.is-selected {
  border-color: #7ba8ed;
  box-shadow: 0 0 0 2px #dbeafe;
  transform: translateY(-1px);
}

.core-icon,
.station-icon,
.review-icon,
.focus-agent-icon {
  border: 1px solid #d8e2ef;
  border-radius: 9px;
  color: #315c9d;
  background: #f1f5fa;
}

.core-icon svg,
.station-icon svg,
.review-icon svg,
.focus-agent-icon svg,
.output-dock-item-v4 > span svg {
  font-size: 18px;
}

.flow-stage-label,
.aggregation-stage-heading {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 11px;
  margin: 26px auto 0;
  padding: 0 2px;
}

.flow-stage-label > span,
.aggregation-stage-heading > span {
  display: grid;
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  place-items: center;
  border: 1px solid var(--workflow-border-strong);
  border-radius: 8px;
  color: #475467;
  background: var(--workflow-surface);
  font-size: 10px;
  font-weight: 800;
}

.flow-stage-label > div,
.aggregation-stage-heading > div {
  min-width: 0;
  flex: 1;
}

.flow-stage-label strong,
.aggregation-stage-heading strong {
  display: block;
  color: var(--workflow-text);
  font-size: 13px;
}

.flow-stage-label p,
.aggregation-stage-heading p {
  margin: 3px 0 0;
  color: var(--workflow-muted);
  font-size: 11px;
  line-height: 1.45;
}

.aggregation-stage-heading em {
  padding: 5px 8px;
  border: 1px solid #cfe0ff;
  border-radius: 6px;
  color: #2456a6;
  background: #f5f8ff;
  font-size: 10px;
  font-style: normal;
  font-weight: 700;
}

.agent-station-row-v4.base-agent-row,
.agent-station-row-v4.aggregation-agent-row {
  margin-top: 14px;
}

.agent-station-card,
.agent-station-card-v4 {
  border-radius: var(--radius-card);
  background: var(--generator-card-bg);
  border: var(--generator-card-border);
  box-shadow: var(--generator-card-shadow);
}

.agent-station-card:hover,
.agent-station-card.is-selected {
  transform: translateY(-5px);
  border-color: var(--cat-resource);
  box-shadow: 0 16px 36px var(--cat-resource-glow);
}

.agent-station-card.status-running {
  border-color: #79a6e8;
  box-shadow: inset 3px 0 0 #2563eb;
}

.agent-station-card.status-success,
.agent-station-card.has-artifact {
  border-color: #a9d6c3;
  background: #fbfefc;
}

.station-live-log {
  border-color: var(--workflow-border);
  border-radius: 9px;
  background: var(--workflow-surface-subtle);
}

.station-live-dot {
  box-shadow: none;
}

.flow-stage-divider {
  position: relative;
  display: flex;
  width: min(560px, 100%);
  align-items: center;
  gap: 10px;
  margin: 24px auto 14px;
  color: #98a2b3;
  font-size: 10px;
  text-align: center;
}

.flow-stage-divider::before,
.flow-stage-divider::after {
  content: '';
  position: absolute;
  left: 50%;
  width: 1px;
  height: 14px;
  background: #aebccc;
  transform: translateX(-50%);
}

.flow-stage-divider::before {
  top: -14px;
}

.flow-stage-divider::after {
  bottom: -14px;
}

.flow-stage-divider i {
  height: 1px;
  flex: 1;
  background: var(--workflow-border-strong);
}

.coordinator-checkpoint-row {
  display: flex;
  justify-content: center;
}

.coordinator-checkpoint {
  width: min(420px, 100%);
}

.aggregation-stage-heading {
  position: relative;
  margin-top: 22px;
  padding-top: 14px;
  border-top: 1px solid var(--workflow-border);
}

.aggregation-stage-heading::before {
  content: '';
  position: absolute;
  left: 50%;
  top: -22px;
  width: 1px;
  height: 22px;
  background: #aebccc;
  transform: translateX(-50%);
}

.aggregation-agent-row {
  max-width: 100%;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.aggregation-agent-row .agent-station-card-v4.is-unselected {
  cursor: default;
  opacity: 0.62;
  box-shadow: none;
}

.aggregation-agent-row .agent-station-card-v4.is-unselected:hover {
  border-color: var(--workflow-border);
  box-shadow: none;
  transform: none;
}

.aggregation-agent-row .agent-station-card-v4.is-unselected .station-footer .station-progress-track {
  visibility: hidden;
}

.dual-flow-connector {
  position: relative;
  width: 50%;
  height: 30px;
  margin: 6px auto 0;
  color: #aebccc;
}

.dual-flow-connector::before,
.dual-flow-connector span,
.dual-flow-connector i {
  position: absolute;
  display: block;
  background: currentColor;
}

.dual-flow-connector::before {
  content: '';
  left: 50%;
  top: 0;
  width: 1px;
  height: 15px;
  transform: translateX(-50%);
}

.dual-flow-connector span {
  left: 0;
  right: 0;
  top: 14px;
  height: 1px;
}

.dual-flow-connector i {
  top: 14px;
  width: 1px;
  height: 16px;
}

.dual-flow-connector i:first-of-type {
  left: 0;
}

.dual-flow-connector i:last-of-type {
  right: 0;
}

.dual-flow-connector + .aggregation-agent-row {
  margin-top: 0;
}

.dual-flow-connector.is-merge {
  margin-top: 0;
  transform: rotate(180deg);
}

.dual-flow-connector.is-merge + .bundle-stage-shell {
  margin-top: 0;
}

.output-dock-item-v4 > span:first-child {
  display: grid;
  place-items: center;
  color: #315c9d;
}

.output-dock-section-v4 {
  grid-template-columns: 170px minmax(0, 1fr);
  padding: 11px 14px;
}

.output-dock-section-v4 .panel-eyebrow {
  font-size: 9px;
}

.output-dock-section-v4 .output-dock-heading {
  gap: 4px;
}

.output-dock-section-v4 .output-dock-heading strong {
  font-size: 13px;
}

.output-dock-section-v4 .output-dock-heading p {
  font-size: 10px;
  line-height: 1.4;
}

.output-dock-list-v4 {
  gap: 8px;
}

.output-dock-item-v4 {
  min-height: 64px;
  padding: 7px 76px 7px 9px;
  border-radius: 10px;
}

.output-dock-item-v4 > span {
  width: 28px;
  height: 28px;
  border-radius: 8px;
}

.output-dock-item-v4 > span svg {
  font-size: 15px;
}

.output-dock-item-v4 strong {
  font-size: 11px;
}

.output-dock-item-v4 p {
  font-size: 9px;
}

.output-dock-item-v4 em {
  right: 9px;
  top: 9px;
  padding: 2px 6px;
  font-size: 9px;
}

.detail-close-btn:focus-visible,
.core-agent-node:focus-visible,
.agent-station-card:focus-visible,
.review-station-card:focus-visible,
.output-dock-item-v4:focus-visible {
  outline: 3px solid rgba(37, 99, 235, 0.3);
  outline-offset: 2px;
}

@media (max-width: 720px) {
  .flow-stage-label,
  .aggregation-stage-heading {
    align-items: flex-start;
  }

  .aggregation-stage-heading em {
    display: none;
  }

  .aggregation-agent-row {
    grid-template-columns: minmax(0, 1fr);
  }

  .dual-flow-connector {
    width: 1px;
  }

  .dual-flow-connector span,
  .dual-flow-connector i {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .workflow-stage-page-v4 *,
  .workflow-stage-page-v4 *::before,
  .workflow-stage-page-v4 *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }

  .core-agent-node:hover,
  .agent-station-card:hover {
    transform: none;
  }
}

/* v8 compact header: turn the oversized dashboard card into a quiet status bar */
.stage-topbar-v4 {
  display: grid;
  grid-template-columns: minmax(300px, 1fr) auto;
  align-items: center;
  gap: 18px;
  margin-bottom: 10px;
  padding: 4px 2px 12px;
  border: 0;
  border-bottom: 1px solid var(--workflow-border);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.stage-title-area {
  display: grid;
  grid-template-columns: auto minmax(280px, 1fr);
  align-items: center;
  gap: 22px;
  min-width: 0;
}

.stage-title-copy {
  min-width: 0;
}

.stage-title-area h2 {
  font-size: 17px;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.stage-title-area p {
  max-width: 360px;
  margin-top: 3px;
  overflow: hidden;
  color: #7a8495;
  font-size: 11px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stage-route-progress {
  flex-wrap: nowrap;
  gap: 6px;
  min-width: 0;
}

.route-step {
  height: 22px;
  padding: 0 8px;
  font-size: 10px;
  white-space: nowrap;
}

.route-line {
  width: clamp(12px, 2vw, 28px);
  min-width: 12px;
}

.stage-stat-group-v4 {
  display: flex;
  flex: none;
  flex-wrap: nowrap;
  gap: 0;
  justify-content: flex-end;
  min-width: 0;
}

.stage-stat-group-v4 .stage-stat-card,
.stage-stat-group-v4 .progress-stat-card {
  display: grid;
  grid-template-columns: auto auto;
  align-items: baseline;
  column-gap: 7px;
  flex: none;
  width: auto;
  min-width: 0;
  max-width: none;
  padding: 3px 14px;
  border: 0;
  border-left: 1px solid var(--workflow-border);
  border-radius: 0;
  background: transparent;
}

.stage-stat-card span {
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
}

.stage-stat-card strong {
  font-size: 15px;
  line-height: 1;
}

.stage-stat-card small {
  font-size: 9px;
}

.stage-stat-group-v4 .mini-progress-track {
  grid-column: 1 / -1;
  width: 100%;
  height: 3px;
  margin-top: 5px;
}

.stage-log-btn {
  flex: none;
  height: 32px;
  margin-left: 10px;
  padding: 0 13px;
  border-color: var(--workflow-border-strong) !important;
  color: #44546a !important;
  font-size: 11px;
  font-weight: 700;
}

@media (max-width: 1180px) {
  .stage-topbar-v4 {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .stage-stat-group-v4 {
    justify-content: flex-start;
  }

  .stage-stat-group-v4 .stage-stat-card:first-child {
    padding-left: 0;
    border-left: 0;
  }
}

@media (max-width: 760px) {
  .stage-title-area {
    grid-template-columns: 1fr;
    gap: 9px;
  }

  .stage-title-area p {
    white-space: normal;
  }

  .stage-route-progress {
    overflow-x: auto;
    padding-bottom: 2px;
  }

  .stage-stat-group-v4 {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    width: 100%;
  }

  .stage-stat-group-v4 .stage-stat-card,
  .stage-stat-group-v4 .progress-stat-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
    padding: 3px 9px;
  }

  .stage-log-btn {
    grid-column: 1 / -1;
    width: 100%;
    margin: 8px 0 0;
  }
}

/* v9 anchored Agent detail: follows the card that opened it */
.agent-detail-floating-panel {
  right: auto !important;
  bottom: auto;
  z-index: 90;
  max-width: calc(100vw - 24px);
  padding: 0;
  overflow-x: visible;
  overflow-y: auto;
  border: var(--generator-card-border);
  border-radius: var(--radius-outer);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.12);
  transform-origin: left top;
}

.detail-anchor-caret {
  position: absolute;
  top: 26px;
  left: -7px;
  width: 13px;
  height: 13px;
  border-bottom: 1px solid #d9e0e8;
  border-left: 1px solid #d9e0e8;
  background: #fff;
  transform: rotate(45deg);
}

.detail-panel-title {
  position: sticky;
  top: 0;
  z-index: 2;
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) 10px;
  align-items: center;
  gap: 11px;
  min-height: 72px;
  margin: 0;
  padding: 13px 52px 13px 14px;
  border-bottom: 1px solid #e6eaf0;
  background: rgba(255, 255, 255, 0.97);
}

.detail-panel-title .focus-agent-icon {
  width: 40px;
  height: 40px;
  font-size: 17px;
}

.detail-title-copy {
  min-width: 0;
}

.detail-title-copy > span {
  display: block;
  margin-bottom: 2px;
  color: #7a8495;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.detail-title-copy h3 {
  margin: 0;
  overflow: hidden;
  color: #172033;
  font-size: 14px;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-title-copy p {
  margin: 2px 0 0;
  color: #667085;
  font-size: 10px;
  font-weight: 600;
}

.detail-close-btn {
  position: absolute;
  top: 15px;
  right: 14px;
  z-index: 3;
  width: 30px;
  height: 30px;
  border: 1px solid #e3e8ef;
  border-radius: 8px;
  background: #f7f8fa;
  color: #5d6879;
  font-size: 18px;
}

.selected-agent-detail-card {
  gap: 12px;
  padding: 14px;
}

.detail-current-task {
  padding: 12px 13px;
  border-color: #dde4ec;
  border-radius: 10px;
  background: #f8fafc;
}

.detail-current-task span {
  margin-bottom: 5px;
  font-size: 10px;
}

.detail-current-task strong {
  font-size: 12px;
  line-height: 1.45;
}

.detail-progress-line {
  height: 5px;
  margin-top: 10px;
}

.detail-current-task em {
  margin-top: 4px;
  font-size: 10px;
}

.detail-metrics-v3 {
  gap: 0;
  overflow: hidden;
  border: 1px solid #e1e6ed;
  border-radius: 10px;
  background: #fff;
}

.detail-metrics-v3 > div {
  padding: 10px 12px;
  border: 0;
  border-radius: 0;
  background: #fff;
}

.detail-metrics-v3 > div:nth-child(odd) {
  border-right: 1px solid #e8ecf1;
}

.detail-metrics-v3 > div:nth-child(-n + 2) {
  border-bottom: 1px solid #e8ecf1;
}

.detail-metrics-v3 dt {
  font-size: 9px;
}

.detail-metrics-v3 dd {
  margin-top: 3px;
  font-size: 11px;
}

.detail-io-grid {
  gap: 8px;
}

.detail-io-grid div {
  padding: 10px 12px;
  border-radius: 9px;
  background: #fff;
}

.detail-io-grid span {
  color: #476b9e;
  font-size: 9px;
}

.detail-io-grid p {
  margin-top: 4px;
  font-size: 10px;
}

.focus-metric-chips {
  gap: 5px;
}

.focus-metric-chips span {
  padding: 3px 7px;
  border-radius: 6px;
  font-size: 9px;
}

.detail-history-v3 {
  max-height: none;
  padding-top: 2px;
}

.detail-live-log-item {
  padding: 8px 0 8px 10px;
}

.detail-live-log-item span,
.detail-live-log-item em,
.detail-live-log-item p {
  font-size: 9px;
}

.detail-float-enter-from,
.detail-float-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

@media (max-width: 760px) {
  .agent-detail-floating-panel {
    right: auto !important;
  }

  .detail-anchor-caret {
    display: none;
  }
}

/* v10 contextual failure status: keep errors with the workflow they belong to */
.workflow-error-status {
  display: inline-flex;
  height: 30px;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid #f4b8b8;
  border-radius: 7px;
  color: #9f2f2f;
  background: #fff7f6;
  font: inherit;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease;
}

.workflow-error-status:hover {
  border-color: #e58c8c;
  background: #fff0ee;
}

.workflow-error-status > span {
  width: 7px;
  height: 7px;
  flex: 0 0 7px;
  border-radius: 50%;
  background: #d94a4a;
}

.workflow-error-status strong {
  font-size: 10px;
  font-weight: 750;
  white-space: nowrap;
}

.workflow-error-status em {
  color: #b45a5a;
  font-size: 9px;
  font-style: normal;
  white-space: nowrap;
}

.workflow-error-status svg {
  font-size: 11px;
}

.workflow-error-status:focus-visible {
  outline: 3px solid rgba(217, 74, 74, 0.2);
  outline-offset: 2px;
}

/* Custom Styles for Simplified Cards & Neon Breathing Glow */
.msg-queue-shell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.message-queue-item {
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  min-height: 0 !important;
  grid-template-columns: none !important;
}

.message-queue-item.is-head {
  opacity: 0.5;
}

.message-queue-item.is-head .live-message-only {
  font-size: 0.7rem !important;
  font-weight: var(--weight-bold) !important;
  -webkit-line-clamp: 1 !important;
}

/* Broadcast queue animation:
   - New message (tail): slides up from below + fades in
   - Old head leaving: slides up + fades out
   - Tail becoming head: smoothly transitions opacity/size via is-head class */
.msg-queue-enter-active {
  transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.msg-queue-leave-active {
  transition: opacity 0.28s ease, transform 0.28s cubic-bezier(0.4, 0, 1, 1);
  position: absolute;
  width: 100%;
}

.msg-queue-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.msg-queue-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.msg-queue-move {
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.message-only-layout {
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  height: 100% !important;
  grid-template-columns: none !important;
}

.live-message-only {
  margin: 0 !important;
  color: var(--color-text);
  font-size: 0.76rem !important;
  font-weight: var(--weight-bold) !important;
  line-height: 1.4 !important;
  display: -webkit-box;
  -webkit-line-clamp: 3 !important;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-family: var(--agent-body-font);
}

/* Pulsing Neon border glow animation for running cards */
@keyframes card-neon-glow {
  0% {
    border-color: rgba(59, 130, 246, 0.45);
    box-shadow: 0 0 10px rgba(59, 130, 246, 0.2), 0 10px 25px rgba(59, 130, 246, 0.1);
  }
  50% {
    border-color: rgba(59, 130, 246, 0.95);
    box-shadow: 0 0 20px rgba(59, 130, 246, 0.55), 0 10px 40px rgba(59, 130, 246, 0.25);
  }
  100% {
    border-color: rgba(59, 130, 246, 0.45);
    box-shadow: 0 0 10px rgba(59, 130, 246, 0.2), 0 10px 25px rgba(59, 130, 246, 0.1);
  }
}

.agent-station-card.status-running {
  animation: card-neon-glow 2s infinite ease-in-out !important;
  border-color: rgba(59, 130, 246, 0.8) !important;
}

/* Beautiful custom status-aligned dots */
.station-live-dot.waiting,
.station-live-dot.skipped {
  background: #94A3B8 !important;
  box-shadow: 0 0 0 4px rgba(148, 163, 184, 0.2) !important;
}

.station-live-dot.running {
  background: #3B82F6 !important;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.25) !important;
  animation: dot-pulse-glow 1.5s infinite ease-in-out !important;
}

.station-live-dot.success {
  background: #10B981 !important;
  box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.25) !important;
}

.station-live-dot.failed {
  background: #EF4444 !important;
  box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.25) !important;
}

@keyframes dot-pulse-glow {
  0% {
    transform: scale(0.9);
    opacity: 0.8;
  }
  50% {
    transform: scale(1.15);
    opacity: 1;
    box-shadow: 0 0 8px rgba(59, 130, 246, 0.6), 0 0 0 5px rgba(59, 130, 246, 0.3) !important;
  }
  100% {
    transform: scale(0.9);
    opacity: 0.8;
  }
}

/* 微调多智能体动画页面样式 - 保持原有布局，仅增强高级感 */
.agent-flow-canvas {
  background: 
    radial-gradient(circle at 50% 25%, rgba(99, 102, 241, 0.08), transparent 45%),
    radial-gradient(circle at 20% 75%, rgba(14, 165, 233, 0.05), transparent 35%),
    radial-gradient(circle at 80% 80%, rgba(16, 185, 129, 0.05), transparent 35%),
    #fafbfd !important;
  border-color: rgba(15, 23, 42, 0.05) !important;
}

.agent-station-card-v4 {
  background: rgba(255, 255, 255, 0.85) !important;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(15, 23, 42, 0.06) !important;
  box-shadow: 0 4px 18px rgba(15, 23, 42, 0.02) !important;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.agent-station-card-v4:hover,
.agent-station-card-v4.is-selected {
  transform: translateY(-4px) !important;
  border-color: var(--color-primary) !important;
  box-shadow: 0 12px 28px rgba(99, 102, 241, 0.08) !important;
}

/* 运行中的呼吸光晕 */
.agent-station-card.status-running {
  border-color: var(--color-primary) !important;
  animation: card-premium-glow 2.5s infinite ease-in-out !important;
}

@keyframes card-premium-glow {
  0%, 100% {
    box-shadow: 0 4px 18px rgba(99, 102, 241, 0.03), 0 0 0 1px rgba(99, 102, 241, 0.1);
    border-color: rgba(99, 102, 241, 0.3) !important;
  }
  50% {
    box-shadow: 0 12px 30px rgba(99, 102, 241, 0.08), 0 0 0 2px rgba(99, 102, 241, 0.2);
    border-color: rgba(99, 102, 241, 0.7) !important;
  }
}

/* 成功状态 */
.agent-station-card.status-success,
.agent-station-card.has-artifact {
  background: rgba(255, 255, 255, 0.95) !important;
  border-color: rgba(16, 185, 129, 0.24) !important;
  box-shadow: 0 4px 18px rgba(16, 185, 129, 0.02) !important;
}

/* 连接线微妙光晕 */
.agent-link-path {
  stroke-width: 2;
  transition: all 0.3s ease;
}

.agent-link-path.status-running {
  stroke-width: 2.5;
  stroke: var(--color-primary);
  opacity: 0.8;
}

.agent-link-path.status-success {
  stroke: #10B981 !important;
  opacity: 0.6;
}
</style>
