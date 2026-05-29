<template>
  <div class="learn-path-container">
    <!-- 头部横幅：输入课程目标 -->
    <section class="hero-section" v-if="!coursePath && !isGenerating">
      <div class="hero-content">
        <h1 class="hero-title">系统学习路径规划</h1>
        <p class="hero-subtitle">
          输入你想要系统学习的课程或专业领域，AI 将基于高校标准知识库为你生成一棵科学的专属技能树。
        </p>
        <div class="search-box">
          <el-input
            v-model="courseGoal"
            placeholder="例如：数据结构、计算机网络、微观经济学..."
            class="course-input"
            size="large"
            @keyup.enter="handleGeneratePath"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button 
            type="primary" 
            size="large" 
            class="generate-btn"
            :loading="isGenerating"
            @click="handleGeneratePath"
          >
            生成路径
          </el-button>
        </div>
      </div>
      <div class="hero-bg-decoration"></div>
    </section>

    <!-- 骨架屏：生成中 -->
    <div v-if="isGenerating" class="loading-state">
      <el-skeleton :rows="3" animated class="skeleton-header" />
      <div class="skeleton-grid">
        <el-skeleton-item variant="image" class="skeleton-card" />
        <el-skeleton-item variant="image" class="skeleton-card" />
        <el-skeleton-item variant="image" class="skeleton-card" />
      </div>
      <p class="loading-text">正在检索高校标准大纲并构建专属技能树...</p>
    </div>

    <!-- 技能树展示区 -->
    <div v-else-if="coursePath" class="path-display-section">
      <div class="path-header">
        <div class="path-title-group">
          <h2>{{ coursePath.title }} <span class="path-badge">专属学习地图</span></h2>
          <p class="path-meta">
            包含 {{ coursePath.nodes.length }} 个核心知识点 · 预计学习时长 {{ coursePath.eta_days }} 天
          </p>
        </div>
        <div class="path-actions">
          <el-button type="primary" plain @click="openOptimizationDialog" class="opt-btn-action">
            <el-icon class="btn-icon"><MagicStick /></el-icon>
            诊断优化路径
          </el-button>
          <el-button plain @click="resetPath">重新规划</el-button>
        </div>
      </div>

      <!-- 智能诊断建议卡片 -->
      <transition name="el-zoom-in-top">
        <div v-if="coursePath.needs_optimization && coursePath.optimization_tips?.length" class="diagnostic-card">
          <div class="diagnostic-header">
            <el-icon class="diagnostic-icon"><Cpu /></el-icon>
            <span class="diagnostic-title">AI 学习诊断与优化建议</span>
          </div>
          <div class="diagnostic-body">
            <ul class="tips-list">
              <li v-for="(tip, i) in coursePath.optimization_tips" :key="i" class="tip-item">
                <el-icon class="tip-icon"><Warning /></el-icon>
                <span>{{ tip }}</span>
              </li>
            </ul>
            <div class="diagnostic-actions">
              <el-button type="primary" size="default" class="optimize-btn-cta" @click="openOptimizationDialog">
                <el-icon class="btn-icon"><MagicStick /></el-icon>
                一键诊断并优化路径
              </el-button>
            </div>
          </div>
        </div>
      </transition>

      <!-- 路径微调说明 -->
      <div v-if="coursePath.adjustment_rationale && coursePath.adjustment_rationale.length > 0" class="adjustment-banner">
        <div class="banner-title">
          <el-icon class="banner-title-icon"><InfoFilled /></el-icon>
          <span>路径微调说明</span>
        </div>
        <ul class="rationale-list">
          <li v-for="(rat, i) in coursePath.adjustment_rationale" :key="i" class="rationale-item">
            {{ rat }}
          </li>
        </ul>
      </div>

      <!-- 阶段时间线布局 -->
      <div class="skill-tree-layout">
        <div 
          v-for="(stage, index) in groupedStages" 
          :key="stage.stage_id"
          class="phase-block"
        >
          <!-- 阶段标识 -->
          <div class="phase-indicator">
            <div class="phase-number">{{ index + 1 }}</div>
            <div v-if="index !== groupedStages.length - 1" class="phase-line"></div>
          </div>

          <!-- 阶段内容 -->
          <div class="phase-content">
            <h3 class="phase-title">{{ stage.title }}</h3>
            <p class="phase-desc">{{ stage.description }}</p>

            <!-- 节点卡片网格 -->
            <div class="nodes-grid" v-if="stage.nodes && stage.nodes.length > 0">
              <div 
                v-for="node in stage.nodes" 
                :key="node.id"
                class="node-card"
                :class="`status-${node.status}`"
              >
                <div class="node-header">
                  <span class="node-title">{{ node.title }}</span>
                  <el-tag 
                    :type="getStatusTagType(node.status)" 
                    size="small" 
                    effect="light"
                    class="status-tag"
                  >
                    {{ getStatusText(node.status) }}
                  </el-tag>
                </div>
                
                <div class="node-body">
                  <p class="node-summary">{{ node.recommendation_reason || node.mastery_target }}</p>
                  <div v-if="node.resource_status === 'generating' && getNodeTaskStatus(node)" class="task-progress">
                    <div class="task-progress-head">
                      <span>{{ getNodeTaskStatus(node)?.progress.latest_message || '资源团队正在工作' }}</span>
                      <strong>{{ getNodeProgress(node) }}%</strong>
                    </div>
                    <el-progress :percentage="getNodeProgress(node)" :show-text="false" />
                    <div class="agent-progress-list">
                      <span
                        v-for="(snapshot, agentId) in getNodeTaskStatus(node)?.progress.agents"
                        :key="agentId"
                        class="agent-chip"
                        :class="`agent-${snapshot.status}`"
                      >
                        {{ getAgentLabel(agentId) }} · {{ getAgentStatusText(snapshot.status) }}
                      </span>
                    </div>
                  </div>
                </div>

                <div class="node-footer">
                  <!-- Available + not_started: show "生成学习资料" -->
                  <el-button
                    v-if="node.status === 'available' && node.resource_status === 'not_started'"
                    type="primary"
                    class="action-btn"
                    :loading="generatingNodeId === node.id"
                    @click="handleGenerateResources(node)"
                  >
                    生成学习资料
                    <el-icon v-if="generatingNodeId !== node.id" class="el-icon--right"><ArrowRight /></el-icon>
                  </el-button>
                  <!-- Available + generating: disabled with loading -->
                  <el-button
                    v-else-if="node.status === 'available' && node.resource_status === 'generating'"
                    type="primary"
                    plain
                    loading
                    class="action-btn"
                  >
                    AI资源生成中...
                  </el-button>
                  <!-- Available + ready: begin the persisted learning node -->
                  <el-button
                    v-else-if="node.status === 'available' && node.resource_status === 'ready'"
                    type="primary"
                    class="action-btn"
                    @click="handleStartLearning(node)"
                  >
                    开始学习
                    <el-icon class="el-icon--right"><ArrowRight /></el-icon>
                  </el-button>
                  <!-- Available + failed: show "重新生成" -->
                  <el-button
                    v-else-if="node.status === 'available' && node.resource_status === 'failed'"
                    type="warning"
                    class="action-btn"
                    @click="handleGenerateResources(node)"
                  >
                    重新生成
                  </el-button>
                  <div v-else-if="node.status === 'in_progress'" class="active-actions">
                    <el-button class="action-btn" @click="viewResource(node)">继续学习</el-button>
                    <el-button
                      type="success"
                      class="action-btn"
                      :loading="completingNodeId === node.id"
                      @click="handleCompleteNode(node)"
                    >
                      完成本节点
                    </el-button>
                  </div>
                  <el-button
                    v-else-if="node.status === 'completed'"
                    type="success"
                    plain
                    class="action-btn"
                    @click="viewResource(node)"
                  >
                    复习资源
                  </el-button>
                  <!-- Locked: disabled -->
                  <el-button
                    v-else-if="node.status === 'locked'"
                    disabled
                    class="action-btn"
                  >
                    需完成前置节点
                    <el-icon class="el-icon--right"><Lock /></el-icon>
                  </el-button>
                  <el-button
                    v-else
                    disabled
                    class="action-btn"
                  >
                    未就绪
                  </el-button>
                </div>
              </div>
            </div>
            <!-- 对于还没有生成的后续阶段 -->
            <div v-else class="nodes-empty">
              <el-alert title="随进度动态解锁中..." type="info" :closable="false" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 路径调整与诊断优化对话框 -->
    <el-dialog
      v-model="showOptimizeDialog"
      title="学习路径智能诊断与微调"
      width="540px"
      border-radius="16px"
      class="optimize-dialog"
    >
      <div class="dialog-desc">
        AI 将根据你最近的知识掌握情况（如测验成绩、学习偏好等）和你的反馈，精细化调整后续的学习节点。已学完的节点将保持不变。
      </div>
      
      <div class="preset-section">
        <span class="section-label">快捷诊断意图：</span>
        <div class="preset-tags">
          <el-tag
            v-for="tag in presetTags"
            :key="tag"
            class="preset-tag"
            :effect="customFeedback === tag ? 'dark' : 'plain'"
            type="info"
            @click="selectPresetTag(tag)"
          >
            {{ tag }}
          </el-tag>
        </div>
      </div>
      
      <div class="feedback-input-section">
        <span class="section-label">自定义微调要求（可选）：</span>
        <el-input
          v-model="customFeedback"
          type="textarea"
          :rows="4"
          placeholder="例如：我觉得目前的理论有点深，希望能放缓坡度，增加一些更基础的图解材料和代码练习案例。"
          maxlength="200"
          show-word-limit
        />
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showOptimizeDialog = false">取消</el-button>
          <el-button type="primary" :loading="isOptimizing" @click="handleOptimizePath">
            开始诊断并应用优化
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- AI 诊断与优化加载中动画 -->
    <div v-if="isOptimizing" class="optimizing-overlay">
      <div class="optimizing-box">
        <div class="glowing-spinner">
          <div class="spinner-inner"></div>
        </div>
        <h3 class="optimizing-title">AI 智能诊断与路径微调中</h3>
        <p class="optimizing-subtitle">正在计算最佳学习路径...</p>
        
        <div class="step-progress">
          <div 
            v-for="(step, idx) in optimizeSteps" 
            :key="idx" 
            class="step-item"
            :class="{ active: idx <= currentOptimizeStep, completed: idx < currentOptimizeStep }"
          >
            <el-icon class="step-icon">
              <CircleCheck v-if="idx < currentOptimizeStep" />
              <Loading v-else-if="idx === currentOptimizeStep" />
              <CircleClose v-else />
            </el-icon>
            <span>{{ step }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search,
  Lock,
  ArrowRight,
  Cpu,
  Warning,
  MagicStick,
  InfoFilled,
  CircleCheck,
  CircleClose,
  Loading,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  completeCoursePathNode,
  generateCoursePath,
  getActiveCoursePathTask,
  getCoursePathTaskStatus,
  generatePathNodeResources,
  getActiveCoursePath,
  startCoursePathNode,
  adjustCoursePath,
  type CoursePathNodeDTO,
  type CoursePathResponse,
  type PathGenerationTaskResponse,
  type PathNodeResourceRequest,
} from '@/api/ai'
import { pollResourceStatus, type ResourceTaskStatus } from '@/api/resource'

