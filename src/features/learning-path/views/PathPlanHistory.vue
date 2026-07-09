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

const loading = ref(false)
const items = ref<LearningPathHistoryItem[]>([])
const keyword = ref('')
const statusFilter = ref('all')
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

const totalPages = computed(() => {
  return Math.max(1, Math.ceil(filteredItems.value.length / pageSize.value))
})

const pageStartIndex = computed(() => {
  return (currentPage.value - 1) * pageSize.value
})

const pageEndIndex = computed(() => {
  return Math.min(pageStartIndex.value + pageSize.value, filteredItems.value.length)
})

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

const continueLearning = async (item: LearningPathHistoryItem) => {
  if (!canActivate(item)) return
  try {
    const res = await activateLearningPath(item.id)
    router.push(`/path-planner/overview/${res.data.data.id}`)
  } catch (error) {
    toast.error(getErrorMessage(error, '恢复历史路径失败'))
  }
}

const goPage = (page: number) => {
  currentPage.value = Math.min(Math.max(1, page), totalPages.value)
}

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

watch([keyword, statusFilter, pageSize], () => {
  currentPage.value = 1
})

watch(totalPages, (value) => {
  if (currentPage.value > value) {
    currentPage.value = value
  }
})

onMounted(loadHistory)
</script>

<style scoped>
/* ============================================================
   Path Planner 页面细节优化版
   目标：
   1. 减少卡片感，强化工作台感
   2. 压缩无效留白
   3. 提升输入、模板、偏好按钮的精致度
   4. 保留当前 template/script 逻辑
   ============================================================ */

.path-planner-page {
  min-height: calc(100vh - 64px);
  box-sizing: border-box;
  background:
      radial-gradient(circle at 12% 6%, rgba(70, 184, 180, 0.08), transparent 32%),
      linear-gradient(180deg, #f7fbfa 0%, #f4f8f7 48%, #f7faf9 100%);
}

.planner-unified-container {
  width: min(1320px, calc(100vw - 96px));
  margin: 0 auto;
  padding: 34px 0 42px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ============================================================
   顶部标题区：降低“宣传页”感，改成工作台标题
   ============================================================ */

.workspace-brand-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 28px;
  padding: 0 4px 4px;
}

.header-headline-group {
  max-width: 760px;
}

.agent-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: var(--color-primary);
}

.agent-eyebrow::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-primary);
  box-shadow: 0 0 0 4px rgba(70, 184, 180, 0.12);
}

.workspace-brand-header h1 {
  margin: 8px 0 6px;
  font-size: 30px;
  line-height: 1.15;
  font-weight: 850;
  letter-spacing: -0.04em;
  color: #102326;
}

.cognitive-subtext {
  margin: 0;
  max-width: 700px;
  font-size: 13px;
  line-height: 1.7;
  color: #60777a;
}

.header-action-group {
  flex-shrink: 0;
}

.header-action-group .btn-outline {
  height: 34px;
  padding: 0 15px;
  border-radius: 999px;
  border-color: rgba(70, 184, 180, 0.28);
  background: rgba(255, 255, 255, 0.72);
  color: #173c40;
  font-size: 12px;
  font-weight: 700;
  box-shadow: 0 8px 22px rgba(15, 38, 41, 0.04);
}

.header-action-group .btn-outline:hover:not(:disabled) {
  border-color: rgba(70, 184, 180, 0.55);
  background: #ffffff;
  transform: translateY(-1px);
}

.arrow-symbol {
  margin-left: 4px;
  font-weight: 900;
}

/* ============================================================
   内容流
   ============================================================ */

.workspace-content-flow {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ============================================================
   常用模板：从小卡片改成轻量模板条
   ============================================================ */

.horizontal-templates-gallery {
  padding: 0;
  display: grid;
  grid-template-columns: 172px minmax(0, 1fr);
  align-items: center;
  gap: 14px;
}

.gallery-title-strip {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.gallery-title-strip h4 {
  margin: 0;
  font-size: 13px;
  line-height: 1.2;
  font-weight: 850;
  letter-spacing: -0.02em;
  color: #173c40;
}

.gallery-title-strip span {
  font-size: 11px;
  line-height: 1.2;
  color: #8aa0a3;
}

.templates-horizontal-grid {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  overflow: hidden;
  border: 1px solid rgba(165, 199, 199, 0.65);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.62);
  box-shadow: 0 12px 32px rgba(15, 38, 41, 0.035);
}

.micro-template-gallery-card {
  position: relative;
  height: 50px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 0;
  border-right: 1px solid rgba(202, 222, 222, 0.72);
  border-radius: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
  color: #46b8b4;
  transition: background 0.18s ease, color 0.18s ease;
}

.micro-template-gallery-card:last-child {
  border-right: 0;
}

.micro-template-gallery-card::after {
  content: "";
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 0;
  height: 2px;
  border-radius: 999px;
  background: currentColor;
  opacity: 0;
  transform: scaleX(0.35);
  transition: all 0.18s ease;
}

.micro-template-gallery-card:hover:not(:disabled),
.micro-template-gallery-card.active {
  background: rgba(255, 255, 255, 0.86);
}

.micro-template-gallery-card.active::after {
  opacity: 1;
  transform: scaleX(1);
}

.category-glow-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  background: currentColor;
}

