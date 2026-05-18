<template>
  <div class="command-center-modern">
    <header class="page-header fade-in-up">
      <div class="header-content">
        <h1 class="page-title">全景中枢</h1>
        <p class="page-subtitle">
          聚合学习任务、资源状态与下一步行动，帮助你高效推进学习闭环。
        </p>
      </div>
      <div class="header-actions">
        <el-button type="primary" round size="large" class="shadow-btn" @click="router.push('/tutor')">
          继续学习 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
        <el-button plain round size="large" @click="router.push('/path-planner')">
          查看完整路径
        </el-button>
      </div>
    </header>

    <section class="metrics-grid fade-in-up" style="animation-delay: 0.1s">
      <div class="metric-card">
        <div class="metric-top">
          <div class="metric-value">{{ metrics.activePaths }}</div>
          <div class="metric-icon bg-blue-light"><el-icon class="text-blue"><Position /></el-icon></div>
        </div>
        <div class="metric-info">
          <h4 class="metric-name">进行中路径</h4>
          <p class="metric-desc">正在推进的学习计划</p>
        </div>
        <div class="metric-action">
          <el-button link type="primary" @click="router.push('/path-planner')">查看路径</el-button>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-top">
          <div class="metric-value">{{ metrics.availableResources }}</div>
          <div class="metric-icon bg-indigo-light"><el-icon class="text-indigo"><Cpu /></el-icon></div>
        </div>
        <div class="metric-info">
          <h4 class="metric-name">已生成资源</h4>
          <p class="metric-desc">可用于学习、练习和复习的个性化资源</p>
        </div>
        <div class="metric-action">
          <el-button link type="primary" @click="router.push('/profile-assistant')">查看资源</el-button>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-top">
          <div class="metric-value">{{ metrics.pendingTasks }}</div>
          <div class="metric-icon bg-amber-light"><el-icon class="text-amber"><List /></el-icon></div>
        </div>
        <div class="metric-info">
          <h4 class="metric-name">待完成任务</h4>
          <p class="metric-desc">来自学习路径和评估结果的待办事项</p>
        </div>
        <div class="metric-action">
          <el-button link type="primary" @click="router.push('/path-planner')">处理任务</el-button>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-top">
          <div class="metric-value">{{ metrics.recentScore }}</div>
          <div class="metric-icon bg-emerald-light"><el-icon class="text-emerald"><DataAnalysis /></el-icon></div>
        </div>
        <div class="metric-info">
          <h4 class="metric-name">最近评估得分</h4>
          <p class="metric-desc">反映当前阶段的知识掌握情况</p>
        </div>
        <div class="metric-action">
          <el-button link type="primary" @click="router.push('/evaluation')">查看评估</el-button>
        </div>
      </div>
    </section>

    <section class="loop-banner fade-in-up" style="animation-delay: 0.2s">
      <div class="loop-header">
        <h3>学习闭环</h3>
        <p>从薄弱点识别到资源生成、路径规划、智能辅导和学习评估，形成完整的个性化学习流程。</p>
      </div>
      <div class="loop-nodes">
        <div class="loop-node">
          <h4 class="node-title">薄弱点识别</h4>
          <p class="node-desc">发现当前掌握不牢的知识点</p>
          <el-button link type="primary" @click="router.push('/evaluation')">查看薄弱点 <el-icon><ArrowRight /></el-icon></el-button>
        </div>
        <div class="loop-divider"><el-icon><Right /></el-icon></div>

        <div class="loop-node">
          <h4 class="node-title">资源生成</h4>
          <p class="node-desc">生成讲解、练习、代码等资源</p>
          <el-button link type="primary" @click="router.push('/resource-generator')">生成资源 <el-icon><ArrowRight /></el-icon></el-button>
        </div>
        <div class="loop-divider"><el-icon><Right /></el-icon></div>

        <div class="loop-node">
          <h4 class="node-title">路径规划</h4>
          <p class="node-desc">把资源组织成可执行学习步骤</p>
          <el-button link type="primary" @click="router.push('/path-planner')">规划路径 <el-icon><ArrowRight /></el-icon></el-button>
        </div>
        <div class="loop-divider"><el-icon><Right /></el-icon></div>

        <div class="loop-node">
          <h4 class="node-title">智能辅导</h4>
          <p class="node-desc">针对学习问题进行即时答疑</p>
          <el-button link type="primary" @click="router.push('/tutor')">开始提问 <el-icon><ArrowRight /></el-icon></el-button>
        </div>
        <div class="loop-divider"><el-icon><Right /></el-icon></div>

        <div class="loop-node">
          <h4 class="node-title">学习评估</h4>
          <p class="node-desc">检测学习效果，反向优化安排</p>
          <el-button link type="primary" @click="router.push('/evaluation')">开始评估 <el-icon><ArrowRight /></el-icon></el-button>
        </div>
      </div>
    </section>

    <div class="bento-grid">
      <div class="bento-card highlight-card col-span-2 fade-in-up" style="animation-delay: 0.3s">
        <div class="card-header">
          <h3 class="card-title"><el-icon><Aim /></el-icon> 下一步建议</h3>
          <p class="card-subtitle">系统根据最近的学习任务、资源使用情况和评估结果推荐的最优操作。</p>
        </div>
        <div class="suggestion-body">
          <div class="suggestion-main">
            <h4 class="suggestion-topic">建议继续学习「{{ nextStepData.topic }}」</h4>
            <div class="suggestion-reason">
              <span class="reason-label">推荐原因：</span>
              <p>{{ nextStepData.reason }}</p>
            </div>
            <div class="suggestion-steps">
              <span class="steps-label">建议步骤：</span>
              <ul class="steps-list">
                <li v-for="(step, index) in nextStepData.steps" :key="index">
                  <span class="step-num">{{ index + 1 }}</span>
                  {{ step }}
                </li>
              </ul>
            </div>
          </div>
        </div>
        <div class="card-actions mt-auto">
          <el-button type="primary" round size="large" @click="router.push('/tutor')">继续学习</el-button>
          <el-button plain round size="large" @click="router.push('/resource-generator')">生成补充资源</el-button>
          <el-button plain round size="large" @click="router.push('/path-planner')">查看学习路径</el-button>
        </div>
      </div>

      <div class="bento-card tutor-card col-span-1 fade-in-up" style="animation-delay: 0.4s">
        <div class="card-header">
          <h3 class="card-title"><el-icon><Service /></el-icon> 遇到问题？直接问智能导师</h3>
          <p class="card-subtitle">遇到不理解的知识点，可以直接向智能导师提问，获得分步骤讲解。</p>
        </div>
        <div class="tutor-quick-access">
          <div class="tutor-input-box">
            <el-input
                v-model="quickTutorQuery"
                type="textarea"
                :rows="4"
                placeholder="输入你想问的问题，例如：为什么二叉树递归遍历需要回溯？"
                resize="none"
                @keydown.enter.prevent="jumpToTutor"
            />
            <el-button type="primary" class="tutor-submit-btn w-full" size="large" @click="jumpToTutor">
              开始辅导 <el-icon class="el-icon--right"><Position /></el-icon>
            </el-button>
          </div>
        </div>
        <div class="recent-tutor-topics mt-auto">
          <span class="topic-label">最近辅导主题：</span>
          <div class="topic-tags">
            <span v-for="(topic, idx) in recentTutorTopics" :key="idx" class="topic-tag" @click="setTutorQuery(topic)">
              {{ topic }}
            </span>
          </div>
        </div>
      </div>

      <div class="bento-card path-card col-span-1 fade-in-up" style="animation-delay: 0.5s">
        <div class="card-header">
          <h3 class="card-title"><el-icon><Compass /></el-icon> 进行中路径</h3>
          <p class="card-subtitle">{{ currentPath.title }}</p>
        </div>
        <div class="path-details">
          <div class="path-progress-row">
            <div class="progress-info">
              <span class="progress-label">进度</span>
              <span class="progress-val">{{ currentPath.progress }}%</span>
            </div>
            <el-progress :percentage="currentPath.progress" :show-text="false" :stroke-width="8" color="#4F46E5" class="flex-1" />
          </div>
          <div class="path-nodes-info">
            <div class="node-box">
              <span class="n-label">当前节点</span>
              <span class="n-val">{{ currentPath.currentNode }}</span>
            </div>
            <div class="node-box">
              <span class="n-label">下一任务</span>
              <span class="n-val">{{ currentPath.nextTask }}</span>
            </div>
            <div class="node-box">
              <span class="n-label">预计剩余</span>
              <span class="n-val">{{ currentPath.timeLeft }}</span>
            </div>
          </div>
        </div>
        <div class="card-actions mt-auto">
          <el-button type="primary" round plain @click="router.push('/path-planner')">继续路径</el-button>
          <el-button plain round>重新规划</el-button>
        </div>
      </div>

      <div class="bento-card resource-card col-span-1 fade-in-up" style="animation-delay: 0.6s">
        <div class="card-header">
          <h3 class="card-title"><el-icon><Collection /></el-icon> 最近生成资源</h3>
          <p class="card-subtitle">这里展示最近生成的学习资源，可用于继续学习、加入路径或发起提问。</p>
        </div>
        <div class="resource-list">
          <div v-for="res in recentResources" :key="res.id" class="res-item-row">
            <div class="res-info-basic">
              <span class="res-type">【{{ res.type }}】</span>
              <span class="res-title" :title="res.title">{{ res.title }}</span>
            </div>
            <div class="res-inline-actions">
              <span class="res-action-link" @click="router.push('/profile-assistant')">查看</span>
              <el-divider direction="vertical" />
              <span class="res-action-link" @click="router.push('/tutor')">提问</span>
              <el-divider direction="vertical" />
              <span class="res-action-link" @click="router.push('/path-planner')">加入路径</span>
            </div>
          </div>
        </div>
      </div>

      <div class="bento-card weak-card col-span-1 fade-in-up" style="animation-delay: 0.7s">
        <div class="card-header">
          <h3 class="card-title text-rose"><el-icon><Warning /></el-icon> 薄弱知识点</h3>
          <p class="card-subtitle">根据练习与评估结果识别需要优先巩固的知识点。</p>
        </div>
        <div class="weak-points-list">
          <div v-for="(wp, idx) in weakPoints" :key="idx" class="weak-point-row">
            <div class="wp-info-basic">
              <span class="wp-name">{{ wp.name }}</span>
              <span class="wp-level" :class="wp.levelClass">{{ wp.level }}</span>
            </div>
            <div class="wp-inline-actions">
              <span class="wp-action-link" @click="router.push('/resource-generator')">生成资源</span>
              <el-divider direction="vertical" />
              <span class="wp-action-link" @click="router.push('/tutor')">问导师</span>
              <el-divider direction="vertical" />
              <span class="wp-action-link" @click="router.push('/path-planner')">加入路径</span>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight, Warning, Aim, Position, Collection, Service,
  List, Compass, Right, Cpu, DataAnalysis
} from '@element-plus/icons-vue'

