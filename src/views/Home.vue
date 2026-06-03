<template>
  <div class="home-hub">
    <section class="hub-hero">
      <div class="hero-main">
        <el-tag class="hero-kicker" effect="plain" round>
          <span class="status-dot" :class="{ 'is-new': isNewUser }"></span>
          {{ isNewUser ? '全新学习旅程已开启' : '学习画像已同步' }}
        </el-tag>
        <h1>{{ isNewUser ? '欢迎来到智能学习中心' : `今天建议从${recommendedGoal.topic}开始` }}</h1>
        <p>
          {{ isNewUser ? '完善你的个人画像并生成首个学习资源，AI 协同智能体将为你量身定制专属的高效学习路径' : '基于你的学习画像、最近生成资源和当前路径进度，系统已整理出下一步目标' }}
        </p>

        <div class="portrait-strip">
          <div
            v-for="item in actionIndicators"
            :key="item.label"
            class="portrait-stat clickable"
            @click="handleIndicatorClick(item.type)"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </div>

      <aside class="goal-panel">
        <div class="panel-topline">
          <span>{{ isNewUser ? '上手指南' : '推荐学习目标' }}</span>
          <el-tag size="small" effect="plain" round>{{ recommendedGoal.confidence }}</el-tag>
        </div>
        <h2>{{ recommendedGoal.title }}</h2>
        <div class="goal-steps">
          <div v-for="step in recommendedGoal.steps" :key="step" class="goal-step">
            <el-icon><CircleCheckFilled /></el-icon>
            <span>{{ step }}</span>
          </div>
        </div>
        <div class="goal-actions">
          <el-button class="home-primary-button" type="primary" @click="goTo('/resource-generator')">
            生成配套资源
            <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
          <el-button class="home-primary-button" type="primary" @click="goTo('/path-planner')">加入学习路径</el-button>
        </div>
      </aside>
    </section>

    <section class="feature-row" aria-label="主要功能">
      <article
          v-for="action in primaryActions"
          :key="action.title"
          class="feature-card"
          :class="action.tone"
          @click="goTo(action.path)"
      >
        <div class="feature-icon">
          <el-icon><component :is="action.icon" /></el-icon>
        </div>
        <div class="feature-copy">
          <span>{{ action.badge }}</span>
          <h3>{{ action.title }}</h3>
          <p>{{ action.description }}</p>
        </div>
        <el-icon class="feature-arrow"><ArrowRight /></el-icon>
      </article>
    </section>

    <section class="hub-grid">
      <article class="insight-card profile-card">
        <div class="section-heading">
          <div>
            <span class="section-label">LEARNING PORTRAIT</span>
            <h2>你的学习画像</h2>
          </div>
          <el-button class="home-link-button" @click="goTo('/tutor')">
            {{ isNewUser ? '开始学习' : '继续学习' }}
          </el-button>
        </div>

        <div class="portrait-radar-section" v-if="!isNewUser || profileScoreData">
          <div class="radar-chart-wrapper">
            <v-chart class="chart" :option="radarOption" :autoresize="true" />
          </div>
          <div class="prominent-dimensions">
            <div class="dimensions-title">能力最强维度</div>
            <div class="dimension-tags-list">
              <div v-for="dim in prominentDimensions" :key="dim.name" class="dim-tag-item">
                <span class="dim-name">{{ dim.name }}</span>
                <span class="dim-score">{{ dim.score }}分</span>
                <span class="dim-trend" :class="dim.trendType">
                  <el-icon v-if="dim.trendType === 'up'"><Top /></el-icon>
                  <el-icon v-else-if="dim.trendType === 'down'"><Bottom /></el-icon>
                  <el-icon v-else><Right /></el-icon>
                </span>
              </div>
            </div>
          </div>
        </div>
        <div class="profile-summary" v-else>
          <div class="profile-avatar">
            <el-icon><User /></el-icon>
          </div>
          <div>
            <h3>{{ learnerProfile.role }}</h3>
            <p>{{ learnerProfile.summary }}</p>
          </div>
        </div>

        <div class="weak-focus" id="weak-focus-section">
          <div class="focus-header">
            <span>当前薄弱点</span>
            <b>{{ learnerProfile.weakPoints.length }} 项</b>
          </div>
          <div class="weak-list" v-if="learnerProfile.weakPoints.length > 0">
            <div
                v-for="point in learnerProfile.weakPoints.slice(0, 3)"
                :key="point.name"
                class="weak-item"
            >
              <div class="weak-info">
                <strong>{{ point.name }}</strong>
                <span>{{ point.hint }}</span>
              </div>
              <el-button
                type="primary"
                size="small"
                class="weak-cta-btn"
                @click="generateResourceForWeakPoint(point.name)"
              >
                生成资源 <el-icon class="el-icon--right"><Cpu /></el-icon>
              </el-button>
            </div>
          </div>
          <div class="empty-state-text" v-else>
            暂无薄弱点记录，开始学习评测或生成资源后将自动同步
          </div>
        </div>

        <div class="card-footer-link">
          <el-button class="home-link-button" @click="goTo('/profile')">
            <span>查看完整画像</span> <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
        </div>
      </article>

      <article class="insight-card resource-card">
        <div class="section-heading">
          <div>
            <span class="section-label">MULTI-AGENT RESOURCES</span>
            <h2>多智能体资源流</h2>
          </div>
        </div>

        <div class="resource-flow" :class="{ 'is-empty': multiAgentResources.length === 0 }">
          <template v-if="multiAgentResources.length > 0">
            <button
                v-for="resource in multiAgentResources.slice(0, 3)"
                :key="resource.id"
                type="button"
                class="resource-item"
                :class="resource.tone"
                @click="goToResourceDetail(resource.id)"
            >
              <div class="resource-icon">
                <el-icon><component :is="resource.icon" /></el-icon>
              </div>
              <div class="resource-info">
                <div class="resource-meta">
                  <span>{{ resource.agent }}</span>
                  <em>{{ resource.time }}</em>
                </div>
                <h3>{{ resource.title }}</h3>
                <p>{{ resource.hint }}</p>
              </div>
            </button>
          </template>
          <div class="empty-resource-state" v-else>
            <el-icon class="empty-icon"><Cpu /></el-icon>
            <p>尚未生成任何学习资源</p>
            <el-button type="primary" plain @click="goTo('/resource-generator')">立即生成</el-button>
          </div>
        </div>
        <div class="card-footer-link" style="margin-top: auto;">
          <el-button class="home-link-button" @click="goTo('/profile')">
            <span>查看全部资源历史</span> <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  ArrowRight,
  ChatDotRound,
  CircleCheckFilled,
  Collection,
  Connection,
  Cpu,
  Document,
  Edit,
  Monitor,
  Share,
  User,
  Top,
  Bottom,
  Right
} from '@element-plus/icons-vue'

