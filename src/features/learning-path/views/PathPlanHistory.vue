<template>
  <main class="path-history-page">
    <section class="history-shell">

      <header class="history-toolbar">
        <button
            class="btn btn-outline toolbar-action-btn"
            type="button"
            @click="router.push('/path-planner/overview/latest')"
        >
          <svg class="icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          当前路径
        </button>

        <div class="toolbar-divider">/</div>

        <div class="history-title-box">
          <span class="title-mark"></span>
          <strong>路径历史仓储</strong>
          <em class="count-badge">{{ filteredItems.length }} / {{ items.length }}</em>
        </div>

        <label class="search-box-container">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="icon-svg text-faint">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
              v-model.trim="keyword"
              type="text"
              placeholder="输入路径标题、核心方向或学术目标..."
          />
        </label>

        <button
            class="btn btn-primary toolbar-action-btn"
            type="button"
            @click="router.push('/path-planner')"
        >
          新建学习路径
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="icon-svg">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
      </header>

      <section class="status-strip">
        <button
            v-for="tab in statusTabs"
            :key="tab.value"
            type="button"
            :class="['btn-pill', { active: statusFilter === tab.value }]"
            @click="statusFilter = tab.value"
        >
          <span class="tab-label">{{ tab.label }}</span>
          <em class="tab-counter">{{ getStatusCount(tab.value) }}</em>
        </button>
      </section>

      <section class="history-panel">
        <div class="panel-head">
          <div class="panel-filter">
            <span class="agent-eyebrow">Active Scope</span>
            <strong>{{ activeStatusLabel }}维度项</strong>
          </div>

          <div class="page-size">
            <span>每页平铺</span>
            <select v-model.number="pageSize" class="native-select">
              <option :value="5">5 条 / 页</option>
              <option :value="8">8 条 / 页</option>
              <option :value="12">12 条 / 页</option>
            </select>
          </div>
        </div>

        <section v-if="loading" class="state-area">
          <div class="state-spinner"></div>
          <p>评估数据中心正在提取历史路径记录...</p>
        </section>

        <section v-else-if="items.length === 0" class="state-area-empty">
          <div class="empty-icon-box">
            <svg class="state-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            </svg>
          </div>
          <h2>暂无历史生成路径</h2>
          <p>您调遣智能体规划构建的学习路径与认知链条都将在本中心归档留存。</p>
          <button class="btn btn-primary" type="button" @click="router.push('/path-planner')" style="margin-top: var(--space-2);">
            规划首个自适应路径
          </button>
        </section>

        <section v-else-if="filteredItems.length === 0" class="state-area-empty">
          <div class="empty-icon-box muted">
            <svg class="state-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
          </div>
          <h2>无匹配的相关路径</h2>
          <p>未能检索到目标特征信息，建议精简关键词或切换上方的自适应分流标签。</p>
        </section>

        <section v-else class="history-list">
          <article
              v-for="item in pagedItems"
              :key="item.id"
              :class="['history-row', statusClass(item.status), { disabled: !canActivate(item) }]"
          >
            <div class="row-status-avatar">
              <span>{{ statusShortLabel(item.status) }}</span>
            </div>

            <div class="row-main-content">
              <div class="row-title-bar">
                <h2 :title="item.title">{{ item.title || '未命名智能路径链' }}</h2>
                <span class="tag-pill state-tag" :class="statusClass(item.status)">
                  {{ statusLabel(item.status) }}
                </span>
              </div>

              <p class="row-goal-desc">{{ item.goal || '暂无该自适应路径的全局目标特征描述' }}</p>

              <div class="row-metadata-stream">
                <span class="meta-inline-item">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="meta-svg">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                    <line x1="16" y1="2" x2="16" y2="6"></line>
                    <line x1="8" y1="2" x2="8" y2="6"></line>
                    <line x1="3" y1="10" x2="21" y2="10"></line>
                  </svg>
                  {{ formatTime(item.updated_at) }}
                </span>

                <span class="meta-inline-item">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="meta-svg">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                  </svg>
                  认知链完备度 {{ clampProgress(item.overall_progress) }}%
                </span>
              </div>
            </div>

            <div class="row-progress-rail">
              <div class="progress-txt-val">
                <strong>{{ clampProgress(item.overall_progress) }}<small>%</small></strong>
              </div>
              <div class="progress-track-bar">
                <i class="fill-indicator" :style="{ width: `${clampProgress(item.overall_progress)}%` }"></i>
              </div>
            </div>

            <div class="row-action-zone">
              <button
                  class="btn btn-outline row-action-btn"
                  type="button"
                  :disabled="!canActivate(item)"
                  @click="continueLearning(item)"
              >
                {{ actionText(item) }}
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="arrow-forward-icon">
                  <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
              </button>
            </div>
          </article>
        </section>

        <footer v-if="filteredItems.length > 0" class="pagination-bar">
          <div class="pagination-info">
            共查询到记录 {{ filteredItems.length }} 项 · 当前视区范围 {{ pageStartIndex + 1 }} - {{ pageEndIndex }} 项
          </div>

          <div class="pagination-actions-group">
            <button class="pag-nav-btn" type="button" :disabled="currentPage === 1" @click="goPage(1)">
              首页
            </button>
            <button class="pag-nav-btn" type="button" :disabled="currentPage === 1" @click="goPage(currentPage - 1)">
              上一页
            </button>

            <button
                v-for="page in visiblePages"
                :key="page"
                type="button"
                :class="['pag-num-btn', { active: currentPage === page }]"
                @click="goPage(page)"
            >
              {{ page }}
            </button>

            <button class="pag-nav-btn" type="button" :disabled="currentPage === totalPages" @click="goPage(currentPage + 1)">
              下一页
            </button>
            <button class="pag-nav-btn" type="button" :disabled="currentPage === totalPages" @click="goPage(totalPages)">
              末页
            </button>
          </div>
        </footer>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { activateLearningPath, getLearningPathHistory } from '@/features/learning-path/api/path'
