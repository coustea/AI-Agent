<template>
  <main class="path-history-page">
    <section class="history-shell">
      <header class="history-toolbar">
        <button
            class="toolbar-button toolbar-back-button"
            type="button"
            @click="router.push('/path-planner/overview/latest')"
        >
          <svg
              class="icon-svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
              stroke-linejoin="round"
          >
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>

          <span>当前路径</span>
        </button>

        <div class="history-title-box">
          <span class="title-mark"></span>

          <div class="history-title-content">
            <strong>路径历史</strong>

            <span>
              共 {{ items.length }} 条
              <template v-if="filteredItems.length !== items.length">
                · 当前显示 {{ filteredItems.length }} 条
              </template>
            </span>
          </div>
        </div>

        <label class="search-box-container">
          <svg
              class="icon-svg search-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
              stroke-linejoin="round"
          >
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>

          <input
              v-model.trim="keyword"
              type="search"
              autocomplete="off"
              placeholder="搜索路径标题或学习目标"
              aria-label="搜索路径历史"
          />

          <button
              v-if="keyword"
              class="search-clear-button"
              type="button"
              aria-label="清空搜索内容"
              @click="keyword = ''"
          >
            <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </label>

        <button
            class="toolbar-button toolbar-create-button"
            type="button"
            @click="router.push('/path-planner')"
        >
          <svg
              class="icon-svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
              stroke-linejoin="round"
          >
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>

          <span>新建学习路径</span>
        </button>
      </header>

      <section class="status-strip" aria-label="路径状态筛选">
        <button
            v-for="tab in statusTabs"
            :key="tab.value"
            type="button"
            class="history-status-tab"
            :class="{
            'is-selected': statusFilter === tab.value,
          }"
            :aria-pressed="statusFilter === tab.value"
            @click="statusFilter = tab.value"
        >
          <span class="tab-label">{{ tab.label }}</span>

          <span class="tab-counter">
            {{ getStatusCount(tab.value) }}
          </span>
        </button>
      </section>

      <section class="history-panel">
        <div class="panel-head">
          <div class="panel-filter">
            <span class="panel-filter-label">当前筛选</span>
            <strong>{{ activeStatusLabel }}</strong>
          </div>

          <div class="page-size">
            <label for="history-page-size">每页显示</label>

            <select
                id="history-page-size"
                v-model.number="pageSize"
                class="native-select"
            >
              <option :value="5">5 条</option>
              <option :value="8">8 条</option>
              <option :value="12">12 条</option>
            </select>
          </div>
        </div>

        <section v-if="loading" class="state-area">
          <div class="state-spinner"></div>
          <p>正在加载路径记录</p>
        </section>

        <section
            v-else-if="items.length === 0"
            class="state-area-empty"
        >
          <div class="empty-icon-box">
            <svg
                class="state-svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.6"
                stroke-linecap="round"
                stroke-linejoin="round"
            >
              <path
                  d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
              ></path>
            </svg>
          </div>

          <h2>暂无学习路径</h2>

          <p>
            创建后的学习路径会保存在这里，方便继续学习和查看历史进度。
          </p>

          <button
              class="empty-primary-button"
              type="button"
              @click="router.push('/path-planner')"
          >
            创建首条学习路径
          </button>
        </section>

        <section
            v-else-if="filteredItems.length === 0"
            class="state-area-empty"
        >
          <div class="empty-icon-box muted">
            <svg
                class="state-svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.6"
                stroke-linecap="round"
                stroke-linejoin="round"
            >
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
          </div>

          <h2>没有匹配的学习路径</h2>

          <p>
            可以尝试精简搜索关键词，或者切换其他状态筛选条件。
          </p>

          <button
              class="empty-secondary-button"
              type="button"
              @click="resetFilters"
          >
            清除筛选条件
          </button>
        </section>

        <section v-else class="history-list">
          <article
              v-for="item in pagedItems"
              :key="item.id"
              class="history-row"
              :class="[
              statusClass(item.status),
              {
                'is-disabled': !canActivate(item),
              },
            ]"
          >
            <div class="row-status-avatar">
              <span>{{ statusShortLabel(item.status) }}</span>
            </div>

            <div class="row-main-content">
              <div class="row-title-bar">
                <h2 :title="item.title || '未命名学习路径'">
                  {{ item.title || '未命名学习路径' }}
                </h2>

                <span
                    class="state-tag"
                    :class="statusClass(item.status)"
                >
                  {{ statusLabel(item.status) }}
                </span>
              </div>

              <p class="row-goal-desc">
                {{
                  item.goal ||
                  '暂无该学习路径的目标描述'
                }}
              </p>

              <div class="row-metadata-stream">
                <span class="meta-inline-item">
                  <svg
                      class="meta-svg"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                  >
                    <rect
                        x="3"
                        y="4"
                        width="18"
                        height="18"
                        rx="2"
                        ry="2"
                    ></rect>
                    <line x1="16" y1="2" x2="16" y2="6"></line>
                    <line x1="8" y1="2" x2="8" y2="6"></line>
                    <line x1="3" y1="10" x2="21" y2="10"></line>
                  </svg>

                  <span>{{ formatTime(item.updated_at) }}</span>
                </span>

                <span class="meta-separator">·</span>

                <span class="meta-inline-item">
                  <svg
                      class="meta-svg"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                  >
                    <path
                        d="M22 11.08V12a10 10 0 1 1-5.93-9.14"
                    ></path>
                    <polyline
                        points="22 4 12 14.01 9 11.01"
                    ></polyline>
                  </svg>

                  <span>
                    {{ progressMetaText(item) }}
                  </span>
                </span>
              </div>
            </div>

            <div class="row-progress-rail">
              <div class="progress-header">
                <span class="progress-label">
                  {{ progressLabel(item) }}
                </span>

                <strong>
                  {{ progressValueText(item) }}
                </strong>
              </div>

              <div
                  class="progress-track-bar"
                  :class="{
                  'is-generating': item.status === 'generating',
                  'is-failed': item.status === 'failed',
                }"
              >
                <span
                    class="fill-indicator"
                    :style="{
                    width: '100%',
                    transform: `scaleX(${progressWidth(item) / 100})`,
                    transformOrigin: 'left',
                  }"
                ></span>
              </div>
            </div>

            <div class="row-action-zone">
              <button
                  class="row-action-button"
                  type="button"
                  :disabled="!canActivate(item)"
                  @click="continueLearning(item)"
              >
                <span>{{ actionText(item) }}</span>

                <svg
                    v-if="canActivate(item)"
                    class="arrow-forward-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.3"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                >
                  <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
              </button>
            </div>
          </article>
        </section>

        <footer
            v-if="filteredItems.length > 0"
            class="pagination-bar"
        >
          <div class="pagination-info">
            共 {{ filteredItems.length }} 条，第
            {{ pageStartIndex + 1 }}–{{ pageEndIndex }} 条
          </div>

          <div class="pagination-actions-group">
            <button
                v-if="totalPages > 5"
                class="pag-nav-btn"
                type="button"
                :disabled="currentPage === 1"
                @click="goPage(1)"
            >
              首页
            </button>

            <button
                class="pag-nav-btn"
                type="button"
                :disabled="currentPage === 1"
                @click="goPage(currentPage - 1)"
            >
              上一页
            </button>

            <button
                v-for="page in visiblePages"
                :key="page"
                type="button"
                class="pag-num-btn"
                :class="{
                'is-selected': currentPage === page,
              }"
                :aria-current="currentPage === page ? 'page' : undefined"
                @click="goPage(page)"
            >
              {{ page }}
            </button>

            <button
                class="pag-nav-btn"
                type="button"
                :disabled="currentPage === totalPages"
                @click="goPage(currentPage + 1)"
            >
              下一页
            </button>

            <button
                v-if="totalPages > 5"
                class="pag-nav-btn"
                type="button"
                :disabled="currentPage === totalPages"
                @click="goPage(totalPages)"
            >
              末页
            </button>
          </div>
        </footer>
      </section>
    </section>
  </main>