const router = useRouter()

const courseGoal = ref('')
const isGenerating = ref(false)
const generatingNodeId = ref<number | null>(null)
const completingNodeId = ref<number | null>(null)
const coursePath = ref<CoursePathResponse | null>(null)
const nodeTaskStatuses = ref<Record<number, ResourceTaskStatus>>({})
const activePathTask = ref<PathGenerationTaskResponse | null>(null)

const showOptimizeDialog = ref(false)
const isOptimizing = ref(false)
const customFeedback = ref('')
const currentOptimizeStep = ref(0)
const presetTags = [
  '测验成绩不理想，需要强化复习',
  '概念过于抽象，希望增加图解和案例',
  '时间紧迫，快速突破核心要点',
  '偏好实践，多提供一些代码实操'
]
const optimizeSteps = [
  '正在读取历史学习数据与测试成绩...',
  '智能分析画像并检测薄弱知识点...',
  '构建增量规划图并调整后续节点...',
  '重新编排依赖拓扑并生成新地图...'
]

const groupedStages = computed(() => {
  if (!coursePath.value) return []
  
  const stages = coursePath.value.stages.map(stage => ({
    ...stage,
    nodes: coursePath.value!.nodes.filter(n => n.stage_id === stage.stage_id)
  }))
  return stages
})