const router = useRouter()

// --- 1. 状态概览数据 ---
const metrics = ref({
  activePaths: 2,
  availableResources: 12,
  pendingTasks: 5,
  recentScore: 82
})

// --- 2. 下一步建议数据 ---
const nextStepData = ref({
  topic: '二叉树遍历',
  reason: '最近练习中，递归调用栈相关题目正确率较低，建议优先巩固递归遍历过程。',
  steps: [
    '阅读讲解文档',
    '查看思维导图',
    '完成专项练习',
    '进入智能辅导提问'
  ]
})

// --- 3. 学习路径数据 ---
const currentPath = ref({
  title: '数据结构基础强化路径',
  progress: 45,
  currentNode: '栈与队列',
  nextTask: '完成队列应用练习',
  timeLeft: '2 小时 30 分钟'
})

// --- 4. 最近生成资源数据 ---
const recentResources = ref([
  { id: 1, type: '讲解文档', title: '二叉树遍历核心概念' },
  { id: 2, type: '思维导图', title: '数据结构知识体系' },
  { id: 3, type: '练习题', title: '栈与队列专项训练' },
  { id: 4, type: '代码案例', title: '链表反转 Python 实现' }
])

// --- 5. 薄弱知识点数据 ---
const weakPoints = ref([
  { name: '递归调用栈', level: '掌握较弱', levelClass: 'text-rose' },
  { name: 'SQL 子查询', level: '需要加强', levelClass: 'text-amber' },
  { name: '最短路径算法', level: '理解一般', levelClass: 'text-indigo' }
])

