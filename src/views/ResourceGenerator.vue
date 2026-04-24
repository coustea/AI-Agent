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
        
        <template v-if="previewData.hasFile">
          <video 
            v-if="previewData.fileCategory === 'video'" 
            :src="previewData.fileUrl" 
            controls 
            class="full-media"
          ></video>
          
          <div v-else-if="previewData.fileCategory === 'image'" class="flex-center">
            <el-image :src="previewData.fileUrl" fit="contain" class="full-media" />
          </div>
          
          <iframe 
            v-else-if="['html', 'pdf'].includes(previewData.fileCategory)" 
            :src="previewData.fileUrl" 
            class="full-iframe" 
            frameborder="0"
          ></iframe>
          
          <div v-else-if="['ppt', 'json', 'markdown', 'other'].includes(previewData.fileCategory)" class="placeholder-view">
            <el-icon class="huge-icon" :class="previewData.fileCategory === 'ppt' ? 'text-ppt' : 'text-slate'"><DataBoard v-if="previewData.fileCategory === 'ppt'"/><Document v-else/></el-icon>
            <p class="placeholder-text">{{ previewData.fileCategory === 'ppt' ? 'PPT 演示文稿' : (previewData.fileCategory.toUpperCase() + ' 文件') }}暂不支持直接内嵌预览</p>
            <el-button type="primary" size="large" @click="downloadUrl(previewData.fileUrl, previewData.title)">
              <el-icon class="mr-2"><Download /></el-icon> 立即下载文件
            </el-button>
          </div>
        </template>

        <template v-else>
          <div 
            v-if="['content', 'reading', 'ppt'].includes(previewData.agentId) || (typeof previewData.resultData === 'string' && previewData.resultData.includes('#'))" 
            class="markdown-body custom-md" 
            v-html="parseMarkdown(previewData.resultData?.content || previewData.resultData?.outline || previewData.resultData)"
          ></div>
          
          <div v-else-if="previewData.agentId === 'code'" class="code-view">
            <pre><code>{{ extractCode(previewData.resultData?.content) || previewData.resultData }}</code></pre>
          </div>
          
          <div v-else-if="previewData.agentId === 'quiz'" class="quiz-view">
            <div class="quiz-item" v-for="(q, i) in (previewData.resultData?.questions || [])" :key="i">
              <div class="q-stem"><strong>Q{{ displayIndex(i) }}:</strong> {{ q.stem }}</div>
              <div class="q-options" v-if="q.options">
                <div v-for="(opt, oi) in q.options" :key="oi" class="q-opt">{{ opt }}</div>
              </div>
              <div class="q-answer" v-if="q.answer"><strong>答案:</strong> {{ q.answer }}</div>
              <div class="q-analysis" v-if="q.analysis"><strong>解析:</strong> {{ q.analysis }}</div>
            </div>
            <pre v-if="!previewData.resultData?.questions" class="code-view"><code>{{ formatJson(previewData.resultData) }}</code></pre>
          </div>
          
          <div v-else class="code-view">
            <pre><code>{{ formatJson(previewData.resultData) }}</code></pre>
          </div>
        </template>
        
      </div>
    </el-dialog>
    
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import {
  Cpu, Document, Edit, Collection, VideoPlay, Monitor, Guide, Setting,
  Share, Connection, FolderOpened, Select, ArrowRightBold, CaretRight, Loading, CircleCheckFilled, CollectionTag, Aim, Check, Download, DataBoard
} from '@element-plus/icons-vue'

import ResourceCard from '@/components/ResourceCard.vue'
import { generateResources, recordLearningEvent, type GenerateParams, type ResourceGenerateEvent } from '@/api/ai'
import { marked } from 'marked'
import 'github-markdown-css/github-markdown-light.css'

// ================= 数据定义 =================
const isSidebarCollapsed = ref(false)
const isGenerating = ref(false)
const progress = ref(0)
const results = ref<Record<string, any>>({})
const workflowController = ref<AbortController | null>(null)

const form = reactive({
  topic: 'TCP/IP 三次握手',
  gap: '总是记不住状态流转过程',
  selected: ['content', 'mindmap', 'quiz', 'code', 'image', 'ppt'] // 默认多选几个以测试分列效果
})