</template>

<script setup lang="ts">
import {
  computed,
  onMounted,
  ref,
  watch,
} from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import {
  getLearningPathHistory,
} from '@/features/learning-path/api/path'

import type {
  LearningPathHistoryItem,
} from '@/features/learning-path/model/path'

import {
  getErrorMessage,
} from '@/shared/api/http'

type StatusTab = {
  label: string
  value: string
}

const router = useRouter()

const loading = ref(false)
const items = ref<LearningPathHistoryItem[]>([])
const keyword = ref('')
const statusFilter = ref('all')
const currentPage = ref(1)
const pageSize = ref(8)

const statusTabs: StatusTab[] = [
  {
    label: '全部路径',
    value: 'all',
  },
  {
    label: '学习中',
    value: 'active',
  },
  {
    label: '已完成',
    value: 'completed',
  },
  {
    label: '生成中',
    value: 'generating',
  },
  {
    label: '生成失败',
    value: 'failed',
  },
]

const filteredItems = computed(() => {
  const key = keyword.value
      .trim()
      .toLowerCase()

  return items.value
      .filter((item) => {
        if (statusFilter.value === 'all') {
          return true
        }

        return item.status === statusFilter.value
      })
      .filter((item) => {
        if (!key) {
          return true
        }

        const searchableText = [
          item.title || '',
          item.goal || '',
        ]
            .join(' ')
            .toLowerCase()

        return searchableText.includes(key)
      })
})

