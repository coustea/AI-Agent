<template>
  <main class="path-history-page">
    <section class="history-shell">
      <header class="page-head">
        <div class="head-left">
          <button class="btn-text back-btn" type="button" @click="router.push('/path-planner/overview/latest')">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.42-1.41L7.83 13H20v-2Z" />
            </svg>
            当前路径
          </button>

          <div class="title-block">
            <span>Learning Path History</span>
            <h1>学习路径历史</h1>
          </div>
        </div>

        <button class="btn-outline" type="button" @click="router.push('/path-planner')">
          新建路径
        </button>
      </header>

      <section class="table-toolbar">
        <div class="search-box">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M9.5 3a6.5 6.5 0 0 1 5.17 10.44l5.45 5.44-1.41 1.41-5.45-5.44A6.5 6.5 0 1 1 9.5 3Zm0 2a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9Z" />
          </svg>
          <input
            v-model.trim="keyword"
            type="text"
            placeholder="搜索路径标题或学习目标"
          />
        </div>

        <div class="status-tabs">
          <button
            v-for="tab in statusTabs"
            :key="tab.value"
            type="button"
            :class="{ active: statusFilter === tab.value }"
            @click="statusFilter = tab.value"
          >
            <span>{{ tab.label }}</span>
            <em>{{ getStatusCount(tab.value) }}</em>
          </button>
        </div>
      </section>

      <section v-if="loading" class="state-panel">
        <div class="state-spinner"></div>
        <p>正在加载历史路径...</p>
      </section>

      <section v-else-if="items.length === 0" class="state-panel">
        <h2>还没有历史路径记录</h2>
        <p>创建学习路径后，历史记录会在这里统一展示。</p>
        <button class="btn-primary" type="button" @click="router.push('/path-planner')">
          创建第一条学习路径
        </button>
      </section>

      <section v-else-if="filteredItems.length === 0" class="state-panel">
        <h2>没有匹配的路径</h2>
        <p>可以调整搜索关键词或切换状态筛选。</p>
      </section>

      <section v-else class="history-table">
        <div class="table-head">
          <span>路径信息</span>
          <span>状态</span>
          <span>学习进度</span>
          <span>更新时间</span>
          <span>操作</span>
        </div>

        <article
          v-for="item in filteredItems"
          :key="item.id"
          class="history-row"
        >
          <div class="path-info">
            <div class="path-mark" :class="item.status">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 3 20 7.5v9L12 21l-8-4.5v-9L12 3Zm0 2.2L6 8.6v6.8l6 3.4 6-3.4V8.6l-6-3.4Zm0 4.1 3 1.7v3.4l-3 1.7-3-1.7v-3.4l3-1.7Z" />
              </svg>
            </div>

            <div class="path-copy">
              <strong>{{ item.title }}</strong>
              <p>{{ item.goal || '暂无学习目标说明' }}</p>
            </div>
          </div>

          <div class="status-cell">
            <span class="status-pill" :class="item.status">
              {{ statusLabel(item.status) }}
            </span>
          </div>

          <div class="progress-cell">
            <div class="progress-top">
              <strong>{{ clampProgress(item.overall_progress) }}%</strong>
            </div>
            <div class="progress-track">
              <i :style="{ width: `${clampProgress(item.overall_progress)}%` }"></i>
            </div>
          </div>

          <div class="time-cell">
            {{ formatTime(item.updated_at) }}
          </div>

          <div class="action-cell">
            <button class="btn-text" type="button" @click="viewPath(item.id)">
              查看
            </button>
            <button
              class="btn-primary"
              style="min-height: 34px; padding: 0 var(--space-3);"
              type="button"
              :disabled="!canActivate(item)"
              @click="activate(item.id)"
            >
              继续学习
            </button>
          </div>
        </article>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { activateLearningPath, getLearningPathHistory } from '@/features/learning-path/api/path'
import type { LearningPathHistoryItem } from '@/features/learning-path/model/path'
import { getErrorMessage } from '@/shared/api/http'

type StatusTab = {
  label: string
  value: string
}

const router = useRouter()

const loading = ref(false)
const items = ref<LearningPathHistoryItem[]>([])
const keyword = ref('')
const statusFilter = ref('all')

const statusTabs: StatusTab[] = [
  { label: '全部', value: 'all' },
  { label: '学习中', value: 'active' },
  { label: '已归档', value: 'archived' },
  { label: '生成中', value: 'generating' },
  { label: '失败', value: 'failed' },
]