// 🌟 动态排序队列 (决定前端展示顺序)
const dynamicExecutionQueue = ref<string[]>([])
const completedAgentsQueue = ref<string[]>([])

const agentConfig = [
  { id: 'content', name: '核心精讲', icon: Document },
  { id: 'mindmap', name: '思维导图', icon: Share },
  { id: 'quiz', name: '专项题库', icon: Edit },
  { id: 'code', name: '实操代码', icon: Cpu },
  { id: 'image', name: '教学配图', icon: Monitor },
  { id: 'reading', name: '拓展阅读', icon: Collection },
  { id: 'ppt', name: '演示讲稿', icon: Document },
  { id: 'video', name: '视频脚本', icon: VideoPlay }
]

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

type CoordinatorStatus = 'idle' | 'profile_loading' | 'planning' | 'core_generating' | 'persisting' | 'done'
type WorkerStatus = 'idle' | 'queued' | 'running' | 'success' | 'failed'
type NodeStatus = CoordinatorStatus | WorkerStatus

interface NodeState { status: NodeStatus; currentAction: string; }
const coordinatorState = ref<NodeState>({ status: 'idle', currentAction: '' })
const nodesState = ref<Record<string, NodeState>>({})

// ================= 计算属性 =================
const canGenerate = computed(() => form.topic.trim() !== '' && form.selected.length > 0)
const getAgentMeta = (id: string) => agentConfig.find(a => a.id === id) || { id, name: id, icon: Document }

// 🌟 核心：计算每列 4 个元素的二维数组
const chunkedExecutionQueue = computed(() => {
  const chunkSize = 4
  const chunks = []
  for (let i = 0; i < dynamicExecutionQueue.value.length; i += chunkSize) {
    chunks.push(dynamicExecutionQueue.value.slice(i, i + chunkSize))
  }
  return chunks
})
const isCoordinatorBusy = computed(() => coordinatorState.value.status !== 'idle' && coordinatorState.value.status !== 'done')

const selectAll = () => { form.selected = agentConfig.map(a => a.id) }
const getStatusTagType = (status?: string) => {
  if (status === 'running' || status === 'planning' || status === 'profile_loading' || status === 'core_generating' || status === 'persisting') return 'primary'
  if (status === 'success' || status === 'done') return 'success'
  if (status === 'failed') return 'danger'
  return 'info'
}
const getStatusText = (status?: string) => {
  if (status === 'profile_loading') return 'profile_loading'
  if (status === 'planning') return 'planning'
  if (status === 'core_generating') return 'core_generating'
  if (status === 'persisting') return 'persisting'
  if (status === 'running') return 'AI 处理中'
  if (status === 'queued') return 'queued'
  if (status === 'success' || status === 'done') return '已产出'
  if (status === 'failed') return 'failed'
  return '等待调度'
}
const workflowStageFallback: Record<string, string> = {
  profile_loading: coordinatorActions[0] || '正在读取学习者画像...',
  planning: coordinatorActions[1] || '正在生成资源计划...',
  core_generating: coordinatorActions[2] || '正在编排核心资源...',
  persisting: '正在保存本次资源包...',
  done: '资源包构建完成'
}

const agentStatusFallback: Record<string, string> = {
  queued: '等待进入执行队列...',
  running: '正在构建资源...',
  success: '资源已生成完成',
  failed: '资源生成失败'
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
  coordinatorState.value = { status: 'idle', currentAction: '' }
  Object.keys(nodesState.value).forEach((key) => {
    delete nodesState.value[key]
  })
}

const getWorkflowActionText = (status: string, message?: string) => {
  return message || workflowStageFallback[status] || coordinatorActions[0] || '正在协调任务...'
}

const getAgentActionText = (agentId: string, status: string, message?: string) => {
  const fallbackList = friendlyActions[agentId] || []
  return message || agentStatusFallback[status] || fallbackList[0] || '正在构建资源...'
}

const getEventString = (event: ResourceGenerateEvent, key: string) => {
  const value = event[key]
  return typeof value === 'string' ? value : ''
}

const getEventNumber = (event: ResourceGenerateEvent, key: string) => {
  const value = event[key]
  return typeof value === 'number' ? value : undefined
}