const needsPolling = computed(() => {
  if (!coursePath.value) return false
  return coursePath.value.nodes.some(n => n.resource_status === 'generating')
})

let pollTimer: number | null = null
const agentLabels: Record<string, string> = {
  content: '讲解',
  mindmap: '图解',
  quiz: '练习',
  reading: '阅读',
  code: '实操',
  ppt: '课件',
}

onMounted(() => {
  initializePathView()
})

onUnmounted(() => {
  stopPolling()
})

async function initializePathView() {
  const hasActivePath = await fetchExistingPath()
  if (hasActivePath) return
  await resumePathGenerationTask()
}

async function fetchExistingPath() {
  try {
    const res = await getActiveCoursePath()
    if (res.data.data) {
      coursePath.value = res.data.data
      activePathTask.value = null
      isGenerating.value = false
      await refreshTaskStatuses()
      if (needsPolling.value) {
        startPolling()
      } else {
        stopPolling()
      }
      return true
    }
  } catch (error) {
    console.error('鎷夊彇璺緞澶辫触', error)
  }
  coursePath.value = null
  return false
}

async function resumePathGenerationTask() {
  try {
    const res = await getActiveCoursePathTask()
    const task = res.data.data
    if (!task) {
      activePathTask.value = null
      isGenerating.value = false
      return
    }

    activePathTask.value = task
    if (task.status === 'completed') {
      isGenerating.value = false
      await fetchActivePath(true)
      return
    }

    if (task.status === 'failed') {
      isGenerating.value = false
      return
    }

    isGenerating.value = true
    startPolling()
  } catch (error) {
    console.error('鎭㈠璺緞鐢熸垚浠诲姟澶辫触', error)
  }
}

