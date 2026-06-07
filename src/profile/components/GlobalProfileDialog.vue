<template>
  <el-dialog
    v-model="isGlobalProfileVisible"
    title="我的学习画像"
    width="920px"
    class="global-profile-dialog"
    :append-to-body="true"
    @open="handleOpen"
  >
    <div v-if="profile" class="dialog-body">
      <section class="section">
        <h3>冷启动基础信息</h3>
        <div class="kv-grid">
          <div><span>学校</span><strong>{{ profile.base_info.school || '未填写' }}</strong></div>
          <div><span>专业</span><strong>{{ profile.base_info.major || '未填写' }}</strong></div>
          <div><span>年级</span><strong>{{ profile.base_info.grade || '未填写' }}</strong></div>
          <div><span>每日学习时长</span><strong>{{ profile.base_info.daily_study_time || '未填写' }}</strong></div>
          <div><span>全局学习目标</span><strong>{{ profile.base_info.global_learning_goal || '未填写' }}</strong></div>
          <div><span>课程数</span><strong>{{ profile.base_info.courses?.length || 0 }}</strong></div>
        </div>
      </section>

      <section class="section">
        <h3>全局画像</h3>
        <div class="card-grid">
          <article v-for="item in globalCards" :key="item.title" class="profile-card">
            <h4>{{ item.title }}</h4>
            <p>{{ item.summary }}</p>
          </article>
        </div>
      </section>

      <section class="section">
        <h3>课程子画像</h3>
        <div v-if="courseCards.length" class="card-grid">
          <article v-for="course in courseCards" :key="course.name" class="profile-card">
            <div class="course-head">
              <h4>{{ course.name }}</h4>
              <span>{{ course.level }}</span>
            </div>
            <p>{{ course.goal }}</p>
            <div v-if="course.weakPoints.length" class="tag-list">
              <span v-for="point in course.weakPoints" :key="point">{{ point }}</span>
            </div>
          </article>
        </div>
        <div v-else class="empty-state">当前还没有课程子画像。</div>
      </section>

      <section v-if="strategyList.length" class="section">
        <h3>当前策略</h3>
        <ul class="strategy-list">
          <li v-for="item in strategyList" :key="item">{{ item }}</li>
        </ul>
      </section>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { getProfile, type ProfileData } from '@/profile/api/profile'
import { isGlobalProfileVisible, profileRefreshTrigger } from '@/profile/composables/useGlobalProfile'

const profile = ref<ProfileData | null>(null)

const globalCards = computed(() => {
  const globalProfile = (profile.value?.learning_profile as any)?.global_profile || {}
  return [
    { title: '专业背景', summary: globalProfile.major_background?.value || '暂无' },
    { title: '学习阶段', summary: globalProfile.student_stage?.value || '暂无' },
    { title: '学习节奏', summary: globalProfile.learning_pace?.value || '暂无' },
    { title: '认知风格', summary: globalProfile.cognitive_style?.value || '暂无' },
  ]
})

const courseCards = computed(() => {
  const courses = ((profile.value?.learning_profile as any)?.course_profiles || []) as any[]
  return courses.map((course) => ({
    name: course.course_context?.value?.course || '未命名课程',
    level: course.knowledge_level?.value || '暂无',
    goal: ((course.learning_goal_type?.value || []) as string[]).join(' / ') || '暂无目标',
    weakPoints: (course.weak_knowledge_points?.value || []).map((item: any) => item.name || item),
  }))
})

const strategyList = computed(() => {
  const strategy = profile.value?.initial_strategy || {}
  return [
    strategy.strategy_summary,
    strategy.path_planning_strategy,
    strategy.tutor_strategy,
  ].filter(Boolean) as string[]
})

const fetchProfile = async () => {
  try {
    const res = await getProfile()
    profile.value = res.data.data
  } catch (error) {
    console.error('Failed to fetch profile dialog data', error)
  }
}

const handleOpen = () => {
  fetchProfile()
}

watch(profileRefreshTrigger, () => {
  if (isGlobalProfileVisible.value) {
    fetchProfile()
  }
})
</script>

<style scoped>
.dialog-body {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section h3 {
  margin: 0;
  font-size: 18px;
}

.kv-grid,
.card-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.kv-grid div,
.profile-card {
  padding: 14px;
  border-radius: 14px;
  border: 1px solid var(--color-border);
  background: #fff;
}

.kv-grid span {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.profile-card h4 {
  margin: 0 0 8px;
}

.profile-card p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.course-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.tag-list span {
  padding: 4px 8px;
  border-radius: 999px;
  background: #fff7ed;
  color: #c2410c;
  font-size: 12px;
}

.strategy-list {
  margin: 0;
  padding-left: 18px;
  color: var(--color-text-secondary);
}

.strategy-list li {
  line-height: 1.7;
}

.empty-state {
  color: var(--color-text-faint);
}
</style>
