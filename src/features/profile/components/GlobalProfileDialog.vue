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
        <h3><el-icon><Monitor /></el-icon> 全局学习特征 (Global Profile Dimensions)</h3>
        <div class="card-grid">
          <article v-for="item in globalCards" :key="item.title" class="profile-card">
            <h4>{{ item.title }}</h4>
            <p>{{ item.summary }}</p>
          </article>
        </div>
      </section>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Monitor } from '@element-plus/icons-vue'

import { getProfile, type ProfileData } from '@/features/profile/api/profile'
import { isGlobalProfileVisible, profileRefreshTrigger } from '@/features/profile/model/useGlobalProfile'

const profile = ref<ProfileData | null>(null)

const globalCards = computed(() => {
  const dims = profile.value?.dimensions || {}
  return [
    { title: '专业背景', summary: dims.major_background?.value || '暂无' },
    { title: '学习阶段', summary: dims.student_stage?.value || '暂无' },
    { title: '学习节奏', summary: dims.learning_pace?.value || '暂无' },
    { title: '认知风格', summary: dims.cognitive_style?.value || '暂无' },
    { title: '实践特征', summary: dims.practice_profile?.value || '暂无' },
    { title: '目标类型', summary: dims.learning_goal_type?.value || '暂无' },
    { title: '资源偏好', summary: dims.resource_preference_weight?.value || '暂无' },
  ]
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
  display: flex;
  align-items: center;
  gap: 8px;
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
  color: var(--color-text-primary);
  font-size: 15px;
}

.profile-card p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: 1.6;
  font-size: 14px;
}
</style>