async function fetchActivePath(silent = false) {
  try {
    const res = await getActiveCoursePath()
    if (res.data.data) {
      coursePath.value = res.data.data
      activePathTask.value = null
      isGenerating.value = false
      await refreshTaskStatuses()
      if (needsPolling.value) {
        startPolling()
      } else {
        stopPolling()
      }
    } else if (!silent) {
      coursePath.value = null
    }
  } catch (error) {
    if (!silent) {
      console.error('拉取路径失败', error)
    }
  }
}

async function handleGeneratePath() {
  if (!courseGoal.value.trim()) {
    ElMessage.warning('请输入你想学习的课程名称')
    return
  }
  
  isGenerating.value = true
  coursePath.value = null
  activePathTask.value = null
  nodeTaskStatuses.value = {}
  stopPolling()
  
  try {
    const goal = courseGoal.value.trim()
    const res = await generateCoursePath({ goal, topic: goal, module: 'mentor' })
    activePathTask.value = res.data.data
    ElMessage.success('专属学习路径已生成！')
    
    startPolling()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '路径生成失败，请重试')
  } finally {
    if (!activePathTask.value) {
      isGenerating.value = false
    }
  }
}

function resetPath() {
  courseGoal.value = ''
  coursePath.value = null
  activePathTask.value = null
  isGenerating.value = false
  nodeTaskStatuses.value = {}
  stopPolling()
}

