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
          <el-button plain @click="resetPath">重新规划</el-button>
        </div>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Lock, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  completeCoursePathNode,
  generateCoursePath,
  generatePathNodeResources,
  getActiveCoursePath,
  startCoursePathNode,
  type CoursePathNodeDTO,
  type CoursePathResponse,
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
  fetchActivePath()
})

onUnmounted(() => {
  stopPolling()
})

async function fetchActivePath(silent = false) {
  try {
    const res = await getActiveCoursePath()
    if (res.data.data) {
      coursePath.value = res.data.data
      await refreshTaskStatuses()
      if (needsPolling.value) {
        startPolling()
      } else {
        stopPolling()
      }
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
  stopPolling()
  
  try {
    const goal = courseGoal.value.trim()
    const res = await generateCoursePath({ goal, topic: goal, module: 'mentor' })
    coursePath.value = res.data.data
    ElMessage.success('专属学习路径已生成！')
    
    // 如果有生成中的节点，自动开启轮询
    if (needsPolling.value) {
      startPolling()
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || '路径生成失败，请重试')
  } finally {
    isGenerating.value = false
  }
}

function resetPath() {
  courseGoal.value = ''
  coursePath.value = null
  nodeTaskStatuses.value = {}
  stopPolling()
}

function startPolling() {
  if (pollTimer) return
  pollTimer = window.setInterval(async () => {
    await fetchActivePath(true)
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
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
        { agent_id: 'ppt', enabled: true, priority: 4 },
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
</style>
