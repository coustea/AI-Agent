<template>
  <div class="home-hub">
    <section class="hub-hero">
      <div class="hero-main">
        <el-tag class="hero-kicker" effect="plain" round>
          <span class="status-dot"></span>
          学习画像已同步
        </el-tag>
        <h1>今天建议从{{ recommendedGoal.topic }}开始</h1>
        <p>
          基于你的学习画像、最近生成资源和当前路径进度，系统已整理出下一步目标。
        </p>

        <div class="portrait-strip">
          <div v-for="item in portraitStats" :key="item.label" class="portrait-stat">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </div>

      <aside class="goal-panel">
        <div class="panel-topline">
          <span>推荐学习目标</span>
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
          <el-button class="home-link-button" @click="goTo('/profile')">查看画像</el-button>
        </div>

        <div class="profile-summary">
          <div class="profile-avatar">
            <el-icon><User /></el-icon>
          </div>
          <div>
            <h3>{{ learnerProfile.role }}</h3>
            <p>{{ learnerProfile.summary }}</p>
          </div>
        </div>

        <div class="profile-tags">
          <span v-for="tag in learnerProfile.tags" :key="tag">{{ tag }}</span>
        </div>

        <div class="weak-focus">
          <div class="focus-header">
            <span>当前薄弱点</span>
            <b>{{ learnerProfile.weakPoints.length }} 项</b>
          </div>
          <div class="weak-list">
            <button
              v-for="point in learnerProfile.weakPoints"
              :key="point.name"
              type="button"
              @click="goTo('/resource-generator')"
            >
              <strong>{{ point.name }}</strong>
              <span>{{ point.hint }}</span>
            </button>
          </div>
        </div>
      </article>

      <article class="insight-card resource-card">
        <div class="section-heading">
          <div>
            <span class="section-label">MULTI-AGENT RESOURCES</span>
            <h2>多智能体资源流</h2>
          </div>
          <el-button class="home-link-button" @click="goTo('/resource-generator')">进入资源引擎</el-button>
        </div>

        <div class="resource-flow">
          <button
            v-for="resource in multiAgentResources"
            :key="resource.id"
            type="button"
            class="resource-item"
            :class="resource.tone"
            @click="goTo('/resource-generator')"
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
        </div>
      </article>
    </section>

    <section class="bottom-utility">
      <div class="utility-copy">
        <span class="section-label">START SMART</span>
        <h2>先确认学习目标，再选择合适的工具继续推进</h2>
      </div>
      <div class="utility-actions">
        <button
          v-for="tip in starterTips"
          :key="tip.label"
          type="button"
          class="tip-pill"
          @click="goTo(tip.path)"
        >
          <el-icon><component :is="tip.icon" /></el-icon>
          <span>{{ tip.label }}</span>
        </button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowRight,
  ChatDotRound,
  CircleCheckFilled,
  Clock,
  Collection,
  Connection,
  Cpu,
  DataLine,
  Document,
  Edit,
  MagicStick,
  Monitor,
  Odometer,
  Position,
  Share,
  User
} from '@element-plus/icons-vue'

const router = useRouter()

const goTo = (path: string) => {
  router.push(path)
}

const recommendedGoal = ref({
  topic: '操作系统死锁复习',
  confidence: '基于 5 份资源',
  title: '完成死锁四条件图解与自测闭环',
  steps: [
    '复习最近生成的图解讲义',
    '完成 5 道自适应测验',
    '把错题加入本周学习路径'
  ]
})

const portraitStats = ref([
  { label: '当前阶段', value: '软件工程大二' },
  { label: '学习场景', value: '考试备考' },
  { label: '资源偏好', value: '图解 + 自测' }
])

const learnerProfile = ref({
  role: '软件工程学习者',
  summary: '更适合先建立结构图，再通过题目和代码样例巩固概念。',
  tags: ['图解优先', '考点驱动', '偏好短任务', '需要错题回流'],
  weakPoints: [
    { name: '死锁必要条件', hint: '建议先看图解再做判断题' },
    { name: '动态规划状态转移', hint: '适合生成代码模板和例题' },
    { name: '红黑树旋转', hint: '需要流程图和逐步演示' }
  ]
})