function startPolling() {
  if (pollTimer) return
  pollTimer = window.setInterval(async () => {
    await pollPageState()
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function pollPageState() {
  if (activePathTask.value && isGenerating.value) {
    await refreshPathTaskStatus()
    return
  }
  await fetchActivePath(true)
}

async function refreshPathTaskStatus() {
  if (!activePathTask.value) return

  try {
    const res = await getCoursePathTaskStatus(activePathTask.value.task_id)
    const task = res.data.data
    activePathTask.value = task

    if (task.status === 'completed') {
      isGenerating.value = false
      await fetchActivePath(true)
      stopPolling()
      ElMessage.success('专属学习路径已生成！')
      return
    }

    if (task.status === 'failed') {
      isGenerating.value = false
      stopPolling()
      ElMessage.error(task.error_message || task.latest_message || '路径生成失败，请重试')
      return
    }

    isGenerating.value = true
  } catch (error) {
    console.error('刷新路径任务状态失败', error)
  }
}

function getStatusTagType(status: string) {
  const map: Record<string, string> = {
    'completed': 'success',
    'available': 'primary',
    'in_progress': 'warning',
    'locked': 'info'
  }
  return map[status] || 'info'
}

function getStatusText(status: string) {
  const map: Record<string, string> = {
    'completed': '已掌握',
    'available': '已解锁 / 去学习',
    'in_progress': '学习中',
    'locked': '未解锁'
  }
  return map[status] || '未知'
}

function getNodeTaskStatus(node: CoursePathNodeDTO) {
  return node.resource_id ? nodeTaskStatuses.value[node.resource_id] : undefined
}

function getNodeProgress(node: CoursePathNodeDTO) {
  return Math.round(getNodeTaskStatus(node)?.progress.progress || 0)
}

function getAgentLabel(agentId: string) {
  return agentLabels[agentId] || agentId
}

function getAgentStatusText(status: string) {
  const labels: Record<string, string> = {
    waiting: '等待',
    running: '生成中',
    success: '完成',
    failed: '失败',
    skipped: '跳过',
  }
  return labels[status] || status
}

async function refreshTaskStatuses() {
  const generatingNodes = coursePath.value?.nodes.filter(
    node => node.resource_status === 'generating' && node.resource_id,
  ) || []
  await Promise.all(generatingNodes.map(async (node) => {
    if (!node.resource_id) return
    try {
      nodeTaskStatuses.value[node.resource_id] = await pollResourceStatus(node.resource_id)
    } catch {
      // Path polling remains the source of truth when one progress snapshot fails.
    }
  }))
}

async function handleGenerateResources(node: CoursePathNodeDTO) {
  if (generatingNodeId.value) return
  generatingNodeId.value = node.id
  try {
    const defaultPayload: PathNodeResourceRequest = {
      selected_agents: [
        { agent_id: 'content', enabled: true, priority: 0 },
        { agent_id: 'mindmap', enabled: true, priority: 1 },
        { agent_id: 'quiz', enabled: true, priority: 2 },
        { agent_id: 'reading', enabled: true, priority: 3 },
        { agent_id: 'code', enabled: true, priority: 4 },
        { agent_id: 'ppt', enabled: true, priority: 5 },
      ],
      agent_configs: {},
      output_options: { output_format: 'json' },
    }
    const res = await generatePathNodeResources(node.id, defaultPayload)
    ElMessage.success(`已开始生成「${node.title}」的学习资料`)
    if (coursePath.value) {
      const found = coursePath.value.nodes.find(n => n.id === node.id)
      if (found) {
        found.resource_status = res.data.data.status
        found.resource_id = res.data.data.resource_id
      }
    }
    await refreshTaskStatuses()
    startPolling()
  } catch (error: any) {
    ElMessage.error(error?.message || '生成资料失败，请重试')
  } finally {
    generatingNodeId.value = null
  }
}

async function handleStartLearning(node: CoursePathNodeDTO) {
  try {
    const res = await startCoursePathNode(node.id)
    coursePath.value = res.data.data
    viewResource(coursePath.value.nodes.find(item => item.id === node.id) || node)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '暂时无法开始学习')
  }
}

async function handleCompleteNode(node: CoursePathNodeDTO) {
  completingNodeId.value = node.id
  try {
    const res = await completeCoursePathNode(node.id)
    coursePath.value = res.data.data
    ElMessage.success(`「${node.title}」已完成，下一学习节点已更新`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '完成节点失败，请重试')
  } finally {
    completingNodeId.value = null
  }
}

function viewResource(node: CoursePathNodeDTO) {
  if (node.resource_id) {
    router.push({ name: 'ResourceDetail', params: { id: node.resource_id } })
  } else {
    ElMessage.warning('资源未就绪')
  }
}

function openOptimizationDialog() {
  customFeedback.value = ''
  showOptimizeDialog.value = true
}

function selectPresetTag(tag: string) {
  customFeedback.value = tag
}

async function handleOptimizePath() {
  const feedbackText = customFeedback.value.trim() || '依据画像诊断自动优化'
  showOptimizeDialog.value = false
  isOptimizing.value = true
  currentOptimizeStep.value = 0
  
  const interval = window.setInterval(() => {
    if (currentOptimizeStep.value < optimizeSteps.length - 1) {
      currentOptimizeStep.value++
    }
  }, 1200)

  try {
    const res = await adjustCoursePath({ feedback: feedbackText })
    await new Promise(resolve => setTimeout(resolve, 800))
    coursePath.value = res.data.data
    ElMessage.success('学习路径优化成功！已更新后续学习节点。')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '路径优化失败，请重试')
  } finally {
    clearInterval(interval)
    isOptimizing.value = false
    currentOptimizeStep.value = 0
  }
}
</script>

<style scoped>
/* 全局容器变量与基础设定，保持高级感和克制 */
.learn-path-container {
  --primary-color: #4f46e5;
  --primary-light: #e0e7ff;
  --text-main: #1e293b;
  --text-muted: #64748b;
  --bg-main: #f8fafc;
  --border-color: #e2e8f0;
  
  padding: 24px 40px;
  max-width: 1200px;
  margin: 0 auto;
  min-height: calc(100vh - 64px);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* 头部 Hero Section */
.hero-section {
  position: relative;
  background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%);
  border-radius: 24px;
  padding: 48px;
  margin-bottom: 40px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03), inset 0 2px 0 rgba(255, 255, 255, 1);
  overflow: hidden;
  text-align: center;
}