.micro-card-meta {
  min-width: 0;
}

.micro-card-meta strong {
  display: block;
  max-width: 100%;
  font-size: 13px;
  line-height: 1.2;
  font-weight: 800;
  color: #132f33;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.micro-card-meta span {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: #789196;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.micro-template-gallery-card.teal {
  color: var(--color-primary);
}

.micro-template-gallery-card.blue {
  color: #5267df;
}

.micro-template-gallery-card.amber {
  color: #c58a2d;
}

.micro-template-gallery-card.violet {
  color: #7c5ce0;
}

/* ============================================================
   主表单：弱化大卡片，增强行级秩序
   ============================================================ */

.structured-form-panel {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 20px 24px 22px;
  border: 1px solid rgba(166, 201, 201, 0.72);
  border-radius: 22px;
  background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(255, 255, 255, 0.82)),
      rgba(255, 255, 255, 0.86);
  box-shadow:
      0 18px 48px rgba(24, 70, 74, 0.06),
      inset 0 1px 0 rgba(255, 255, 255, 0.75);
}

.structured-form-panel::before {
  content: "";
  position: absolute;
  top: 0;
  left: 28px;
  right: 28px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(70, 184, 180, 0.55), transparent);
}

.form-grid-row {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr);
  gap: 28px;
  padding: 19px 0;
  border-bottom: 1px solid rgba(205, 224, 224, 0.74);
}

.form-grid-row:first-child {
  padding-top: 2px;
}

.form-grid-row:last-of-type {
  border-bottom: 0;
}

.row-meta-pane {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
}

.row-badge-num {
  width: 28px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #e6f5f4;
  color: #2c7c7a;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 900;
  box-shadow: inset 0 0 0 1px rgba(70, 184, 180, 0.12);
}

.row-headline-group h3 {
  margin: 0;
  font-size: 15px;
  line-height: 1.25;
  font-weight: 850;
  color: #123236;
  letter-spacing: -0.02em;
}

.row-headline-group p {
  margin: 6px 0 0;
  max-width: 170px;
  font-size: 12px;
  line-height: 1.45;
  color: #718a8f;
}

/* ============================================================
   输入框：统一高度、聚焦态、placeholder 颜色
   ============================================================ */

.row-control-pane {
  min-width: 0;
}

.input-container-box input,
.textarea-container-box textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(161, 194, 196, 0.76);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.76);
  color: #16363a;
  font-family: inherit;
  font-size: 13px;
  outline: none;
  transition:
      border-color 0.16s ease,
      box-shadow 0.16s ease,
      background 0.16s ease;
}

.input-container-box input {
  height: 42px;
  padding: 0 15px;
}

.textarea-container-box textarea {
  min-height: 84px;
  max-height: 150px;
  padding: 13px 15px;
  resize: none;
  line-height: 1.65;
}

.input-container-box input::placeholder,
.textarea-container-box textarea::placeholder,
.tag-inner-flex input::placeholder {
  color: #9aadb1;
}

.input-container-box input:focus,
.textarea-container-box textarea:focus {
  border-color: rgba(70, 184, 180, 0.9);
  background: #ffffff;
  box-shadow: 0 0 0 4px rgba(70, 184, 180, 0.13);
}

.textarea-info-bar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 8px;
  font-size: 11px;
  color: #8da2a6;
}

.char-counter {
  flex-shrink: 0;
  font-family: var(--font-mono);
}

/* ============================================================
   当前基础标签输入
   ============================================================ */

.tag-input-bezel-box {
  min-height: 42px;
  box-sizing: border-box;
  padding: 6px 10px;
  border: 1px solid rgba(161, 194, 196, 0.76);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.76);
  transition:
      border-color 0.16s ease,
      box-shadow 0.16s ease,
      background 0.16s ease;
}

