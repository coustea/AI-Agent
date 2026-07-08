<template>
  <!-- 生成进度主视图：顶部摘要 + 智能体流程画布 + 浮层详情 + 产物区 + 日志抽屉 -->
  <div class="phase-view generating-view workflow-stage-page workflow-stage-page-v4">
    <!-- 顶部进度摘要栏：展示整体进度、运行中智能体数量、已交付产物数与路由步骤 -->
    <!-- 内联 Summary：工作流顶部状态栏 -->
    <header class="stage-topbar stage-topbar-v4">
      <div class="stage-title-area">
        <!-- 工作流标题与当前提示文案 -->
        <div class="stage-title-copy">
          <h2>资源生成工作流</h2>
          <p>{{ dagHeroMessage }}</p>
        </div>
        <!-- 生成阶段步骤条：遍历步骤并渲染连接线 -->
        <div class="stage-route-progress" aria-label="生成阶段">
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

      <!-- 右侧统计区：进度、活跃数、已交付数与日志入口 -->
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
        <!-- 点击打开运行日志抽屉 -->
        <button class="btn btn-outline rounded-full stage-log-btn" type="button" @click="workflowLogDrawerVisible = true">
          运行日志
          <ArrowRight class="h-4 w-4" />
        </button>
      </div>
    </header>
    <!-- 主体区域：包含调度工作台面板与详情浮层 -->
    <main class="agent-stage-shell-v4">
      <!-- 调度工作台面板：标题/状态/控制按钮 + 智能体流程画布 -->
      <section class="dispatch-workbench-panel dispatch-workbench-panel-v4">
        <!-- 面板头部：执行流程标题、错误状态入口与日志按钮 -->
        <div class="workbench-header workbench-header-v4">
          <div>
            <span class="panel-eyebrow">执行流程</span>
            <h3>资源生成进度</h3>
            <p>教学计划完成后生成基础资源，再生成教学课件，最后完成资源整合。</p>
          </div>
          <div class="workbench-actions">
            <!-- 生成出错时展示中断状态按钮，点击打开日志抽屉 -->
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
            <!-- 正常状态下展示 SSE 实时流追踪标签 -->
            <span v-else class="control-pill active"><span class="live-dot"></span> SSE 实时流追踪</span>
            <!-- 教学计划生成状态标签 -->
            <span class="control-pill muted">计划 {{ planReady ? '已生成' : '生成中' }}</span>
            <button class="btn btn-outline btn-sm rounded-full" @click="workflowLogDrawerVisible = true">查看日志</button>
          </div>
        </div>

        <!-- 智能体流程画布：包含计划核心、连接线 SVG、基础资源工位行、聚合工位行、整合卡片 -->
        <div ref="flowCanvasRef" class="agent-flow-canvas agent-flow-canvas-v4">
          <!-- 装饰性背景：网格与三条轨道光晕 -->
          <div class="flow-grid-bg"></div>
          <div class="flow-orbit orbit-one"></div>
          <div class="flow-orbit orbit-two"></div>
          <div class="flow-orbit orbit-three"></div>

          <!-- 核心区：教学计划智能体卡片 -->
          <div class="flow-core-stack flow-core-stack-v4">
            <!-- Planning Agent 卡片，点击打开详情浮层 -->
            <article
              ref="planningNodeRef"
              class="agent-station-card agent-station-card-v4 planning-core"
              :class="['status-' + getStageNode('planning').status, { 'is-selected': selectedDagNodeId === 'planning' }]"
              @click="handleAgentClick('planning')"
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
              <!-- 内联 AgentMessageTicker：planning 节点 -->
              <div class="station-live-log" :class="[`is-${getStageNode('planning').status}`]">
                <div v-if="planningTicker.visibleMessages.value.length" class="live-message-queue">
                  <TransitionGroup name="live-message" tag="div" class="live-message-list">
                    <div
                        v-for="(item, index) in planningTicker.visibleMessages.value"
                        :key="item.id"
                        class="live-message-row"
                        :class="{
                        'is-latest': index === planningTicker.visibleMessages.value.length - 1,
                        'is-fresh': planningTicker.freshMessageId.value === item.id
                      }"
                    >
                      <span class="station-live-dot" :class="getStageNode('planning').status"></span>
                      <p class="live-message-only">{{ item.text }}</p>
                    </div>
                  </TransitionGroup>
                </div>
                <div v-else class="live-message-row fallback-row">
                  <span class="station-live-dot" :class="getStageNode('planning').status"></span>
                  <p class="live-message-only">{{ planningTicker.fallbackMessage.value }}</p>
                </div>
              </div>
              <div class="station-footer">
                <span>{{ getNodeStageLabel(getStageNode('planning')) }}</span>
              </div>
            </article>
          </div>

          <!-- SVG 连接线层：根据各工位卡片实测坐标绘制贝塞尔连线与端点圆 -->
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

          <!-- 基础资源并行工位行：渲染各 Worker 智能体卡片 -->
          <transition-group name="agent-station" tag="div" class="agent-station-row agent-station-row-v4 base-agent-row">
            <article
              v-for="node in parallelPoolNodes"
              :key="node.id"
              class="agent-station-card agent-station-card-v4"
              :ref="el => setStationCardRef(node.id, el)"
              :class="['status-' + node.status, { 'is-selected': selectedDagNodeId === node.id, 'has-artifact': hasGeneratedResource(node.id) }]"
              @click="handleAgentClick(node.id)"
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
              <!-- 内联 AgentMessageTicker：并行工位节点 -->
              <div class="station-live-log" :class="[`is-${node.status}`]">
                <div v-if="getTickerState(node.id).visibleMessages.value.length" class="live-message-queue">
                  <TransitionGroup name="live-message" tag="div" class="live-message-list">
                    <div
                        v-for="(item, index) in getTickerState(node.id).visibleMessages.value"
                        :key="item.id"
                        class="live-message-row"
                        :class="{
                        'is-latest': index === getTickerState(node.id).visibleMessages.value.length - 1,
                        'is-fresh': getTickerState(node.id).freshMessageId.value === item.id
                      }"
                    >
                      <span class="station-live-dot" :class="node.status"></span>
                      <p class="live-message-only">{{ item.text }}</p>
                    </div>
                  </TransitionGroup>
                </div>
                <div v-else class="live-message-row fallback-row">
                  <span class="station-live-dot" :class="node.status"></span>
                  <p class="live-message-only">{{ getTickerState(node.id).fallbackMessage.value }}</p>
                </div>
              </div>
              <div class="station-footer">
                <span>{{ getNodeStageLabel(node) }}</span>
              </div>
            </article>
          </transition-group>

          <!-- 聚合阶段连接器装饰（仅在存在 PPT/动画 智能体时显示） -->
          <div v-if="showAggregationStage" class="dual-flow-connector" aria-hidden="true">
            <span></span><i></i><i></i>
          </div>

          <!-- 聚合工位行：渲染 PPT / 动画 智能体卡片 -->
          <div v-if="showAggregationStage" class="agent-station-row agent-station-row-v4 aggregation-agent-row">
            <article
              v-for="node in aggregationNodes"
              :key="node.id"
              class="agent-station-card agent-station-card-v4"
              :class="['status-' + node.status, { 'is-selected': selectedDagNodeId === node.id, 'has-artifact': hasGeneratedResource(node.id) }]"
              @click="handleAgentClick(node.id)"
            >
              <div class="station-header">
                <div class="station-icon">
                  <component :is="getWorkflowIcon(node.id)" class='w-4 h-4' />
                </div>
                <div>
                  <strong>{{ getWorkflowTitle(node.id) }}</strong>
                  <span>{{ node.id === CARTOON_AGENT_ID ? 'Cartoon Agent' : 'PPT Agent' }}</span>
                </div>
                <em>{{ getNodeStatusLabel(node) }}</em>
              </div>
              <!-- 内联 AgentMessageTicker：聚合工位节点 -->
              <div class="station-live-log" :class="[`is-${node.status}`]">
                <div v-if="getTickerState(node.id).visibleMessages.value.length" class="live-message-queue">
                  <TransitionGroup name="live-message" tag="div" class="live-message-list">
                    <div
                        v-for="(item, index) in getTickerState(node.id).visibleMessages.value"
                        :key="item.id"
                        class="live-message-row"
                        :class="{
                        'is-latest': index === getTickerState(node.id).visibleMessages.value.length - 1,
                        'is-fresh': getTickerState(node.id).freshMessageId.value === item.id
                      }"
                    >
                      <span class="station-live-dot" :class="node.status"></span>
                      <p class="live-message-only">{{ item.text }}</p>
                    </div>
                  </TransitionGroup>
                </div>
                <div v-else class="live-message-row fallback-row">
                  <span class="station-live-dot" :class="node.status"></span>
                  <p class="live-message-only">{{ getTickerState(node.id).fallbackMessage.value }}</p>
                </div>
              </div>
              <div class="station-footer">
                <span>{{ getNodeStageLabel(node) }}</span>
              </div>
            </article>

          </div>

          <!-- 合并连接器：将聚合结果汇入资源整合卡片 -->
          <div v-if="showAggregationStage" class="dual-flow-connector is-merge" aria-hidden="true">
            <span></span><i></i><i></i>
          </div>

          <!-- 资源整合（Bundle Agent）卡片：最终产物打包交付节点 -->
          <div class="bundle-stage-shell">
            <article
              class="review-station-card review-station-card-v4 bundle-stage-card"
              :class="['status-' + bundleNode.status, { 'is-selected': selectedDagNodeId === bundleNode.id }]"
              @click="handleAgentClick(bundleNode.id)"
            >
              <div class="review-icon">
                <component :is="getWorkflowIcon(bundleNode.id)"  class='w-4 h-4' />
              </div>
              <div>
                <strong>资源整合</strong>
                <span>{{ getNodeStageLabel(bundleNode) }}</span>
              </div>
              <em>{{ getNodeStatusLabel(bundleNode) }}</em>
            </article>
          </div>
        </div>
      </section>

      <!-- 详情浮层：传送至 body，点击工位卡片时展示选中智能体的运行详情 -->
      <Teleport to="body">
        <transition name="detail-fade">
          <!-- 遮罩层，点击关闭详情 -->
          <div
            v-if="detailPanelVisible && selectedDagNode"
            class="detail-overlay"
            @click="closeAgentDetail"
          >
            <!-- 详情面板容器，按智能体类型应用主题色 -->
            <aside
              class="agent-detail-floating-panel"
              :class="[getResourceToneClass(selectedDagNode.id)]"
              role="dialog"
              aria-label="Agent 运行详情"
              @click.stop
            >
              <!-- 详情面板头部：图标、标题、状态点、关闭按钮 -->
              <div class="detail-panel-title">
                <div class="focus-agent-icon">
                  <component :is="getWorkflowIcon(selectedDagNode.id)" class='w-4 h-4' />
                </div>
                <div class="detail-title-copy">
                  <span>运行详情</span>
                  <h3>{{ getWorkflowTitle(selectedDagNode.id) }}</h3>
                  <p>{{ getNodeStageLabel(selectedDagNode) }}</p>
                </div>
                <span class="detail-status-dot" :class="`status-${selectedDagNode.status}`"></span>
                <button class="detail-close-btn" type="button" aria-label="关闭 Agent 详情" @click="closeAgentDetail">×</button>
              </div>

              <!-- 详情主体卡片：当前任务、指标网格、输入输出、指标标签 -->
              <div class="selected-agent-detail-card">
                <!-- 当前任务区：任务描述 -->
                <div class="detail-current-task">
                  <span>当前任务</span>
                  <strong>{{ getNodeDisplayMessage(selectedDagNode) }}</strong>
                </div>

                <!-- 关键指标网格：阶段、耗时、更新时间、成果状态 -->
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

                <!-- 输入输出摘要网格 -->
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

                <!-- 指标标签条：展示 metrics 中的前四项键值 -->
                <div class="focus-metric-chips" v-if="getMetricChips(selectedDagNode).length">
                  <span v-for="chip in getMetricChips(selectedDagNode)" :key="chip">{{ chip }}</span>
                </div>
              </div>
            </aside>
          </div>
        </transition>
      </Teleport>
    </main>

    <!-- 内联 Outputs：已交付资源停靠区 -->
    <section class="output-dock-section output-dock-section-v4">
      <div class="output-dock-heading">
        <div>
          <span>READY RESOURCES</span>
          <strong>已交付资源</strong>
        </div>
        <p>这里仅展示已经完成并可预览的资源，不改变主流水线的阅读顺序。</p>
      </div>
      <div class="output-dock-list">
        <button
          v-for="agentId in visibleOutputAgentIds"
          :key="agentId"
          type="button"
          class="output-dock-item"
          :class="[
            isOutputReady(agentId) ? 'ready' : isOutputRunning(agentId) ? 'running' : 'waiting',
            { 'just-arrived': latestArtifactAgentId === agentId }
          ]"
          :disabled="!isOutputReady(agentId)"
          @click="isOutputReady(agentId) && openResourcePreview(agentId)"
        >
          <span class="output-icon"><component :is="getOutputIcon(agentId)" class="h-4 w-4" /></span>
          <span class="output-copy">
            <strong>{{ getArtifactLabel(agentId) }}</strong>
            <small>{{ getAgentOutputFormat(agentId) }}</small>
          </span>
          <em class="output-status">
            <template v-if="isOutputReady(agentId)">刚刚完成 ▶</template>
            <template v-else-if="isOutputRunning(agentId)">执行中<span class="loading-dots">...</span></template>
            <template v-else>就绪待命</template>
          </em>
        </button>
      </div>
    </section>

    <!-- 内联 Logs：工作流日志抽屉 -->
    <Teleport to="body">
      <transition name="slide-over">
        <div v-if="workflowLogDrawerVisible" class="custom-modal-overlay" @click="workflowLogDrawerVisible = false">
          <aside class="log-drawer" aria-label="实时调度日志" @click.stop>
            <header>
              <h3>实时调度日志</h3>
              <button type="button" aria-label="关闭日志" @click="workflowLogDrawerVisible = false">×</button>
            </header>
            <div class="drawer-log-list">
              <div
                v-for="item in workflowLogItems"
                :key="item.id"
                class="drawer-log-item"
                :class="`is-${item.status}`"
              >
                <span class="drawer-log-dot"></span>
                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.message }}</p>
                </div>
              </div>
              <p v-if="!workflowLogItems.length" class="empty-log">等待智能体上报运行日志</p>
            </div>
          </aside>
        </div>
      </transition>
    </Teleport>

    <!-- 资源预览弹窗：点击产物时打开 -->
    <PreviewDialog
      v-model:activeAgent="activePreviewAgent"
      :data="previewData"
      :resource="previewResource"
    />
  </div>
