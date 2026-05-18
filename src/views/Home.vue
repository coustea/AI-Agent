<template>
  <div class="home-dashboard">
    <!-- User Profile & Welcome Banner -->
    <header class="welcome-banner fade-in-up">
      <div class="banner-content">
        <div class="user-profile">
          <el-avatar :size="80" :src="userInfo.avatar" class="user-avatar" />
          <div class="user-greeting">
            <h1 class="greeting-text">早安，{{ userInfo.name }} <span class="wave">👋</span></h1>
            <p class="greeting-sub">
              <span class="level-tag">{{ userInfo.level }}</span>
              今日有 <strong>{{ userInfo.todayTasks }}</strong> 个学习任务待完成，继续保持！
            </p>
          </div>
        </div>
        <div class="user-stats">
          <div class="stat-item">
            <div class="stat-val">{{ userInfo.studyDays }} <span>天</span></div>
            <div class="stat-label">连续学习</div>
          </div>
          <div class="divider"></div>
          <div class="stat-item">
            <div class="stat-val">{{ userInfo.masteryScore }} <span>分</span></div>
            <div class="stat-label">掌握度评估</div>
          </div>
          <div class="divider"></div>
          <div class="stat-item">
            <div class="stat-val">{{ userInfo.resourcesCount }} <span>份</span></div>
            <div class="stat-label">已生成资源</div>
          </div>
        </div>
      </div>
    </header>

    <div class="dashboard-bento">
      <!-- Row 1: Current Path & Tutor -->
      <section class="bento-card path-card fade-in-up" style="animation-delay: 0.1s">
        <div class="card-header">
          <div class="header-title">
            <div class="icon-box bg-indigo-soft"><el-icon><Position /></el-icon></div>
            <h3>当前学习路径</h3>
          </div>
          <el-button link type="primary" @click="router.push('/path-planner')">查看完整路径 <el-icon><ArrowRight /></el-icon></el-button>
        </div>
        <div class="path-content">
          <div class="path-info">
            <h4 class="path-title">{{ activePath.title }}</h4>
            <p class="path-next"><strong>下一步：</strong>{{ activePath.nextTask }}</p>
            <div class="path-meta">
              <span><el-icon><Clock /></el-icon> 预计 {{ activePath.remaining }}</span>
            </div>
          </div>
          <div class="path-action">
            <div class="progress-wrap">
              <span class="progress-text">进度 {{ activePath.progress }}%</span>
              <el-progress :percentage="activePath.progress" :show-text="false" color="#4F46E5" :stroke-width="10" />
            </div>
            <el-button type="primary" round class="continue-btn" @click="router.push('/tutor')">继续学习</el-button>
          </div>
        </div>
      </section>

      <section class="bento-card tutor-card fade-in-up" style="animation-delay: 0.2s">
        <div class="card-header">
          <div class="header-title">
            <div class="icon-box bg-cyan-soft"><el-icon><ChatDotRound /></el-icon></div>
            <h3>向导师提问</h3>
          </div>
        </div>
        <div class="tutor-content">
          <p class="tutor-desc">遇到难题？随时向你的专属智能导师求助。</p>
          <el-input
            v-model="quickQuestion"
            type="textarea"
            :rows="3"
            placeholder="例如：为什么快排的最坏时间复杂度是O(n²)？"
            resize="none"
            class="custom-textarea"
            @keydown.enter.prevent="askTutor"
          />
          <el-button type="primary" class="w-full mt-3 submit-btn" size="large" @click="askTutor">
            发送提问 <el-icon class="el-icon--right"><Position /></el-icon>
          </el-button>
        </div>
      </section>

      <!-- Row 2: Learning Activity & Weak Points -->
      <section class="bento-card activity-card fade-in-up" style="animation-delay: 0.3s">
        <div class="card-header">
          <div class="header-title">
            <div class="icon-box bg-blue-soft"><el-icon><DataLine /></el-icon></div>
            <h3>学习活跃度</h3>
          </div>
          <div class="chart-legend">
            <span class="legend-item"><i class="dot study"></i> 学习时长</span>
            <span class="legend-item"><i class="dot resource"></i> 资源生成</span>
          </div>
        </div>
        <div class="chart-container">
          <v-chart class="chart" :option="chartOption" autoresize />
        </div>
      </section>

      <section class="bento-card weak-card fade-in-up" style="animation-delay: 0.4s">
        <div class="card-header">
          <div class="header-title">
            <div class="icon-box bg-rose-soft"><el-icon><Warning /></el-icon></div>
            <h3>薄弱知识点</h3>
          </div>
        </div>
        <div class="weak-list" v-if="weakPoints.length > 0">
          <div v-for="(wp, idx) in weakPoints" :key="idx" class="weak-item">
            <div class="weak-info">
              <span class="weak-name">{{ wp.name }}</span>
              <span class="weak-level">{{ wp.level }}</span>
            </div>
            <el-button link type="primary" @click="router.push('/resource-generator')">生成强化资源</el-button>
          </div>
        </div>
        <div v-else class="empty-state">
          <el-empty description="太棒了，暂无明显薄弱点" :image-size="60" />
        </div>
      </section>

      <!-- Row 3: Multi-Agent Resources & Achievements -->
      <section class="bento-card resources-card fade-in-up" style="animation-delay: 0.5s">
        <div class="card-header">
          <div class="header-title">
            <div class="icon-box bg-emerald-soft"><el-icon><Share /></el-icon></div>
            <h3>最近生成资源</h3>
          </div>
          <el-button link type="primary" @click="router.push('/resource-generator')">查看全部 <el-icon><ArrowRight /></el-icon></el-button>
        </div>
        
        <div v-if="multiAgentResources.length > 0" class="resources-grid">
          <div v-for="res in multiAgentResources" :key="res.id" class="resource-item">
            <div class="res-icon-wrap" :class="res.colorClass">
              <el-icon><component :is="res.icon" /></el-icon>
            </div>
            <div class="res-details">
              <h4 class="res-title" :title="res.title">{{ res.title }}</h4>
              <div class="res-meta">
                <span class="agent-badge">{{ res.agent }}</span>
                <span class="res-time">{{ res.time }}</span>
              </div>
            </div>
            <div class="res-actions">
              <el-button circle size="small" :icon="View" @click="router.push('/resource-generator')" />
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <el-empty description="暂无生成的资源" :image-size="80" />
        </div>
      </section>

      <section class="bento-card achievement-card fade-in-up" style="animation-delay: 0.6s">
        <div class="card-header">
          <div class="header-title">
            <div class="icon-box bg-amber-soft"><el-icon><Lightning /></el-icon></div>
            <h3>近期成就</h3>
          </div>
        </div>
        <div class="achievement-list">
          <div v-for="ach in achievements" :key="ach.id" class="achievement-item">
            <div class="ach-icon">{{ ach.emoji }}</div>
            <div class="ach-info">
              <span class="ach-name">{{ ach.name }}</span>
              <span class="ach-date">{{ ach.date }}</span>
            </div>
            <div class="ach-status">
              <el-tag size="small" type="success" effect="plain" round>已达成</el-tag>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Clock, DataLine, Lightning, Position, ArrowRight,
  Share, Document, Edit, VideoPlay, ChatDotRound, Warning, View
} from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  BarChart,
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent
])

