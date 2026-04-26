<template>
  <div class="resource-generator-layout" :class="{ 'sidebar-collapsed': isSidebarCollapsed }">
    
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="brand-logo-box"><el-icon class="brand-icon"><Cpu /></el-icon></div>
        <div class="brand-title">
          <h2>资源编排中枢</h2>
          <span class="sub-title">Multi-Agent Studio</span>
        </div>
      </div>

      <div class="sidebar-form">
        <el-form label-position="top" class="custom-form">
          <el-form-item>
            <template #label><div class="custom-label"><el-icon><CollectionTag /></el-icon> 学习课题 <span class="req-star">*</span></div></template>
            <el-input v-model="form.topic" placeholder="例如：TCP/IP 三次握手" clearable class="modern-input" />
          </el-form-item>

          <el-form-item>
            <template #label><div class="custom-label"><el-icon><Aim /></el-icon> 知识盲区 <span class="req-star">*</span></div></template>
            <el-input v-model="form.gap" type="textarea" :rows="3" placeholder="例如：总是记不住状态流转过程" resize="none" class="modern-input" />
          </el-form-item>

          <div class="divider-with-text"><span>智能体集群配置</span></div>

          <el-form-item>
            <template #label>
              <div class="checkbox-header">
                <div class="custom-label"><el-icon><Setting /></el-icon> 定制生成项</div>
                <el-button type="primary" link size="small" @click="selectAll">一键全选</el-button>
              </div>
            </template>
            
            <div class="custom-agent-grid">
              <label v-for="agent in agentConfig" :key="agent.id" class="agent-select-card" :class="{ 'is-active': form.selected.includes(agent.id) }">
                <input type="checkbox" v-model="form.selected" :value="agent.id" hidden />
                <div class="card-icon"><el-icon><component :is="agent.icon" /></el-icon></div>
                <div class="card-name">{{ agent.name }}</div>
                <div class="active-indicator"><el-icon><Check /></el-icon></div>
              </label>
            </div>
          </el-form-item>

        </el-form>
      </div>

      <div class="sidebar-footer">
        <button class="magic-submit-btn" :disabled="!canGenerate || isGenerating" @click="startResourceGeneration">
          <span class="btn-text">
            <el-icon v-if="!isGenerating" class="mr-2"><VideoPlay /></el-icon>
            <el-icon v-else class="mr-2 is-loading"><Loading /></el-icon>
            {{ isGenerating ? '系统调度运转中...' : '启动智能体工作流' }}
          </span>
        </button>
      </div>
    </aside>

    <main class="main-workspace">
      <div class="expand-trigger" v-if="isSidebarCollapsed" @click="isSidebarCollapsed = false" title="修改需求">
        <el-icon><ArrowRightBold /></el-icon>
      </div>

      <div class="workspace-scroll-container">
        
        <section class="workflow-section">
          <div class="section-header">
            <h3><el-icon><Connection /></el-icon> 实时协同执行流</h3>
            <div class="workflow-plan-title" v-if="currentExecutionGroupText">{{ currentExecutionGroupText }}</div>
            <div class="progress-info" v-if="isGenerating || progress === 100">
              <span>构建总进度: {{ progress }}%</span>
              <el-progress :percentage="progress" :show-text="false" class="top-progress" />
            </div>
          </div>

          <div class="network-topology" v-if="form.selected.length > 0">
            
            <div class="coordinator-zone">
              <div class="agent-workflow-node brain-node" :class="coordinatorState.status">
                <div class="node-header">
                  <div class="n-title"><el-icon class="n-icon"><Guide /></el-icon> Coordinator (主控大脑)</div>
                  <el-tag size="small" :type="getStatusTagType(coordinatorState.status)" effect="dark">{{ getStatusText(coordinatorState.status) }}</el-tag>
                </div>
                
                <div class="node-animation-window" v-if="isCoordinatorBusy">
                  <div class="human-action-text text-primary">
                    <el-icon class="is-loading"><Loading /></el-icon><span>{{ coordinatorState.currentAction }}</span>
                  </div>
                  <div class="skeleton-builder brain-skeleton"><div class="sk-line w-full"></div><div class="sk-line w-80"></div></div>
                </div>

                <div class="node-summary" v-if="coordinatorState.status === 'done'">
                  <div class="success-circle"><el-icon><Select /></el-icon></div><span>意图拆解完毕，数据流推送中</span>
                </div>
              </div>
            </div>

            <div class="tree-trunk" v-if="dynamicExecutionQueue.length > 0">
               <div class="trunk-flow" :class="{'is-flowing': isGenerating && isCoordinatorBusy}"></div>
            </div>

            <div class="execution-zone">
              <div class="worker-column" v-for="(col, colIndex) in chunkedExecutionQueue" :key="'col-' + colIndex">
                
                <div class="worker-row slide-fade-enter" v-for="(agentId, rowIndex) in col" :key="agentId">
                  <div class="spine-segment" :class="{ 'is-first': rowIndex === 0, 'is-last': rowIndex === col.length - 1, 'is-only': col.length === 1 }"></div>
                  <div class="branch-segment">
                    <div class="branch-flow" :class="{'is-flowing': nodesState[agentId]?.status === 'running'}"></div>
                    <el-icon class="branch-arrow is-active"><CaretRight /></el-icon>
                  </div>

                  <div class="agent-workflow-node worker-node" :class="nodesState[agentId]?.status || 'idle'">
                    <div class="node-header">
                      <div class="n-title"><el-icon class="n-icon"><component :is="getAgentMeta(agentId).icon" /></el-icon>{{ getAgentMeta(agentId).name }}</div>
                      <el-tag size="small" :type="getStatusTagType(nodesState[agentId]?.status)">{{ getStatusText(nodesState[agentId]?.status) }}</el-tag>
                    </div>
                    
                    <div class="node-animation-window" v-if="nodesState[agentId]?.status === 'running'">
                      <div class="human-action-text">
                        <el-icon class="is-loading"><Loading /></el-icon><span>{{ nodesState[agentId]?.currentAction }}</span>
                      </div>
                      <div class="skeleton-builder"><div class="sk-line w-full"></div><div class="sk-line w-60"></div></div>
                    </div>

                    <div class="node-summary" v-if="['success', 'done'].includes(nodesState[agentId]?.status || '')">
                      <el-icon class="text-success" style="font-size: 1.2rem;"><CircleCheckFilled /></el-icon><span>资源构建成功</span>
                    </div>

                    <div class="node-summary skipped-summary" v-else-if="nodesState[agentId]?.status === 'skipped'">
                      <el-icon style="font-size: 1.2rem;"><CircleCloseFilled /></el-icon><span>{{ nodesState[agentId]?.currentAction || '已跳过' }}</span>
                    </div>
                  </div>
                </div>

              </div>
            </div>
            
          </div>
          <el-empty v-else description="请在左侧勾选需要生成的资源" :image-size="100" />
        </section>

        <section class="results-section" v-if="completedAgentsQueue.length > 0">
          <div class="section-header">
            <h3><el-icon><FolderOpened /></el-icon> 专属资源产出 ({{ completedAgentsQueue.length }})</h3>
          </div>
          <div class="results-grid">
            <ResourceCard 
              v-for="agentId in completedAgentsQueue" 
              :key="'res-' + agentId"
              :agent-id="agentId"
              :meta="getAgentMeta(agentId)"
              :topic="form.topic"
              :gap="form.gap"
              :result-data="results[agentId]"
              @preview="handlePreview"
            />
          </div>
        </section>

      </div>
    </main>

    <!-- 全局预览弹窗 -->
    <el-dialog
      v-model="previewDialogVisible"
      :title="previewData?.title ? `预览 - ${previewData.title}` : '预览内容'"
      width="75%"
      top="8vh"
      class="custom-preview-dialog"
      destroy-on-close
    >
      <div v-if="previewData" class="preview-dialog-body">
        <MindmapResourceView
          v-if="previewData.agentId === 'mindmap'"
          :result-data="previewData.resultData"
        />
        <QuizResourceView
          v-else-if="previewData.agentId === 'quiz'"
          :result-data="previewData.resultData"
        />
        <MarkdownResourceView
          v-else-if="['content', 'reading', 'code'].includes(previewData.agentId)"
          :result-data="previewData.resultData"
        />
        <pre v-else class="code-view"><code>{{ formatJson(previewData.resultData) }}</code></pre>
      </div>
    </el-dialog>
    
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, type Component } from 'vue'
import {
  Cpu, Document, Edit, Collection, VideoPlay, Monitor, Guide, Setting,
  Share, Connection, FolderOpened, Select, ArrowRightBold, CaretRight, Loading, CircleCheckFilled, CircleCloseFilled, CollectionTag, Aim, Check, DataBoard
} from '@element-plus/icons-vue'

