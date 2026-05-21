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
  --home-primary: var(--color-primary);
  --home-primary-soft: var(--color-primary-soft);
  --home-primary-border: var(--color-primary-border);
  min-height: calc(100vh - var(--navbar-height));
  padding: var(--space-8);
  background: var(--color-bg);
  color: var(--color-text);
  box-sizing: border-box;
  font-family: var(--font-sans);
}

.hub-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, 0.75fr);
  gap: var(--space-5);
  max-width: var(--page-max-width);
  margin: 0 auto var(--space-5);
}

.hero-main,
.goal-panel,
.feature-card,
.insight-card,
.bottom-utility {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
}

.hero-main {
  padding: var(--space-8);
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
  font-weight: var(--weight-extrabold);
}

.status-dot {
  display: inline-block;
  width: var(--space-2);
  height: var(--space-2);
  margin-right: 6px;
  border-radius: var(--radius-pill);
  background: var(--color-success);
}

.hero-main h1 {
  margin: 22px 0 var(--space-3);
  max-width: 100%;
  font-size: var(--text-3xl);
  line-height: 1.05;
  letter-spacing: 0;
  font-weight: 850;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hero-main p {
  margin: 0;
  max-width: 640px;
  color: var(--color-text-muted);
  line-height: 1.7;
  font-size: 1.02rem;
}

.portrait-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin-top: 28px;
}

.portrait-stat {
  padding: var(--space-4);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.portrait-stat span,
.section-label,
.panel-topline span {
  display: block;
  color: var(--color-text-faint);
  font-size: 0.76rem;
  font-weight: 850;
  letter-spacing: 0.04em;
}

.portrait-stat strong {
  display: block;
  margin-top: var(--space-2);
  color: var(--color-text-strong);
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
  gap: var(--space-3);
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
  gap: var(--space-3);
  margin-bottom: 22px;
}

.goal-step {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  color: var(--color-text-secondary);
  line-height: 1.55;
}

.goal-step .el-icon {
  margin-top: 2px;
  color: var(--color-success);
}

.goal-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: auto;
}

.home-primary-button {
  border-radius: var(--radius-lg) !important;
  font-weight: var(--weight-semibold) !important;
}

.home-link-button {
  min-height: 32px;
  padding: var(--space-2) 14px !important;
  border: 1px solid var(--home-primary-border) !important;
  border-radius: var(--radius-lg) !important;
  background: var(--home-primary-soft) !important;
  color: var(--home-primary) !important;
  font-weight: var(--weight-bold) !important;
  box-shadow: none !important;
  transition: transform var(--transition-base), border-color var(--transition-base), background-color var(--transition-base), box-shadow var(--transition-base) !important;
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
  max-width: var(--page-max-width);
  margin: 0 auto var(--space-5);
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.feature-card {
  border: 0;
  cursor: pointer;
  min-height: 150px;
  padding: var(--space-5);
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 14px;
  text-align: left;
  transition: transform var(--transition-base), border-color var(--transition-base), box-shadow var(--transition-base);
}

.feature-card:hover {
  transform: translateY(-3px);
  border-color: var(--color-border-hover);
  box-shadow: 0 16px 30px rgba(15, 23, 42, 0.07);
}

.feature-icon,
.resource-icon,
.profile-avatar {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
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
  margin: var(--space-2) 0 var(--space-2);
  color: var(--color-text);
  font-size: 1.05rem;
  font-weight: 850;
}

.feature-copy p {
  margin: 0;
  color: var(--color-text-muted);
  line-height: 1.52;
  font-size: 0.9rem;
}

.feature-arrow {
  color: var(--color-border-hover);
  margin-top: 2px;
}

.hub-grid {
  max-width: var(--page-max-width);
  margin: 0 auto var(--space-5);
  display: grid;
  grid-template-columns: minmax(340px, 0.8fr) minmax(0, 1.2fr);
  gap: var(--space-5);
}

.insight-card {
  padding: var(--space-6);
}

.resource-card {
  display: flex;
  flex-direction: column;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  align-items: flex-start;
  margin-bottom: var(--space-5);
}

.section-heading h2 {
  margin: 6px 0 0;
  color: var(--color-text);
  font-size: var(--text-lg);
  font-weight: 850;
}

.profile-summary {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 14px;
  align-items: start;
  padding: var(--space-4);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.profile-summary h3 {
  margin: 0 0 6px;
  color: var(--color-text);
  font-size: 1rem;
}

.profile-summary p {
  margin: 0;
  color: var(--color-text-muted);
  line-height: 1.58;
}

.profile-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: var(--space-4) 0;
}

.profile-tags span {
  padding: 6px 10px;
  border-radius: var(--radius-pill);
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
  font-size: 0.82rem;
  font-weight: var(--weight-bold);
}

.weak-focus {
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-4);
}

.focus-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: var(--color-text-muted);
  font-size: 0.88rem;
  font-weight: var(--weight-extrabold);
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
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  text-align: left;
  transition: background-color var(--transition-base), border-color var(--transition-base);
}

.weak-list button:hover {
  background: var(--color-bg);
  border-color: var(--color-border-hover);
}

.weak-list strong,
.weak-list span {
  display: block;
}

.weak-list strong {
  color: var(--color-text);
  font-size: 0.95rem;
  margin-bottom: 5px;
}

.weak-list span {
  color: var(--color-text-muted);
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
  gap: var(--space-3);
  align-items: start;
  min-height: 0;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  text-align: left;
  transition: transform var(--transition-base), box-shadow var(--transition-base), border-color var(--transition-base);
}

.resource-item:hover {
  transform: translateY(-2px);
  border-color: var(--color-border-hover);
  box-shadow: 0 12px 22px rgba(15, 23, 42, 0.06);
}

.resource-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
  color: var(--tone-accent);
  font-size: 0.76rem;
  font-weight: 850;
}

.resource-meta em {
  color: var(--color-text-faint);
  font-style: normal;
  font-weight: 650;
}

.resource-info h3 {
  margin: 6px 0 var(--space-1);
  color: var(--color-text);
  font-size: 0.94rem;
  font-weight: 850;
  line-height: 1.32;
}

.resource-info p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.8rem;
  line-height: 1.45;
}

.bottom-utility {
  max-width: var(--page-max-width);
  margin: 0 auto;
  padding: 18px var(--space-5);
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
  color: var(--color-text);
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
  gap: var(--space-2);
  padding: 10px var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-weight: 750;
  transition: background-color var(--transition-base), color var(--transition-base), border-color var(--transition-base);
}

.tip-pill:hover {
  background: var(--home-primary-soft);
  color: var(--home-primary);
  border-color: var(--home-primary-border);
}

.tone-blue {
  --tone-accent: var(--tone-blue);
  --tone-soft: var(--tone-blue-soft);
}

.tone-emerald {
  --tone-accent: var(--tone-emerald);
  --tone-soft: var(--tone-emerald-soft);
}

.tone-indigo {
  --tone-accent: var(--tone-indigo);
  --tone-soft: var(--tone-indigo-soft);
}

.tone-amber {
  --tone-accent: var(--tone-amber);
  --tone-soft: var(--tone-amber-soft);
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
    padding: var(--space-5);
  }

  .portrait-strip,
  .feature-row,
  .resource-flow {
    grid-template-columns: 1fr;
  }

  .hero-main h1 {
    font-size: var(--text-2xl);
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