</template>

<script setup lang="ts">
// 引入 Vue 响应式原语、计算属性、生命周期钩子与组件类型
import { ref, computed, onScopeDispose, watch, type Component } from 'vue'
// 引入 Phosphor 图标集，为各智能体匹配视觉图标
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
  PhShareNetwork as Share,
  // 内联 Outputs 所需图标
  PhChartBar as SlidesIcon,
  PhCpu as CodeIcon,
  PhFileText as ArticleIcon,
  PhFilmStrip as VideoIcon,
  PhNotePencil as QuizIcon,
  PhBookOpen as ReadingIcon,
  PhShareNetwork as MindMapIcon,
} from '@phosphor-icons/vue'
// 资源智能体 ID 联合类型
import type { ResourceAgentId } from '@/features/resource/model/resource'
// 预览弹窗
import PreviewDialog from '@/shared/content/PreviewDialog.vue'
// 共享的内容类型标签工具（内联 Outputs 所需）
import { getArtifactLabel } from '@/shared/content/kind'
// 智能体工位连线坐标计算组合式函数
import { useFlow } from '../composables/useFlow'
// 引入智能体常量、显示信息与 DAG 节点状态类型
import {
  COORDINATOR_AGENT_ID,
  CARTOON_AGENT_ID,
  PPT_AGENT_ID,
  BUNDLE_AGENT_ID,
  SYSTEM_AGENT_IDS,
  AGENT_DISPLAY,
  getAgentOutputFormat,
  getResourceToneClass,
  type DagNodeState,
} from '../model/catalog'

