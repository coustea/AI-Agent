<template>
  <div class="learn-path-container">
    <!-- 头部横幅：输入课程目标 -->
    <section class="hero-section">
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
            @keyup.enter="generatePath"
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
            @click="generatePath"
          >
            生成路径
          </el-button>
        </div>
      </div>
      <!-- 装饰性背景图或图形 -->
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
          <h2>{{ coursePath.course_name }} <span class="path-badge">专属学习地图</span></h2>
          <p class="path-meta">
            包含 {{ coursePath.total_nodes }} 个核心知识点 · 预计学习时长 {{ coursePath.estimated_hours }} 小时
          </p>
        </div>
        <div class="path-actions">
          <el-button plain @click="resetPath">重新规划</el-button>
        </div>
      </div>

      <!-- 阶段时间线布局 -->
      <div class="skill-tree-layout">
        <div 
          v-for="(phase, index) in coursePath.phases" 
          :key="index"
          class="phase-block"
        >
          <!-- 阶段标识 -->
          <div class="phase-indicator">
            <div class="phase-number">{{ Number(index) + 1 }}</div>
            <div v-if="index !== coursePath.phases.length - 1" class="phase-line"></div>
          </div>

          <!-- 阶段内容 -->
          <div class="phase-content">
            <h3 class="phase-title">{{ phase.title }}</h3>
            <p class="phase-desc">{{ phase.description }}</p>

            <!-- 节点卡片网格 -->
            <div class="nodes-grid">
              <div 
                v-for="node in phase.nodes" 
                :key="node.id"
                class="node-card"
                :class="`status-${node.status}`"
              >
                <div class="node-header">
                  <span class="node-title">{{ node.topic_name }}</span>
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
                  <p class="node-summary">{{ node.summary }}</p>
                </div>

                <div class="node-footer">
                  <el-button 
                    v-if="node.status === 'available'"
                    type="primary" 
                    class="action-btn"
                    @click="openResourceConfig(node)"
                  >
                    配置并生成资源
                    <el-icon class="el-icon--right"><ArrowRight /></el-icon>
                  </el-button>
                  <el-button 
                    v-else-if="node.status === 'completed'"
                    type="success" 
                    plain 
                    class="action-btn"
                    @click="viewResource(node)"
                  >
                    复习资源
                  </el-button>
                  <el-button 
                    v-else
                    disabled 
                    class="action-btn"
                  >
                    需完成前置节点
                    <el-icon class="el-icon--right"><Lock /></el-icon>
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <el-empty description="输入你想学的课程，开启你的专属学习之旅吧！">
        <template #image>
          <!-- 这里可以使用一个更好看的插画，为了演示使用默认 -->
        </template>
      </el-empty>
    </div>

    <!-- 微观资源配置抽屉 (Mock) -->
    <el-drawer
      v-model="drawerVisible"
      :title="`正在为「${selectedNode?.topic_name}」配置资源`"
      direction="rtl"
      size="40%"
    >
      <div class="drawer-content">
        <el-alert
          title="你已进入“微观单点突破”模式"
          type="info"
          description="系统已自动提取该节点在宏观图谱中的上下文。你可以进一步微调多智能体生成策略。"
          show-icon
          :closable="false"
          style="margin-bottom: 20px;"
        />
        
        <div class="config-form">
          <div class="config-item">
            <h4>生成深度</h4>
            <el-radio-group v-model="configMock.depth">
              <el-radio-button label="浅尝辄止" />
              <el-radio-button label="标准掌握" />
              <el-radio-button label="极客探索" />
            </el-radio-group>
          </div>
          
          <div class="config-item">
            <h4>倾向资源类型</h4>
            <el-checkbox-group v-model="configMock.types">
              <el-checkbox label="核心概念文档" />
              <el-checkbox label="思维导图" />
              <el-checkbox label="代码沙箱实操" />
              <el-checkbox label="测验题库" />
            </el-checkbox-group>
          </div>
        </div>
        
      </div>
      <template #footer>
        <div style="flex: auto">
          <el-button @click="drawerVisible = false">取消</el-button>
          <el-button type="primary" @click="startGeneration" :loading="isResourceGenerating">
            呼叫智能体团队开始生成
          </el-button>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Search, Lock, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