import type { LearningPathHistoryItem } from '@/features/learning-path/model/path'
import { getErrorMessage } from '@/shared/api/http'

type StatusTab = {
  label: string
  value: string
}

const router = useRouter()

// 历史路径列表与筛选分页状态
const loading = ref(false)
const items = ref<LearningPathHistoryItem[]>([])
const keyword = ref('')           // 搜索关键词
const statusFilter = ref('all')   // 状态筛选标签
const currentPage = ref(1)
const pageSize = ref(5)

const statusTabs: StatusTab[] = [
  { label: '全部路径', value: 'all' },
  { label: '正在推进', value: 'active' },
  { label: '已通关点', value: 'completed' },
  { label: '历史归档', value: 'archived' },
  { label: '多维生成中', value: 'generating' },
  { label: '发生编译阻断', value: 'failed' },
]

// 根据状态筛选和关键词搜索过滤历史记录
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

// 总页数与当前页起止索引（分页逻辑）
const totalPages = computed(() => {
  return Math.max(1, Math.ceil(filteredItems.value.length / pageSize.value))
})

const pageStartIndex = computed(() => {
  return (currentPage.value - 1) * pageSize.value
})

const pageEndIndex = computed(() => {
  return Math.min(pageStartIndex.value + pageSize.value, filteredItems.value.length)
})

// 当前页展示的数据切片
const pagedItems = computed(() => {
  return filteredItems.value.slice(pageStartIndex.value, pageEndIndex.value)
})

const visiblePages = computed(() => {
  const max = totalPages.value
  const current = currentPage.value
  const start = Math.max(1, current - 2)
  const end = Math.min(max, current + 2)

  const pages: number[] = []
  for (let page = start; page <= end; page += 1) {
    pages.push(page)
  }
  return pages
})

const activeStatusLabel = computed(() => {
  return statusTabs.find((tab) => tab.value === statusFilter.value)?.label || '全部'
})

// 加载历史路径列表
const loadHistory = async () => {
  loading.value = true
  try {
    const res = await getLearningPathHistory()
    items.value = res.data.data || []
  } catch (error) {
    toast.error(getErrorMessage(error, '加载路径历史失败'))
  } finally {
    loading.value = false
  }
}