import ResourceCard from '@/components/ResourceCard.vue'
import MindmapResourceView from '@/components/resources/MindmapResourceView.vue'
import MarkdownResourceView from '@/components/resources/MarkdownResourceView.vue'
import QuizResourceView from '@/components/resources/QuizResourceView.vue'
import {
  generateResources,
  getAgents,
  type AgentInfo,
  type ResourceAgentLogEvent,
  type ResourceAgentStatusEvent,
  type ResourceArtifact,
  type ResourceArtifactReadyEvent,
  type ResourceBundleUpdateEvent,
  type ResourceGenerateEvent,
  type ResourceGenerateRequest,
  type ResourceWorkflowEvent,
} from '@/api/resource'
import { recordLearningEvent } from '@/api/ai'

// ================= 数据定义 =================
const isSidebarCollapsed = ref(false)
const isGenerating = ref(false)
const progress = ref(0)
const results = ref<Record<string, ResourceArtifact>>({})
const workflowController = ref<AbortController | null>(null)

const form = reactive({
  topic: 'TCP/IP 三次握手',
  gap: '总是记不住状态流转过程',
  selected: ['content', 'mindmap', 'quiz', 'reading', 'code']
})

// 🌟 动态排序队列 (决定前端展示顺序)
const dynamicExecutionQueue = ref<string[]>([])
const completedAgentsQueue = ref<string[]>([])