// 已生成资源条目类型（含可选生成时间与排序字段）
type GeneratedResourceItem = Record<string, any> & {
  generatedAt?: string
  displayOrder?: number
}

// 组件 props：由父组件 ResourceGenerator 传入的 DAG 状态与生成数据
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

// 事件输出：选中节点与打开资源预览
const emit = defineEmits<{
  selectNode: [id: string]
  openResource: [type: string]
}>()

// 日志抽屉显隐状态
const workflowLogDrawerVisible = ref(false)
// 详情浮层显隐状态
const detailPanelVisible = ref(false)

// 预览弹窗状态（点击产物区资源时打开预览）
const activePreviewAgent = ref<string | null>(null)
const previewData        = ref<any>(null)
const previewResource    = ref<any>(null)

// 点击产物时打开预览：数据已加载则直接展示，否则委托父组件从 API 获取
function openResourcePreview(type: string) {
  const resource = props.generatedResources.find((r: any) => r.type === type)
  if (!resource) {
    // 数据尚未加载，委托父组件从 API 获取后打开预览
    emit('openResource', type)
    return
  }
  if (resource.content) {
    activePreviewAgent.value = resource.type || resource.agent_type
    previewData.value        = resource.content
    previewResource.value    = resource
  } else {
    // 资源内容尚未加载，委托父组件从后端获取后打开预览
    emit('openResource', type)
  }
}

// 智能体 ID 到 Phosphor 图标组件的映射表
const workflowIconMap: Record<string, Component> = {
  planning: Aim,
  coordinator: Connection,
  content: Document,
  mindmap: Share,
  quiz: EditPen,
  code: Cpu,
  reading: Reading,
  ppt: DataBoard,
  cartoon: DataBoard,
  bundle: Box,
}

// 智能体 ID 到中文显示标题的映射表
const workflowTitleMap: Record<string, string> = {
  planning: '教学计划',
  coordinator: '结果汇总',
  content: '课程讲解',
  mindmap: '思维导图',
  quiz: '练习题',
  code: '代码示例',
  reading: '拓展阅读',
  ppt: '教学课件',
  cartoon: '动画讲解',
  bundle: '资源包交付',
}

// 根据智能体 ID 获取对应图标，缺省返回文档图标
function getWorkflowIcon(id: string) {
  return workflowIconMap[id] || Document
}

// 根据智能体 ID 获取中文标题，缺省返回 AGENT_DISPLAY 标签或原始 ID
function getWorkflowTitle(id: string) {
  return workflowTitleMap[id] || AGENT_DISPLAY[id]?.label || id
}

// 点击工位卡片：打开详情浮层并通知父组件选中节点
function handleAgentClick(id: string) {
  detailPanelVisible.value = true
  emit('selectNode', id)
}