.tag-input-bezel-box:focus-within {
  border-color: rgba(70, 184, 180, 0.9);
  background: #ffffff;
  box-shadow: 0 0 0 4px rgba(70, 184, 180, 0.13);
}

.tag-inner-flex {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  align-items: center;
}

.tag-inner-flex input {
  min-width: 170px;
  flex: 1;
  height: 28px;
  padding: 0 2px;
  border: 0;
  outline: 0;
  background: transparent;
  color: #16363a;
  font-family: inherit;
  font-size: 13px;
}

.custom-tag-node {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 26px;
  padding: 0 8px 0 10px;
  border-radius: 999px;
  background: #e9f7f6;
  color: #237c79;
  font-size: 12px;
  font-weight: 750;
}

.tag-close-trigger {
  width: 16px;
  height: 16px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: rgba(35, 124, 121, 0.08);
  color: inherit;
  line-height: 1;
  cursor: pointer;
}

.tag-close-trigger:hover {
  background: rgba(35, 124, 121, 0.18);
}

.quick-tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

/* ============================================================
   通用 pill 按钮细节
   ============================================================ */

.btn-pill {
  height: 30px;
  padding: 0 13px;
  border: 1px solid rgba(168, 196, 198, 0.74);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.62);
  color: #526d72;
  font-size: 12px;
  font-weight: 650;
  cursor: pointer;
  transition:
      background 0.16s ease,
      border-color 0.16s ease,
      color 0.16s ease,
      transform 0.16s ease,
      box-shadow 0.16s ease;
}

.btn-pill:hover {
  background: #ffffff;
  border-color: rgba(70, 184, 180, 0.45);
  color: #173c40;
}

.btn-pill.active,
.quick-tags-container .btn-pill.active,
.segmented-pill-group .btn-pill.active {
  border-color: rgba(70, 184, 180, 0.86) !important;
  background: #e8f7f6 !important;
  color: #227c79 !important;
  font-weight: 800;
  box-shadow: 0 5px 14px rgba(70, 184, 180, 0.11);
}

.btn-pill.active:hover {
  transform: translateY(-1px);
}

/* ============================================================
   偏好矩阵：减少行距，增强标签对齐
   ============================================================ */

.preferences-matrix {
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.preference-flex-line {
  display: grid;
  grid-template-columns: 78px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.pref-field-label {
  color: #173c40;
  font-size: 13px;
  font-weight: 850;
}

.segmented-pill-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.focus-accent-group .btn-pill.foundation.active {
  background: #ecfdf5 !important;
  border-color: #10b981 !important;
  color: #047857 !important;
}

.focus-accent-group .btn-pill.key_points.active {
  background: #eef2ff !important;
  border-color: #6366f1 !important;
  color: #4f46e5 !important;
}

.focus-accent-group .btn-pill.practice.active {
  background: #fff7ed !important;
  border-color: #f59e0b !important;
  color: #b45309 !important;
}

.focus-accent-group .btn-pill.weakness.active {
  background: #fff1f2 !important;
  border-color: #fb7185 !important;
  color: #be123c !important;
}

/* ============================================================
   底部提交区：更像工具栏，减少“大提示卡”感觉
   ============================================================ */

.form-action-footer {
  margin-top: 4px;
  padding-top: 16px;
  border-top: 1px solid rgba(205, 224, 224, 0.74);
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 18px;
}

.ai-readiness-inline-dashboard {
  min-width: 0;
  max-width: none;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  border: 1px solid rgba(187, 211, 213, 0.74);
  border-radius: 14px;
  background: rgba(247, 251, 250, 0.8);
}

.dashboard-visual-pulse {
  position: relative;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.pulse-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: #9badb0;
  opacity: 0.2;
}

.pulse-center-core {
  position: absolute;
  left: 4px;
  top: 4px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #8ca2a5;
}

.dashboard-inline-meta {
  min-width: 0;
}

.dashboard-inline-meta strong {
  display: block;
  font-size: 13px;
  line-height: 1.25;
  font-weight: 850;
  color: #173c40;
}

.dashboard-inline-meta p {
  margin: 3px 0 0;
  font-size: 11.5px;
  line-height: 1.45;
  color: #6f888c;
}

.dashboard-inline-meta .lack {
  color: #be123c;
  font-weight: 850;
}

.ai-readiness-inline-dashboard.is-ready {
  border-color: rgba(70, 184, 180, 0.48);
  background: #edfafa;
}

.ai-readiness-inline-dashboard.is-ready .pulse-ring {
  background: var(--color-primary);
  animation: pulseSpread 1.8s infinite ease-out;
  opacity: 0.35;
}

.ai-readiness-inline-dashboard.is-ready .pulse-center-core {
  background: var(--color-primary);
}

.ai-readiness-inline-dashboard.is-ready .dashboard-inline-meta strong,
.ai-readiness-inline-dashboard.is-ready .dashboard-inline-meta p {
  color: #1d7471;
}

@keyframes pulseSpread {
  0% {
    transform: scale(1);
    opacity: 0.42;
  }
  100% {
    transform: scale(2.25);
    opacity: 0;
  }
}

.footer-buttons-cluster {
  display: flex;
  align-items: center;
  gap: 10px;
}

.footer-buttons-cluster .btn-outline,
.custom-premium-action {
  height: 38px;
  padding: 0 18px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 800;
}

.footer-buttons-cluster .btn-outline {
  border: 1px solid rgba(168, 196, 198, 0.78);
  background: rgba(255, 255, 255, 0.68);
  color: #526d72;
}

.footer-buttons-cluster .btn-outline:hover {
  background: #ffffff;
  color: #173c40;
  border-color: rgba(70, 184, 180, 0.42);
}

.custom-premium-action {
  min-width: 138px;
  border: 1px solid rgba(19, 110, 108, 0.12) !important;
  background: linear-gradient(135deg, #3ab7b2 0%, #31a7d8 100%) !important;
  color: #ffffff !important;
  box-shadow: 0 9px 22px rgba(49, 167, 216, 0.22) !important;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.08);
}

.custom-premium-action:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 26px rgba(49, 167, 216, 0.28) !important;
}

.custom-premium-action:active:not(:disabled) {
  transform: translateY(0);
}

.custom-premium-action:disabled {
  opacity: 0.48;
  cursor: not-allowed;
  box-shadow: none !important;
}

/* ============================================================
   页脚说明：降噪，不抢主操作
   ============================================================ */

.workspace-flow-footnote {
  padding: 0;
}

.agile-notice-banner-box {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 14px;
  align-items: start;
  padding: 13px 16px;
  border: 1px dashed rgba(163, 195, 198, 0.86);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.42);
}