.hero-content {
  position: relative;
  z-index: 2;
  max-width: 680px;
  margin: 0 auto;
}

.hero-title {
  font-size: 32px;
  font-weight: 800;
  color: var(--text-main);
  margin-bottom: 16px;
  letter-spacing: -0.5px;
}

.hero-subtitle {
  font-size: 16px;
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 32px;
}

.search-box {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.course-input {
  width: 400px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.02);
}
:deep(.course-input .el-input__wrapper) {
  border-radius: 12px;
  padding-left: 16px;
}

.generate-btn {
  border-radius: 12px;
  padding: 0 32px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

/* 加载状态骨架屏 */
.loading-state {
  padding: 40px 0;
  text-align: center;
}
.skeleton-header {
  max-width: 600px;
  margin: 0 auto 40px;
}
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 24px;
}
.skeleton-card {
  height: 180px;
  border-radius: 16px;
}
.loading-text {
  color: var(--primary-color);
  font-weight: 500;
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* 技能树主干容器 */
.path-display-section {
  animation: fadeIn 0.5s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.path-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 40px;
  padding-bottom: 20px;
  border-bottom: 2px dashed var(--border-color);
}

.path-title-group h2 {
  font-size: 28px;
  color: var(--text-main);
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.path-badge {
  font-size: 13px;
  background: var(--primary-light);
  color: var(--primary-color);
  padding: 4px 12px;
  border-radius: 20px;
  font-weight: 600;
}

.path-meta {
  color: var(--text-muted);
  font-size: 14px;
  margin: 0;
}

/* 时间线式的技能树布局 */
.skill-tree-layout {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.phase-block {
  display: flex;
  gap: 32px;
}

.phase-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 40px;
}

.phase-number {
  width: 40px;
  height: 40px;
  background: var(--primary-color);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
  z-index: 2;
}

.phase-line {
  flex-grow: 1;
  width: 2px;
  background: linear-gradient(to bottom, var(--primary-color) 0%, #cbd5e1 100%);
  margin-top: 8px;
  margin-bottom: 8px;
  border-radius: 2px;
}

.phase-content {
  flex-grow: 1;
  padding-bottom: 64px;
}

.phase-title {
  font-size: 20px;
  color: var(--text-main);
  margin: 0 0 8px 0;
}

.phase-desc {
  color: var(--text-muted);
  font-size: 14px;
  margin: 0 0 24px 0;
}

/* 节点网格卡片 */
.nodes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.node-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid var(--border-color);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
}

.node-card.status-available {
  border-color: rgba(79, 70, 229, 0.3);
  box-shadow: 0 8px 24px rgba(79, 70, 229, 0.08);
}
.node-card.status-available:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(79, 70, 229, 0.12);
}

.node-card.status-locked {
  background: #f8fafc;
  opacity: 0.8;
}

.node-card.status-completed {
  border-color: rgba(16, 185, 129, 0.3);
  background: #f0fdf4;
}

.node-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.node-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.4;
}