const filteredItems = computed(() => {
  const key = keyword.value.toLowerCase()

  return items.value
    .filter((item) => {
      if (statusFilter.value === 'all') return true
      return item.status === statusFilter.value
    })
    .filter((item) => {
      if (!key) return true
      return `${item.title || ''} ${item.goal || ''}`.toLowerCase().includes(key)
    })
})

const loadHistory = async () => {
  loading.value = true

  try {
    const res = await getLearningPathHistory()
    items.value = res.data.data || []
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '加载路径历史失败'))
  } finally {
    loading.value = false
  }
}

const activate = async (pathId: number) => {
  try {
    const res = await activateLearningPath(pathId)
    router.push(`/path-planner/overview/${res.data.data.id}`)
  } catch (error) {
    ElMessage.error(getErrorMessage(error, '恢复历史路径失败'))
  }
}

const viewPath = (pathId: number) => {
  router.push(`/path-planner/overview/${pathId}`)
}

const canActivate = (item: LearningPathHistoryItem) => {
  return item.status !== 'failed' && item.status !== 'generating'
}

const getStatusCount = (status: string) => {
  if (status === 'all') return items.value.length
  return items.value.filter((item) => item.status === status).length
}

const statusLabel = (status: string) => {
  switch (status) {
    case 'active':
      return '学习中'
    case 'archived':
      return '已归档'
    case 'generating':
      return '生成中'
    case 'failed':
      return '失败'
    default:
      return status || '未知'
  }
}

const clampProgress = (value: number) => {
  return Math.max(0, Math.min(Number(value || 0), 100))
}

const formatTime = (value: string) => {
  if (!value) return '-'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'

  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(loadHistory)
</script>

<style scoped>
.path-history-page {
  --ph-primary: #4f46e5;
  --ph-primary-dark: #3730a3;
  --ph-primary-soft: #eef2ff;
  --ph-blue: #0ea5e9;
  --ph-green: #10b981;
  --ph-red: #ef4444;
  --ph-orange: #f59e0b;
  --ph-slate: #64748b;
  --ph-muted: #94a3b8;
  --ph-text: #0f172a;
  --ph-border: #e2e8f0;
  --ph-border-strong: #c7d2fe;
  --ph-row-hover: #f8fafc;

  min-height: calc(100vh - 64px);
  padding: 18px 24px 42px;
  background:
    radial-gradient(circle at 8% 0%, rgba(79, 70, 229, 0.06), transparent 30%),
    radial-gradient(circle at 94% 0%, rgba(14, 165, 233, 0.05), transparent 28%),
    linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
  color: var(--ph-text);
}

.path-history-page svg {
  width: 1em;
  height: 1em;
  fill: currentColor;
}

.history-shell {
  width: min(1360px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 14px;
}

.page-head {
  min-height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.head-left {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 18px;
}

.back-btn {
  padding: 0 4px 0 0 !important;
  color: var(--ph-primary) !important;
}

.back-btn:hover {
  color: var(--ph-primary-dark) !important;
  transform: translateX(-2px) !important;
}

.title-block {
  min-width: 0;
}

.title-block span {
  display: block;
  margin-bottom: 3px;
  color: var(--ph-muted);
  font-size: 0.76rem;
  font-weight: 900;
  letter-spacing: 0.01em;
}

.title-block h1 {
  margin: 0;
  color: var(--ph-text);
  font-size: clamp(1.35rem, 2.2vw, 2rem);
  line-height: 1.2;
  letter-spacing: -0.04em;
}


.table-toolbar {
  min-height: 52px;
  display: grid;
  grid-template-columns: minmax(280px, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 8px 0 12px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.95);
}

.search-box {
  min-height: 42px;
  padding: 0 13px;
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  border-radius: 13px;
  background: #ffffff;
  border: 1px solid var(--ph-border);
  color: var(--ph-muted);
}

.search-box input {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--ph-text);
  font: inherit;
  font-size: 0.9rem;
}

.search-box input::placeholder {
  color: var(--ph-muted);
}

.status-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.status-tabs button {
  min-height: 38px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--ph-border);
  border-radius: 999px;
  background: #ffffff;
  color: #475569;
  font: inherit;
  font-size: 0.82rem;
  font-weight: 900;
  cursor: pointer;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}

.status-tabs button:hover,
.status-tabs button.active {
  color: var(--ph-primary-dark);
  background: var(--ph-primary-soft);
  border-color: var(--ph-border-strong);
  transform: translateY(-1px);
}

.status-tabs em {
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  font-size: 0.72rem;
  font-style: normal;
  font-weight: 900;
}

.status-tabs button.active em {
  background: #ffffff;
  color: var(--ph-primary-dark);
}

.state-panel {
  min-height: 260px;
  padding: 36px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  text-align: center;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.74);
  border: 1px dashed var(--ph-border);
}