.mini-badge {
  display: block;
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 1.4;
  font-weight: 850;
  letter-spacing: 0.08em;
  color: #2c8f8b;
}

.agile-notice-banner-box p {
  margin: 0;
  font-size: 12px;
  line-height: 1.65;
  color: #6d8589;
}

/* ============================================================
   生成中状态：更稳的流程视觉
   ============================================================ */

.planning-card-wrapper {
  width: min(980px, 100%);
  margin: 34px auto 0;
}

.bezel-card-inner {
  padding: 34px 38px;
  border: 1px solid rgba(166, 201, 201, 0.76);
  border-radius: 26px;
  background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 255, 255, 0.88)),
      #ffffff;
  box-shadow: 0 22px 60px rgba(24, 70, 74, 0.08);
}

.planning-engine-head {
  margin-bottom: 28px;
  text-align: center;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: #e8f7f6;
  color: #227c79;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.08em;
}

.status-badge.pulse-animation {
  animation: pulseOpacity 1.8s infinite ease-in-out;
}

@keyframes pulseOpacity {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.58;
  }
}

.planning-engine-head h2 {
  margin: 12px 0 6px;
  font-size: 24px;
  line-height: 1.2;
  font-weight: 850;
  color: #102326;
  letter-spacing: -0.035em;
}

.planning-engine-head p {
  margin: 0;
  color: #6f888c;
  font-size: 12px;
}

.orbit-timeline-container {
  position: relative;
  display: flex;
  justify-content: space-between;
  margin: 8px 0 28px;
  padding: 0 12px;
}

.orbit-line-track {
  position: absolute;
  z-index: 1;
  top: 15px;
  left: 52px;
  right: 52px;
  height: 2px;
  background: #dce9e9;
}

.orbit-node-item {
  position: relative;
  z-index: 2;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #46b8b4;
}

.node-geometric-dot {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 2px solid #d2e3e3;
  border-radius: 50%;
  background: #ffffff;
  color: #91a5a8;
  font-size: 12px;
  font-weight: 850;
  transition: all 0.18s ease;
}

.node-label {
  color: #8a9fa3;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
}

.orbit-node-item.done .node-geometric-dot,
.orbit-node-item.active .node-geometric-dot {
  border-color: currentColor;
  background: currentColor;
  color: #ffffff;
}

.orbit-node-item.active .node-geometric-dot {
  box-shadow: 0 0 0 5px rgba(70, 184, 180, 0.14);
}