const totalPages = computed(() => {
  return Math.max(
      1,
      Math.ceil(
          filteredItems.value.length /
          pageSize.value,
      ),
  )
})

const pageStartIndex = computed(() => {
  return (
      (currentPage.value - 1) *
      pageSize.value
  )
})

const pageEndIndex = computed(() => {
  return Math.min(
      pageStartIndex.value + pageSize.value,
      filteredItems.value.length,
  )
})

const pagedItems = computed(() => {
  return filteredItems.value.slice(
      pageStartIndex.value,
      pageEndIndex.value,
  )
})

const visiblePages = computed(() => {
  const max = totalPages.value
  const current = currentPage.value

  let start = Math.max(
      1,
      current - 2,
  )

  let end = Math.min(
      max,
      start + 4,
  )

  if (end - start < 4) {
    start = Math.max(
        1,
        end - 4,
    )
  }

  const pages: number[] = []

  for (
      let page = start;
      page <= end;
      page += 1
  ) {
    pages.push(page)
  }

  return pages
})

const activeStatusLabel = computed(() => {
  return (
      statusTabs.find(
          tab => tab.value === statusFilter.value,
      )?.label || '全部路径'
  )
})

async function loadHistory() {
  loading.value = true

  try {
    const response =
        await getLearningPathHistory()

    items.value =
        response.data.data || []
  } catch (error) {
    toast.error(
        getErrorMessage(
            error,
            '加载路径历史失败',
        ),
    )
  } finally {
    loading.value = false
  }
}

function continueLearning(
    item: LearningPathHistoryItem,
) {
  if (!canActivate(item)) {
    return
  }

  router.push(
      `/path-planner/overview/${item.id}`,
  )
}

function goPage(page: number) {
  currentPage.value = Math.min(
      Math.max(1, page),
      totalPages.value,
  )
}

function resetFilters() {
  keyword.value = ''
  statusFilter.value = 'all'
  currentPage.value = 1
}

function canActivate(
    item: LearningPathHistoryItem,
) {
  return ![
    'failed',
    'generating',
  ].includes(item.status)
}

function actionText(
    item: LearningPathHistoryItem,
) {
  switch (item.status) {
    case 'generating':
      return '生成中'
    case 'failed':
      return '生成失败'
    case 'completed':
      return '查看路径'
    default:
      return '继续学习'
  }
}

function getStatusCount(status: string) {
  if (status === 'all') {
    return items.value.length
  }

  return items.value.filter(
      item => item.status === status,
  ).length
}

function statusLabel(status: string) {
  switch (status) {
    case 'active':
      return '学习中'
    case 'completed':
      return '已完成'
    case 'archived':
      return '已归档'
    case 'paused':
      return '已暂停'
    case 'generating':
      return '生成中'
    case 'failed':
      return '生成失败'
    default:
      return status || '未知状态'
  }
}

function statusShortLabel(status: string) {
  switch (status) {
    case 'active':
      return '学'
    case 'completed':
      return '完'
    case 'archived':
      return '档'
    case 'paused':
      return '停'
    case 'generating':
      return '生'
    case 'failed':
      return '错'
    default:
      return '径'
  }
}