// ---- 状态与数据 ----
const courseGoal = ref('')
const isGenerating = ref(false)
const coursePath = ref<any>(null)

const drawerVisible = ref(false)
const selectedNode = ref<any>(null)
const isResourceGenerating = ref(false)

const configMock = ref({
  depth: '标准掌握',
  types: ['核心概念文档', '思维导图', '代码沙箱实操', '测验题库']
})

// ---- 模拟数据生成 ----
const mockGeneratePath = () => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        course_name: courseGoal.value || '数据结构',
        total_nodes: 12,
        estimated_hours: 45,
        phases: [
          {
            title: '第一阶段：线性表与基础逻辑',
            description: '掌握数据的线性结构，这是所有复杂数据结构的基础。',
            nodes: [
              { id: 'n1', topic_name: '数组与字符串', summary: '连续内存分配的利与弊，理解随机访问的本质。', status: 'completed' },
              { id: 'n2', topic_name: '链表 (单链表/双向链表)', summary: '动态内存分配，指针的艺术。这是本课程的核心难点之一。', status: 'available' },
              { id: 'n3', topic_name: '栈与队列', summary: '受限的线性表及其在算法中的神奇应用（如括号匹配、广度优先遍历）。', status: 'available' }
            ]
          },
          {
            title: '第二阶段：树形结构与非线性思维',
            description: '从一维跨越到二维，理解层级关系。',
            nodes: [
              { id: 'n4', topic_name: '二叉树基础与遍历', summary: '前中后序遍历的递归与非递归实现。', status: 'locked' },
              { id: 'n5', topic_name: '二叉搜索树 (BST)', summary: '利用结构特性提升搜索效率。', status: 'locked' },
              { id: 'n6', topic_name: '平衡二叉树 (AVL/红黑树)', summary: '如何防止树退化为链表，高级自平衡机制。', status: 'locked' }
            ]
          },
          {
            title: '第三阶段：图与进阶算法',
            description: '最通用的非线性结构，解决复杂的网状关系问题。',
            nodes: [
              { id: 'n7', topic_name: '图的存储与遍历', summary: '邻接矩阵与邻接表，DFS与BFS。', status: 'locked' },
              { id: 'n8', topic_name: '最短路径算法', summary: 'Dijkstra与Floyd算法。', status: 'locked' }
            ]
          }
        ]
      })
    }, 1500)
  })
}

// ---- 方法 ----
const generatePath = async () => {
  if (!courseGoal.value.trim()) {
    ElMessage.warning('请输入你想学习的课程名称')
    return
  }
  
  isGenerating.value = true
  coursePath.value = null
  
  try {
    // 模拟调用后端 MacroPlannerAgent API
    const data = await mockGeneratePath()
    coursePath.value = data
    ElMessage.success('专属学习路径已生成！')
  } catch (error) {
    ElMessage.error('路径生成失败，请重试')
  } finally {
    isGenerating.value = false
  }
}

const resetPath = () => {
  courseGoal.value = ''
  coursePath.value = null
}

const getStatusTagType = (status: string) => {
  const map: Record<string, string> = {
    'completed': 'success',
    'available': 'primary',
    'locked': 'info'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    'completed': '已掌握',
    'available': '已解锁 / 去学习',
    'locked': '未解锁'
  }
  return map[status] || '未知'
}

const openResourceConfig = (node: any) => {
  selectedNode.value = node
  drawerVisible.value = true
}

const viewResource = (node: any) => {
  ElMessage.success(`正在打开 ${node.topic_name} 的复习资料...`)
  // 实际项目中会跳转到资源详情页
}

const startGeneration = () => {
  isResourceGenerating.value = true
  setTimeout(() => {
    isResourceGenerating.value = false
    drawerVisible.value = false
    
    // 模拟完成状态变更
    if (selectedNode.value) {
      selectedNode.value.status = 'completed'
    }
    
    ElMessage({
      message: '多智能体协作生成完毕！资源已就绪。',
      type: 'success',
      duration: 3000
    })
  }, 2000)
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

.node-footer {
  margin-top: auto;
}

.action-btn {
  width: 100%;
  border-radius: 8px;
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