// --- 6. 智能辅导数据 ---
const quickTutorQuery = ref('')
const recentTutorTopics = ref([
  '二叉树递归过程',
  'SQL 多表查询',
  'RAG 知识库构建'
])

const setTutorQuery = (topic: string) => {
  quickTutorQuery.value = `关于“${topic}”，我有个问题想请教：`
}

const jumpToTutor = () => {
  if (quickTutorQuery.value.trim()) {
    router.push('/tutor')
  } else {
    router.push('/tutor')
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

.command-center-modern {
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding: 32px 40px;
  max-width: 1600px;
  margin: 0 auto;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  background-color: #F8FAFC;
  min-height: 100vh;
  box-sizing: border-box;
}

/* ================= 1. 顶部：全景中枢 Header ================= */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 8px;
}

.header-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.page-title {
  margin: 0;
  font-size: 2.2rem;
  font-weight: 800;
  color: #0F172A;
  letter-spacing: -0.02em;
}

.page-subtitle {
  margin: 0;
  font-size: 1.05rem;
  color: #64748B;
  max-width: 600px;
  line-height: 1.6;
}

.header-actions {
  display: flex;
  gap: 16px;
}

.shadow-btn {
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.3);
  font-weight: 700;
}
.shadow-btn:hover {
  box-shadow: 0 6px 20px rgba(79, 70, 229, 0.4);
  transform: translateY(-1px);
}