interface AgentMeta {
  id: string
  name: string
  desc: string
  type: string
  icon: Component
}

const defaultAgentMeta: Record<string, AgentMeta> = {
  content: { id: 'content', name: '核心精讲', desc: '撰写深度知识精讲', type: 'doc', icon: Document },
  mindmap: { id: 'mindmap', name: '思维导图', desc: '构建核心知识拓扑图', type: 'mindmap', icon: Share },
  quiz: { id: 'quiz', name: '专项题库', desc: '生成分层练习题库', type: 'quiz', icon: Edit },
  code: { id: 'code', name: '实操代码', desc: '编写可运行实操案例', type: 'code', icon: Cpu },
  reading: { id: 'reading', name: '拓展阅读', desc: '检索拓展阅读与论文', type: 'reading', icon: Collection },
  ppt: { id: 'ppt', name: '演示讲稿', desc: '生成演示文稿与讲稿', type: 'ppt', icon: DataBoard },
  image: { id: 'image', name: '教学配图', desc: '生成教学配图', type: 'image', icon: Monitor },
  video: { id: 'video', name: '视频脚本', desc: '生成视频脚本', type: 'video', icon: VideoPlay }
}

const supportedResourceIds = ['content', 'mindmap', 'quiz', 'reading', 'code']
const backendAgentOrder: Array<keyof typeof defaultAgentMeta> = ['content', 'mindmap', 'quiz', 'reading', 'code']
const agentConfig = ref<AgentMeta[]>(backendAgentOrder.map((id) => defaultAgentMeta[id] as AgentMeta))

const friendlyActions: Record<string, string[]> = {
  coordinator: ['应用全局编排指令...', '诊断知识盲区特征...', '拆解任务并下发...'],
  content: ['正在重组知识脉络...', '结合痛点润色细节...'],
  mindmap: ['提炼核心层级...', '构建关联拓扑...'],
  quiz:    ['检索大纲...', '定制专项习题...'],
  code:    ['分析逻辑边界...', '编写实操样例...'],
  image:   ['提炼结构特征...', '渲染核心图表...'],
  reading: ['匹配学术库...', '提取论文摘要...'],
  ppt:     ['拆分演示切片...', '生成演讲备注...'],
  video:   ['转化多模态解说...', '编排分镜时间...']
}
const coordinatorActions = friendlyActions.coordinator ?? []

type CoordinatorStatus = 'idle' | 'profile_loading' | 'planning' | 'persisting' | 'core_generating' | 'enhancement_generating' | 'presentation_generating' | 'video_generating' | 'done'
type WorkerStatus = 'idle' | 'queued' | 'running' | 'success' | 'failed' | 'skipped'
type NodeStatus = CoordinatorStatus | WorkerStatus

interface NodeState { status: NodeStatus; currentAction: string; }
const coordinatorState = ref<NodeState>({ status: 'idle', currentAction: '' })
const nodesState = ref<Record<string, NodeState>>({})
const processedAgentIds = ref<Set<string>>(new Set())
const currentExecutionGroupText = ref('')

// ================= 计算属性 =================
const canGenerate = computed(() => form.topic.trim() !== '' && form.selected.length > 0)
const getAgentMeta = (id: string): AgentMeta => agentConfig.value.find(a => a.id === id) || defaultAgentMeta[id] || { id, name: id, desc: '', type: 'doc', icon: Document }

// 🌟 核心：计算每列 4 个元素的二维数组
const chunkedExecutionQueue = computed(() => {
  const chunkSize = 4
  const chunks: string[][] = []
  for (let i = 0; i < dynamicExecutionQueue.value.length; i += chunkSize) {
    chunks.push(dynamicExecutionQueue.value.slice(i, i + chunkSize))
  }
  return chunks
})
const isCoordinatorBusy = computed(() => coordinatorState.value.status !== 'idle' && coordinatorState.value.status !== 'done')