// 继续学习：激活并跳转到指定历史路径
const continueLearning = async (item: LearningPathHistoryItem) => {
  if (!canActivate(item)) return
  try {
    const res = await activateLearningPath(item.id)
    router.push(`/path-planner/overview/${res.data.data.id}`)
  } catch (error) {
    toast.error(getErrorMessage(error, '恢复历史路径失败'))
  }
}

// 切换分页
const goPage = (page: number) => {
  currentPage.value = Math.min(Math.max(1, page), totalPages.value)
}

// 判断路径是否可以激活（失败/生成中不可激活）
const canActivate = (item: LearningPathHistoryItem) => {
  return item.status !== 'failed' && item.status !== 'generating'
}

const actionText = (item: LearningPathHistoryItem) => {
  if (item.status === 'generating') return '组织中'
  if (item.status === 'failed') return '已锁死'
  return '恢复学习进度'
}

const getStatusCount = (status: string) => {
  if (status === 'all') return items.value.length
  return items.value.filter((item) => item.status === status).length
}

const statusLabel = (status: string) => {
  switch (status) {
    case 'active': return '学习中'
    case 'completed': return '已完成'
    case 'archived': return '已归档'
    case 'paused': return '已暂停'
    case 'generating': return '生成中'
    case 'failed': return '失败'
    default: return status || '未知'
  }
}

const statusShortLabel = (status: string) => {
  switch (status) {
    case 'active': return '学'
    case 'completed': return '完'
    case 'archived': return '档'
    case 'paused': return '停'
    case 'generating': return '生'
    case 'failed': return '错'
    default: return '径'
  }
}

const statusClass = (status: string) => {
  switch (status) {
    case 'active': return 'active'
    case 'completed': return 'completed'
    case 'archived': return 'archived'
    case 'paused': return 'paused'
    case 'generating': return 'generating'
    case 'failed': return 'failed'
    default: return 'unknown'
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

// 筛选条件变化时重置到第一页
watch([keyword, statusFilter, pageSize], () => {
  currentPage.value = 1
})

// 总页数变化时自动修正当前页
watch(totalPages, (value) => {
  if (currentPage.value > value) {
    currentPage.value = value
  }
})

// 页面挂载时加载历史记录
onMounted(loadHistory)
</script>

<style scoped>
/* ============================================================
   Page Fluid Container
   ============================================================ */
.path-history-page {
  min-height: calc(100vh - var(--navbar-height, 72px));
  padding: 16px var(--space-6) var(--space-10);
  background-color: var(--color-bg);
}

.history-shell {
  max-width: var(--page-max-width);
  width: 100%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* ============================================================
   高精矢量微标控制约束（防胀大撑爆）
   ============================================================ */
.icon-svg {
  width: 14px !important;
  height: 14px !important;
  flex-shrink: 0 !important;
  display: inline-block;
}
.icon-svg.text-faint { color: var(--color-text-faint); }

/* ============================================================
   Header Axis Layout: 100% 对齐高精 40px 高度线
   ============================================================ */
.history-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-1) 0;
  width: 100%;
}

.nav-back-style {
  white-space: nowrap;
  flex-shrink: 0;
}

.toolbar-divider {
  color: var(--color-border-light);
  font-size: var(--text-md);
  user-select: none;
  flex-shrink: 0;
}

.history-title-box {
  height: 40px;
  padding: 0 var(--space-3.5);
  display: inline-flex;
  align-items: center;
  gap: var(--space-2.5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  flex-shrink: 0;
  box-shadow: var(--shadow-xs);
  box-sizing: border-box;
}

.title-mark {
  width: 6px;
  height: 6px;
  border-radius: 2px;
  background: var(--color-primary);
  flex-shrink: 0;
}

.history-title-box strong {
  color: var(--color-text-strong);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  white-space: nowrap;
}

.count-badge {
  font-family: var(--font-mono);
  font-style: normal;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  padding: 1px 6px;
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  border-radius: 4px;
  white-space: nowrap;
}

/* 40px 工业检索器扩展流 */
.search-box-container {
  height: 40px;
  padding: 0 var(--space-3.5);
  display: flex;
  align-items: center;
  gap: var(--space-2.5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: #ffffff;
  box-shadow: var(--shadow-xs);
  flex-grow: 1;
  box-sizing: border-box;
}

.search-box-container input {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-text);
  font-size: var(--text-sm);
  padding: 0;
}

.create-path-btn {
  white-space: nowrap;
  flex-shrink: 0;
}

/* ============================================================
   Status Tabs Section - 36px
   ============================================================ */
.status-strip {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: var(--space-2);
}

.status-strip .btn-pill {
  height: 36px !important;
  min-height: 36px !important;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-3) !important;
  white-space: nowrap;
}

.tab-counter {
  font-family: var(--font-mono);
  font-style: normal;
  font-size: 11px;
  font-weight: var(--weight-bold);
  padding: 0 5px;
  min-width: 18px;
  height: 18px;
  display: inline-grid;
  place-items: center;
  border-radius: 4px;
  background: #ffffff;
  color: var(--color-text-muted);
  border: 1px solid var(--color-border-light);
  flex-shrink: 0;
  margin-left: 6px;
}

.btn-pill.active .tab-counter {
  background: var(--color-primary-text);
  color: #ffffff;
  border-color: var(--color-primary-text);
}

/* ============================================================
   Master History Board Container Panel Style
   ============================================================ */
.history-panel {
  border-radius: var(--radius-md);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
}

.panel-head {
  height: 44px;
  padding: 0 var(--space-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-surface);
}

.panel-filter {
  display: inline-flex;
  align-items: baseline;
  gap: var(--space-2);
}

.panel-filter strong {
  color: var(--color-text-strong);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
}

.page-size {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}
.page-size span {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
}

.native-select {
  height: 26px;
  padding: 0 var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: #ffffff;
  color: var(--color-text);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  outline: none;
}

/* ============================================================
   Grid History Item Rows - 精密比例再分布（消灭空白断层）
   ============================================================ */
.history-list {
  display: flex;
  flex-direction: column;
}

.history-row {
  position: relative;
  padding: var(--space-4) var(--space-5);
  display: grid;
  /* ⚖️ 精密栅格分栏：完美延展 260px 进度条轨道，压缩空白断层，右侧动作按键精准留白 */
  grid-template-columns: 40px 1fr 260px 140px;
  gap: var(--space-5);
  align-items: center;
  border-bottom: 1px solid var(--color-border-light);
  transition: var(--btn-transition);
}

.history-row:last-child { border-bottom: 0; }

.history-row::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--color-primary);
  opacity: 0;
  transition: var(--btn-transition);
}