import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { RadarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

import { getProfileOnboarding, getGeneratedResources, getPathPlan, getProfileScore } from '@/api/ai'

use([CanvasRenderer, RadarChart, GridComponent, TooltipComponent])

const router = useRouter()
const route = useRoute()

const goTo = (path: string) => {
  router.push(path)
}

const goToResourceDetail = (resourceId: number) => {
  router.push({ name: 'ResourceDetail', params: { id: resourceId } })
}

// 默认设为 true，即默认展示新用户状态，直到加载到数据才切换
const isNewUser = ref(true)

const recommendedGoal = ref({
  topic: '智能学习',
  confidence: '核心指南',
  title: '开启个性化定制路径',
  steps: [
    '在个人中心建立精准画像',
    '利用多智能体生成配套资源',
    '将薄弱点一键转化为学习路径'
  ]
})

const portraitStats = ref([
  { label: '当前阶段', value: '未设置' },
  { label: '学习目标', value: '未设置' },
  { label: '主修专业', value: '未设置' }
])

const learnerProfile = ref({
  role: '新晋学习者',
  summary: '完成画像多维评测后，AI 将在此为你输出核心认知偏好与学习节奏建议',
  tags: [] as string[],
  weakPoints: [] as { name: string; hint: string }[]
})

const profileScoreData = ref<any>(null)

const multiAgentResources = ref<any[]>([])

const primaryActions = ref([
  {
    title: '多智能体资源生成',
    badge: 'RESOURCE ENGINE',
    description: '生成讲解、导图、图解、代码、测验和阅读材料',
    icon: Cpu,
    path: '/resource-generator',
    tone: 'tone-blue'
  },
  {
    title: '开始路径规划',
    badge: 'LEARNING PATH',
    description: '把资源和薄弱点整理成可执行的阶段目标',
    icon: Connection,
    path: '/path-planner',
    tone: 'tone-emerald'
  },
  {
    title: '向智能导师提问',
    badge: 'AI TUTOR',
    description: '围绕当前画像和学习目标获得即时解释',
    icon: ChatDotRound,
    path: '/tutor',
    tone: 'tone-indigo'
  },
  {
    title: '查看路径评估',
    badge: 'ADAPTIVE PATH',
    description: '在学习路径中查看掌握度与自适应优化建议',
    icon: Connection,
    path: '/path-planner',
    tone: 'tone-amber'
  }
])

const radarValuesList = computed(() => {
  const dimensionMap: Record<string, number> = {
    knowledge_foundation: 0,
    learning_goal: 1,
    cognitive_style: 2,
    weakness_points: 3,
    practice_ability: 4,
    interaction_preference: 5,
  }

  const scores = profileScoreData.value?.metrics?.dimension_scores || {}
  const vals = [0, 0, 0, 0, 0, 0] // No fallbacks, start at 0

  for (const [key, index] of Object.entries(dimensionMap)) {
    const score = scores[key]
    if (score !== null && score !== undefined) {
      vals[index] = score
    }
  }
  return vals
})

const radarOption = computed(() => {
  return {
    radar: {
      indicator: [
        { name: '知识基础', max: 100 },
        { name: '学习目标', max: 100 },
        { name: '认知风格', max: 100 },
        { name: '薄弱点', max: 100 },
        { name: '实践能力', max: 100 },
        { name: '交互偏好', max: 100 },
      ],
      shape: 'polygon',
      radius: '68%',
      axisName: { color: '#64748B', fontSize: 10, fontWeight: 'bold' },
      splitArea: { show: false },
      splitLine: { lineStyle: { color: '#E2E8F0' } }
    },
    series: [{
      type: 'radar',
      data: [{
        value: radarValuesList.value,
        areaStyle: { color: 'rgba(79, 70, 229, 0.15)' },
        lineStyle: { color: '#4F46E5', width: 2 },
        itemStyle: { color: '#4F46E5' },
        symbol: 'none'
      }]
    }]
  }
})

// Computes the top 3 prominent dimensions
const prominentDimensions = computed(() => {
  const dimensions = [
    { name: '知识基础', score: radarValuesList.value[0] ?? 0, key: 'knowledge_foundation' },
    { name: '学习目标', score: radarValuesList.value[1] ?? 0, key: 'learning_goal' },
    { name: '认知风格', score: radarValuesList.value[2] ?? 0, key: 'cognitive_style' },
    { name: '薄弱点', score: radarValuesList.value[3] ?? 0, key: 'weakness_points' },
    { name: '实践能力', score: radarValuesList.value[4] ?? 0, key: 'practice_ability' },
    { name: '交互偏好', score: radarValuesList.value[5] ?? 0, key: 'interaction_preference' },
  ]
  // Sort descending by score
  const sorted = [...dimensions].sort((a, b) => b.score - a.score)
  // Take top 3 and add trends
  return sorted.slice(0, 3).map((d) => {
    let trendType = 'stable'
    if (d.score >= 80) trendType = 'up'
    else if (d.score < 65) trendType = 'down'
    return {
      name: d.name,
      score: d.score,
      trendType
    }
  })
})

// Action indicators computed
const actionIndicators = computed(() => {
  const goalVal = recommendedGoal.value.topic || '暂无目标'
  const weakCount = learnerProfile.value.weakPoints.length
  const progressVal = recommendedGoal.value.confidence.includes('完成度')
    ? recommendedGoal.value.confidence.replace('完成度 ', '')
    : '0%'

  return [
    { label: '推荐学习目标', value: goalVal, type: 'goal' },
    { label: '当前薄弱点数量', value: `${weakCount} 项`, type: 'weakness' },
    { label: '学习路径完成度', value: progressVal, type: 'progress' }
  ]
})

const handleIndicatorClick = (type: string) => {
  if (type === 'weakness') {
    const el = document.getElementById('weak-focus-section')
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' })
    }
  } else if (type === 'progress') {
    goTo('/path-planner')
  } else if (type === 'goal') {
    const el = document.querySelector('.goal-panel')
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' })
    }
  }
}