const primaryActions = ref([
  {
    title: '多智能体资源生成',
    badge: 'RESOURCE ENGINE',
    description: '生成讲解、导图、图解、代码、测验和阅读材料。',
    icon: Cpu,
    path: '/resource-generator',
    tone: 'tone-blue'
  },
  {
    title: '继续学习路径',
    badge: 'LEARNING PATH',
    description: '把资源和薄弱点整理成可执行的阶段目标。',
    icon: Connection,
    path: '/path-planner',
    tone: 'tone-emerald'
  },
  {
    title: '向智能导师提问',
    badge: 'AI TUTOR',
    description: '围绕当前画像和学习目标获得即时解释。',
    icon: ChatDotRound,
    path: '/tutor',
    tone: 'tone-indigo'
  },
  {
    title: '查看多维评估',
    badge: 'EVALUATION',
    description: '查看掌握度、练习表现和下一步建议。',
    icon: DataLine,
    path: '/evaluation',
    tone: 'tone-amber'
  }
])

const multiAgentResources = ref([
  {
    id: 1,
    title: '死锁四条件图解讲义',
    agent: '图解智能体',
    time: '12 分钟前',
    hint: '适合作为今日目标的第一步',
    icon: Share,
    tone: 'tone-blue'
  },
  {
    id: 2,
    title: '操作系统同步互斥自测题',
    agent: '测验智能体',
    time: '34 分钟前',
    hint: '建议完成后更新薄弱点',
    icon: Edit,
    tone: 'tone-amber'
  },
  {
    id: 3,
    title: '动态规划状态设计模板',
    agent: '代码智能体',
    time: '昨天',
    hint: '可加入算法强化路径',
    icon: Monitor,
    tone: 'tone-emerald'
  },
  {
    id: 4,
    title: '红黑树旋转知识树',
    agent: '导图智能体',
    time: '昨天',
    hint: '适合配合导师问答复盘',
    icon: Document,
    tone: 'tone-indigo'
  },
  {
    id: 5,
    title: '进程调度算法对比表',
    agent: '阅读智能体',
    time: '2 天前',
    hint: '适合考前横向复习',
    icon: Collection,
    tone: 'tone-blue'
  },
  {
    id: 6,
    title: '数据库索引错题解析',
    agent: '评估智能体',
    time: '2 天前',
    hint: '已关联到掌握度评估',
    icon: DataLine,
    tone: 'tone-amber'
  },
  {
    id: 7,
    title: '网络分层速记卡片',
    agent: '卡片智能体',
    time: '3 天前',
    hint: '可用于碎片时间复习',
    icon: MagicStick,
    tone: 'tone-emerald'
  },
  {
    id: 8,
    title: '链表反转代码练习',
    agent: '代码智能体',
    time: '3 天前',
    hint: '建议加入算法训练任务',
    icon: Monitor,
    tone: 'tone-indigo'
  }
])

const starterTips = ref([
  { label: '建立画像', icon: User, path: '/profile?action=edit-profile' },
  { label: '生成资源', icon: MagicStick, path: '/resource-generator' },
  { label: '继续任务', icon: Position, path: '/path-planner' },
  { label: '查看进度', icon: Odometer, path: '/evaluation' },
  { label: '最近资源', icon: Collection, path: '/resource-generator' },
  { label: '学习时长', icon: Clock, path: '/dashboard' }
])
</script>

<style scoped>
.home-hub {
  --home-primary: var(--primary, #4F46E5);
  --home-primary-soft: var(--primary-light, #EEF2FF);
  --home-primary-border: #C7D2FE;
  min-height: calc(100vh - 64px);
  padding: 28px;
  background: #F8FAFC;
  color: #0F172A;
  box-sizing: border-box;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, -apple-system, sans-serif;
}

.hub-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
  gap: 20px;
  max-width: 1680px;
  margin: 0 auto 20px;
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
  max-width: 640px;
  color: #64748B;
  line-height: 1.7;
  font-size: 1.02rem;
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
  margin: 0 auto 20px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
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
  margin: 0 auto 20px;
  display: grid;
  grid-template-columns: minmax(340px, 0.8fr) minmax(0, 1.2fr);
  gap: 20px;
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

  .bottom-utility {
    align-items: flex-start;
    flex-direction: column;
  }

  .utility-actions {
    justify-content: flex-start;
  }
}
</style>