/* ================= 2. 数据概览卡片 ================= */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.metric-card {
  background: #FFFFFF;
  border-radius: 20px;
  border: 1px solid #E2E8F0;
  padding: 24px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px -4px rgba(15, 23, 42, 0.03);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.metric-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.06);
}

.metric-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.metric-value {
  font-size: 2.5rem;
  font-weight: 800;
  color: #0F172A;
  line-height: 1;
}

.metric-icon {
  width: 48px; height: 48px;
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem;
}
.bg-blue-light { background: #EFF6FF; }
.bg-indigo-light { background: #EEF2FF; }
.bg-amber-light { background: #FFFBEB; }
.bg-emerald-light { background: #ECFDF5; }
.text-blue { color: #3B82F6; }
.text-indigo { color: #4F46E5; }
.text-amber { color: #F59E0B; }
.text-emerald { color: #10B981; }

.metric-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 20px;
  flex: 1;
}

.metric-name {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #1E293B;
}

.metric-desc {
  margin: 0;
  font-size: 0.8rem;
  color: #64748B;
  line-height: 1.5;
}

.metric-action {
  border-top: 1px solid #F1F5F9;
  padding-top: 16px;
}
.metric-action .el-button {
  padding: 0;
  font-weight: 700;
}

/* ================= 3. 学习闭环节点横幅 ================= */
.loop-banner {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 20px;
  padding: 24px 32px;
  box-shadow: 0 4px 20px -4px rgba(15, 23, 42, 0.03);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.loop-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.loop-header h3 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  color: #0F172A;
}

.loop-header p {
  margin: 0;
  color: #64748B;
  font-size: 0.9rem;
}

.loop-nodes {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.loop-node {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  background: #F8FAFC;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #F1F5F9;
}

.node-title {
  margin: 0 0 4px;
  font-size: 0.95rem;
  font-weight: 800;
  color: #1E293B;
}

.node-desc {
  margin: 0 0 12px;
  font-size: 0.75rem;
  color: #64748B;
  line-height: 1.4;
}

.loop-node .el-button {
  padding: 0;
  font-weight: 700;
  font-size: 0.8rem;
  margin-top: auto;
}

.loop-divider {
  color: #CBD5E1;
  font-size: 1.2rem;
  margin: 0 12px;
}

/* ================= 4. Bento Grid 布局 ================= */
.bento-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  align-items: stretch;
}

.col-span-1 { grid-column: span 1; }
.col-span-2 { grid-column: span 2; }
.col-span-3 { grid-column: span 3; }

.bento-card {
  background: #FFFFFF;
  border-radius: 20px;
  border: 1px solid #E2E8F0;
  padding: 28px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 20px -4px rgba(15, 23, 42, 0.03);
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 24px;
}

.card-title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  color: #1E293B;
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-title .el-icon {
  color: #4F46E5;
  font-size: 1.25rem;
}

.card-subtitle {
  margin: 0;
  font-size: 0.85rem;
  color: #64748B;
  line-height: 1.5;
}

.mt-auto { margin-top: auto; }
.w-full { width: 100%; }

.card-actions {
  display: flex;
  gap: 12px;
  border-top: 1px solid #F1F5F9;
  padding-top: 20px;
  margin-top: 24px;
}

/* ================= 卡片细节设计 ================= */

/* 下一步建议 (重点区域) */
.highlight-card {
  background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
  border: 1px solid #E0E7FF;
}
.card-header {
  position: relative;
}
.urgency-tag {
  position: absolute;
  right: 0; top: 0;
  background: #4F46E5 !important;
  border: none;
  font-weight: 700;
}
.suggestion-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.suggestion-topic {
  margin: 0 0 16px;
  font-size: 1.3rem;
  color: #0F172A;
  font-weight: 800;
}
.suggestion-reason {
  background: #EFF6FF;
  padding: 16px;
  border-radius: 12px;
  border-left: 4px solid #3B82F6;
  margin-bottom: 16px;
}
.reason-label {
  font-weight: 700;
  color: #1D4ED8;
  font-size: 0.9rem;
  margin-bottom: 4px;
  display: block;
}
.suggestion-reason p {
  margin: 0;
  color: #1E3A8A;
  font-size: 0.95rem;
  line-height: 1.5;
}
.suggestion-steps {
  display: flex;
  flex-direction: column;
}
.steps-label {
  font-weight: 700;
  color: #475569;
  font-size: 0.95rem;
  margin-bottom: 12px;
}
.steps-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.steps-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.95rem;
  color: #334155;
  font-weight: 600;
}
.step-num {
  width: 24px; height: 24px;
  background: #E2E8F0;
  color: #475569;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.8rem; font-weight: 800;
}

/* 智能辅导入口 */
.tutor-card {
  background: #F5F3FF;
  border-color: #EDE9FE;
}
.tutor-card .card-title .el-icon { color: #7C3AED; }
.tutor-input-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
}
.tutor-input-box :deep(.el-textarea__inner) {
  border-radius: 12px;
  border: 1px solid #DDD6FE;
  padding: 12px;
  font-size: 0.95rem;
  box-shadow: none !important;
}
.tutor-input-box :deep(.el-textarea__inner:focus) {
  border-color: #8B5CF6;
  background: #FFFFFF;
}
.tutor-submit-btn {
  background: #7C3AED !important;
  border: none;
  font-weight: 700;
  border-radius: 12px;
}
.tutor-submit-btn:hover { background: #6D28D9 !important; }
.recent-tutor-topics {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 24px;
}
.topic-label {
  font-size: 0.85rem;
  color: #6D28D9;
  font-weight: 700;
}
.topic-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.topic-tag {
  background: #EDE9FE;
  color: #5B21B6;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.topic-tag:hover {
  background: #DDD6FE;
}

/* 进行中路径 */
.path-details {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.path-progress-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.flex-1 { flex: 1; }
.progress-info {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.progress-val { font-size: 1.1rem; font-weight: 800; color: #0F172A; }
.progress-label { font-size: 0.8rem; color: #64748B; font-weight: 600; }

.path-nodes-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.node-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #F8FAFC;
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid #F1F5F9;
}
.n-label { font-size: 0.85rem; color: #64748B; font-weight: 600; }
.n-val { font-size: 0.95rem; color: #1E293B; font-weight: 700; }

/* 最近生成资源 */
.resource-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.res-item-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  background: #F8FAFC;
  border-radius: 12px;
  border: 1px solid #F1F5F9;
}
.res-info-basic {
  display: flex;
  align-items: center;
  gap: 4px;
}
.res-type {
  font-size: 0.85rem;
  color: #64748B;
  font-weight: 700;
  flex-shrink: 0;
}
.res-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #1E293B;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.res-inline-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.res-action-link {
  font-size: 0.85rem;
  color: #3B82F6;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s;
}
.res-action-link:hover { color: #1D4ED8; text-decoration: underline; }

/* 薄弱知识点 */
.weak-card .card-title .el-icon { color: #E11D48; }
.text-rose { color: #E11D48 !important; }
.text-amber { color: #F59E0B !important; }
.text-indigo { color: #4F46E5 !important; }

.weak-points-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.weak-point-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  background: #F8FAFC;
  border-radius: 12px;
  border: 1px solid #F1F5F9;
}
.wp-info-basic {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.wp-name { font-size: 0.95rem; font-weight: 700; color: #1E293B; }
.wp-level { font-size: 0.8rem; font-weight: 600; }
.wp-inline-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.wp-action-link {
  font-size: 0.85rem;
  color: #3B82F6;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s;
}
.wp-action-link:hover { color: #1D4ED8; text-decoration: underline; }


/* ================= 动画 ================= */
.fade-in-up {
  animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ================= 响应式 ================= */
@media (max-width: 1200px) {
  .bento-grid { grid-template-columns: repeat(2, 1fr); }
  .col-span-3 { grid-column: span 2; }
}

@media (max-width: 960px) {
  .loop-nodes { flex-wrap: wrap; gap: 16px; }
  .loop-divider { display: none; }
  .loop-node { min-width: calc(33.333% - 16px); }
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
  .page-header { flex-direction: column; align-items: flex-start; gap: 16px; }
}

@media (max-width: 768px) {
  .bento-grid { grid-template-columns: 1fr; }
  .col-span-1, .col-span-2, .col-span-3 { grid-column: span 1; }
  .loop-node { min-width: 100%; }
}

@media (max-width: 600px) {
  .command-center-modern { padding: 16px; }
  .metrics-grid { grid-template-columns: 1fr; }
  .card-actions { flex-direction: column; }
  .card-actions .el-button { width: 100%; margin-left: 0 !important; margin-bottom: 8px; }
}
</style>