const generateResourceForWeakPoint = (pointName: string) => {
  router.push({
    path: '/resource-generator',
    query: { prompt: `请帮我生成关于“${pointName}”的配套学习资源` }
  })
}

const loadDashboardData = async () => {
  try {
    const [profileRes, resourcesRes, pathRes, scoreRes] = await Promise.allSettled([
      getProfileOnboarding(),
      getGeneratedResources(8),
      getPathPlan(),
      getProfileScore()
    ])

    let hasProfile = false
    let hasResources = false
    let hasPath = false
    let hasScore = false

    if (scoreRes.status === 'fulfilled' && scoreRes.value.data?.data) {
      profileScoreData.value = scoreRes.value.data.data
      hasScore = true
    }

    if (profileRes.status === 'fulfilled' && profileRes.value.data?.data) {
      const profile = profileRes.value.data.data.student_profile
      if (profile && (profile.grade || profile.learning_goal || profile.major)) {
        hasProfile = true
        portraitStats.value = [
          { label: '当前阶段', value: profile.grade || '未填写' },
          { label: '学习目标', value: profile.learning_goal || '未填写' },
          { label: '主修专业', value: profile.major || '未填写' }
        ]

        learnerProfile.value.role = `${profile.major || ''} 学习者`
        learnerProfile.value.tags = profile.courses || []

        const weakPoints = profile.weakness_points || []
        learnerProfile.value.weakPoints = weakPoints.map((point: string) => ({
          name: point,
          hint: '建议生成对应资源进行巩固'
        }))

        learnerProfile.value.summary = weakPoints.length > 0
            ? '系统已为您捕获部分薄弱环节，建议针对性攻克。'
            : '暂未发现明显薄弱点，继续保持当前学习节奏。'
      }
    }

    if (resourcesRes.status === 'fulfilled' && resourcesRes.value.data?.data) {
      const resources = resourcesRes.value.data.data
      if (Array.isArray(resources) && resources.length > 0) {
        hasResources = true
        const toneMap = ['tone-blue', 'tone-amber', 'tone-emerald', 'tone-indigo']
        const iconMap = [Share, Edit, Monitor, Document, Collection, Connection]

        multiAgentResources.value = resources.map((res: any, index: number) => ({
          id: res.id,
          title: res.learning_need || '未命名学习资源',
          agent: '智能体协同',
          time: res.created_at ? new Date(res.created_at).toLocaleDateString() : '最近',
          hint: res.status === 'completed' ? '已就绪，随时可查阅' : '资源生成或处理中',
          icon: iconMap[index % iconMap.length],
          tone: toneMap[index % toneMap.length]
        }))
      }
    }

    if (pathRes.status === 'fulfilled' && pathRes.value.data?.data) {
      const plan = pathRes.value.data.data
      const currentStage = plan.stages?.find((s: any) => s.stage_id === plan.current_stage_id) || plan.stages?.[0]

      if (currentStage) {
        hasPath = true
        const stageNodes = plan.nodes?.filter((n: any) => n.stage_id === currentStage.stage_id) || []
        recommendedGoal.value = {
          topic: currentStage.title || '日常学习',
          confidence: `完成度 ${plan.overall_progress || 0}%`,
          title: plan.goal || currentStage.title,
          steps: stageNodes.slice(0, 3).map((n: any) => n.title) || []
        }
      }
    }

    if (hasProfile || hasResources || hasPath || hasScore) {
      isNewUser.value = false
    }

  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
}

watch(() => route.path, (newPath) => {
  if (newPath === '/' || newPath === '/home') {
    loadDashboardData()
  }
})

onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped>
.home-hub {
  --home-primary: var(--primary, #4F46E5);
  --home-primary-soft: var(--primary-light, #EEF2FF);
  --home-primary-border: #C7D2FE;
  min-height: calc(100vh - 64px);
  padding: 32px;
  background: #F8FAFC;
  color: #0F172A;
  box-sizing: border-box;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, -apple-system, sans-serif;
}

.hub-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
  gap: 24px;
  max-width: 1680px;
  margin: 0 auto 24px;
}

.hero-main,
.goal-panel,
.feature-card,
.insight-card,
.bottom-utility {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 8px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
}

.hero-main {
  padding: 32px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 280px;
}

.hero-kicker {
  width: fit-content;
  color: var(--home-primary) !important;
  border-color: var(--home-primary-border) !important;
  background: var(--home-primary-soft) !important;
  font-weight: 800;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 6px;
  border-radius: 999px;
  background: #10B981;
}

.status-dot.is-new {
  background: #3B82F6;
}

.hero-main h1 {
  margin: 22px 0 12px;
  max-width: 100%;
  font-size: 2.85rem;
  line-height: 1.05;
  letter-spacing: 0;
  font-weight: 850;
  color: #0F172A;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hero-main p {
  margin: 0;
  max-width: 100%; /* 放宽原本的 640px 限制 */
  color: #64748B;
  line-height: 1.7;
  font-size: 1.02rem;
  white-space: nowrap; /* 强制在一行显示 */
  overflow: hidden;
  text-overflow: ellipsis; /* 超出部分优雅省略 */
}

.portrait-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 28px;
}

.portrait-stat {
  padding: 16px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
}

.portrait-stat span,
.section-label,
.panel-topline span {
  display: block;
  color: #94A3B8;
  font-size: 0.76rem;
  font-weight: 850;
  letter-spacing: 0.04em;
}

.portrait-stat strong {
  display: block;
  margin-top: 8px;
  color: #1E293B;
  font-size: 1rem;
}

.goal-panel {
  padding: 26px;
  display: flex;
  flex-direction: column;
}

.panel-topline {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.goal-panel h2 {
  margin: 18px 0 18px;
  font-size: 1.45rem;
  line-height: 1.3;
  font-weight: 850;
}

.goal-steps {
  display: grid;
  gap: 12px;
  margin-bottom: 22px;
}

.goal-step {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  color: #475569;
  line-height: 1.55;
}

.goal-step .el-icon {
  margin-top: 2px;
  color: #10B981;
}

.goal-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: auto;
}

.home-primary-button {
  border-radius: 12px !important;
  font-weight: 600 !important;
}

.home-link-button {
  min-height: 32px;
  padding: 8px 14px !important;
  border: 1px solid var(--home-primary-border) !important;
  border-radius: 12px !important;
  background: var(--home-primary-soft) !important;
  color: var(--home-primary) !important;
  font-weight: 700 !important;
  box-shadow: none !important;
  transition: transform 0.2s ease, border-color 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease !important;
}

.home-link-button:hover {
  background: var(--home-primary-soft) !important;
  border-color: var(--home-primary) !important;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px -8px rgba(79, 70, 229, 0.35) !important;
}

.home-link-button:active {
  transform: translateY(0);
  box-shadow: 0 4px 12px -8px rgba(79, 70, 229, 0.3) !important;
}

.feature-row {
  max-width: 1680px;
  margin: 0 auto 24px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 24px;
}

.feature-card {
  border: 0;
  cursor: pointer;
  min-height: 150px;
  padding: 20px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 14px;
  text-align: left;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.feature-card:hover {
  transform: translateY(-3px);
  border-color: #CBD5E1;
  box-shadow: 0 16px 30px rgba(15, 23, 42, 0.07);
}

.feature-icon,
.resource-icon,
.profile-avatar {
  width: 42px;
  height: 42px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  background: var(--tone-soft);
  color: var(--tone-accent);
  font-size: 1.25rem;
}

.feature-copy span {
  color: var(--tone-accent);
  font-size: 0.72rem;
  font-weight: 850;
  letter-spacing: 0.04em;
}

.feature-copy h3 {
  margin: 8px 0 8px;
  color: #0F172A;
  font-size: 1.05rem;
  font-weight: 850;
}

.feature-copy p {
  margin: 0;
  color: #64748B;
  line-height: 1.52;
  font-size: 0.9rem;
}

.feature-arrow {
  color: #CBD5E1;
  margin-top: 2px;
}

.hub-grid {
  max-width: 1680px;
  margin: 0 auto 24px;
  display: grid;
  grid-template-columns: minmax(340px, 0.8fr) minmax(0, 1.2fr);
  gap: 24px;
}

.insight-card {
  padding: 24px;
}

.resource-card {
  display: flex;
  flex-direction: column;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.section-heading h2 {
  margin: 6px 0 0;
  color: #0F172A;
  font-size: 1.25rem;
  font-weight: 850;
}

.profile-summary {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 14px;
  align-items: start;
  padding: 16px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
}

.profile-summary h3 {
  margin: 0 0 6px;
  color: #0F172A;
  font-size: 1rem;
}

.profile-summary p {
  margin: 0;
  color: #64748B;
  line-height: 1.58;
}

.profile-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 16px 0;
}

.profile-tags span {
  padding: 6px 10px;
  border-radius: 999px;
  background: #F1F5F9;
  color: #475569;
  font-size: 0.82rem;
  font-weight: 700;
}

.weak-focus {
  border-top: 1px solid #E2E8F0;
  padding-top: 16px;
}

.focus-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: #64748B;
  font-size: 0.88rem;
  font-weight: 800;
}

.focus-header b {
  color: var(--home-primary);
}

.empty-state-text {
  padding: 16px;
  text-align: center;
  background: #F8FAFC;
  border: 1px dashed #E2E8F0;
  border-radius: 8px;
  color: #94A3B8;
  font-size: 0.88rem;
}

.weak-list,
.resource-flow {
  display: grid;
  gap: 10px;
}

.weak-list button,
.resource-item,
.tip-pill {
  font: inherit;
  cursor: pointer;
}

.weak-list button {
  width: 100%;
  padding: 13px 14px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  background: #FFFFFF;
  text-align: left;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

.weak-list button:hover {
  background: #F8FAFC;
  border-color: #CBD5E1;
}

.weak-list strong,
.weak-list span {
  display: block;
}

.weak-list strong {
  color: #0F172A;
  font-size: 0.95rem;
  margin-bottom: 5px;
}

.weak-list span {
  color: #64748B;
  font-size: 0.84rem;
}

.resource-flow {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-content: start;
  flex: 1;
}

.resource-flow.is-empty {
  grid-template-columns: 1fr;
}

.empty-resource-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px 20px;
  background: #F8FAFC;
  border: 1px dashed #E2E8F0;
  border-radius: 8px;
  height: 100%;
  box-sizing: border-box;
}

.empty-icon {
  font-size: 2.2rem;
  color: #CBD5E1;
  margin-bottom: 12px;
}

.empty-resource-state p {
  margin: 0 0 6px;
  color: #475569;
  font-size: 0.95rem;
  font-weight: 700;
}

.empty-resource-state span {
  color: #94A3B8;
  font-size: 0.84rem;
  line-height: 1.5;
  max-width: 380px;
}

.resource-item {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  min-height: 0;
  padding: 12px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  background: #FFFFFF;
  text-align: left;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.resource-item:hover {
  transform: translateY(-2px);
  border-color: #CBD5E1;
  box-shadow: 0 12px 22px rgba(15, 23, 42, 0.06);
}

.resource-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  color: var(--tone-accent);
  font-size: 0.76rem;
  font-weight: 850;
}

.resource-meta em {
  color: #94A3B8;
  font-style: normal;
  font-weight: 650;
}

.resource-info h3 {
  margin: 6px 0 4px;
  color: #0F172A;
  font-size: 0.94rem;
  font-weight: 850;
  line-height: 1.32;
}

.resource-info p {
  margin: 0;
  color: #64748B;
  font-size: 0.8rem;
  line-height: 1.45;
}

.bottom-utility {
  max-width: 1680px;
  margin: 0 auto;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.utility-copy {
  min-width: 0;
}

.utility-copy h2 {
  margin: 6px 0 0;
  font-size: 1.08rem;
  color: #0F172A;
  white-space: nowrap;
}

.utility-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.tip-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid #E2E8F0;
  border-radius: 999px;
  background: #FFFFFF;
  color: #475569;
  font-weight: 750;
  transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}

.tip-pill:hover {
  background: var(--home-primary-soft);
  color: var(--home-primary);
  border-color: var(--home-primary-border);
}

.tone-blue {
  --tone-accent: #2563EB;
  --tone-soft: #EFF6FF;
}

.tone-emerald {
  --tone-accent: #059669;
  --tone-soft: #ECFDF5;
}

.tone-indigo {
  --tone-accent: #4F46E5;
  --tone-soft: #EEF2FF;
}

.tone-amber {
  --tone-accent: #D97706;
  --tone-soft: #FFFBEB;
}

:deep(.el-button--primary) {
  --el-button-bg-color: var(--home-primary) !important;
  --el-button-border-color: var(--home-primary) !important;
  --el-button-hover-bg-color: var(--home-primary) !important;
  --el-button-hover-border-color: var(--home-primary) !important;
  background: var(--home-primary) !important;
  border-color: var(--home-primary) !important;
}

:deep(.el-button--primary:hover) {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px -5px rgba(79, 70, 229, 0.3);
}

.portrait-stat.clickable {
  cursor: pointer;
  transition: border-color 0.25s ease, background-color 0.25s ease, transform 0.2s ease;
}

.portrait-stat.clickable:hover {
  border-color: var(--home-primary-border);
  background-color: var(--home-primary-soft);
  transform: translateY(-2px);
}

.portrait-radar-section {
  display: flex;
  gap: 20px;
  align-items: center;
  margin-bottom: 20px;
}

.radar-chart-wrapper {
  flex: 1.2;
  height: 240px;
  min-height: 240px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.prominent-dimensions {
  flex: 0.8;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dimensions-title {
  font-size: 0.85rem;
  font-weight: 800;
  color: #64748B;
  letter-spacing: 0.04em;
  margin-bottom: 4px;
}

.dimension-tags-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dim-tag-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 700;
}

.dim-name {
  color: #475569;
}

.dim-score {
  color: #0F172A;
  font-weight: 800;
}

.dim-trend {
  display: inline-flex;
  align-items: center;
  font-weight: bold;
}

.dim-trend.up {
  color: #10B981;
}

.dim-trend.down {
  color: #EF4444;
}

.dim-trend.stable {
  color: #94A3B8;
}

.weak-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  background: #FFFFFF;
  margin-bottom: 8px;
  transition: border-color 0.2s ease, background-color 0.2s ease;
}

.weak-item:hover {
  border-color: #CBD5E1;
  background-color: #F8FAFC;
}

.weak-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.weak-info strong {
  color: #0F172A;
  font-size: 0.95rem;
}

.weak-info span {
  color: #64748B;
  font-size: 0.84rem;
}

.weak-cta-btn {
  flex-shrink: 0;
  border-radius: 8px !important;
  font-weight: 700 !important;
}

.card-footer-link {
  display: flex;
  justify-content: center;
  padding-top: 14px;
  border-top: 1px solid #E2E8F0;
  margin-top: 16px;
}



@media (max-width: 1280px) {
  .feature-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .hub-grid,
  .hub-hero {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .home-hub {
    padding: 18px;
  }

  .hero-main,
  .goal-panel,
  .insight-card {
    padding: 20px;
  }

  .portrait-strip,
  .feature-row,
  .resource-flow {
    grid-template-columns: 1fr;
  }

  .hero-main h1 {
    font-size: 2rem;
  }

  .hero-main p {
    white-space: normal;
  }

  .bottom-utility {
    align-items: flex-start;
    flex-direction: column;
  }

  .utility-actions {
    justify-content: flex-start;
  }

  .portrait-radar-section {
    flex-direction: column;
    gap: 10px;
  }

  .radar-chart-wrapper {
    width: 100%;
    height: 200px;
    min-height: 200px;
  }

  .prominent-dimensions {
    width: 100%;
  }
}
</style>