// 关闭详情浮层
function closeAgentDetail() {
  detailPanelVisible.value = false
}

// 基础资源智能体 ID 列表（排除 PPT 与动画等聚合阶段智能体）
const baseGenerationAgentIds = computed(() => {
  return props.dagSelectedAgentIds.filter(id => ![PPT_AGENT_ID, CARTOON_AGENT_ID].includes(id))
})

// 基础资源并行工位的 DAG 节点状态数组
const parallelPoolNodes = computed(() => {
  return baseGenerationAgentIds.value.map(agentId => getStageNode(agentId))
})

// 连线组合式函数：基于工位卡片 DOM 实测坐标计算 SVG 连线路径
const {
  canvasSize: linkCanvasSize,
  links: agentLinkPaths,
  setCardRef: setStationCardRef,
} = useFlow(parallelPoolNodes)



// 尾部聚合阶段节点（PPT / 动画智能体），仅当选中时纳入
const trailingStageNodes = computed(() => {
  const nodes: DagNodeState[] = []
  if (props.dagSelectedAgentIds.includes(PPT_AGENT_ID as ResourceAgentId)) {
    nodes.push(getStageNode(PPT_AGENT_ID))
  }
  if (props.dagSelectedAgentIds.includes(CARTOON_AGENT_ID as ResourceAgentId)) {
    nodes.push(getStageNode(CARTOON_AGENT_ID))
  }
  return nodes
})

// 聚合阶段节点（别名，指向尾部阶段）
const aggregationNodes = computed(() => trailingStageNodes.value)

// 是否展示聚合阶段（存在 PPT/动画 智能体时为 true）
const showAggregationStage = computed(() => aggregationNodes.value.length > 0)

// 资源整合节点状态
const bundleNode = computed(() => getStageNode(BUNDLE_AGENT_ID))

// 当前选中的 DAG 节点（用于详情浮层展示）
const selectedDagNode = computed(() => {
  if (!props.selectedDagNodeId) return null
  if (props.selectedDagNodeId === COORDINATOR_AGENT_ID) return getStageNode(COORDINATOR_AGENT_ID)
  return props.dagNodeStates[props.selectedDagNodeId] || getStageNode(props.selectedDagNodeId)
})

// 当前运行中的智能体数量（排除协调器）
const runningAgentCount = computed(() => {
  return props.visibleWorkflowNodes.filter(node => node.id !== COORDINATOR_AGENT_ID && node.status === 'running').length
})

// 顶部摘要文案：优先展示运行中消息，其次全局完成/最新工作流消息
const dagHeroMessage = computed(() => {
  const running = Object.values(props.dagNodeStates).find(n => n.id !== COORDINATOR_AGENT_ID && n.status === 'running')
  if (running) return running.currentMessage || `${running.label}处理中...`
  if (getStageNode(COORDINATOR_AGENT_ID).status === 'running') return '正在准备教学课件...'
  const allDone = Object.values(props.dagNodeStates).every(n => n.status === 'success')
  if (allDone) return '所有资源生成完成'
  return props.latestWorkflowMessage || '多智能体协同生成中'
})

// 路由步骤数组：教学计划 → 基础资源 → 教学课件 → 资源整合四阶段进度状态
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

// 产物输出区需要展示的智能体 ID 列表
const visibleOutputAgentIds = computed(() => {
  return props.dagSelectedAgentIds
})

// 工作流日志条目汇总：全局错误 + 各节点最近事件/步骤历史
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

    // 优先展示最近 4 条结构化事件日志
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

    // 无结构化日志时回退到步骤历史，取最近 3 条
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

// 将事件阶段英文名翻译为简短中文标签
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

// 安全获取 DAG 节点状态：不存在时返回带默认值的占位节点
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

// 判断某智能体是否已生成资源（资源列表或节点成功状态）
function hasGeneratedResource(type: string) {
  const isReadyInResources = props.generatedResources.some(resource => resource.type === type)
  const isReadyInDag = props.dagNodeStates[type]?.status === 'success'
  return isReadyInResources || isReadyInDag
}

// 节点状态标签（受阻/跳过/就绪/执行中/就绪待命）
function getNodeStatusLabel(node: DagNodeState) {
  if (node.status === 'failed') return '受阻'
  if (node.status === 'skipped') return '已跳过'
  if (node.status === 'success') return '就绪'
  if (node.status === 'running') return '执行中'
  return '就绪待命'
}

// 节点阶段标签：根据节点类型与运行阶段给出中文进度描述
function getNodeStageLabel(node: DagNodeState) {
  if (node.status === 'success') return node.id === BUNDLE_AGENT_ID ? '整合完成' : '已完成'
  if (node.status === 'failed') return '协作中断'
  if (node.status === 'skipped') return '已跳过'
  if (node.status === 'running') {
    if (node.id === 'planning') return '计划生成中'
    if (node.id === COORDINATOR_AGENT_ID) return '结果汇总中'
    if ([PPT_AGENT_ID, CARTOON_AGENT_ID].includes(node.id)) return '生成中'
    if (node.phase === 'llm_generating') return '核心推演中'
    if (node.phase === 'research' || node.phase === 'research_delegate') return '资料研究中'
    if (node.phase === 'validating') return '一致性校验中'
    if (node.phase === 'artifact_saved') return '资源已保存'
    if (node.phase === 'bundling') return '资源整合中'
    return '工位执行中'
  }
  if (node.id === BUNDLE_AGENT_ID) return '等待基础资源与课件'
  if ([PPT_AGENT_ID, CARTOON_AGENT_ID].includes(node.id)) return '等待基础资源'
  return '等待上游协同'
}