function statusClass(status: string) {
  switch (status) {
    case 'active':
      return 'status-active'
    case 'completed':
      return 'status-completed'
    case 'archived':
      return 'status-archived'
    case 'paused':
      return 'status-paused'
    case 'generating':
      return 'status-generating'
    case 'failed':
      return 'status-failed'
    default:
      return 'status-unknown'
  }
}

function clampProgress(value: number) {
  return Math.max(
      0,
      Math.min(
          Number(value || 0),
          100,
      ),
  )
}

function progressLabel(
    item: LearningPathHistoryItem,
) {
  if (item.status === 'generating') {
    return '生成进度'
  }

  if (item.status === 'failed') {
    return '路径状态'
  }

  return '学习进度'
}

function progressValueText(
    item: LearningPathHistoryItem,
) {
  if (item.status === 'generating') {
    return '生成中'
  }

  if (item.status === 'failed') {
    return '未生成'
  }

  return `${clampProgress(
      item.overall_progress,
  )}%`
}

function progressMetaText(
    item: LearningPathHistoryItem,
) {
  if (item.status === 'generating') {
    return '正在生成路径结构'
  }

  if (item.status === 'failed') {
    return '路径生成未完成'
  }

  return `学习进度 ${clampProgress(
      item.overall_progress,
  )}%`
}

function progressWidth(
    item: LearningPathHistoryItem,
) {
  if (item.status === 'failed') {
    return 0
  }

  if (item.status === 'generating') {
    const progress = clampProgress(
        item.overall_progress,
    )

    return progress > 0
        ? progress
        : 36
  }

  return clampProgress(
      item.overall_progress,
  )
}

