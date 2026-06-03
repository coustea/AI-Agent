<template>
  <div class="home-page">
    <section class="hero-card">
      <div class="hero-copy">
        <el-tag round effect="plain">{{ isColdStart ? '冷启动阶段' : '画像已激活' }}</el-tag>
        <h1>{{ heroTitle }}</h1>
        <p>{{ heroDescription }}</p>
      </div>
      <div class="hero-stats">
        <div v-for="item in statCards" :key="item.label" class="stat-card">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>
    </section>

    <section class="grid">
      <article class="panel">
        <div class="panel-head">
          <h2>全局画像</h2>
          <el-button text @click="goTo('/profile')">查看详情</el-button>
        </div>
        <div class="info-grid">
          <div v-for="item in globalCards" :key="item.label" class="info-card">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>课程子画像</h2>
          <el-button text @click="goTo('/path-planner')">规划路径</el-button>
        </div>
        <div v-if="courseCards.length" class="list">
          <div v-for="item in courseCards" :key="item.name" class="course-card">
            <div class="course-head">
              <strong>{{ item.name }}</strong>
              <span>{{ item.level }}</span>
            </div>
            <p>{{ item.goal }}</p>
            <div v-if="item.weakPoints.length" class="tag-list">
              <span v-for="point in item.weakPoints" :key="point">{{ point }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">当前还没有课程子画像。</div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>掌握度追踪</h2>
          <el-button text @click="goTo('/question-bank')">去练习</el-button>
        </div>
        <div v-if="masteryTop.length" class="list">
          <div v-for="item in masteryTop" :key="`${item.course}-${item.knowledge_point}`" class="mastery-card">
            <div class="mastery-top">
              <div>
                <strong>{{ item.knowledge_point }}</strong>
                <span>{{ item.course }}</span>
              </div>
              <em>{{ item.status }}</em>
            </div>
            <el-progress :percentage="item.mastery_score" :status="item.mastery_score < 40 ? 'exception' : undefined" />
          </div>
        </div>
        <div v-else class="empty-state">掌握度会在练习、资源学习和辅导过程中逐步更新。</div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>当前策略</h2>
          <el-button text @click="goTo('/resource-generator')">生成资源</el-button>
        </div>
        <ul v-if="strategyList.length" class="strategy-list">
          <li v-for="item in strategyList" :key="item">{{ item }}</li>
        </ul>
        <div v-else class="empty-state">当前还没有可展示的学习策略。</div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { getProfile, type ProfileData } from '@/profile/api/profile'

const router = useRouter()
const profile = ref<ProfileData | null>(null)

const goTo = (path: string) => router.push(path)

const globalProfile = computed(() => ((profile.value?.learning_profile as any)?.global_profile || {}))

const globalCards = computed(() => [
  { label: '专业背景', value: globalProfile.value.major_background?.value || '暂无' },
  { label: '学习阶段', value: globalProfile.value.student_stage?.value || '暂无' },
  { label: '学习节奏', value: globalProfile.value.learning_pace?.value || '暂无' },
  { label: '认知风格', value: globalProfile.value.cognitive_style?.value || '暂无' },
])

const courseCards = computed(() => {
  const courses = ((profile.value?.learning_profile as any)?.course_profiles || []) as any[]
  return courses.map((course) => ({
    name: course.course_context?.value?.course || '未命名课程',
    level: course.knowledge_level?.value || '暂无',
    goal: ((course.learning_goal_type?.value || []) as string[]).join(' / ') || '暂无目标',
    weakPoints: (course.weak_knowledge_points?.value || []).map((item: any) => item.name || item),
  }))
})

const masteryTop = computed(() => {
  const items = (profile.value?.knowledge_mastery || []) as Array<any>
  return [...items].sort((a, b) => (a.mastery_score || 0) - (b.mastery_score || 0)).slice(0, 4)
})

const strategyList = computed(() => {
  const strategy = profile.value?.initial_strategy || {}
  return [
    strategy.strategy_summary,
    strategy.path_planning_strategy,
    strategy.tutor_strategy,
  ].filter(Boolean) as string[]
})

const isColdStart = computed(() => !profile.value?.base_info?.major)
const heroTitle = computed(() => {
  if (isColdStart.value) return '先建立你的基础学习画像'
  return `今天建议从 ${courseCards.value[0]?.name || '当前课程'} 开始`
})

const heroDescription = computed(() => {
  if (isColdStart.value) {
    return '首次画像只负责冷启动。真正影响资源推荐、路径规划和智能辅导的，是你后续使用系统时持续形成的动态画像。'
  }
  return '系统会优先基于课程子画像、知识掌握度和最近学习信号，动态调整资源生成、路径规划和辅导策略。'
})

const statCards = computed(() => [
  { label: '学校', value: profile.value?.base_info.school || '未填写' },
  { label: '目标', value: profile.value?.base_info.global_learning_goal || '未填写' },
  { label: '课程数', value: String(profile.value?.base_info.courses?.length || 0) },
])

const loadProfile = async () => {
  try {
    const res = await getProfile()
    profile.value = res.data.data
  } catch (error) {
    console.error('Failed to load dashboard profile', error)
  }
}

onMounted(loadProfile)
</script>

<style scoped>
.home-page {
  min-height: calc(100vh - 64px);
  padding: 28px;
  background: #f8fafc;
}

.hero-card,
.panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.hero-card {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 20px;
  padding: 28px;
  margin-bottom: 24px;
}

.hero-copy h1 {
  margin: 16px 0 10px;
  font-size: 2.3rem;
  line-height: 1.05;
  color: #0f172a;
}

.hero-copy p {
  margin: 0;
  line-height: 1.75;
  color: #64748b;
}

.hero-stats,
.info-grid,
.list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-card,
.info-card,
.course-card,
.mastery-card {
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.stat-card span,
.info-card span {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: #64748b;
}

.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

.panel {
  padding: 24px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-head h2 {
  margin: 0;
  font-size: 1.08rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.course-head,
.mastery-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.course-card p,
.mastery-top span,
.mastery-top em {
  color: #64748b;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.tag-list span {
  padding: 4px 8px;
  border-radius: 999px;
  background: #fff7ed;
  color: #c2410c;
  font-size: 12px;
}

.mastery-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mastery-top strong {
  display: block;
  margin-bottom: 4px;
}

.strategy-list {
  margin: 0;
  padding-left: 18px;
  color: #475569;
}

.strategy-list li {
  line-height: 1.8;
}

.empty-state {
  color: #94a3b8;
}

@media (max-width: 960px) {
  .home-page {
    padding: 18px;
  }

  .hero-card,
  .grid,
  .info-grid {
    grid-template-columns: 1fr;
  }

  .hero-copy h1 {
    font-size: 1.9rem;
  }
}
</style>