// 节点阶段名称（详情面板用）：阶段英文 key 映射为中文短标签
function getNodePhaseLabel(node: DagNodeState) {
  const phaseMap: Record<string, string> = {
    planning_blueprint: '蓝图构建',
    coverage_gap_warning: '覆盖校验',
    llm_generating: '深度推演',
    validating: '一致性校验',
    ppt_generating: 'PPT 聚合',
    ppt_waiting_sources: '等待讲义要义',
    cartoon_planning: '动画分镜',
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
  if ([PPT_AGENT_ID, CARTOON_AGENT_ID].includes(node.id) && node.status === 'running') return '聚合生成'
  if (node.id === BUNDLE_AGENT_ID && node.status === 'running') return '打包交付'
  if (node.status === 'waiting') return '等待上游'
  if (node.status === 'success') return '已完成'
  if (node.status === 'failed') return '受阻'
  return '工位状态'
}

// 节点展示消息：只展示后端发送的消息，无消息时返回空
function getNodeDisplayMessage(node: DagNodeState) {
  if (node.status === 'failed') return node.currentMessage || '执行失败'
  if (node.currentMessage) return node.currentMessage
  return ''
}

// 节点成果状态描述：按智能体类型返回产物就绪/生成中/等待状态文案
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
  if (node.id === CARTOON_AGENT_ID) {
    return hasGeneratedResource(node.id) ? '动画视频已交付' : '等待基础资源后生成'
  }
  return hasGeneratedResource(node.id) ? '基础资源已交付' : '工位响应中'
}

// 节点输入摘要：按智能体类型描述上游输入要素
function getNodeInputSummary(node: DagNodeState) {
  if (node.id === 'planning') return '学习需求 / 学习场景 / 用户画像 / 已选 Agent'
  if (node.id === COORDINATOR_AGENT_ID) return '教学计划 / 基础资源执行结果 / 当前执行快照'
  if (node.id === BUNDLE_AGENT_ID) return '基础资源结果 / 聚合资源结果 / 已持久化产物'
  if (node.id === PPT_AGENT_ID) return '教学计划 / 基础资源 handoff / 上游已完成内容'
  if (node.id === CARTOON_AGENT_ID) return '学习需求 / 基础资源 handoff / 动画个性化参数'
  return '学习需求 / 用户画像 / 教学计划'
}

// 节点输出摘要：按智能体类型描述产物格式与生成状态
function getNodeOutputSummary(node: DagNodeState) {
  if (node.id === 'planning') return '教学计划 / 大纲 / Agent 分工'
  if (node.id === COORDINATOR_AGENT_ID) return '成功失败统计 / 覆盖情况 / 基础资源 handoff'
  if (node.id === BUNDLE_AGENT_ID) return node.status === 'success' ? '最终资源包 / 可预览结果' : '等待汇总后生成资源包'
  if (hasGeneratedResource(node.id)) return getAgentOutputFormat(node.id)
  if (node.id === PPT_AGENT_ID) return '聚合资源生成中 / 等待中'
  if (node.id === CARTOON_AGENT_ID) return 'MP4 动画视频生成中 / 等待中'
  return '基础资源生成中 / 等待中'
}

// 将毫秒耗时格式化为人类可读的 "Xs" / "Xm Ys" 文本
function formatElapsed(ms?: number | null) {
  if (!ms || ms < 0) return '未开始'
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${minutes}m ${rest}s`
}

// 节点更新时间标签：刚刚/X秒前/X分钟前
function getNodeTimeLabel(node: DagNodeState) {
  if (node.status === 'waiting') return '等待上游'
  if (!node.lastUpdatedAt) return formatElapsed(node.elapsedMs)
  const seconds = Math.max(0, Math.floor((Date.now() - node.lastUpdatedAt) / 1000))
  if (seconds < 3) return '刚刚更新'
  if (seconds < 60) return `${seconds}s 前更新`
  return `${Math.floor(seconds / 60)}m 前更新`
}

// 提取节点 metrics 中的前四项指标，格式化为 "key: value" 标签数组
function getMetricChips(node: DagNodeState) {
  const metrics = node.metrics || {}
  return Object.entries(metrics)
    .filter(([, value]) => value !== null && value !== undefined && value !== '')
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${String(value)}`)
}

// ==================== 内联 AgentMessageTicker 逻辑 ====================
// 消息条目内部结构：唯一 id、去重 key、展示文本
type LiveMessage = {
  id: string
  key: string
  text: string
}

// 同时最多展示的消息条数（超出滚动淘汰旧消息）
const MAX_VISIBLE_MESSAGES = 2
// 每条消息至少展示多久
const MIN_DISPLAY_MS = 1400
// 新消息高亮动画持续时间
const FRESH_ANIMATION_MS = 420