.orbit-node-item.done .node-label,
.orbit-node-item.active .node-label {
  color: #173c40;
}

.orbit-node-item.teal {
  color: var(--color-primary);
}

.orbit-node-item.blue {
  color: #5267df;
}

.orbit-node-item.amber {
  color: #c58a2d;
}

.orbit-node-item.violet {
  color: #7c5ce0;
}

.progress-bar-block {
  margin-bottom: 16px;
}

.progress-bar-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
}

.task-title {
  color: #173c40;
  font-weight: 850;
}

.percent-value {
  color: #227c79;
  font-family: var(--font-mono);
}

.progress-bar-track {
  height: 7px;
  overflow: hidden;
  border-radius: 999px;
  background: #dce9e9;
}

.progress-bar-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #46b8b4, #5267df);
  transition: width 0.38s ease;
}

.planning-logs-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 118px;
  padding: 14px 16px;
  border: 1px solid rgba(187, 211, 213, 0.74);
  border-radius: 16px;
  background: #f7fbfa;
}

.log-row-item {
  display: flex;
  align-items: center;
  gap: 9px;
}

.log-dot-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
}

.log-message-text {
  color: #60777a;
  font-size: 12px;
}

.log-slide-enter-active,
.log-slide-leave-active {
  transition: all 0.22s ease;
}

.log-slide-enter-from {
  opacity: 0;
  transform: translateY(5px);
}

.error-handling-panel {
  margin-top: 14px;
  padding: 14px 16px;
  border: 1px solid rgba(225, 29, 72, 0.14);
  border-radius: 16px;
  background: #fff1f2;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
}

.error-message-content strong {
  display: block;
  color: #be123c;
  font-size: 13px;
  font-weight: 850;
}

.error-message-content p {
  margin: 4px 0 0;
  color: #6f888c;
  font-size: 12px;
}

.danger-border {
  border-color: rgba(225, 29, 72, 0.24) !important;
  color: #be123c !important;
}

/* ============================================================
   响应式
   ============================================================ */

@media (max-width: 1180px) {
  .planner-unified-container {
    width: min(100% - 48px, 1120px);
  }

  .horizontal-templates-gallery {
    grid-template-columns: 1fr;
  }

  .gallery-title-strip {
    flex-direction: row;
    align-items: baseline;
    gap: 8px;
  }

  .templates-horizontal-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    border-radius: 16px;
  }

  .micro-template-gallery-card:nth-child(2n) {
    border-right: 0;
  }

  .micro-template-gallery-card:nth-child(-n + 2) {
    border-bottom: 1px solid rgba(202, 222, 222, 0.72);
  }
}

@media (max-width: 860px) {
  .planner-unified-container {
    width: min(100% - 28px, 760px);
    padding-top: 22px;
  }

  .workspace-brand-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 14px;
  }

  .header-headline-group {
    max-width: 100%;
  }

  .workspace-brand-header h1 {
    font-size: 26px;
  }

  .form-grid-row {
    grid-template-columns: 1fr;
    gap: 12px;
    padding: 18px 0;
  }

  .row-meta-pane {
    grid-template-columns: 30px minmax(0, 1fr);
  }

  .row-headline-group p {
    max-width: 100%;
  }

  .preference-flex-line {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .form-action-footer {
    grid-template-columns: 1fr;
  }

  .footer-buttons-cluster {
    width: 100%;
  }

  .footer-buttons-cluster button {
    flex: 1;
  }

  .agile-notice-banner-box {
    grid-template-columns: 1fr;
    gap: 6px;
  }

  .orbit-timeline-container {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
    padding: 0;
  }

  .orbit-line-track {
    top: 16px;
    bottom: 16px;
    left: 16px;
    right: auto;
    width: 2px;
    height: auto;
  }

  .orbit-node-item {
    flex-direction: row;
    justify-content: flex-start;
    gap: 12px;
  }

  .node-label {
    text-align: left;
  }
}

@media (max-width: 560px) {
  .templates-horizontal-grid {
    grid-template-columns: 1fr;
  }

  .micro-template-gallery-card {
    border-right: 0;
    border-bottom: 1px solid rgba(202, 222, 222, 0.72);
  }

  .micro-template-gallery-card:last-child {
    border-bottom: 0;
  }

  .micro-template-gallery-card:nth-child(-n + 2) {
    border-bottom: 1px solid rgba(202, 222, 222, 0.72);
  }

  .structured-form-panel {
    padding: 18px 16px;
    border-radius: 18px;
  }

  .textarea-info-bar {
    flex-direction: column;
    gap: 4px;
  }
}
</style>