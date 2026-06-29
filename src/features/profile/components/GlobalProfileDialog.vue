<template>
  <Teleport to="body">
    <transition name="modal-fade">
      <div v-if="isGlobalProfileVisible" class="custom-modal-overlay" @click="isGlobalProfileVisible = false">
        <div class="custom-modal-content global-profile-modal" @click.stop>
          <div class="modal-header border-b border-slate-100 pb-3 mb-4 flex justify-between items-start">
            <div class="header-brand flex items-center gap-3">
              <div class="brand-icon w-10 h-10 bg-blue text-white flex items-center justify-center rounded-xl">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
              </div>
              <div>
                <h2 class="text-lg font-bold text-slate-900">全局学习画像</h2>
                <p class="text-xs text-slate-400 mt-0.5">
                  基于学习行为推断的 7 个维度特征
                  <span v-if="profile?.updated_at">· 最后更新 {{ formatTime(profile.updated_at) }}</span>
                </p>
              </div>
            </div>
            <button class="modal-close-btn text-slate-400 hover:text-slate-600" @click="isGlobalProfileVisible = false">×</button>
          </div>

          <div class="profile-panel py-2">
            <!-- 维度列表 -->
            <div class="dimensions-list" v-if="dimensionCards.length">
              <article
                v-for="(dim, idx) in dimensionCards"
                :key="dim.key"
                class="dimension-row"
                :class="{ 'is-expanded': expandedKey === dim.key }"
                @click="toggleExpand(dim.key)"
              >
                <div class="row-index">{{ String(idx + 1).padStart(2, '0') }}</div>

                <div class="row-main">
                  <div class="row-header flex justify-between items-center mb-1">
                    <h4 class="font-bold text-slate-800 text-sm">{{ dim.label }}</h4>
                    <span class="row-status text-xs text-green bg-green-50 px-2 py-0.5 rounded-full" v-if="dim.value">已推断</span>
                    <span class="row-status pending text-xs text-slate-400 bg-slate-50 px-2 py-0.5 rounded-full" v-else>待推断</span>
                  </div>

                  <p class="row-value text-xs text-slate-500 leading-relaxed">{{ dim.value || '系统尚未推断出此维度特征，继续学习后将自动生成' }}</p>

                  <!-- 证据列表 -->
                  <div class="row-evidence mt-2 p-2 bg-slate-50 border border-slate-100 rounded-lg" v-if="dim.evidence?.length && expandedKey === dim.key">
                    <div class="evidence-label flex items-center gap-1.5 text-xs text-slate-400 mb-1 font-semibold">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14,2 14,8 20,8"/>
                        <line x1="16" y1="13" x2="8" y2="13"/>
                        <line x1="16" y1="17" x2="8" y2="17"/>
                      </svg>
                      <span>推断依据</span>
                    </div>
                    <ul class="evidence-list list-disc pl-4 text-xs text-slate-500 space-y-0.5">
                      <li v-for="(ev, i) in dim.evidence" :key="i">{{ ev }}</li>
                    </ul>
                  </div>
                </div>

                <div class="row-expand-icon text-slate-400 self-center" v-if="dim.evidence?.length">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline :points="expandedKey === dim.key ? '18 15 12 9 6 15' : '6 9 12 15 18 9'"/>
                  </svg>
                </div>
              </article>
            </div>

            <div class="empty-state py-12 flex flex-col items-center justify-center text-center text-slate-400" v-else>
              <div class="empty-icon w-12 h-12 bg-slate-50 text-slate-300 rounded-full flex items-center justify-center mb-3">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 6v6l4 2"/>
                </svg>
              </div>
              <p class="text-sm">完成更多学习后，系统将自动推断你的画像维度</p>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { getProfile, type ProfileData, type ProfileDimensionKey } from '@/features/profile/api/profile'
import { isGlobalProfileVisible, profileRefreshTrigger } from '@/features/profile/model/useGlobalProfile'

const profile = ref<ProfileData | null>(null)
const loading = ref(false)
const expandedKey = ref<string | null>(null)

/**
 * 7 维度画像
 * - 知识层: knowledge_level, weak_knowledge_points, knowledge_gap_pattern
 * - 认知层: cognitive_style, learning_goal_type, difficulty_tolerance, self_correction_ability
 */
const DIMENSION_NAMES: Record<ProfileDimensionKey, string> = {
  knowledge_level: '知识基础',
  cognitive_style: '认知风格',
  weak_knowledge_points: '易错点偏好',
  knowledge_gap_pattern: '知识缺口模式',
  learning_goal_type: '学习目标导向',
  difficulty_tolerance: '难度耐受度',
  self_correction_ability: '自纠能力水平',
}

const dimensionCards = computed(() => {
  const dims = profile.value?.dimensions ?? {} as Record<ProfileDimensionKey, { value: string; evidence: string[] }>
  const evidences = profile.value?.profile_score_json?.dimension_evidence ?? {} as Record<ProfileDimensionKey, string[]>

  return Object.entries(DIMENSION_NAMES)
    .map(([key, label]) => ({
      key,
      label,
      value: dims[key as ProfileDimensionKey]?.value || '',
      evidence: evidences[key as ProfileDimensionKey] || [],
    }))
    .filter(dim => dim.value)
})

const toggleExpand = (key: string) => {
  expandedKey.value = expandedKey.value === key ? null : key
}

const formatTime = (time: string | null) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  if (diffHours < 1) return '刚刚'
  if (diffHours < 24) return `${diffHours} 小时前`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays} 天前`
  return date.toLocaleDateString('zh-CN')
}

const fetchProfile = async () => {
  loading.value = true
  try {
    const res = await getProfile()
    profile.value = res.data.data
  } catch (error) {
    console.error('Failed to fetch profile', error)
    profile.value = null
  } finally {
    loading.value = false
  }
}

watch(isGlobalProfileVisible, (newVal) => {
  if (newVal) {
    expandedKey.value = null
    fetchProfile()
  }
})

watch(profileRefreshTrigger, () => {
  if (isGlobalProfileVisible.value) {
    fetchProfile()
  }
})
</script>

<style scoped>
.profile-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.dimensions-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.dimension-row {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  cursor: pointer;
  background: var(--color-surface);
  transition: all var(--transition-base);
}

.dimension-row:hover {
  border-color: var(--color-border-hover);
  background: var(--color-surface-hover);
}

.dimension-row.is-expanded {
  border-color: var(--color-border-hover);
  background: var(--color-surface-hover);
}

.row-index {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
  font-size: var(--text-2xs);
  font-family: var(--font-mono);
  font-weight: var(--weight-bold);
}

.row-main {
  flex: 1;
  min-width: 0;
}
</style>