const router = useRouter()

// 用户信息
const userInfo = ref({
  name: '学习者',
  avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
  level: 'Lv.4 知识达人',
  studyDays: 24,
  todayTasks: 3,
  masteryScore: 88,
  resourcesCount: 15
})

// 当前学习路径
const activePath = ref({
  title: '数据结构与算法强化',
  progress: 65,
  nextTask: '完成图的广度优先遍历',
  remaining: '1.5 小时'
})

// 多智能体最近生成的资源
const multiAgentResources = ref([
  { id: 1, title: '二叉树遍历原理详解', agent: '内容规划', type: 'document', time: '10分钟前', icon: Document, colorClass: 'icon-indigo' },
  { id: 2, title: '数据结构全景思维导图', agent: '导图智能体', type: 'mindmap', time: '2小时前', icon: Share, colorClass: 'icon-cyan' },
  { id: 3, title: '排序算法专项练习题', agent: '测试智能体', type: 'quiz', time: '昨天', icon: Edit, colorClass: 'icon-amber' },
  { id: 4, title: '红黑树原理解析视频', agent: '视频智能体', type: 'video', time: '昨天', icon: VideoPlay, colorClass: 'icon-emerald' }
])

// 薄弱知识点
const weakPoints = ref([
  { name: '动态规划：背包问题', level: '待突破' },
  { name: '红黑树：左旋右旋', level: '需巩固' }
])