const selectAll = () => { form.selected = agentConfig.value.map(a => a.id).filter((id) => supportedResourceIds.includes(id)) }
const getStatusTagType = (status?: string) => {
  if (status === 'running' || status === 'planning' || status === 'profile_loading' || status === 'core_generating' || status === 'enhancement_generating' || status === 'presentation_generating' || status === 'video_generating' || status === 'persisting') return 'primary'
  if (status === 'success' || status === 'done') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'skipped') return 'warning'
  return 'info'
}
const getStatusText = (status?: string) => {
  if (status === 'profile_loading') return '读取画像'
  if (status === 'planning') return '规划中'
  if (status === 'core_generating') return '核心资源'
  if (status === 'enhancement_generating') return '增强资源'
  if (status === 'presentation_generating') return '演示资源'
  if (status === 'video_generating') return '视频资源'
  if (status === 'persisting') return '保存中'
  if (status === 'running') return 'AI 处理中'
  if (status === 'queued') return '排队中'
  if (status === 'success' || status === 'done') return '已产出'
  if (status === 'failed') return '失败'
  if (status === 'skipped') return '已跳过'
  return '等待调度'
}
const workflowStageFallback: Record<string, string> = {
  profile_loading: coordinatorActions[0] || '正在读取学习者画像...',
  planning: coordinatorActions[1] || '正在生成资源计划...',
  core_generating: coordinatorActions[2] || '正在编排核心资源...',
  enhancement_generating: '正在补充增强资源...',
  presentation_generating: '正在生成演示资源...',
  video_generating: '正在生成视频资源...',
  persisting: '正在保存本次资源包...',
  done: '资源包构建完成'
}

const agentStatusFallback: Record<string, string> = {
  queued: '等待进入执行队列...',
  running: '正在构建资源...',
  success: '资源已生成完成',
  failed: '资源生成失败',
  skipped: '已跳过'
}

const ensureNodeState = (agentId: string) => {
  if (!nodesState.value[agentId]) {
    nodesState.value[agentId] = { status: 'idle', currentAction: '' }
  }
  return nodesState.value[agentId]
}

const clearWorkflowState = () => {
  results.value = {}
  progress.value = 0
  dynamicExecutionQueue.value = []
  completedAgentsQueue.value = []
  processedAgentIds.value = new Set()
  currentExecutionGroupText.value = ''
  coordinatorState.value = { status: 'idle', currentAction: '' }
  Object.keys(nodesState.value).forEach((key) => {
    delete nodesState.value[key]
  })
}

const formatAgentList = (agents: string[]) => agents.map((agentId) => getAgentMeta(agentId).name || agentId).join('、')

const getExecutionGroupAgents = (event: ResourceWorkflowEvent) => {
  const agents = event.meta?.agents
  if (Array.isArray(agents)) return agents.filter((agent): agent is string => typeof agent === 'string')

  const executionGroup = event.meta?.execution_group
  if (Array.isArray(executionGroup)) {
    return executionGroup.filter((agent): agent is string => typeof agent === 'string')
  }
  if (typeof executionGroup === 'string') {
    return executionGroup.split(',').map((agent) => agent.trim()).filter(Boolean)
  }
  return []
}

const getWorkflowGroupText = (event: ResourceWorkflowEvent) => {
  const groupIndex = event.meta?.group_index
  const groupTotal = event.meta?.group_total
  const agents = getExecutionGroupAgents(event)

  if (typeof groupIndex !== 'number' || typeof groupTotal !== 'number' || agents.length === 0) return ''
  return `第 ${groupIndex}/${groupTotal} 组：${formatAgentList(agents)} 并行执行`
}

const getWorkflowActionText = (event: ResourceWorkflowEvent) => {
  const groupText = getWorkflowGroupText(event)
  if (groupText) return groupText
  return event.message || workflowStageFallback[event.stage] || coordinatorActions[0] || '正在协调任务...'
}

const getAgentActionText = (agentId: string, status: string, message?: string, event?: ResourceAgentStatusEvent) => {
  if (status === 'skipped') {
    return event?.meta?.skipped_reason || message || agentStatusFallback.skipped || '已跳过'
  }
  const fallbackList = friendlyActions[agentId] || []
  return message || agentStatusFallback[status] || fallbackList[0] || '正在构建资源...'
}

const updateProcessedProgress = () => {
  const total = form.selected.length
  if (total > 0) {
    progress.value = Math.max(progress.value, Math.min(100, Math.round((processedAgentIds.value.size / total) * 100)))
  }
}