.history-row:hover {
  background-color: var(--color-surface-hover);
}
.history-row:hover::before { opacity: 1; }

.history-row.completed::before { background-color: var(--color-success); }
.history-row.generating::before { background-color: #0ea5e9; }
.history-row.failed::before { background-color: var(--color-danger); }
.history-row.archived::before, .history-row.paused::before { background-color: var(--color-text-faint); }

.row-status-avatar span {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 4px;
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
}

.history-row.completed .row-status-avatar span { background: var(--color-success-soft); color: var(--color-success); }
.history-row.generating .row-status-avatar span { background: #e0f2fe; color: #0369a1; }
.history-row.failed .row-status-avatar span { background: var(--color-danger-soft); color: var(--color-danger); }
.history-row.archived .row-status-avatar span, .history-row.paused .row-status-avatar span { background: #f1f5f9; color: var(--color-text-muted); }

.row-main-content { min-width: 0; }

.row-title-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.row-title-bar h2 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.state-tag {
  flex-shrink: 0;
  font-size: 10px;
}

.state-tag.completed { background: var(--color-success-soft); color: var(--color-success); }
.state-tag.generating { background: #e0f2fe; color: #0369a1; }
.state-tag.failed { background: var(--color-danger-soft); color: var(--color-danger); }
.state-tag.archived, .state-tag.paused { background: #f1f5f9; color: var(--color-text-muted); }

.row-goal-desc {
  margin: var(--space-1.5) 0 0 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.row-metadata-stream {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  margin-top: var(--space-2);
}

.meta-inline-item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-text-faint);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
}

.meta-svg {
  width: 12px;
  height: 12px;
  color: var(--color-text-light);
  flex-shrink: 0;
}

/* 精密分栏进度轨道 */
.row-progress-rail {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  width: 100%;
}

.progress-txt-val {
  text-align: right;
  line-height: 1;
}
.progress-txt-val strong {
  font-size: var(--text-md);
  font-weight: var(--weight-extrabold);
  color: var(--color-text-strong);
  font-family: var(--font-mono);
}
.progress-txt-val strong small {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
}

.progress-track-bar {
  height: 5px;
  border-radius: 2px;
  background-color: var(--color-border-light);
  overflow: hidden;
}

.fill-indicator {
  display: block;
  height: 100%;
  background-color: var(--color-primary);
  border-radius: inherit;
}

.row-action-zone {
  display: flex;
  justify-content: flex-end;
}

.row-action-btn {
  height: 32px !important;
  min-height: 32px !important;
  padding: 0 var(--space-3.5) !important;
  font-size: var(--text-xs) !important;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.arrow-forward-icon {
  width: 11px !important;
  height: 11px !important;
  transition: transform var(--transition-fast);
  flex-shrink: 0;
}
.row-action-btn:hover:not(:disabled) .arrow-forward-icon {
  transform: translateX(1px);
}

/* ============================================================
   Pagination Controls System Sheet
   ============================================================ */
.pagination-bar {
  padding: var(--space-3) var(--space-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  border-top: 1px solid var(--color-border-light);
}

.pagination-info {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
}

.pagination-actions-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pag-nav-btn,
.pag-num-btn {
  height: 28px;
  border-radius: 4px;
  border: 1px solid var(--color-border);
  background: #ffffff;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: var(--btn-transition);
}

.pag-nav-btn { padding: 0 var(--space-2.5); }
.pag-num-btn { width: 28px; font-family: var(--font-mono); }

.pag-nav-btn:hover:not(:disabled),
.pag-num-btn:hover,
.pag-num-btn.active {
  border-color: var(--color-border-hover);
  background: var(--color-surface-hover);
  color: var(--color-text-strong);
}

.pag-num-btn.active {
  border-color: var(--color-primary-text);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-weight: var(--weight-bold);
}

.pag-nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ============================================================
   Global Processing States Sheet Overrides
   ============================================================ */
.state-area,
.state-area-empty {
  min-height: 320px;
  padding: var(--space-10) var(--space-6);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  text-align: center;
}

.state-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border-light);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}

.empty-icon-box {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-size: var(--text-xl);
}
.empty-icon-box.muted { background: #f1f5f9; color: var(--color-text-faint); }

.state-area-empty h2 { font-size: var(--text-base); font-weight: var(--weight-bold); color: var(--color-text-strong); }
.state-area-empty p { font-size: var(--text-sm); color: var(--color-text-secondary); max-width: 420px; margin: 0; }

/* ============================================================
   Responsive Architecture System Breakpoints
   ============================================================ */
@theme inline {
  --animate-spin: spin 0.75s linear infinite;
}

@media (max-width: 1100px) {
  .status-strip {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 960px) {
  .history-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-2.5);
  }
  .nav-back-style, .history-title-box, .search-box-container, .create-path-btn {
    width: 100%;
    justify-content: center;
  }
  .history-row {
    grid-template-columns: 36px 1fr auto;
  }
  .row-progress-rail {
    grid-column: 2 / 4;
    grid-template-columns: 60px 1fr;
    align-items: center;
  }
  .progress-txt-val { text-align: left; }
  .row-action-zone {
    grid-column: 1 / -1;
    width: 100%;
  }
  .row-action-btn { width: 100%; justify-content: center; }
}

@media (max-width: 640px) {
  .path-history-page { padding: var(--space-3) var(--space-4); }
  .status-strip { grid-template-columns: repeat(2, 1fr); }
  .panel-head, .pagination-bar { flex-direction: column; height: auto; align-items: flex-start; gap: var(--space-3); padding: var(--space-4); }
  .pagination-actions-group { flex-wrap: wrap; }
  .history-row { grid-template-columns: 1fr; gap: var(--space-2.5); }
  .row-status-avatar { display: none; }
  .row-title-bar { flex-direction: column; align-items: flex-start; gap: var(--space-1); }
  .row-progress-rail { grid-column: 1 / -1; grid-template-columns: 1fr; }
  .progress-txt-val { text-align: right; }
}
</style>