// 近期成就
const achievements = ref([
  { id: 1, name: '七日连续打卡', date: '2026-05-15', emoji: '🔥' },
  { id: 2, name: '算法之星：快速排序', date: '2026-05-12', emoji: '⭐' },
  { id: 3, name: '资源收集家', date: '2026-05-10', emoji: '📚' }
])

// 导师提问
const quickQuestion = ref('')

const askTutor = () => {
  router.push('/tutor')
}

// ECharts 配置
const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' }
  },
  grid: {
    top: '10%',
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#64748B' }
  },
  yAxis: {
    type: 'value',
    splitLine: { lineStyle: { type: 'dashed', color: '#E2E8F0' } },
    axisLabel: { color: '#64748B' }
  },
  series: [
    {
      name: '学习时长 (min)',
      type: 'bar',
      barWidth: '25%',
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: '#4F46E5'
      },
      data: [45, 60, 85, 40, 95, 120, 80]
    },
    {
      name: '资源生成 (份)',
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      itemStyle: { color: '#06B6D4' },
      lineStyle: { width: 3 },
      data: [2, 3, 5, 1, 4, 6, 3]
    }
  ]
}))
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

.home-dashboard {
  padding: 32px;
  width: 100%;
  margin: 0;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  background-color: #F8FAFC;
  min-height: 100vh;
  box-sizing: border-box;
}