const applyWorkflowEvent = (event: ResourceWorkflowEvent) => {
  coordinatorState.value.status = (event.stage || 'planning') as CoordinatorStatus
  currentExecutionGroupText.value = getWorkflowGroupText(event) || currentExecutionGroupText.value
  coordinatorState.value.currentAction = getWorkflowActionText(event)
}

const applyAgentStatusEvent = (event: ResourceAgentStatusEvent) => {
  if (!event.agent || !event.status) return

  if (!dynamicExecutionQueue.value.includes(event.agent)) {
    dynamicExecutionQueue.value.push(event.agent)
  }

  const node = ensureNodeState(event.agent)
  node.status = event.status
  node.currentAction = getAgentActionText(event.agent, event.status, event.message, event)

  if (event.status === 'success' || event.status === 'failed' || event.status === 'skipped') {
    processedAgentIds.value = new Set(processedAgentIds.value).add(event.agent)
    updateProcessedProgress()
  }
}

const applyAgentLogEvent = (event: ResourceAgentLogEvent) => {
  if (!event.agent || !event.log) return

  if (event.agent === 'coordinator') {
    coordinatorState.value.currentAction = event.log
    return
  }

  const node = ensureNodeState(event.agent)
  node.currentAction = event.log
}

const applyArtifactReadyEvent = (event: ResourceArtifactReadyEvent) => {
  if (!event.agent) return

  results.value[event.agent] = event.artifact

  if (!dynamicExecutionQueue.value.includes(event.agent)) {
    dynamicExecutionQueue.value.push(event.agent)
  }

  const node = ensureNodeState(event.agent)
  node.status = 'success'
  node.currentAction = getAgentActionText(event.agent, 'success')
  processedAgentIds.value = new Set(processedAgentIds.value).add(event.agent)
  updateProcessedProgress()

  if (!completedAgentsQueue.value.includes(event.agent)) {
    completedAgentsQueue.value.push(event.agent)
  }

  recordLearningEvent({
    event_type: 'resource_completed',
    course: form.topic.trim(),
    topic: getAgentMeta(event.agent).name,
    metadata: { agent: event.agent },
  }).catch((err) => {
    console.warn('[ResourceGenerator] record learning event failed:', err)
  })
}

const applyBundleUpdateEvent = (event: ResourceBundleUpdateEvent) => {
  const visibleCompleted = typeof event.meta?.visible_completed === 'number' ? event.meta.visible_completed : undefined
  const visibleTotal = typeof event.meta?.visible_total === 'number' ? event.meta.visible_total : undefined
  const completed = visibleCompleted ?? event.completed
  const total = visibleTotal && visibleTotal > 0 ? visibleTotal : event.total
  if (total > 0) {
    progress.value = Math.max(progress.value, Math.min(100, Math.round((completed / total) * 100)))
  }

  const latestAgent = typeof event.latest_agent === 'string' ? event.latest_agent : ''
  if (!latestAgent) return

  if (!dynamicExecutionQueue.value.includes(latestAgent)) {
    dynamicExecutionQueue.value.push(latestAgent)
  }
  const node = ensureNodeState(latestAgent)
  if (node.status === 'queued') {
    node.status = 'running'
  }
}

const handleGenerateEvent = (event: ResourceGenerateEvent) => {
  if (!event || typeof event.type !== 'string') return

  switch (event.type) {
    case 'workflow':
      applyWorkflowEvent(event)
      break
    case 'agent_status':
      applyAgentStatusEvent(event)
      break
    case 'agent_log':
      applyAgentLogEvent(event)
      break
    case 'artifact_ready':
      applyArtifactReadyEvent(event)
      break
    case 'bundle_update':
      applyBundleUpdateEvent(event)
      break
    case 'done':
      coordinatorState.value.status = 'done'
      coordinatorState.value.currentAction = event.message || workflowStageFallback.done || '资源包构建完成'
      progress.value = 100
      isGenerating.value = false
      workflowController.value = null
      break
  }
}

const buildGenerateRequest = (): ResourceGenerateRequest => ({
  learning_task: {
    course: form.topic.trim(),
    gap: form.gap.trim(),
    need: 'review',
    extra: '',
    template_id: 'auto',
  },
  selected_resources: [...form.selected],
})

// ================= 预览功能 =================
const previewDialogVisible = ref(false)
const previewData = ref<{
  agentId: string
  title: string
  hasFile: boolean
  fileUrl: string
  fileCategory: string
  resultData: ResourceArtifact
} | null>(null)

const handlePreview = (data: {
  agentId: string
  title: string
  hasFile: boolean
  fileUrl: string
  fileCategory: string
  resultData: ResourceArtifact
}) => {
  previewData.value = data
  previewDialogVisible.value = true
}

