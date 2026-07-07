<template>
  <Teleport to="body">
    <transition name="modal">
      <div v-if="isGlobalProfileVisible" class="modal-overlay" @click="isGlobalProfileVisible = false">
        <div class="modal-container" @click.stop>
          <!-- Header -->
          <div class="modal-header">
            <div>
              <h2 class="text-sm font-bold tracking-wider text-slate-900 font-mono uppercase">全局特征画像</h2>
              <p class="text-[9px] text-slate-400 font-mono mt-0.5" v-if="profile?.updated_at">
                LAST UPDATED: {{ formatTime(profile.updated_at) }}
              </p>
            </div>
            <button class="modal-close-btn" @click="isGlobalProfileVisible = false">
              <component :is="XIcon" class="w-3.5 h-3.5" />
            </button>
          </div>

          <!-- Body -->
          <div class="modal-body" v-if="profile && dimensionCards.length">
            <div class="dimensions-list">
              <div v-for="(dim, idx) in dimensionCards" :key="dim.key" class="dimension-item">
                <div class="dim-num font-mono">0{{ idx + 1 }}</div>
                <div class="dim-content">
                  <h3 class="dim-title font-bold text-slate-900 text-xs font-mono uppercase tracking-wide">
                    {{ dim.label }}
                  </h3>
                  <p class="dim-value text-slate-700 text-xs mt-1.5 leading-relaxed font-sans">
                    {{ dim.value }}
                  </p>
                  
                  <div v-if="dim.evidence?.length" class="dim-evidence mt-3 p-3 bg-slate-50 border border-slate-100">
                    <div class="evidence-title font-mono text-[9px] text-slate-400 tracking-wider font-bold">BEHAVIORAL EVIDENCE</div>
                    <ul class="evidence-list font-mono text-slate-500 mt-1.5 space-y-1">
                      <li v-for="(ev, i) in dim.evidence" :key="i" class="evidence-item text-xs flex items-start gap-1.5 leading-relaxed">
                        <span class="text-slate-950 font-bold flex-shrink-0">•</span>
                        <span>{{ ev }}</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div class="modal-body flex flex-col items-center justify-center text-center py-16 px-6" v-else-if="!loading">
            <div class="w-10 h-10 border border-slate-200 flex items-center justify-center text-slate-400 font-mono text-sm mb-4">
              ?
            </div>
            <h3 class="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono mb-1">暂无画像特征记录</h3>
            <p class="text-[10px] text-slate-400 max-w-[240px] leading-relaxed font-mono">系统将根据您后续的学习行为，自动提取并推断画像特性。</p>
          </div>

          <!-- Loading state skeleton -->
          <div class="modal-body p-6 space-y-4" v-if="loading">
            <div v-for="n in 3" :key="n" class="animate-pulse space-y-2 pb-4 border-b border-slate-100">
              <div class="h-3.5 bg-slate-100 w-1/4"></div>
              <div class="h-3 bg-slate-100 w-3/4"></div>
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
import type { DimensionValue } from '@/features/profile/model/profile'
import { XIcon } from '@lucide/vue'

const profile = ref<ProfileData | null>(null)
const loading = ref(false)

const DIM_CONFIG = [
  { key: 'knowledge_level', label: '知识基础' },
  { key: 'cognitive_style', label: '认知风格' },
  { key: 'weak_knowledge_points', label: '易错偏好' },
  { key: 'knowledge_gap_pattern', label: '缺口模式' },
  { key: 'learning_goal_type', label: '目标导向' },
  { key: 'difficulty_tolerance', label: '难度耐受' },
  { key: 'self_correction_ability', label: '自纠能力' }
]

const dimensionCards = computed(() => {
  const dims = (profile.value?.dimensions ?? {}) as Record<ProfileDimensionKey, DimensionValue>

  return DIM_CONFIG.map(config => {
    const key = config.key as ProfileDimensionKey
    const valObj = dims[key] || { value: '', evidence: [] }
    const evidenceList = valObj.evidence || []
    return {
      key,
      label: config.label,
      value: valObj.value || '',
      evidence: evidenceList
    }
  }).filter(dim => dim.value)
})

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
/* Modal Transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.22s ease;
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container {
  transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.22s ease;
}
.modal-leave-active .modal-container {
  transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.22s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.96);
  opacity: 0;
}

/* Overlay & White Container styling */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(15, 23, 42, 0.2);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
}

.modal-container {
  width: 100%;
  max-width: 580px;
  max-height: 85dvh;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  border-radius: 0px !important;
  box-shadow: 0 12px 30px -10px rgba(15, 23, 42, 0.08);
}

.modal-header {
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: justify-between;
  align-items: center;
  flex-shrink: 0;
}

.modal-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid #e2e8f0;
  color: #64748b;
  border-radius: 0px;
  transition: all 0.15s ease;
}

.modal-close-btn:hover {
  background: #f8fafc;
  color: #0f172a;
  border-color: #0f172a;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-5);
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 transparent;
}

.modal-body::-webkit-scrollbar {
  width: 3px;
}
.modal-body::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 0px;
}

/* Dimensions List Styling */
.dimensions-list {
  display: flex;
  flex-direction: column;
}

.dimension-item {
  display: flex;
  gap: var(--space-4);
  padding-bottom: var(--space-5);
  margin-bottom: var(--space-5);
  border-bottom: 1px solid #f1f5f9;
}

.dimension-item:last-child {
  border-bottom: 0;
  padding-bottom: 0;
  margin-bottom: 0;
}

.dim-num {
  font-size: 11px;
  font-weight: 700;
  color: #94a3b8;
  height: 20px;
  display: flex;
  align-items: center;
}

.dim-content {
  flex: 1;
  min-width: 0;
}

.dim-title {
  height: 20px;
  display: flex;
  align-items: center;
}
</style>