const displayIndex = (index: string | number) => Number(index) + 1

const applyWorkflowEvent = (event: ResourceGenerateEvent) => {
  const stage = getEventString(event, 'stage')
  const message = getEventString(event, 'message')
  coordinatorState.value.status = (stage || 'planning') as CoordinatorStatus
  coordinatorState.value.currentAction = getWorkflowActionText(stage, message)
}

const applyAgentStatusEvent = (event: ResourceGenerateEvent) => {
  const agentId = getEventString(event, 'agent')
  const status = getEventString(event, 'status') as WorkerStatus
  if (!agentId || !status) return

  if (!dynamicExecutionQueue.value.includes(agentId)) {
    dynamicExecutionQueue.value.push(agentId)
  }

  const node = ensureNodeState(agentId)
  node.status = status
  node.currentAction = getAgentActionText(agentId, status, getEventString(event, 'message'))
}

const applyAgentLogEvent = (event: ResourceGenerateEvent) => {
  const agentId = getEventString(event, 'agent')
  const logText = getEventString(event, 'log')
  if (!agentId || !logText) return

  if (agentId === 'coordinator') {
    coordinatorState.value.currentAction = logText
    return
  }

  const node = ensureNodeState(agentId)
  node.currentAction = logText
}

const applyArtifactReadyEvent = (event: ResourceGenerateEvent) => {
  const agentId = getEventString(event, 'agent')
  if (!agentId) return

  const artifact = event.artifact ?? event.data ?? event.result ?? null
  if (artifact != null) {
    results.value[agentId] = artifact
  }

  if (!dynamicExecutionQueue.value.includes(agentId)) {
    dynamicExecutionQueue.value.push(agentId)
  }

  const node = ensureNodeState(agentId)
  node.status = 'success'
  node.currentAction = getAgentActionText(agentId, 'success', getEventString(event, 'message'))

  if (!completedAgentsQueue.value.includes(agentId)) {
    completedAgentsQueue.value.push(agentId)
  }

  recordLearningEvent({
    event_type: 'resource_completed',
    course: form.topic.trim(),
    topic: getAgentMeta(agentId).name,
    metadata: { agent: agentId },
  }).catch((err) => {
    console.warn('[ResourceGenerator] record learning event failed:', err)
  })
}

const applyBundleUpdateEvent = (event: ResourceGenerateEvent) => {
  const completed = getEventNumber(event, 'completed')
  const total = getEventNumber(event, 'total')
  if (typeof completed === 'number' && typeof total === 'number' && total > 0) {
    progress.value = Math.min(100, Math.round((completed / total) * 100))
  }

  const latestAgent = getEventString(event, 'latest_agent')
  if (latestAgent) {
    if (!dynamicExecutionQueue.value.includes(latestAgent)) {
      dynamicExecutionQueue.value.push(latestAgent)
    }
    const node = ensureNodeState(latestAgent)
    if (node.status === 'queued') {
      node.status = 'running'
    }
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
      coordinatorState.value.currentAction = getWorkflowActionText('done', getEventString(event, 'message'))
      progress.value = 100
      isGenerating.value = false
      workflowController.value = null
      break
  }
}

const buildGenerateParams = (): GenerateParams => ({
  learning_task: {
    course: form.topic.trim(),
    gap: form.gap.trim(),
    need: 'review',
    extra: '',
  },
  selected_resources: [...form.selected],
})

// ================= 预览功能 =================
const previewDialogVisible = ref(false)
const previewData = ref<any>(null)

const handlePreview = (data: any) => {
  previewData.value = data
  previewDialogVisible.value = true
}

const parseMarkdown = (text: string) => {
  if (!text) return ''
  return marked.parse(text)
}

const extractCode = (text: string) => {
  if (!text) return ''
  return text.replace(/```[\w]*\n/g, '').replace(/```/g, '')
}

const formatJson = (data: any) => {
  try {
    return JSON.stringify(data, null, 2)
  } catch (e) {
    return String(data)
  }
}

const downloadUrl = (url: string, title: string) => {
  const link = document.createElement('a')
  link.href = url
  link.target = '_blank'
  link.download = title || 'download'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
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
    buildGenerateParams(),
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