.state-panel h2,
.state-panel p {
  margin: 0;
}

.state-panel h2 {
  font-size: 1.25rem;
}

.state-panel p {
  color: var(--ph-slate);
}

.state-spinner {
  width: 34px;
  height: 34px;
  border: 4px solid #e0e7ff;
  border-top-color: var(--ph-primary);
  border-radius: 50%;
  animation: spin 0.85s linear infinite;
}

.history-table {
  overflow: hidden;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid var(--ph-border);
}

.table-head,
.history-row {
  display: grid;
  grid-template-columns: minmax(320px, 1.7fr) 110px 170px 180px 170px;
  gap: 14px;
  align-items: center;
}

.table-head {
  min-height: 44px;
  padding: 0 18px;
  background: #f8fafc;
  border-bottom: 1px solid var(--ph-border);
}

.table-head span {
  color: var(--ph-slate);
  font-size: 0.76rem;
  font-weight: 900;
}

.history-row {
  min-height: 88px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--ph-border);
  transition:
    background 0.18s ease,
    box-shadow 0.18s ease;
}

.history-row:last-child {
  border-bottom: 0;
}

.history-row:hover {
  background: var(--ph-row-hover);
}

.path-info {
  min-width: 0;
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
}

.path-mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  color: #ffffff;
  font-size: 21px;
  background: linear-gradient(135deg, var(--ph-primary), var(--ph-blue));
}

.path-mark.archived {
  color: #475569;
  background: linear-gradient(135deg, #e2e8f0, #cbd5e1);
}

.path-mark.generating {
  background: linear-gradient(135deg, #0ea5e9, #06b6d4);
}

.path-mark.failed {
  background: linear-gradient(135deg, #ef4444, #f87171);
}

.path-copy {
  min-width: 0;
}

.path-copy strong {
  display: block;
  margin-bottom: 5px;
  color: var(--ph-text);
  font-size: 0.96rem;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.path-copy p {
  margin: 0;
  color: var(--ph-slate);
  font-size: 0.82rem;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.status-pill {
  min-height: 28px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  color: var(--ph-primary-dark);
  background: var(--ph-primary-soft);
  font-size: 0.74rem;
  font-weight: 900;
  white-space: nowrap;
}

.status-pill.archived {
  color: #475569;
  background: #f1f5f9;
}

.status-pill.generating {
  color: #075985;
  background: #e0f2fe;
}

.status-pill.failed {
  color: #991b1b;
  background: #fee2e2;
}

.progress-cell {
  display: grid;
  gap: 7px;
}

.progress-top strong {
  color: var(--ph-text);
  font-size: 0.83rem;
  font-weight: 900;
}

.progress-track {
  height: 8px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.progress-track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--ph-primary), var(--ph-blue));
}

.time-cell {
  color: var(--ph-slate);
  font-size: 0.82rem;
  line-height: 1.45;
}

.action-cell {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}



@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1120px) {
  .table-head {
    display: none;
  }

  .history-table {
    display: grid;
    gap: 10px;
    background: transparent;
    border: 0;
    border-radius: 0;
  }

  .history-row {
    grid-template-columns: 1fr;
    gap: 12px;
    border: 1px solid var(--ph-border);
    border-radius: 16px;
    background: #ffffff;
  }

  .status-cell,
  .progress-cell,
  .time-cell,
  .action-cell {
    justify-content: flex-start;
  }

  .action-cell {
    flex-wrap: wrap;
  }
}

@media (max-width: 820px) {
  .path-history-page {
    padding: 12px;
  }

  .page-head,
  .head-left,
  .table-toolbar {
    display: grid;
  }

  .head-left {
    gap: 10px;
  }

  .create-btn {
    justify-self: start;
  }

  .table-toolbar {
    grid-template-columns: 1fr;
  }

  .status-tabs {
    justify-content: flex-start;
  }
}

@media (max-width: 520px) {
  .path-info {
    grid-template-columns: 38px minmax(0, 1fr);
  }

  .path-mark {
    width: 38px;
    height: 38px;
    border-radius: 13px;
    font-size: 19px;
  }

  .action-cell {
    display: grid;
  }

  .primary-btn,
  .text-btn {
    width: 100%;
  }
}
</style>