const formatJson = (data: unknown) => {
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

// ================= 动画流真实接入 (SSE) =================
const startResourceGeneration = () => {
  workflowController.value?.abort()
  workflowController.value = null
  isSidebarCollapsed.value = true
  isGenerating.value = true
  clearWorkflowState()
  form.selected.forEach((id) => {
    ensureNodeState(id)
  })
  coordinatorState.value = {
    status: 'profile_loading',
    currentAction: workflowStageFallback.profile_loading || '正在读取学习者画像...',
  }

  workflowController.value = generateResources(
    buildGenerateRequest(),
    handleGenerateEvent,
    () => {
      coordinatorState.value.status = 'done'
      coordinatorState.value.currentAction = workflowStageFallback.done || '资源包构建完成'
      progress.value = 100
      isGenerating.value = false
      workflowController.value = null
    },
    (err) => {
      coordinatorState.value.status = 'done'
      coordinatorState.value.currentAction = err.message || '资源包生成失败'
      isGenerating.value = false
      workflowController.value = null
      console.error('[ResourceGenerator] generateResources failed:', err)
    },
  )
}

const toAgentMeta = (agent: AgentInfo): AgentMeta => {
  const fallback = defaultAgentMeta[agent.id] || {
    id: agent.id,
    name: agent.role || agent.id,
    desc: agent.desc || '',
    type: agent.type || 'doc',
    icon: Document,
  }
  return {
    ...fallback,
    id: agent.id,
    name: fallback.name || agent.role || agent.id,
    desc: agent.desc || fallback.desc,
    type: agent.type || fallback.type,
  }
}

const loadBackendAgents = async () => {
  try {
    const response = await getAgents()
    const agents = response.data.data || []
    if (agents.length === 0) return

    agentConfig.value = agents
      .filter((agent) => supportedResourceIds.includes(agent.id))
      .map(toAgentMeta)
    const availableIds = new Set(agentConfig.value.map((agent) => agent.id))
    form.selected = form.selected.filter((id) => availableIds.has(id))
    if (form.selected.length === 0) {
      form.selected = agentConfig.value.map((agent) => agent.id)
    }
  } catch (err) {
    console.warn('[ResourceGenerator] load agents failed, using fallback config:', err)
  }
}

onMounted(() => {
  loadBackendAgents()
})
</script>

<style scoped>
/* ================= 全局与左侧 (保持精美原样) ================= */
.resource-generator-layout { display: flex; height: calc(100vh - 60px); background-color: #F8FAFC; overflow: hidden; transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
.sidebar { width: 400px; background-color: #FFFFFF; border-right: 1px solid #E2E8F0; display: flex; flex-direction: column; z-index: 20; transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 4px 0 24px rgba(0,0,0,0.02); }
.resource-generator-layout.sidebar-collapsed .sidebar { margin-left: -400px; }
.sidebar-header { padding: 28px 24px; border-bottom: 1px solid #F1F5F9; display: flex; align-items: center; gap: 16px; }
.brand-logo-box { width: 48px; height: 48px; background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%); border-radius: 12px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(99, 102, 241, 0.1); }
.brand-icon { font-size: 24px; color: #4F46E5; }
.brand-title h2 { margin: 0 0 4px 0; font-size: 1.15rem; font-weight: 800; color: #0F172A; letter-spacing: 0.5px;}
.brand-title .sub-title { font-size: 0.75rem; color: #64748B; font-weight: 600; font-family: 'JetBrains Mono', monospace;}
.sidebar-form { flex: 1; padding: 24px; overflow-y: auto; }
.custom-form :deep(.el-form-item) { margin-bottom: 24px; }
.custom-label { display: flex; align-items: center; gap: 6px; font-size: 0.9rem; font-weight: 700; color: #1E293B; margin-bottom: 4px; }
.custom-label .el-icon { color: #6366F1; font-size: 1.1rem; }
.req-star { color: #EF4444; }
.modern-input :deep(.el-input__wrapper), .modern-input :deep(.el-textarea__inner) { background-color: #F8FAFC; border-radius: 8px; border: 1px solid transparent; box-shadow: none !important; padding: 8px 12px; transition: all 0.3s ease; font-size: 0.95rem; }
.modern-input :deep(.el-input__wrapper:focus), .modern-input :deep(.el-textarea__inner:focus) { background-color: #FFFFFF; border-color: #6366F1; box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1) !important; }
.divider-with-text { position: relative; text-align: center; margin: 32px 0 24px; }
.divider-with-text::before { content: ''; position: absolute; left: 0; top: 50%; width: 100%; height: 1px; background: #E2E8F0; z-index: 1; }
.divider-with-text span { position: relative; z-index: 2; background: #FFFFFF; padding: 0 16px; font-size: 0.8rem; color: #94A3B8; font-weight: 600; }
.checkbox-header { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.custom-agent-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px; }
.agent-select-card { position: relative; display: flex; align-items: center; gap: 10px; padding: 12px 14px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; cursor: pointer; transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); overflow: hidden; }
.agent-select-card.is-active { background: #EEF2FF; border-color: #6366F1; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1); }
.agent-select-card.is-active .card-icon, .agent-select-card.is-active .card-name { color: #4F46E5; }
.active-indicator { position: absolute; top: -20px; right: -20px; width: 40px; height: 40px; background: #6366F1; transform: rotate(45deg); transition: all 0.3s; opacity: 0; }
.active-indicator .el-icon { position: absolute; bottom: 4px; left: 14px; color: #FFFFFF; font-size: 0.75rem; transform: rotate(-45deg); }
.agent-select-card.is-active .active-indicator { opacity: 1; }
.sidebar-footer { padding: 24px; border-top: 1px solid #F1F5F9; background: #FFFFFF; }
.magic-submit-btn { position: relative; width: 100%; height: 50px; border: none; border-radius: 10px; background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%); color: #FFFFFF; font-size: 1rem; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3); }
.magic-submit-btn:disabled { background: #E2E8F0; color: #94A3B8; box-shadow: none; cursor: not-allowed; }

/* ================= 右侧工作区 ================= */
.main-workspace { flex: 1; position: relative; display: flex; flex-direction: column; overflow: hidden; background-image: radial-gradient(#E2E8F0 1px, transparent 1px); background-size: 24px 24px; }
.expand-trigger { position: absolute; left: 0; top: 50%; transform: translateY(-50%); width: 24px; height: 60px; background: #FFFFFF; border: 1px solid #E2E8F0; border-left: none; border-radius: 0 8px 8px 0; display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 10; box-shadow: 4px 0 10px rgba(0,0,0,0.05); color: #64748B; transition: all 0.2s; }
.workspace-scroll-container { flex: 1; overflow-y: auto; padding: 32px 40px; display: flex; flex-direction: column; gap: 40px; }
.section-header h3 { display: flex; align-items: center; gap: 8px; font-size: 1.2rem; font-weight: 700; color: #1E293B; margin: 0; }
.workflow-plan-title { margin-top: 8px; font-size: 0.9rem; font-weight: 600; color: #475569; }
.progress-info { display: flex; align-items: center; gap: 16px; margin-top: 12px; font-size: 0.9rem; font-weight: 600; color: #4F46E5; }
.top-progress { flex: 1; max-width: 400px; }

/* 🌟 核心：矩阵式排版网络布局 */
.network-topology {
  display: flex; align-items: flex-start; justify-content: flex-start; gap: 20px;
  background: transparent; padding: 20px 0; overflow-x: auto;
}
.coordinator-zone { flex-shrink: 0; width: 340px; position: relative; z-index: 2; }
.tree-trunk { width: 40px; height: 2px; background: #E2E8F0; position: relative; flex-shrink: 0; margin-top: 50px; /* 对齐到卡片中间 */ }
.trunk-flow { position: absolute; left: 0; top: 0; width: 100%; height: 100%; background: transparent; }
.trunk-flow.is-flowing { background: repeating-linear-gradient(90deg, #6366F1 0, #6366F1 6px, transparent 6px, transparent 12px); animation: flowRight 0.5s linear infinite; }

/* 多列执行区 Flex 布局 */
.execution-zone { 
  display: flex; flex-direction: row; gap: 40px; flex: 1; align-items: flex-start;
}
/* 每一列内部竖向排列 */
.worker-column {
  display: flex; flex-direction: column; gap: 20px; position: relative;
}
.worker-row { display: flex; align-items: center; position: relative; }

/* ================= 节点组件样式 ================= */
.spine-segment { position: absolute; left: 0; width: 2px; background: #E2E8F0; top: -10px; bottom: -10px; }
.spine-segment.is-first { top: 50%; } 
.spine-segment.is-last { bottom: 50%; } 
.spine-segment.is-only { display: none; }
.spine-segment.is-active { background: #E2E8F0; /* 保持静态，通过支线发光展示流向 */ }

.branch-segment { width: 40px; height: 2px; background: #E2E8F0; position: relative; display: flex; align-items: center; flex-shrink: 0; }
.branch-flow { position: absolute; left: 0; top: 0; width: 100%; height: 100%; background: transparent; }
.branch-flow.is-flowing { background: repeating-linear-gradient(90deg, #3B82F6 0, #3B82F6 6px, transparent 6px, transparent 12px); animation: flowRight 0.5s linear infinite; }
.branch-arrow { position: absolute; right: -12px; color: #E2E8F0; font-size: 20px; background: #F8FAFC; z-index: 1; }
.branch-arrow.is-active { color: #6366F1; }

.agent-workflow-node { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); overflow: hidden; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); display: flex; flex-direction: column; position: relative; z-index: 2; }
.worker-node { width: 320px; }
.brain-node { border-width: 2px; }
.brain-node.running,
.brain-node.profile_loading,
.brain-node.planning,
.brain-node.core_generating,
.brain-node.persisting { border-color: #6366F1; box-shadow: 0 10px 30px rgba(99, 102, 241, 0.2); transform: scale(1.02); }
.brain-node.done { border-color: #8B5CF6; }
.worker-node.running { border-color: #3B82F6; box-shadow: 0 8px 20px rgba(59, 130, 246, 0.15); transform: translateY(-4px); }
.worker-node.success,
.worker-node.done { border-color: #10B981; }
.worker-node.failed { border-color: #EF4444; }
.worker-node.skipped { border-color: #F59E0B; }

.node-header { padding: 14px 16px; display: flex; justify-content: space-between; align-items: center; background: #F8FAFC; border-bottom: 1px solid #F1F5F9; }
.brain-node .node-header,
.brain-node.profile_loading .node-header,
.brain-node.planning .node-header,
.brain-node.core_generating .node-header,
.brain-node.persisting .node-header { background: #EEF2FF; border-bottom-color: #E0E7FF; }
.brain-node.done .node-header { background: #F5F3FF; border-bottom-color: #EDE9FE; }
.worker-node.running .node-header { background: #EFF6FF; border-bottom-color: #DBEAFE; }
.worker-node.success .node-header,
.worker-node.done .node-header { background: #ECFDF5; border-bottom-color: #D1FAE5; }
.worker-node.failed .node-header { background: #FEF2F2; border-bottom-color: #FEE2E2; }
.worker-node.skipped .node-header { background: #FFFBEB; border-bottom-color: #FEF3C7; }

.n-title { font-weight: 700; color: #1E293B; display: flex; align-items: center; gap: 8px; font-size: 0.95rem;}
.brain-node .n-title,
.brain-node.profile_loading .n-title,
.brain-node.planning .n-title,
.brain-node.core_generating .n-title,
.brain-node.persisting .n-title { color: #4338CA; font-size: 1.05rem; }
.n-icon { font-size: 1.1rem; color: #64748B; }
.brain-node.running .n-icon,
.brain-node.profile_loading .n-icon,
.brain-node.planning .n-icon,
.brain-node.core_generating .n-icon,
.brain-node.persisting .n-icon { color: #6366F1; }
.worker-node.running .n-icon { color: #3B82F6; }
.worker-node.success .n-icon,
.worker-node.done .n-icon { color: #10B981; }
.worker-node.failed .n-icon { color: #EF4444; }
.worker-node.skipped .n-icon { color: #F59E0B; }
.brain-node.done .n-icon { color: #8B5CF6; }

.node-animation-window { padding: 16px; background: #FFFFFF; }
.human-action-text { display: flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 600; color: #3B82F6; margin-bottom: 16px; }
.text-primary { color: #6366F1 !important; }
.skeleton-builder { display: flex; flex-direction: column; gap: 10px; }
.sk-line { height: 8px; border-radius: 4px; background: #F1F5F9; position: relative; overflow: hidden; }
.sk-line.w-full { width: 100%; } .sk-line.w-80 { width: 80%; } .sk-line.w-60 { width: 60%; }
.sk-line::after { content: ""; position: absolute; top: 0; left: -100%; width: 50%; height: 100%; background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.15), transparent); animation: shimmer 1.5s infinite; }
.brain-skeleton .sk-line::after { background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.2), transparent); }
.node-summary { padding: 16px; display: flex; align-items: center; gap: 10px; font-size: 0.85rem; color: #475569; font-weight: 600; background: #F8FAFC; }
.skipped-summary { color: #92400E; background: #FFFBEB; }
.success-circle { width: 24px; height: 24px; background: #8B5CF6; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; }

/* 🌟 卡片区网格布局 */
.results-section { border-top: 2px dashed #CBD5E1; padding-top: 40px; }
.results-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 24px; }

/* Vue 入场动画 */
.slide-fade-enter-active { transition: all 0.5s ease-out; }
.slide-fade-enter-from { transform: translateX(-20px); opacity: 0; }

@keyframes shimmer { 100% { left: 200%; } }
@keyframes flowRight { from { background-position: 0 0; } to { background-position: 12px 0; } }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }
</style>
