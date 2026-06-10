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
        <h3><el-icon><Monitor /></el-icon> 全局画像 (Root Profile)</h3>
        <div class="card-grid">
          <article v-for="item in globalCards" :key="item.title" class="profile-card">
            <h4>{{ item.title }}</h4>
            <p>{{ item.summary }}</p>
          </article>
        </div>
      </section>

      <section class="section">
        <h3><el-icon><DataBoard /></el-icon> 课程子画像 (Sub Profiles)</h3>
        <el-tabs v-if="courseCards.length" type="border-card" class="course-tabs">
          <el-tab-pane v-for="course in courseCards" :key="course.name" :label="course.name">
            <div class="profile-card sub-profile-card">
              <div class="course-head">
                <h4>知识水平评估</h4>
                <el-tag size="small" type="warning" effect="dark">{{ course.level }}</el-tag>
              </div>
              <p class="course-goal"><strong>近期学习目标:</strong> {{ course.goal }}</p>
              <div class="weak-points-section" v-if="course.weakPoints.length">
                <strong>核心薄弱点:</strong>
                <div class="tag-list">
                  <el-tag effect="light" type="danger" round v-for="point in course.weakPoints" :key="point">{{ point }}</el-tag>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
        <div v-else class="empty-state">
          <el-empty description="当前还没有课程子画像" :image-size="60" />
        </div>
      </section>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Monitor, DataBoard } from '@element-plus/icons-vue'

import { getProfile, type ProfileData } from '@/features/profile/api/profile'
import { isGlobalProfileVisible, profileRefreshTrigger } from '@/features/profile/model/useGlobalProfile'

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

.card-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.profile-card {
  padding: 14px;
  border-radius: 14px;
  border: 1px solid var(--color-border);
  background: #fff;
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





.empty-state {
  color: var(--color-text-faint);
}
</style>