/* ================= Welcome Banner ================= */
.welcome-banner {
  background: linear-gradient(135deg, #3730A3 0%, #4F46E5 50%, #06B6D4 100%);
  border-radius: 32px;
  padding: 48px;
  color: #FFFFFF;
  box-shadow: 0 20px 50px -15px rgba(79, 70, 229, 0.4);
  margin-bottom: 32px;
  position: relative;
  overflow: hidden;
}
.welcome-banner::after {
  content: '';
  position: absolute;
  top: -50%;
  right: -20%;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
  border-radius: 50%;
}

.banner-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: 1800px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 32px;
}
.user-avatar {
  border: 4px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.2);
}
.greeting-text {
  margin: 0 0 12px 0;
  font-size: 2.6rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  text-shadow: 0 2px 10px rgba(0,0,0,0.1);
}
.wave {
  display: inline-block;
  animation: wave-animation 2.5s infinite;
  transform-origin: 70% 70%;
}
@keyframes wave-animation {
  0% { transform: rotate( 0.0deg) }
  10% { transform: rotate(14.0deg) }
  20% { transform: rotate(-8.0deg) }
  30% { transform: rotate(14.0deg) }
  40% { transform: rotate(-4.0deg) }
  50% { transform: rotate(10.0deg) }
  60% { transform: rotate( 0.0deg) }
  100% { transform: rotate( 0.0deg) }
}
.greeting-sub {
  margin: 0;
  font-size: 1.2rem;
  color: rgba(255, 255, 255, 0.95);
  display: flex;
  align-items: center;
  gap: 16px;
}
.level-tag {
  background: rgba(255, 255, 255, 0.25);
  border-radius: 20px;
  padding: 6px 18px;
  font-size: 0.9rem;
  font-weight: 700;
  color: #FFFFFF;
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.user-stats {
  display: flex;
  align-items: center;
  gap: 48px;
  background: rgba(15, 23, 42, 0.3);
  padding: 28px 48px;
  border-radius: 28px;
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 10px 30px rgba(0,0,0,0.1);
}
.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.stat-val {
  font-size: 2.2rem;
  font-weight: 800;
  line-height: 1;
}
.stat-val span {
  font-size: 1.2rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
}
.stat-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.divider {
  width: 1px;
  height: 56px;
  background: rgba(255, 255, 255, 0.15);
}

/* ================= Bento Grid ================= */
.dashboard-bento {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-auto-rows: auto;
  gap: 28px;
  max-width: 1800px;
  margin: 0 auto;
}

/* Card Spanning */
.path-card { grid-column: span 2; }
.tutor-card { grid-column: span 1; }
.activity-card { grid-column: span 2; }
.weak-card { grid-column: span 1; }
.resources-card { grid-column: span 2; }
.achievement-card { grid-column: span 1; }

/* ================= Cards General ================= */
.bento-card {
  background: #FFFFFF;
  border-radius: 28px;
  padding: 36px;
  box-shadow: 0 4px 24px -6px rgba(15, 23, 42, 0.04);
  border: 1px solid #E2E8F0;
  transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.4s ease;
}
.bento-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 20px 40px -15px rgba(15, 23, 42, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}
.header-title {
  display: flex;
  align-items: center;
  gap: 16px;
}
.header-title h3 {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 800;
  color: #0F172A;
}
.icon-box {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
}

/* Updated Icon Colors */
.bg-indigo-soft { background: #EEF2FF; color: #4F46E5; }
.bg-cyan-soft { background: #ECFEFF; color: #0891B2; }
.bg-blue-soft { background: #EFF6FF; color: #3B82F6; }
.bg-rose-soft { background: #FFF1F2; color: #E11D48; }
.bg-emerald-soft { background: #ECFDF5; color: #059669; }
.bg-amber-soft { background: #FFFBEB; color: #D97706; }

/* ================= Path Card ================= */
.path-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #F8FAFC;
  border-radius: 24px;
  padding: 32px;
  border: 1px solid #F1F5F9;
}
.path-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.path-title {
  margin: 0;
  font-size: 1.4rem;
  font-weight: 800;
  color: #0F172A;
}
.path-next {
  margin: 0;
  font-size: 1.05rem;
  color: #475569;
}
.path-meta {
  margin-top: 6px;
  font-size: 0.95rem;
  color: #64748B;
  display: flex;
  align-items: center;
  gap: 10px;
}
.path-action {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 20px;
  width: 280px;
}
.progress-wrap {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.progress-text {
  font-size: 1rem;
  font-weight: 800;
  color: #4F46E5;
  text-align: right;
}
.continue-btn {
  width: 100%;
  height: 52px;
  font-weight: 700;
  font-size: 1.1rem;
  background: #4F46E5 !important;
  border-color: #4F46E5 !important;
  box-shadow: 0 10px 20px -5px rgba(79, 70, 229, 0.4);
}

/* ================= Activity Card ================= */
.chart-container {
  height: 300px;
  width: 100%;
}
.chart {
  height: 100%;
}
.chart-legend {
  display: flex;
  gap: 24px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.9rem;
  color: #64748B;
  font-weight: 600;
}
.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
.dot.study { background: #4F46E5; }
.dot.resource { background: #06B6D4; }

/* ================= Multi-Agent Resources ================= */
.resources-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}
.resource-item {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 24px;
  border-radius: 24px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  transition: all 0.3s ease;
}
.resource-item:hover {
  box-shadow: 0 12px 30px -10px rgba(15, 23, 42, 0.08);
  border-color: #CBD5E1;
}
.res-icon-wrap {
  width: 60px; height: 60px;
  border-radius: 18px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.8rem;
  flex-shrink: 0;
}
.icon-indigo { background: #EEF2FF; color: #4F46E5; }
.icon-cyan { background: #ECFEFF; color: #0891B2; }
.icon-amber { background: #FFFBEB; color: #D97706; }
.icon-emerald { background: #ECFDF5; color: #059669; }

.res-details {
  flex: 1;
  min-width: 0;
}
.res-title {
  margin: 0 0 10px 0;
  font-size: 1.15rem;
  font-weight: 700;
  color: #0F172A;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.res-meta {
  display: flex;
  align-items: center;
  gap: 14px;
}
.agent-badge {
  background: #F1F5F9;
  color: #475569;
  font-size: 0.85rem;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 10px;
}
.res-time {
  font-size: 0.9rem;
  color: #94A3B8;
  font-weight: 500;
}

/* ================= Tutor Card ================= */
.tutor-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.tutor-desc {
  margin: 0;
  font-size: 1.05rem;
  color: #475569;
  line-height: 1.6;
}
.custom-textarea :deep(.el-textarea__inner) {
  border-radius: 20px;
  background: #F8FAFC;
  border: 2px solid #E2E8F0;
  box-shadow: none !important;
  font-size: 1.05rem;
  padding: 20px;
  font-family: inherit;
  transition: all 0.3s ease;
}
.custom-textarea :deep(.el-textarea__inner:focus) {
  border-color: #4F46E5;
  background: #FFFFFF;
}
.submit-btn {
  background: linear-gradient(135deg, #4F46E5 0%, #3730A3 100%) !important;
  border: none;
  font-weight: 700;
  height: 56px;
  border-radius: 18px;
  font-size: 1.1rem;
  box-shadow: 0 8px 20px -5px rgba(79, 70, 229, 0.4);
}

/* ================= Weak Points ================= */
.weak-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.weak-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: #F8FAFC;
  border-radius: 20px;
  border: 1px solid #F1F5F9;
  transition: all 0.2s ease;
}
.weak-item:hover {
  background: #FFF1F2;
  border-color: #FECDD3;
}
.weak-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.weak-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: #0F172A;
}
.weak-level {
  font-size: 0.9rem;
  color: #E11D48;
  font-weight: 700;
  background: rgba(225, 29, 72, 0.1);
  padding: 2px 10px;
  border-radius: 6px;
}

/* ================= Achievements ================= */
.achievement-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.achievement-item {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 0;
}
.achievement-item:not(:last-child) {
  border-bottom: 1px solid #F1F5F9;
}
.ach-icon {
  width: 52px;
  height: 52px;
  background: #F8FAFC;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.8rem;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
}
.ach-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.ach-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: #0F172A;
}
.ach-date {
  font-size: 0.9rem;
  color: #94A3B8;
}

/* ================= Animations ================= */
.fade-in-up {
  animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(40px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ================= Responsive ================= */
@media (max-width: 1440px) {
  .dashboard-bento { grid-template-columns: repeat(2, 1fr); gap: 24px; }
  .path-card, .activity-card, .resources-card { grid-column: span 2; }
  .tutor-card, .weak-card, .achievement-card { grid-column: span 1; }
}

@media (max-width: 1024px) {
  .dashboard-bento { grid-template-columns: 1fr; }
  .path-card, .tutor-card, .activity-card, .weak-card, .resources-card, .achievement-card {
    grid-column: span 1;
  }
  .banner-content { flex-direction: column; gap: 40px; align-items: flex-start; }
  .user-stats { width: 100%; justify-content: space-between; padding: 24px 32px; }
}

@media (max-width: 768px) {
  .home-dashboard { padding: 20px; }
  .welcome-banner { padding: 32px; border-radius: 24px; }
  .user-stats { flex-direction: column; gap: 24px; align-items: flex-start; padding: 24px; }
  .divider { width: 100%; height: 1px; }
  .resources-grid { grid-template-columns: 1fr; }
  .path-content { flex-direction: column; align-items: flex-start; gap: 28px; }
  .path-action { width: 100%; align-items: flex-start; }
  .greeting-text { font-size: 2rem; }
}
</style>