// 为每个节点创建独立的 Ticker 响应式状态
function useTickerState(nodeGetter: () => DagNodeState) {
  const visibleMessages = ref<LiveMessage[]>([])
  const freshMessageId = ref<string | null>(null)

  let pendingQueue: LiveMessage[] = []
  let consumedKeys = new Set<string>()
  let messageSeq = 0
  let lastDisplayAt = 0
  let drainTimer: ReturnType<typeof setTimeout> | null = null
  let freshTimer: ReturnType<typeof setTimeout> | null = null

  // 兜底消息：优先用后端消息，否则按状态给出简短标签
  const fallbackMessage = computed(() => {
    const node = nodeGetter()
    if (node.currentMessage) return node.currentMessage
    const statusLabels: Record<string, string> = {
      waiting: '等待中',
      running: '运行中',
      success: '已完成',
      failed: '执行失败',
      skipped: '已跳过',
    }
    return statusLabels[node.status] || ''
  })

  function resetMessages() {
    clearDrainTimer()
    clearFreshTimer()
    visibleMessages.value = []
    pendingQueue = []
    consumedKeys = new Set<string>()
    freshMessageId.value = null
    lastDisplayAt = 0
  }

  function hydrateInitialMessages() {
    const sources = collectAllSources()
    const latest = sources.slice(-MAX_VISIBLE_MESSAGES)
    visibleMessages.value = latest.map(source => {
      consumedKeys.add(source.key)
      return createMessage(source.text, source.key)
    })
    lastDisplayAt = Date.now()
  }

  function enqueueNewBackendMessages() {
    const sources = collectAllSources()
    for (const source of sources) {
      if (!source.text) continue
      if (consumedKeys.has(source.key)) continue
      if (pendingQueue.some(item => item.key === source.key)) continue
      pendingQueue.push(createMessage(source.text, source.key))
    }
    drainQueue()
  }

  function collectAllSources(): Array<{ key: string; text: string }> {
    const node = nodeGetter()
    const result: Array<{ key: string; text: string }> = []

    const logs = node.eventLogs || []
    logs.forEach((log: any, index: number) => {
      const text = String(log?.message || '').trim()
      if (!text) return
      result.push({ key: buildLogKey(log, index), text })
    })

    const history = node.stepHistory || []
    history.forEach((message, index) => {
      const text = String(message || '').trim()
      if (!text) return
      result.push({ key: `history:${node.id}:${index}:${text}`, text })
    })

    const current = node.currentMessage?.trim()
    if (current) {
      result.push({ key: `current:${node.id}:${node.status}:${current}`, text: current })
    }

    return dedupeSources(result)
  }

  function dedupeSources(sources: Array<{ key: string; text: string }>): Array<{ key: string; text: string }> {
    const result: Array<{ key: string; text: string }> = []
    const seenKeys = new Set<string>()
    for (const source of sources) {
      if (!source.text) continue
      if (seenKeys.has(source.key)) continue
      const last = result[result.length - 1]
      if (last?.text === source.text) continue
      seenKeys.add(source.key)
      result.push(source)
    }
    return result
  }

  function drainQueue() {
    if (!pendingQueue.length) return
    const now = Date.now()
    const elapsed = now - lastDisplayAt
    if (lastDisplayAt > 0 && elapsed < MIN_DISPLAY_MS) {
      scheduleDrain(MIN_DISPLAY_MS - elapsed)
      return
    }
    const next = pendingQueue.shift()
    if (!next) return
    consumedKeys.add(next.key)
    visibleMessages.value = [...visibleMessages.value, next].slice(-MAX_VISIBLE_MESSAGES)
    freshMessageId.value = next.id
    lastDisplayAt = Date.now()
    resetFreshTimer()
    if (pendingQueue.length) scheduleDrain(MIN_DISPLAY_MS)
  }

  function scheduleDrain(delay: number) {
    if (drainTimer) return
    drainTimer = setTimeout(() => { drainTimer = null; drainQueue() }, Math.max(0, delay))
  }

  function createMessage(text: string, key: string): LiveMessage {
    messageSeq += 1
    return { id: `${nodeGetter().id}-${Date.now()}-${messageSeq}`, key, text }
  }

  function buildLogKey(log: any, index: number) {
    const node = nodeGetter()
    const sequence = log?.sequence ?? log?.seq ?? log?.id
    const timestamp = log?.timestamp ?? log?.createdAt ?? log?.created_at
    const phase = log?.phase ?? ''
    const status = log?.status ?? ''
    const message = String(log?.message || '').trim()
    if (sequence !== undefined && sequence !== null && sequence !== '') return `log:${node.id}:${sequence}`
    if (timestamp) return `log:${node.id}:${timestamp}:${phase}:${status}:${message}`
    return `log:${node.id}:${index}:${phase}:${status}:${message}`
  }

  function resetFreshTimer() {
    clearFreshTimer()
    freshTimer = setTimeout(() => { freshMessageId.value = null; freshTimer = null }, FRESH_ANIMATION_MS)
  }

  function clearDrainTimer() {
    if (drainTimer) { clearTimeout(drainTimer); drainTimer = null }
  }

  function clearFreshTimer() {
    if (freshTimer) { clearTimeout(freshTimer); freshTimer = null }
  }

  // 切换节点时重置消息状态并填充初始消息
  watch(() => nodeGetter().id, () => { resetMessages(); hydrateInitialMessages() }, { immediate: true })

  // 监听后端事件日志/步骤历史/当前消息的变化
  watch(
    () => [nodeGetter().eventLogs?.length || 0, nodeGetter().stepHistory?.length || 0, nodeGetter().currentMessage, nodeGetter().lastUpdatedAt || 0],
    () => { enqueueNewBackendMessages() },
    { deep: false }
  )

  onScopeDispose(() => { clearDrainTimer(); clearFreshTimer() })

  return { visibleMessages, freshMessageId, fallbackMessage }
}

// 为 planning 节点创建 Ticker 状态
const planningTicker = useTickerState(() => getStageNode('planning'))

// 用一个普通 Map 来维护各节点的 Ticker 状态（响应性由 useTickerState 内部管理）
const tickerStateMap = new Map<string, ReturnType<typeof useTickerState>>()

// 获取或创建某节点的 Ticker 状态
function getTickerState(nodeId: string): ReturnType<typeof useTickerState> {
  let state = tickerStateMap.get(nodeId)
  if (!state) {
    state = useTickerState(() => getStageNode(nodeId))
    tickerStateMap.set(nodeId, state)
  }
  return state
}

// ==================== 内联 Outputs 逻辑 ====================
// 智能体 id 到图标组件的映射表（Outputs 用）
const outputIcons: Record<string, Component> = {
  content: ArticleIcon,
  mindmap: MindMapIcon,
  quiz: QuizIcon,
  code: CodeIcon,
  reading: ReadingIcon,
  ppt: SlidesIcon,
  cartoon: VideoIcon,
}

// 根据智能体 id 返回对应图标，缺省回退到文章图标
function getOutputIcon(id: string) {
  return outputIcons[id] || ArticleIcon
}

// 判断某智能体产出是否已就绪：已生成或节点状态为成功
function isOutputReady(id: string) {
  return props.generatedResources.some((r: any) => r.type === id) || props.dagNodeStates[id]?.status === 'success'
}

// 判断某智能体是否正在执行中
function isOutputRunning(id: string) {
  return props.dagNodeStates[id]?.status === 'running'
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

/* Legacy floating panel styles removed — modernized styles are defined below */

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

.aggregation-agent-row .agent-station-card-v4:only-child {
  grid-column: 1 / -1;
  width: min(100%, 640px);
  justify-self: center;
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
/* Tone Theme color mappings */
.agent-detail-floating-panel.tone-blue {
  --agent-accent: #3b82f6;
  --agent-accent-soft: rgba(59, 130, 246, 0.08);
  --agent-accent-glow: rgba(59, 130, 246, 0.2);
}
.agent-detail-floating-panel.tone-purple {
  --agent-accent: #8b5cf6;
  --agent-accent-soft: rgba(139, 92, 246, 0.08);
  --agent-accent-glow: rgba(139, 92, 246, 0.2);
}
.agent-detail-floating-panel.tone-rose {
  --agent-accent: #f43f5e;
  --agent-accent-soft: rgba(244, 63, 94, 0.08);
  --agent-accent-glow: rgba(244, 63, 94, 0.2);
}
.agent-detail-floating-panel.tone-emerald {
  --agent-accent: #10b981;
  --agent-accent-soft: rgba(16, 185, 129, 0.08);
  --agent-accent-glow: rgba(16, 185, 129, 0.2);
}
.agent-detail-floating-panel.tone-indigo {
  --agent-accent: #6366f1;
  --agent-accent-soft: rgba(99, 102, 241, 0.08);
  --agent-accent-glow: rgba(99, 102, 241, 0.2);
}
.agent-detail-floating-panel.tone-pink {
  --agent-accent: #ec4899;
  --agent-accent-soft: rgba(236, 72, 153, 0.08);
  --agent-accent-glow: rgba(236, 72, 153, 0.2);
}

.detail-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.3);
  backdrop-filter: blur(4px);
}