.node-body {
  flex-grow: 1;
  margin-bottom: 20px;
}

.node-summary {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
  margin: 0;
}

.task-progress {
  margin-top: 18px;
  padding: 12px;
  border-radius: 12px;
  background: #eef6ff;
}

.task-progress-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 12px;
  color: var(--text-muted);
}

.task-progress-head strong {
  color: var(--primary-color);
}

.agent-progress-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.agent-chip {
  padding: 3px 8px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #475569;
  font-size: 11px;
}

.agent-running {
  background: #dbeafe;
  color: #2563eb;
}

.agent-success {
  background: #dcfce7;
  color: #15803d;
}

.agent-failed {
  background: #fee2e2;
  color: #dc2626;
}

.node-footer {
  margin-top: auto;
}

.action-btn {
  width: 100%;
  border-radius: 8px;
}

.active-actions {
  display: flex;
  gap: 8px;
}

.active-actions .action-btn + .action-btn {
  margin-left: 0;
}

/* 空状态 */
.empty-state {
  padding: 60px 0;
}

/* 抽屉内样式 */
.drawer-content {
  padding: 0 20px;
}
.config-item {
  margin-bottom: 32px;
}
.config-item h4 {
  margin: 0 0 16px 0;
  color: var(--text-main);
}

/* AI 诊断卡片样式 - 流光渐变与高级边框 */
.diagnostic-card {
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.04) 0%, rgba(147, 51, 234, 0.04) 100%);
  border: 1px solid rgba(79, 70, 229, 0.2);
  border-radius: 16px;
  padding: 20px 24px;
  margin-bottom: 24px;
  box-shadow: 0 4px 16px rgba(79, 70, 229, 0.05);
}

