<template>
  <el-dialog
    v-model="isGlobalProfileVisible"
    title=""
    width="920px"
    class="global-profile-dialog"
    :append-to-body="true"
    @open="handleOpen"
  >
    <div class="profile-panel" v-loading="loading">
      <!-- 头部 -->
      <header class="profile-header">
        <div class="header-brand">
          <div class="brand-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
          </div>
          <div>
            <h2>全局学习画像</h2>
            <p>基于学习行为推断的 7 个维度特征</p>
          </div>
        </div>
        <div class="header-meta" v-if="profile?.updated_at">
          <span class="update-label">最后更新</span>
          <span class="update-time">{{ formatTime(profile.updated_at) }}</span>
        </div>
      </header>

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
            <div class="row-header">
              <h4>{{ dim.label }}</h4>
              <span class="row-status" v-if="dim.value">已推断</span>
              <span class="row-status pending" v-else>待推断</span>
            </div>

            <p class="row-value">{{ dim.value || '系统尚未推断出此维度特征，继续学习后将自动生成' }}</p>

            <!-- 证据列表 -->
            <div class="row-evidence" v-if="dim.evidence?.length && expandedKey === dim.key">
              <div class="evidence-label">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14,2 14,8 20,8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                </svg>
                <span>推断依据</span>
              </div>
              <ul class="evidence-list">
                <li v-for="(ev, i) in dim.evidence" :key="i">{{ ev }}</li>
              </ul>
            </div>
          </div>

          <div class="row-expand-icon" v-if="dim.evidence?.length">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline :points="expandedKey === dim.key ? '18 15 12 9 6 15' : '6 9 12 15 18 9'"/>
            </svg>
          </div>
        </article>
      </div>

      <div class="empty-state" v-else>
        <div class="empty-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
          </svg>
        </div>
        <p>完成更多学习后，系统将自动推断你的画像维度</p>
      </div>
    </div>
  </el-dialog>
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

const handleOpen = () => {
  expandedKey.value = null
  fetchProfile()
}

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
  gap: var(--space-5);
  padding: var(--space-5);
  min-height: 520px;
}

/* 头部 */
.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding-bottom: var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.header-brand {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.brand-icon {
  width: 52px;
  height: 52px;
  background: var(--color-primary);
  color: var(--color-surface);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-brand h2 {
  margin: 0 0 var(--space-1);
  color: var(--color-text-strong);
  font-size: var(--text-xl);
  font-weight: var(--weight-extrabold);
}

.header-brand p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  max-width: 360px;
}

.header-meta {
  text-align: right;
}

.update-label {
  display: block;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  margin-bottom: 2px;
}

.update-time {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
}

/* 维度列表 */
.dimensions-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.dimension-row {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-4);
  margin: 0 calc(-1 * var(--space-4));
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-base);
}

.dimension-row:hover {
  background: var(--color-bg);
}

.dimension-row.is-expanded {
  background: var(--color-bg);
}

.row-index {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-hover);
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  font-size: var(--text-2xs);
  font-family: var(--font-mono);
  font-weight: var(--weight-bold);
}

.row-main {
  flex: 1;
  min-width: 0;
}

.row-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-2);
}

.row-header h4 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
}

.row-status {
  font-size: var(--text-xs);
  color: var(--color-success);
  padding: 2px var(--space-2);
  background: var(--color-success-soft);
  border-radius: var(--radius-sm);
  font-weight: var(--weight-semibold);
}

.row-status.pending {
  color: var(--color-text-muted);
  background: var(--color-bg);
}

.row-value {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: 1.6;
}

/* 证据 */
.row-evidence {
  margin-top: var(--space-3);
  padding: var(--space-3);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.evidence-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.evidence-list {
  margin: 0;
  padding-left: var(--space-4);
  list-style: disc;
}

.evidence-list li {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: 1.6;
  margin-bottom: var(--space-1);
}

.evidence-list li:last-child {
  margin-bottom: 0;
}

.row-expand-icon {
  flex-shrink: 0;
  color: var(--color-text-muted);
  transition: transform var(--transition-base);
}

.dimension-row.is-expanded .row-expand-icon {
  transform: rotate(180deg);
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  min-height: 320px;
  text-align: center;
}

.empty-icon {
  width: 64px;
  height: 64px;
  background: var(--color-bg);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
}

.empty-state p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

/* 响应式 */
@media (max-width: 768px) {
  .row-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-2);
  }

  .header-meta {
    display: none;
  }
}
</style>