function formatTime(value: string) {
  if (!value) {
    return '-'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '-'
  }

  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

watch(
    [
      keyword,
      statusFilter,
      pageSize,
    ],
    () => {
      currentPage.value = 1
    },
)

watch(totalPages, (value) => {
  if (currentPage.value > value) {
    currentPage.value = value
  }
})

onMounted(loadHistory)
</script>

<style scoped>
.path-history-page {
  --history-accent: #159a94;
  --history-accent-hover: #10847f;
  --history-accent-text: #176b67;
  --history-accent-soft: #eaf7f6;
  --history-accent-softer: #f4fbfa;
  --history-accent-border: #83cbc7;
  --history-focus-ring: rgba(21, 154, 148, 0.14);

  --history-text-strong: #182f33;
  --history-text: #304448;
  --history-text-secondary: #64767a;
  --history-text-muted: #849397;
  --history-text-faint: #a0abad;

  --history-border: #dce7e6;
  --history-border-light: #e9efee;
  --history-surface: #ffffff;
  --history-background: #f8faf9;
  --history-hover: #f8fbfa;

  min-height:
      calc(
          100vh -
          var(--navbar-height, 72px)
      );
  padding: 20px 24px 40px;
  background:
      radial-gradient(
          circle at 88% 2%,
          rgba(21, 154, 148, 0.035),
          transparent 30rem
      ),
      var(--history-background);
  color: var(--history-text);
}

.path-history-page *,
.path-history-page *::before,
.path-history-page *::after {
  box-sizing: border-box;
}

.path-history-page button,
.path-history-page input,
.path-history-page select {
  font-family: inherit;
}

.history-shell {
  width: min(
      var(--page-max-width, 1280px),
      100%
  );
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.icon-svg {
  display: inline-block;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.history-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.toolbar-button {
  display: inline-flex;
  height: 40px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 14px;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition:
      border-color 180ms ease,
      background-color 180ms ease,
      color 180ms ease,
      box-shadow 180ms ease,
      transform 180ms ease;
}

.toolbar-button:focus-visible,
.search-box-container:focus-within,
.history-status-tab:focus-visible,
.row-action-button:focus-visible,
.pag-nav-btn:focus-visible,
.pag-num-btn:focus-visible,
.native-select:focus-visible {
  outline: 3px solid
  var(--history-focus-ring);
  outline-offset: 2px;
}

.toolbar-back-button {
  border: 1px solid
  var(--history-border);
  background: var(--history-surface);
  color: var(--history-text-secondary);
}

.toolbar-back-button:hover {
  border-color:
      var(--history-accent-border);
  background:
      var(--history-accent-softer);
  color: var(--history-accent-text);
}

.toolbar-create-button {
  border: 1px solid
  var(--history-accent);
  background:
      linear-gradient(
          135deg,
          #159a94,
          #30aaa4
      );
  color: #ffffff;
  box-shadow:
      0 4px 12px
      rgba(21, 154, 148, 0.16);
}

.toolbar-create-button:hover {
  border-color:
      var(--history-accent-hover);
  background:
      linear-gradient(
          135deg,
          #10847f,
          #249c96
      );
  box-shadow:
      0 6px 16px
      rgba(21, 154, 148, 0.2);
  transform: translateY(-1px);
}

.history-title-box {
  display: inline-flex;
  min-width: 170px;
  flex-shrink: 0;
  align-items: center;
  gap: 10px;
  padding: 0 4px;
}

.title-mark {
  width: 7px;
  height: 7px;
  flex-shrink: 0;
  border-radius: 2px;
  background: var(--history-accent);
}

.history-title-content {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 2px;
}

.history-title-content strong {
  color: var(--history-text-strong);
  font-size: 15px;
  font-weight: 800;
  line-height: 1.35;
  white-space: nowrap;
}

.history-title-content span {
  color: var(--history-text-muted);
  font-size: 11px;
  line-height: 1.4;
  white-space: nowrap;
}

.search-box-container {
  display: flex;
  height: 40px;
  min-width: 220px;
  flex: 1;
  align-items: center;
  gap: 9px;
  padding: 0 12px;
  border: 1px solid
  var(--history-border);
  border-radius: 7px;
  background: var(--history-surface);
  transition:
      border-color 180ms ease,
      box-shadow 180ms ease;
}

.search-box-container:hover {
  border-color: #bdcdcb;
}

.search-box-container:focus-within {
  border-color:
      var(--history-accent);
}

.search-icon {
  color: var(--history-text-faint);
}

.search-box-container input {
  width: 100%;
  min-width: 0;
  padding: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--history-text);
  font-size: 13px;
}

.search-box-container input::placeholder {
  color: var(--history-text-faint);
}

.search-clear-button {
  display: inline-flex;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  border-radius: 5px;
  background: transparent;
  color: var(--history-text-muted);
  cursor: pointer;
}

.search-clear-button:hover {
  background: #f0f5f4;
  color: var(--history-text-strong);
}

.search-clear-button svg {
  width: 13px;
  height: 13px;
}

.status-strip {
  display: grid;
  grid-template-columns:
    repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.history-status-tab {
  display: flex;
  height: 38px;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid
  var(--history-border);
  border-radius: 7px;
  background: var(--history-surface);
  color: var(--history-text-secondary);
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition:
      border-color 160ms ease,
      background-color 160ms ease,
      color 160ms ease,
      box-shadow 160ms ease;
}

.history-status-tab:hover {
  border-color:
      var(--history-accent-border);
  background:
      var(--history-accent-softer);
  color: var(--history-accent-text);
}

.history-status-tab.is-selected {
  border-color:
      var(--history-accent);
  background:
      var(--history-accent-soft);
  color: var(--history-accent-text);
  font-weight: 750;
  box-shadow:
      0 0 0 2px
      rgba(21, 154, 148, 0.045);
}

.tab-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tab-counter {
  display: inline-grid;
  min-width: 21px;
  height: 20px;
  flex-shrink: 0;
  place-items: center;
  padding: 0 5px;
  border: 1px solid
  var(--history-border-light);
  border-radius: 5px;
  background: #f7f9f9;
  color: var(--history-text-muted);
  font-family:
      var(--font-mono, monospace);
  font-size: 10px;
  font-weight: 700;
}

.history-status-tab.is-selected
.tab-counter {
  border-color:
      var(--history-accent-border);
  background: #ffffff;
  color: var(--history-accent-text);
}

.history-panel {
  overflow: hidden;
  border: 1px solid
  var(--history-border);
  border-radius: 10px;
  background:
      var(--history-surface);
  box-shadow:
      0 2px 8px
      rgba(26, 65, 68, 0.035);
}

.panel-head {
  display: flex;
  min-height: 46px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 18px;
  border-bottom: 1px solid
  var(--history-border-light);
  background: #fcfdfd;
}

.panel-filter {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.panel-filter-label {
  color: var(--history-text-muted);
  font-size: 11px;
  font-weight: 600;
}

.panel-filter strong {
  color: var(--history-text-strong);
  font-size: 13px;
  font-weight: 750;
}

.page-size {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.page-size label {
  color: var(--history-text-muted);
  font-size: 11px;
  font-weight: 600;
}

.native-select {
  height: 28px;
  padding: 0 24px 0 9px;
  border: 1px solid
  var(--history-border);
  border-radius: 5px;
  outline: 0;
  background-color: #ffffff;
  color: var(--history-text);
  font-size: 11px;
  font-weight: 650;
  cursor: pointer;
}

.history-list {
  display: flex;
  flex-direction: column;
}

.history-row {
  position: relative;
  display: grid;
  grid-template-columns:
    34px minmax(0, 1fr) 190px 128px;
  align-items: center;
  gap: 18px;
  padding: 15px 20px;
  border-bottom: 1px solid
  var(--history-border-light);
  transition:
      background-color 170ms ease;
}

.history-row:last-child {
  border-bottom: 0;
}

.history-row::before {
  content: '';
  position: absolute;
  top: 8px;
  bottom: 8px;
  left: 0;
  width: 2px;
  border-radius: 0 2px 2px 0;
  background: var(--history-accent);
  opacity: 0;
  transition: opacity 170ms ease;
}

.history-row:hover {
  background:
      var(--history-hover);
}

.history-row:hover::before {
  opacity: 1;
}

.history-row.status-completed::before {
  background: #329c83;
}

.history-row.status-generating::before {
  background: #4d96bd;
}

.history-row.status-failed::before {
  background: #cc6868;
}

.history-row.status-archived::before,
.history-row.status-paused::before {
  background: #98a5a8;
}

.row-status-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
}

.row-status-avatar span {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 6px;
  background: var(--history-accent-soft);
  color: var(--history-accent-text);
  font-size: 12px;
  font-weight: 750;
}

.status-completed
.row-status-avatar span {
  background: #eaf7f2;
  color: #26876f;
}

.status-generating
.row-status-avatar span {
  background: #edf6fa;
  color: #377ea5;
}

.status-failed
.row-status-avatar span {
  background: #fceeee;
  color: #bb5959;
}

.status-archived
.row-status-avatar span,
.status-paused
.row-status-avatar span {
  background: #f1f4f4;
  color: var(--history-text-muted);
}

.row-main-content {
  min-width: 0;
}

.row-title-bar {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
}

.row-title-bar h2 {
  overflow: hidden;
  margin: 0;
  color: var(--history-text-strong);
  font-size: 14px;
  font-weight: 750;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.state-tag {
  display: inline-flex;
  min-height: 22px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  padding: 0 7px;
  border: 1px solid
  var(--history-accent-border);
  border-radius: 5px;
  background:
      var(--history-accent-soft);
  color: var(--history-accent-text);
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
}

.state-tag.status-completed {
  border-color: #a9dcca;
  background: #eaf7f2;
  color: #26876f;
}

.state-tag.status-generating {
  border-color: #bad9e8;
  background: #edf6fa;
  color: #377ea5;
}

.state-tag.status-failed {
  border-color: #edc3c3;
  background: #fceeee;
  color: #bb5959;
}

.state-tag.status-archived,
.state-tag.status-paused {
  border-color: #dce3e3;
  background: #f1f4f4;
  color: var(--history-text-muted);
}

.row-goal-desc {
  display: -webkit-box;
  overflow: hidden;
  margin: 5px 0 0;
  color: var(--history-text-secondary);
  font-size: 13px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
}

.row-metadata-stream {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
  margin-top: 8px;
}

.meta-inline-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--history-text-muted);
  font-size: 11px;
  font-weight: 550;
}

.meta-separator {
  color: #c2cbcc;
  font-size: 11px;
}

.meta-svg {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
  color: #96a6a9;
}

.row-progress-rail {
  display: flex;
  width: 100%;
  min-width: 0;
  flex-direction: column;
  gap: 7px;
}

.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.progress-label {
  color: var(--history-text-muted);
  font-size: 11px;
  font-weight: 550;
}

.progress-header strong {
  color: var(--history-text-strong);
  font-family:
      var(--font-mono, monospace);
  font-size: 13px;
  font-weight: 750;
}

.progress-track-bar {
  position: relative;
  height: 5px;
  overflow: hidden;
  border-radius: 999px;
  background: #e5edec;
}

.fill-indicator {
  display: block;
  height: 100%;
  border-radius: inherit;
  background:
      linear-gradient(
          90deg,
          #159a94,
          #5bbcb7
      );
  transform-origin: left;
  transition: transform 300ms cubic-bezier(0.16, 1, 0.3, 1);
}

.progress-track-bar.is-generating
.fill-indicator {
  min-width: 36%;
  background:
      linear-gradient(
          90deg,
          #4d96bd,
          #8ac3de,
          #4d96bd
      );
  background-size: 200% 100%;
  animation:
      generating-progress 1.8s linear
      infinite;
}

.progress-track-bar.is-failed
.fill-indicator {
  width: 0 !important;
}

.row-action-zone {
  display: flex;
  justify-content: flex-end;
}

.row-action-button {
  display: inline-flex;
  height: 34px;
  min-width: 104px;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 0 12px;
  border: 1px solid
  var(--history-accent-border);
  border-radius: 6px;
  background: #ffffff;
  color: var(--history-accent-text);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
  transition:
      border-color 170ms ease,
      background-color 170ms ease,
      color 170ms ease,
      transform 170ms ease;
}

.row-action-button:hover:not(:disabled) {
  border-color:
      var(--history-accent);
  background:
      var(--history-accent-soft);
  color: var(--history-accent-hover);
}

.row-action-button:disabled {
  border-color: #e1e7e7;
  background: #f5f7f7;
  color: #9da9ab;
  cursor: not-allowed;
}

.arrow-forward-icon {
  width: 11px;
  height: 11px;
  flex-shrink: 0;
  transition: transform 170ms ease;
}

.row-action-button:hover:not(:disabled)
.arrow-forward-icon {
  transform: translateX(2px);
}

.pagination-bar {
  display: flex;
  min-height: 54px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 18px;
  border-top: 1px solid
  var(--history-border-light);
  background: #fcfdfd;
}

.pagination-info {
  color: var(--history-text-muted);
  font-size: 11px;
  font-weight: 600;
}

.pagination-actions-group {
  display: flex;
  align-items: center;
  gap: 5px;
}

.pag-nav-btn,
.pag-num-btn {
  display: inline-flex;
  height: 30px;
  align-items: center;
  justify-content: center;
  border: 1px solid
  var(--history-border);
  border-radius: 5px;
  background: #ffffff;
  color: var(--history-text-secondary);
  font-size: 11px;
  font-weight: 650;
  cursor: pointer;
  transition:
      border-color 160ms ease,
      background-color 160ms ease,
      color 160ms ease;
}

.pag-nav-btn {
  padding: 0 10px;
}

.pag-num-btn {
  width: 30px;
  padding: 0;
  font-family:
      var(--font-mono, monospace);
}

.pag-nav-btn:hover:not(:disabled),
.pag-num-btn:hover {
  border-color:
      var(--history-accent-border);
  background:
      var(--history-accent-softer);
  color: var(--history-accent-text);
}

.pag-num-btn.is-selected {
  border-color:
      var(--history-accent);
  background:
      var(--history-accent-soft);
  color: var(--history-accent-text);
  font-weight: 750;
}

.pag-nav-btn:disabled {
  background: #f7f8f8;
  color: #b1babc;
  cursor: not-allowed;
  opacity: 0.72;
}

.state-area,
.state-area-empty {
  display: flex;
  min-height: 330px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 11px;
  padding: 40px 24px;
  text-align: center;
}

.state-area p {
  margin: 0;
  color: var(--history-text-secondary);
  font-size: 13px;
}

.state-spinner {
  width: 31px;
  height: 31px;
  border: 3px solid
  var(--history-border-light);
  border-top-color:
      var(--history-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.empty-icon-box {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border: 1px solid
  var(--history-accent-border);
  border-radius: 10px;
  background:
      var(--history-accent-soft);
  color: var(--history-accent-text);
}

.empty-icon-box.muted {
  border-color: #dfe6e6;
  background: #f2f5f5;
  color: var(--history-text-muted);
}

.state-svg {
  width: 23px;
  height: 23px;
}

.state-area-empty h2 {
  margin: 2px 0 0;
  color: var(--history-text-strong);
  font-size: 15px;
  font-weight: 750;
}

.state-area-empty p {
  max-width: 440px;
  margin: 0;
  color: var(--history-text-secondary);
  font-size: 12px;
  line-height: 1.65;
}

.empty-primary-button,
.empty-secondary-button {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  justify-content: center;
  margin-top: 5px;
  padding: 0 15px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
      border-color 170ms ease,
      background-color 170ms ease,
      color 170ms ease;
}

.empty-primary-button {
  border: 1px solid
  var(--history-accent);
  background:
      var(--history-accent);
  color: #ffffff;
}

.empty-primary-button:hover {
  border-color:
      var(--history-accent-hover);
  background:
      var(--history-accent-hover);
}

.empty-secondary-button {
  border: 1px solid
  var(--history-border);
  background: #ffffff;
  color: var(--history-text-secondary);
}

.empty-secondary-button:hover {
  border-color:
      var(--history-accent-border);
  background:
      var(--history-accent-softer);
  color: var(--history-accent-text);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes generating-progress {
  from {
    background-position: 100% 0;
  }

  to {
    background-position: -100% 0;
  }
}

@media (max-width: 1100px) {
  .history-row {
    grid-template-columns:
      34px minmax(0, 1fr) 160px 118px;
    gap: 14px;
  }
}

@media (max-width: 960px) {
  .history-toolbar {
    display: grid;
    grid-template-columns:
      auto minmax(0, 1fr) auto;
  }

  .history-title-box {
    grid-column: 1 / -1;
    grid-row: 1;
    min-width: 0;
  }

  .toolbar-back-button {
    grid-column: 1;
    grid-row: 2;
  }

  .search-box-container {
    grid-column: 2;
    grid-row: 2;
  }

  .toolbar-create-button {
    grid-column: 3;
    grid-row: 2;
  }

  .history-row {
    grid-template-columns:
      34px minmax(0, 1fr) 118px;
  }

  .row-progress-rail {
    grid-column: 2 / 4;
    grid-row: 2;
  }

  .row-action-zone {
    grid-column: 3;
    grid-row: 1;
  }
}

@media (max-width: 760px) {
  .path-history-page {
    padding: 14px 16px 30px;
  }

  .history-toolbar {
    display: flex;
    align-items: stretch;
    flex-direction: column;
    gap: 9px;
  }

  .history-title-box {
    order: -1;
    padding: 2px 0 5px;
  }

  .toolbar-back-button,
  .toolbar-create-button,
  .search-box-container {
    width: 100%;
  }

  .status-strip {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }

  .history-status-tab:first-child {
    grid-column: 1 / -1;
  }

  .panel-head {
    align-items: flex-start;
    flex-direction: column;
    gap: 9px;
    padding: 11px 14px;
  }

  .page-size {
    width: 100%;
    justify-content: space-between;
  }

  .history-row {
    grid-template-columns:
      32px minmax(0, 1fr);
    gap: 11px;
    padding: 14px;
  }

  .row-main-content {
    grid-column: 2;
  }

  .row-progress-rail {
    grid-column: 1 / -1;
    grid-row: auto;
  }

  .row-action-zone {
    grid-column: 1 / -1;
    grid-row: auto;
  }

  .row-action-button {
    width: 100%;
  }

  .pagination-bar {
    align-items: flex-start;
    flex-direction: column;
    padding: 12px 14px;
  }

  .pagination-actions-group {
    width: 100%;
    flex-wrap: wrap;
  }
}

@media (max-width: 480px) {
  .status-strip {
    grid-template-columns: 1fr;
  }

  .history-status-tab:first-child {
    grid-column: auto;
  }

  .history-row {
    grid-template-columns: 1fr;
  }

  .row-status-avatar {
    display: none;
  }

  .row-main-content {
    grid-column: 1;
  }

  .row-title-bar {
    align-items: flex-start;
    flex-direction: column;
    gap: 5px;
  }

  .row-title-bar h2 {
    width: 100%;
  }

  .row-metadata-stream {
    align-items: flex-start;
    flex-direction: column;
    gap: 5px;
  }

  .meta-separator {
    display: none;
  }

  .pagination-actions-group {
    justify-content: center;
  }

  .pag-nav-btn {
    flex: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .path-history-page *,
  .path-history-page *::before,
  .path-history-page *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>