.diagnostic-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.diagnostic-icon {
  font-size: 20px;
  color: var(--primary-color);
  animation: rotateGlow 3s linear infinite;
}

@keyframes rotateGlow {
  0% { transform: rotate(0deg); filter: drop-shadow(0 0 2px var(--primary-color)); }
  50% { filter: drop-shadow(0 0 6px #9333ea); }
  100% { transform: rotate(360deg); filter: drop-shadow(0 0 2px var(--primary-color)); }
}

.diagnostic-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.2px;
}

.tips-list {
  list-style: none;
  padding: 0;
  margin: 0 0 16px 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tip-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
}

.tip-icon {
  font-size: 16px;
  color: #ea580c;
  margin-top: 2px;
}

.diagnostic-actions {
  display: flex;
  justify-content: flex-start;
}

.optimize-btn-cta {
  border-radius: 10px;
  padding: 8px 18px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);
}

/* 路径微调说明 Banner */
.adjustment-banner {
  background: #f8fafc;
  border-left: 4px solid var(--primary-color);
  border-radius: 4px 12px 12px 4px;
  padding: 16px 20px;
  margin-bottom: 32px;
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
  border-right: 1px solid var(--border-color);
}

.banner-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 14px;
  color: var(--text-main);
  margin-bottom: 8px;
}

.banner-title-icon {
  color: var(--primary-color);
}

.rationale-list {
  padding-left: 20px;
  margin: 0;
}

.rationale-item {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.7;
  margin-bottom: 4px;
}

/* 路径诊断对话框与预设标签 */
.dialog-desc {
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 24px;
}

.preset-section, .feedback-input-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 24px;
}

.section-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.preset-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preset-tag {
  cursor: pointer;
  border-radius: 8px;
  padding: 6px 12px;
  transition: all 0.2s ease;
}

.preset-tag:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

/* AI 诊断覆盖加载中全屏 Overlay */
.optimizing-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(15, 23, 42, 0.85); /* 极暗的高级遮罩 */
  backdrop-filter: blur(10px); /* 玻璃毛玻璃效果 */
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: overlayFadeIn 0.3s ease-out forwards;
}

@keyframes overlayFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.optimizing-box {
  background: white;
  border-radius: 24px;
  padding: 40px 48px;
  width: 460px;
  text-align: center;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  align-items: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
  animation: boxPopUp 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
}

@keyframes boxPopUp {
  from { transform: scale(0.9) translateY(20px); opacity: 0; }
  to { transform: scale(1) translateY(0); opacity: 1; }
}

/* 渐变发光 Spinner */
.glowing-spinner {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary-color) 0%, #9333ea 50%, #06b6d4 100%);
  padding: 4px;
  animation: spinGlow 2s linear infinite;
  margin-bottom: 24px;
}

.spinner-inner {
  width: 100%;
  height: 100%;
  background: white;
  border-radius: 50%;
}

@keyframes spinGlow {
  0% { transform: rotate(0deg); box-shadow: 0 0 10px rgba(79, 70, 229, 0.4); }
  50% { box-shadow: 0 0 24px rgba(147, 51, 234, 0.7); }
  100% { transform: rotate(360deg); box-shadow: 0 0 10px rgba(79, 70, 229, 0.4); }
}

.optimizing-title {
  font-size: 20px;
  font-weight: 800;
  color: var(--text-main);
  margin: 0 0 8px 0;
}

.optimizing-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0 0 32px 0;
}

/* 步骤进度线 */
.step-progress {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  text-align: left;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: #94a3b8;
  transition: all 0.3s ease;
}

.step-icon {
  font-size: 16px;
}

.step-item.active {
  color: var(--primary-color);
  font-weight: 600;
}

.step-item.completed {
  color: #10b981;
}

.opt-btn-action {
  border-radius: 10px;
}
.opt-btn-action .el-icon {
  margin-right: 4px;
}
</style>