.agent-detail-floating-panel {
  width: min(460px, calc(100vw - 24px));
  max-width: calc(100vw - 24px);
  max-height: 80vh;
  padding: 0;
  overflow-x: hidden;
  overflow-y: auto;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: var(--radius-outer, 20px);
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 30px 70px rgba(15, 23, 42, 0.14);
}

.detail-panel-title {
  position: sticky;
  top: 0;
  z-index: 2;
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 64px;
  margin: 0;
  padding: 14px 48px 14px 16px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  background: rgba(255, 255, 255, 0.96);
}

.detail-panel-title .focus-agent-icon {
  width: 38px;
  height: 38px;
  font-size: 15px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: var(--agent-accent-soft, #f1f5f9);
  color: var(--agent-accent, #64748b);
  border: 1px solid var(--agent-accent-glow, rgba(226, 232, 240, 0.8));
}

.detail-title-copy {
  min-width: 0;
}

.detail-title-copy > span {
  display: block;
  margin-bottom: 1px;
  color: #94a3b8;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.detail-title-copy h3 {
  margin: 0;
  overflow: hidden;
  color: #0f172a;
  font-size: 13.5px;
  font-weight: 800;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-title-copy p {
  margin: 2px 0 0;
  color: #64748b;
  font-size: 10px;
  font-weight: 600;
}

.detail-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #cbd5e1;
}

.detail-status-dot.status-running {
  background: var(--agent-accent, #3b82f6);
  box-shadow: 0 0 0 5px var(--agent-accent-glow, rgba(59, 130, 246, 0.2));
  animation: pulse-ring 1.5s infinite ease-in-out;
}

.detail-status-dot.status-success {
  background: #10b981;
}

.detail-status-dot.status-failed {
  background: #ef4444;
}

@keyframes pulse-ring {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.1); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

.detail-close-btn {
  position: absolute;
  top: 17px;
  right: 14px;
  z-index: 3;
  width: 28px;
  height: 28px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 8px;
  background: #fff;
  color: #64748b;
  font-size: 16px;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.detail-close-btn:hover {
  background: var(--agent-accent-soft, #f1f5f9);
  color: var(--agent-accent, #0f172a);
  border-color: var(--agent-accent-glow, #cbd5e1);
}

.selected-agent-detail-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
}

/* Flattened - No double card layout */
.detail-current-task {
  padding: 4px 4px 14px;
  background: transparent;
  border: none;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: 0;
}

.detail-current-task span {
  display: block;
  color: #94a3b8;
  font-size: 9px;
  font-weight: 700;
  margin-bottom: 6px;
}

.detail-current-task strong {
  display: block;
  color: #1e293b;
  font-size: 12.5px;
  font-weight: 700;
  line-height: 1.45;
}

.detail-progress-line {
  height: 5px;
  margin-top: 10px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.12);
  overflow: hidden;
}

.detail-progress-line i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--agent-accent, #3b82f6), #22d3ee);
  transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.detail-current-task em {
  display: block;
  text-align: right;
  margin-top: 4px;
  font-style: normal;
  color: var(--agent-accent, #64748b);
  font-size: 10px;
  font-weight: 800;
}

/* Light borderless metrics */
.detail-metrics-v3 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  border: none;
  background: transparent;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  padding: 4px 4px 14px;
  border-radius: 0;
  margin: 0;
}

.detail-metrics-v3 > div {
  padding: 9px 11px;
  border: none !important;
  background: #f8fafc;
  border-radius: 8px;
}

.detail-metrics-v3 dt {
  font-size: 9px;
  color: #94a3b8;
  font-weight: 700;
}

.detail-metrics-v3 dd {
  margin-top: 2px;
  color: #334155;
  font-size: 11.5px;
  font-weight: 700;
}

/* IO grid */
.detail-io-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
  padding: 4px 4px 14px;
}

.detail-io-grid div {
  padding: 9px 11px;
  border-radius: 8px;
  background: #f8fafc;
  border: none;
}

.detail-io-grid span {
  color: var(--agent-accent, #476b9e);
  font-size: 9px;
  font-weight: 700;
}

.detail-io-grid p {
  margin-top: 3px;
  color: #475569;
  font-size: 10px;
  line-height: 1.4;
}

/* Metric chips */
.focus-metric-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 2px 4px;
}

.focus-metric-chips span {
  padding: 3px 7px;
  border-radius: 6px;
  font-size: 9px;
  font-weight: 700;
  background: var(--agent-accent-soft, #f1f5f9);
  color: var(--agent-accent, #475569);
  border: 1px solid rgba(226, 232, 240, 0.2);
}

/* Sleek Timeline event stream */
.detail-history-v3 {
  max-height: none;
  padding: 12px 4px 4px;
  margin-top: 4px;
}

.timeline-stream-wrapper {
  position: relative;
  padding-left: 14px;
  margin-top: 10px;
}

.timeline-stream-wrapper::before {
  content: '';
  position: absolute;
  top: 6px;
  left: 3px;
  bottom: 6px;
  width: 1px;
  background: rgba(226, 232, 240, 0.8);
}

.detail-live-log-item {
  position: relative;
  padding: 6px 0 10px;
  background: transparent;
  border: none;
  border-radius: 0;
  margin-top: 0;
}

.timeline-dot {
  position: absolute;
  left: -14px;
  top: 10px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #cbd5e1;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px rgba(226, 232, 240, 0.5);
  z-index: 2;
  transform: translateX(-1px);
  transition: background-color 0.25s ease, box-shadow 0.25s ease;
}

.detail-live-log-item.is-running .timeline-dot {
  background: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.detail-live-log-item.is-success .timeline-dot {
  background: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
}

.detail-live-log-item.is-failed .timeline-dot {
  background: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2);
}

.timeline-content {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.timeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 9px;
}

.timeline-header span {
  font-weight: 700;
  color: #475569;
}

.timeline-header em {
  font-style: normal;
  color: #94a3b8;
  font-family: var(--font-mono);
}

.detail-live-log-item p {
  margin: 2px 0 0;
  font-size: 10px;
  color: #64748b;
  line-height: 1.4;
  font-family: var(--font-mono);
}

.timeline-empty-msg {
  margin-top: 8px;
  color: #94a3b8;
  font-size: 10px;
  text-align: center;
}

.detail-fade-enter-active,
.detail-fade-leave-active {
  transition: opacity 0.22s ease;
}

.detail-fade-enter-from,
.detail-fade-leave-to {
  opacity: 0;
}

.detail-fade-enter-active .agent-detail-floating-panel,
.detail-fade-leave-active .agent-detail-floating-panel {
  transition: transform 0.24s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.22s ease;
}

.detail-fade-enter-from .agent-detail-floating-panel,
.detail-fade-leave-to .agent-detail-floating-panel {
  opacity: 0;
  transform: scale(0.96);
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

/* ==================== 内联 Outputs 样式 ==================== */
.output-dock-section {
  padding: 18px 24px 24px;
  border-top: 1px solid #e3e8ef;
  background: #f6f8fb;
}

.output-dock-section-v4 {
  margin-top: 14px;
  border-radius: var(--radius-outer);
  background: var(--generator-card-bg);
  backdrop-filter: var(--generator-card-blur);
  -webkit-backdrop-filter: var(--generator-card-blur);
  border: var(--generator-card-border);
  box-shadow: var(--generator-card-shadow);
  border-top: none;
}

.output-dock-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.output-dock-heading > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.output-dock-heading span {
  color: #98a2b3;
  font-size: 8px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.output-dock-heading strong {
  color: #263246;
  font-size: 14px;
}

.output-dock-heading p {
  margin: 0;
  color: #7a8494;
  font-size: 10px;
}

.output-dock-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 8px;
}

.output-dock-item {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid transparent;
  border-left: 3px solid transparent;
  border-radius: 10px;
  background: #f4f6f9;
  color: #94a3b8;
  text-align: left;
  opacity: 0.65;
  cursor: default;
  transition: opacity 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.output-dock-item.ready {
  opacity: 1;
  background: #ffffff;
  border-left-color: #20b986;
  border-color: rgba(16, 185, 129, 0.18);
  color: #344054;
  cursor: pointer;
}

.output-dock-item.ready:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgb(15 23 42 / 6%), 0 0 0 1px rgba(16, 185, 129, 0.12);
  border-left-color: #10b981;
}

.output-dock-item.running {
  opacity: 1;
  background: #ffffff;
  border-left-color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.18);
  color: #344054;
  cursor: default;
  animation: border-shimmer 2s infinite ease-in-out;
}

@keyframes border-shimmer {
  0%, 100% { border-left-color: rgba(59, 130, 246, 0.48); }
  50% { border-left-color: rgba(59, 130, 246, 0.9); }
}

.output-icon {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 8px;
  background: #edf4fc;
  color: #2c5f9f;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.output-dock-item.running .output-icon {
  background: #dbeafe;
  color: #3b82f6;
}

.output-dock-item.waiting .output-icon {
  background: #f1f5f9;
  color: #cbd5e1;
}

.output-copy {
  min-width: 0;
}

.output-copy strong,
.output-copy small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.output-copy strong {
  font-size: 11px;
  transition: color 0.2s ease;
}

.output-dock-item.waiting .output-copy strong {
  color: #94a3b8;
}

.output-copy small {
  font-size: 9px;
  color: #98a2b3;
  font-style: normal;
}

.output-dock-item.waiting .output-copy small {
  color: #cbd5e1;
}

.output-status {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px 6px;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 700;
  font-style: normal;
  white-space: nowrap;
  transition: color 0.2s ease, background-color 0.2s ease;
}

.output-dock-item.ready .output-status {
  color: #16a34a;
  background: rgba(16, 185, 129, 0.08);
}

.output-dock-item.running .output-status {
  color: #2563eb;
  background: rgba(59, 130, 246, 0.08);
}

.output-dock-item.waiting .output-status {
  color: #94a3b8;
  background: transparent;
}

.loading-dots {
  display: inline-block;
  animation: dots-pulse 1.2s infinite;
}

@keyframes dots-pulse {
  0%, 20% { opacity: 0.2; }
  50% { opacity: 1; }
  80%, 100% { opacity: 0.2; }
}

.output-dock-item.just-arrived {
  animation: artifact-arrive 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes artifact-arrive {
  0% {
    transform: scale(0.9);
    opacity: 0;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
  60% {
    transform: scale(1.02);
    opacity: 1;
    box-shadow: 0 0 0 8px rgba(16, 185, 129, 0.25);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

/* ==================== 内联 Logs 样式 ==================== */
.custom-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgb(15 23 42 / 28%);
}

.log-drawer {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  width: min(420px, 100%);
  height: 100%;
  flex-direction: column;
  padding: 24px;
  background: #fff;
  box-shadow: -18px 0 48px rgb(15 23 42 / 14%);
}

.log-drawer header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid #e8ecf1;
}

.log-drawer h3 {
  margin: 0;
  color: #263246;
  font-size: 14px;
}

.log-drawer button {
  border: 0;
  color: #98a2b3;
  background: transparent;
  font-size: 22px;
  cursor: pointer;
}

.drawer-log-list {
  overflow-y: auto;
  padding-top: 14px;
}

.drawer-log-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #eef1f5;
}

.drawer-log-dot {
  width: 7px;
  height: 7px;
  margin-top: 5px;
  border-radius: 50%;
  background: #98a2b3;
}

.drawer-log-item.is-running .drawer-log-dot {
  background: #3b75bd;
}

.drawer-log-item.is-success .drawer-log-dot {
  background: #168357;
}

.drawer-log-item.is-failed .drawer-log-dot {
  background: #c04444;
}

.drawer-log-item strong {
  color: #344054;
  font-size: 11px;
}

.drawer-log-item p,
.empty-log {
  margin: 3px 0 0;
  color: #7a8494;
  font-size: 10px;
  line-height: 1.5;
}

.slide-over-enter-active,
.slide-over-leave-active {
  transition: opacity 0.2s ease;
}

.slide-over-enter-from,
.slide-over-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .output-dock-item.just-arrived,
  .output-dock-item.running,
  .loading-dots {
    animation: none !important;
  }
  .output-dock-item.ready:hover {
    transform: none;
  }
}
</style>
