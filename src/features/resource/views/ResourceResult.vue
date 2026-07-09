<template>
  <div class="resource-result-page">
    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <div class="loading-toolbar">
        <div class="sk sk-back"></div>
        <div class="sk sk-title"></div>
        <div class="sk sk-pill"></div>
        <div class="sk sk-meta"></div>
      </div>

      <div class="loading-filter">
        <div v-for="i in 6" :key="i" class="sk sk-filter"></div>
      </div>

      <div class="loading-grid">
        <div v-for="i in 6" :key="i" class="loading-card">
          <div class="sk sk-card-head"></div>
          <div class="sk sk-card-preview"></div>
          <div class="sk sk-line long"></div>
          <div class="sk sk-line"></div>
          <div class="sk sk-footer"></div>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state">
      <div class="error-card">
        <PhWarningCircle class="error-icon" />
        <h2>资源包加载失败</h2>
        <p>请检查网络连接后重试，或返回上一页。</p>
        <div class="error-actions">
          <button type="button" class="btn-ghost" @click="goBack">返回上一页</button>
          <button type="button" class="btn-primary" @click="loadResource">重新加载</button>
        </div>
      </div>
    </div>

    <!-- Content -->
    <template v-else-if="bundle">
      <section class="result-toolbar">
        <div class="toolbar-left">
          <button class="back-btn" type="button" @click="goBack">
            <PhArrowLeft class="toolbar-icon" />
            <span>返回</span>
          </button>

          <div class="title-block">
            <div class="title-line">
              <h1>资源包结果</h1>
              <span class="status-pill" :class="isPartial ? 'warn' : 'ok'">
                <PhWarningCircle v-if="isPartial" />
                <PhCheckCircle v-else />
                {{ isPartial ? '部分完成' : '生成完成' }}
              </span>
            </div>

            <p :title="bundleTitle">{{ bundleTitle }}</p>
          </div>
        </div>

        <div class="toolbar-right">
          <span class="meta-pill">
            <PhFolderOpen />
            资源 {{ resourceCards.length }}
          </span>
          <span class="meta-pill">
            <PhSquaresFour />
            类型 {{ availableFilters.length }}
          </span>
          <span v-if="createdAt" class="meta-pill time">
            <PhClock />
            {{ createdAt }}
          </span>
        </div>
      </section>

      <section class="filter-row" v-if="resourceCards.length > 1">
        <button
            type="button"
            :class="{ active: activeFilter === 'all' }"
            @click="activeFilter = 'all'"
        >
          全部
          <span>{{ resourceCards.length }}</span>
        </button>

        <button
            v-for="f in availableFilters"
            :key="f.type"
            type="button"
            :class="{ active: activeFilter === f.type }"
            @click="activeFilter = f.type"
        >
          {{ f.label }}
          <span>{{ f.count }}</span>
        </button>
      </section>

      <section v-if="isPartial" class="partial-notice">
        <PhWarningCircle />
        <span>部分资源未能完成，当前页面仅展示已经成功生成的资源。</span>
      </section>

      <main class="resource-content">
        <section v-if="filteredCards.length" class="resource-grid">
          <article
              v-for="card in filteredCards"
              :key="card.id"
              class="resource-card"
              :class="`type-${card.type}`"
              tabindex="0"
              role="button"
              :aria-label="`查看 ${card.title}`"
              @click="openPreview(card)"
              @keydown.enter.prevent="openPreview(card)"
              @keydown.space.prevent="openPreview(card)"
          >
            <header class="card-head">
              <div class="card-identity">
                <span class="type-icon">
                  <component :is="getIconComponent(card.type)" />
                </span>
                <div class="card-title-wrap">
                  <h2 :title="card.title">{{ card.title }}</h2>
                  <span>{{ getLabel(card.type) }}</span>
                </div>
              </div>

              <span class="format-badge">{{ card.format }}</span>
            </header>

            <div class="resource-visual">
              <!-- 课程讲解 -->
              <div v-if="card.type === 'content'" class="visual visual-course">
                <div class="course-book">
                  <div class="book-spine">
                    <i></i>
                    <i></i>
                    <i></i>
                  </div>
                  <div class="book-content">
                    <strong></strong>
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>

              <!-- 思维导图 -->
              <div v-else-if="card.type === 'mindmap'" class="visual visual-map">
                <div class="map-center">
                  <PhBrain />
                </div>
                <i class="map-branch b1"></i>
                <i class="map-branch b2"></i>
                <i class="map-branch b3"></i>
                <i class="map-branch b4"></i>
                <span class="map-node n1"></span>
                <span class="map-node n2"></span>
                <span class="map-node n3"></span>
                <span class="map-node n4"></span>
              </div>

              <!-- 随堂练习 -->
              <div v-else-if="card.type === 'quiz'" class="visual visual-quiz">
                <div class="quiz-paper">
                  <div class="question-row">
                    <b>Q1</b>
                    <span></span>
                  </div>
                  <div class="answer-row">
                    <em>A</em>
                    <span></span>
                  </div>
                  <div class="answer-row">
                    <em>B</em>
                    <span></span>
                  </div>
                  <div class="answer-row right">
                    <em>C</em>
                    <span></span>
                    <PhCheckCircle />
                  </div>
                </div>
              </div>

              <!-- 代码实操 -->
              <div v-else-if="card.type === 'code'" class="visual visual-code">
                <div class="code-window">
                  <div class="code-top">
                    <i></i>
                    <i></i>
                    <i></i>
                  </div>
                  <div class="code-main">
                    <div class="line-nums">
                      <span>1</span>
                      <span>2</span>
                      <span>3</span>
                      <span>4</span>
                      <span>5</span>
                    </div>
                    <div class="code-lines">
                      <i></i>
                      <i></i>
                      <i></i>
                      <i></i>
                      <i></i>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 拓展阅读 -->
              <div v-else-if="card.type === 'reading'" class="visual visual-reading">
                <div class="open-book">
                  <div class="page left">
                    <span></span>
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <div class="page right">
                    <span></span>
                    <span></span>
                    <div class="mini-chart">
                      <i></i>
                      <i></i>
                      <i></i>
                    </div>
                  </div>
                </div>
              </div>

              <!-- PPT -->
              <div v-else-if="card.type === 'ppt'" class="visual visual-ppt">
                <div class="slide-main">
                  <PhPresentationChart />
                  <strong></strong>
                  <span></span>
                  <span></span>
                </div>
                <div class="slide-thumb t1"></div>
                <div class="slide-thumb t2"></div>
              </div>

              <!-- 动画 / 视频 -->
              <div v-else class="visual visual-video">
                <div class="video-screen">
                  <PhPlayCircle />
                </div>
                <div class="video-track">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>

            <div class="card-body">
              <p>{{ card.summary }}</p>

              <div class="tag-row" v-if="card.highlights.length">
                <span v-for="tag in card.highlights" :key="tag">{{ tag }}</span>
              </div>
            </div>

            <footer class="card-footer">
              <span>{{ getActionText(card.type) }}</span>
              <PhArrowRight />
            </footer>
          </article>
        </section>

        <section v-else class="empty-state">
          <PhMagnifyingGlass class="empty-icon" />
          <h2>当前分类暂无资源</h2>
          <p>请选择其他资源类型，或查看全部生成结果。</p>
          <button type="button" @click="activeFilter = 'all'">查看全部</button>
        </section>
      </main>

      <PreviewDialog
          v-model:activeAgent="activePreviewAgent"
          :data="previewData"
          :resource="previewResource"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import {
  PhArrowLeft,
  PhArrowRight,
  PhBookOpenText,
  PhBrain,
  PhCheckCircle,
  PhClock,
  PhCode,
  PhFilmSlate,
  PhFolderOpen,
  PhGitFork,
  PhMagnifyingGlass,
  PhPlayCircle,
  PhPresentationChart,
  PhSquaresFour,
  PhStudent,
  PhWarningCircle,
} from '@phosphor-icons/vue'

import PreviewDialog from '@/shared/content/PreviewDialog.vue'
import { getGeneratedResourceDetail } from '@/features/resource/api/history'
import type { GeneratedResourceBundle } from '@/features/resource/api/history'
import { getDifficultyLabel } from '@/features/resource/model/catalog'
import { getArtifactLabel } from '@/shared/content/kind'

type ResourceCard = {
  id: string
  type: string
  title: string
  summary: string
  format: string
  highlights: string[]
  content: any
  resource: any
}

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref(false)
const bundle = shallowRef<GeneratedResourceBundle | null>(null)

const activeFilter = ref('all')
const activePreviewAgent = ref<string | null>(null)
const previewData = ref<any>(null)
const previewResource = ref<any>(null)

const resourceId = computed(() => Number(route.params.id) || null)

onMounted(loadResource)

async function loadResource() {
  if (!resourceId.value) {
    loading.value = false
    error.value = true
    return
  }

  loading.value = true
  error.value = false

  try {
    const res = await getGeneratedResourceDetail(resourceId.value)
    bundle.value = res.data?.data || null
    error.value = !bundle.value
  } catch (e) {
    console.error('Failed to load resource detail:', e)
    error.value = true
    toast.error('加载资源详情失败')
  } finally {
    loading.value = false
  }
}

const bundleTitle = computed(() => String(bundle.value?.title || '个性化学习资源包'))
const isPartial = computed(() => bundle.value?.status === 'partial_completed')
const createdAt = computed(() => formatTime(bundle.value?.created_at || null))

const RESOURCE_ORDER = ['content', 'mindmap', 'quiz', 'code', 'reading', 'ppt', 'cartoon', 'video']
const RESOURCE_TYPES = new Set(RESOURCE_ORDER)

const rawResources = computed<any[]>(() => {
  const r = bundle.value?.resources ?? (bundle.value as any)?.items
  return Array.isArray(r) ? r : []
})

const resourceCards = computed<ResourceCard[]>(() =>
    rawResources.value
        .map(normalizeCard)
        .filter((c): c is ResourceCard => c !== null)
        .sort((a, b) => {
          const oa = RESOURCE_ORDER.indexOf(a.type)
          const ob = RESOURCE_ORDER.indexOf(b.type)
          return (oa === -1 ? 99 : oa) - (ob === -1 ? 99 : ob)
        })
)

const filteredCards = computed(() =>
    activeFilter.value === 'all'
        ? resourceCards.value
        : resourceCards.value.filter(c => c.type === activeFilter.value)
)

const availableFilters = computed(() =>
    RESOURCE_ORDER
        .map(type => ({
          type,
          label: getArtifactLabel(type),
          count: resourceCards.value.filter(c => c.type === type).length,
        }))
        .filter(f => f.count > 0)
)

function normalizeCard(r: any): ResourceCard | null {
  const type = String(r.type || r.agent_type || r.agentId || '').trim().toLowerCase()
  const status = String(r.status || 'completed').toLowerCase()

  if (!RESOURCE_TYPES.has(type)) return null
  if (!['finished', 'completed', 'success'].includes(status)) return null
  if (!hasContent(r.content, type)) return null

  const metadata = isPlainObj(r.metadata_json)
      ? r.metadata_json
      : isPlainObj(r.metadata)
          ? r.metadata
          : {}

  const metrics = isPlainObj(r.metrics) ? r.metrics : {}

  return {
    id: String(r.id ?? type),
    type,
    title: getTitle(r, type),
    summary: getSummary(r, type),
    format: getFormat(r, type),
    highlights: getHighlights(metadata, metrics),
    content: r.content,
    resource: r,
  }
}

function getTitle(r: any, type: string) {
  const t = typeof r.title === 'string' ? r.title.trim() : ''
  return t || `${getArtifactLabel(type)} · ${bundleTitle.value}`
}

function getSummary(r: any, type: string) {
  const candidates = [r.summary, r.description, r.metadata?.summary]
  const found = candidates.find(v => typeof v === 'string' && v.trim())
  return typeof found === 'string' ? found.trim() : getDefaultSummary(type)
}

function getDefaultSummary(type: string) {
  return ({
    content: '围绕学习目标组织系统讲解，帮助建立完整知识框架。',
    mindmap: '将核心概念、层级关系和知识依赖整理为可视化结构。',
    quiz: '通过不同题型检测理解程度，用于学习后的即时巩固。',
    code: '提供可阅读、可运行、可迁移的代码案例，帮助把概念转化为实践能力。',
    reading: '补充相关课程资料与拓展阅读，便于继续深入学习。',
    ppt: '整合重点内容形成结构化课件，适合快速复习和课堂展示。',
    cartoon: '用动画方式呈现概念变化、执行过程和知识关系。',
    video: '基于学习目标生成讲解视频，适合跟学和回看。',
  })[type] ?? '根据本次学习需求生成的个性化学习资源。'
}

function getFormat(r: any, type: string) {
  const raw = r.format || r.file_type || r.fileType

  if (typeof raw === 'string' && raw.trim()) {
    return normalizeFormat(raw)
  }

  return ({
    content: 'Markdown',
    mindmap: 'Markmap',
    quiz: 'JSON',
    code: 'Code',
    reading: 'Links',
    ppt: 'Slides',
    cartoon: 'Video',
    video: 'Video',
  })[type] ?? 'Resource'
}

function normalizeFormat(raw: string) {
  const value = raw.trim().toLowerCase()

  if (value === 'markdown' || value === 'md') return 'Markdown'
  if (value === 'markmap') return 'Markmap'
  if (value === 'json') return 'JSON'
  if (value === 'code') return 'Code'
  if (value === 'links') return 'Links'
  if (value === 'pdf') return 'PDF'
  if (value === 'ppt' || value === 'pptx' || value === 'slides') return 'Slides'
  if (value === 'mp4' || value === 'video') return 'Video'

  return raw.trim()
}

function getHighlights(metadata: any, metrics: any): string[] {
  const candidates = [
    metrics.question_count ? `${metrics.question_count} 道题` : '',
    metrics.node_count ? `${metrics.node_count} 个节点` : '',
    metrics.slide_count ? `${metrics.slide_count} 页课件` : '',
    metrics.resource_count ? `${metrics.resource_count} 条资料` : '',
    metrics.language ? String(metrics.language) : '',
    metadata.programming_language ? String(metadata.programming_language) : '',
    metadata.difficulty ? getDifficultyLabel(metadata.difficulty) : '',
  ]

  const result = [...new Set(candidates.filter(Boolean))].slice(0, 3)

  if (result.length) return result

  return ['重点梳理', '个性化生成', '可直接学习']
}

function hasContent(value: unknown, type?: string) {
  if (type === 'ppt' || type === 'cartoon' || type === 'video') return true
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.length > 0
  return isPlainObj(value) && Object.keys(value).length > 0
}

function isPlainObj(v: unknown): v is Record<string, any> {
  return !!v && typeof v === 'object' && !Array.isArray(v)
}

function getLabel(type: string) {
  return getArtifactLabel(type)
}

function getIconComponent(type: string) {
  return ({
    content: PhBookOpenText,
    mindmap: PhGitFork,
    quiz: PhStudent,
    code: PhCode,
    reading: PhBookOpenText,
    ppt: PhPresentationChart,
    cartoon: PhFilmSlate,
    video: PhPlayCircle,
  })[type] ?? PhFolderOpen
}

function getActionText(type: string) {
  return ({
    content: '查看课程讲解',
    mindmap: '打开思维导图',
    quiz: '查看练习题',
    code: '查看代码实操',
    reading: '查看拓展阅读',
    ppt: '查看课件内容',
    cartoon: '查看动画资源',
    video: '查看视频资源',
  })[type] ?? '查看内容'
}

function openPreview(card: ResourceCard) {
  activePreviewAgent.value = card.type
  previewData.value = card.content
  previewResource.value = card.resource
}

function goBack() {
  router.back()
}

function formatTime(time: string | null) {
  if (!time) return ''

  const d = new Date(time)
  if (isNaN(d.getTime())) return ''

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d)
}
</script>

<style scoped>
.resource-result-page {
  width: 100%;
  min-height: 100%;
  padding: 18px 24px 40px;
  background: #f6f8fc;
  color: #0f172a;
  font-family:
      var(--font-ui, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
}

/* Toolbar */
.result-toolbar {
  min-height: 54px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e4eaf3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.toolbar-left {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 14px;
}

.back-btn {
  height: 32px;
  padding: 0 13px;
  border: 1px solid #d7e0ec;
  border-radius: 999px;
  background: #fff;
  color: #334155;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
}

.back-btn:hover {
  border-color: #b8c7da;
  background: #f8fafc;
}

.toolbar-icon {
  width: 15px;
  height: 15px;
}

.title-block {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.title-line {
  display: flex;
  align-items: center;
  gap: 10px;
}

.title-line h1 {
  margin: 0;
  font-size: 18px;
  line-height: 1.2;
  font-weight: 900;
  letter-spacing: -0.02em;
  color: #0f172a;
}

.title-block p {
  max-width: min(560px, 48vw);
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.4;
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-pill {
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.status-pill svg {
  width: 14px;
  height: 14px;
}

.status-pill.ok {
  color: #047857;
  background: #ecfdf5;
  border: 1px solid #bbf7d0;
}

.status-pill.warn {
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
}

.toolbar-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-pill {
  height: 30px;
  padding: 0 12px;
  border: 1px solid #dbe4ef;
  border-radius: 999px;
  background: #fff;
  color: #334155;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  font-weight: 850;
  white-space: nowrap;
}

.meta-pill svg {
  width: 14px;
  height: 14px;
  color: #64748b;
}

.meta-pill.time {
  color: #0f172a;
}

/* Filters */
.filter-row {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-row button {
  height: 34px;
  padding: 0 15px;
  border: 1px solid #dbe4ef;
  border-radius: 12px;
  background: #fff;
  color: #475569;
  cursor: pointer;
  font-size: 13px;
  font-weight: 850;
  transition:
      background 0.18s ease,
      color 0.18s ease,
      border-color 0.18s ease,
      transform 0.18s ease;
}

.filter-row button span {
  margin-left: 8px;
  color: #94a3b8;
}

.filter-row button:hover {
  transform: translateY(-1px);
  border-color: #b7c7da;
}

.filter-row button.active {
  background: #0f172a;
  border-color: #0f172a;
  color: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.14);
}

.filter-row button.active span {
  color: rgba(255, 255, 255, 0.72);
}

.partial-notice {
  margin-top: 12px;
  padding: 11px 13px;
  border: 1px solid #fde68a;
  border-radius: 14px;
  background: #fffbeb;
  color: #92400e;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 800;
}

.partial-notice svg {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
}

/* Main */
.resource-content {
  margin-top: 16px;
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.resource-card {
  min-height: 348px;
  border: 1px solid #e1e8f2;
  border-radius: 20px;
  background: #fff;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.045);
  transition:
      transform 0.2s ease,
      box-shadow 0.2s ease,
      border-color 0.2s ease;
}

.resource-card:hover {
  transform: translateY(-4px);
  border-color: #cbd5e1;
  box-shadow: 0 22px 54px rgba(15, 23, 42, 0.1);
}

.resource-card:focus-visible {
  outline: 3px solid rgba(37, 99, 235, 0.25);
  outline-offset: 3px;
}

.card-head {
  padding: 16px 16px 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.card-identity {
  min-width: 0;
  display: flex;
  align-items: flex-start;
  gap: 11px;
}

.type-icon {
  width: 38px;
  height: 38px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: #fff;
  background: #2563eb;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25);
}

.type-icon svg {
  width: 21px;
  height: 21px;
}

.card-title-wrap {
  min-width: 0;
}

.card-title-wrap h2 {
  margin: 0;
  color: #0f172a;
  font-size: 15px;
  line-height: 1.35;
  font-weight: 950;
  letter-spacing: -0.02em;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  overflow: hidden;
}

.card-title-wrap span {
  display: block;
  margin-top: 4px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 900;
}

.format-badge {
  height: 24px;
  padding: 0 9px;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: #f8fafc;
  color: #64748b;
  font-size: 11px;
  font-weight: 900;
  white-space: nowrap;
}

/* Type color */
.type-content .type-icon {
  background: linear-gradient(135deg, #2563eb, #60a5fa);
}

.type-mindmap .type-icon {
  background: linear-gradient(135deg, #7c3aed, #a78bfa);
}

.type-quiz .type-icon {
  background: linear-gradient(135deg, #059669, #34d399);
}

.type-code .type-icon {
  background: linear-gradient(135deg, #0f172a, #334155);
}

.type-reading .type-icon {
  background: linear-gradient(135deg, #d97706, #fb923c);
}

.type-ppt .type-icon {
  background: linear-gradient(135deg, #dc2626, #f87171);
}

.type-cartoon .type-icon,
.type-video .type-icon {
  background: linear-gradient(135deg, #4f46e5, #818cf8);
}

/* Visual */
.resource-visual {
  height: 136px;
  margin: 0 16px;
  position: relative;
  overflow: hidden;
  border: 1px solid #e8eef6;
  border-radius: 16px;
  background:
      linear-gradient(rgba(148, 163, 184, 0.09) 1px, transparent 1px),
      linear-gradient(90deg, rgba(148, 163, 184, 0.09) 1px, transparent 1px),
      linear-gradient(135deg, #ffffff, #f8fafc);
  background-size:
      22px 22px,
      22px 22px,
      auto;
}

.visual {
  position: absolute;
  inset: 0;
}

/* Course */
.course-book {
  position: absolute;
  inset: 24px 42px;
  display: grid;
  grid-template-columns: 58px 1fr;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: #fff;
  overflow: hidden;
  box-shadow: 0 16px 34px rgba(37, 99, 235, 0.12);
}

.book-spine {
  background: linear-gradient(180deg, #2563eb, #60a5fa);
  display: grid;
  place-items: center;
  align-content: center;
  gap: 9px;
}

.book-spine i {
  width: 24px;
  height: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
}

.book-content {
  padding: 20px 22px;
  display: grid;
  align-content: center;
  gap: 10px;
}

.book-content strong,
.book-content span {
  height: 7px;
  border-radius: 999px;
}

.book-content strong {
  width: 46%;
  background: #2563eb;
}

.book-content span {
  background: #dbe7f7;
}

.book-content span:nth-child(2) {
  width: 92%;
}

.book-content span:nth-child(3) {
  width: 78%;
}

.book-content span:nth-child(4) {
  width: 62%;
}

/* Map */
.visual-map {
  background: radial-gradient(circle at 50% 50%, rgba(124, 58, 237, 0.08), transparent 60%);
}

.map-center {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 74px;
  height: 42px;
  transform: translate(-50%, -50%);
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #7c3aed, #a78bfa);
  color: #fff;
  box-shadow: 0 18px 36px rgba(124, 58, 237, 0.2);
  z-index: 2;
}

.map-center svg {
  width: 23px;
  height: 23px;
}

.map-node {
  position: absolute;
  width: 58px;
  height: 24px;
  border: 2px solid #c4b5fd;
  border-radius: 999px;
  background: #fff;
  z-index: 2;
}

.map-node::after {
  content: "";
  position: absolute;
  left: 14px;
  top: 9px;
  width: 30px;
  height: 5px;
  border-radius: 999px;
  background: #ddd6fe;
}

.map-node.n1 {
  left: 15%;
  top: 24%;
}

.map-node.n2 {
  right: 15%;
  top: 24%;
}

.map-node.n3 {
  left: 16%;
  bottom: 22%;
}

.map-node.n4 {
  right: 16%;
  bottom: 22%;
}

.map-branch {
  position: absolute;
  height: 2px;
  background: #b894f6;
  transform-origin: left center;
  z-index: 1;
}

.map-branch.b1 {
  width: 94px;
  left: 31%;
  top: 43%;
  transform: rotate(25deg);
}

.map-branch.b2 {
  width: 96px;
  left: 53%;
  top: 44%;
  transform: rotate(-25deg);
}

.map-branch.b3 {
  width: 90px;
  left: 31%;
  top: 58%;
  transform: rotate(-24deg);
}

.map-branch.b4 {
  width: 92px;
  left: 53%;
  top: 57%;
  transform: rotate(24deg);
}

/* Quiz */
.quiz-paper {
  position: absolute;
  inset: 18px 34px;
  display: grid;
  gap: 8px;
}

.question-row,
.answer-row {
  display: flex;
  align-items: center;
  gap: 9px;
}

.question-row b {
  height: 19px;
  padding: 0 10px;
  border-radius: 999px;
  background: #10b981;
  color: #fff;
  display: inline-flex;
  align-items: center;
  font-size: 10px;
}

.question-row span {
  height: 7px;
  flex: 1;
  border-radius: 999px;
  background: #94a3b8;
}

.answer-row {
  height: 20px;
  padding: 0 9px;
  border: 1px solid #dce7f2;
  border-radius: 999px;
  background: #fff;
}

.answer-row em {
  width: 16px;
  height: 16px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: #dcfce7;
  color: #059669;
  font-size: 10px;
  font-style: normal;
  font-weight: 900;
}

.answer-row span {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: #e2e8f0;
}

.answer-row.right {
  border-color: #bbf7d0;
}

.answer-row.right span {
  background: #a7f3d0;
}

.answer-row svg {
  width: 14px;
  height: 14px;
  color: #059669;
}

/* Code */
.code-window {
  position: absolute;
  inset: 18px 30px;
  border-radius: 16px;
  overflow: hidden;
  background: #111827;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.2);
}

.code-top {
  height: 24px;
  padding-left: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  background: #1f2937;
}

.code-top i {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #64748b;
}

.code-main {
  display: grid;
  grid-template-columns: 36px 1fr;
}

.line-nums {
  padding-top: 11px;
  display: grid;
  gap: 7px;
  justify-items: center;
  color: #64748b;
  font-size: 10px;
  font-weight: 800;
}

.code-lines {
  padding: 14px 18px 0;
  display: grid;
  gap: 8px;
}

.code-lines i {
  height: 6px;
  border-radius: 999px;
  background: #64748b;
}

.code-lines i:nth-child(1) {
  width: 42%;
  background: #c084fc;
}

.code-lines i:nth-child(2) {
  width: 70%;
  background: #60a5fa;
}

.code-lines i:nth-child(3) {
  width: 56%;
  background: #a7f3d0;
}

.code-lines i:nth-child(4) {
  width: 82%;
  background: #f9a8d4;
}

.code-lines i:nth-child(5) {
  width: 50%;
  background: #fde68a;
}

/* Reading */
.open-book {
  position: absolute;
  inset: 20px 38px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  transform: perspective(500px) rotateX(5deg);
}

.page {
  padding: 17px;
  background: #fff;
  border: 1px solid #fed7aa;
  box-shadow: 0 16px 34px rgba(217, 119, 6, 0.1);
}

.page.left {
  border-radius: 16px 6px 6px 16px;
}

.page.right {
  border-radius: 6px 16px 16px 6px;
}

.page span {
  display: block;
  height: 6px;
  margin-bottom: 9px;
  border-radius: 999px;
  background: #e2e8f0;
}

.page span:nth-child(1) {
  width: 78%;
}

.page span:nth-child(2) {
  width: 92%;
}

.page span:nth-child(3) {
  width: 86%;
}

.page span:nth-child(4) {
  width: 60%;
}

.mini-chart {
  height: 34px;
  margin-top: 8px;
  display: flex;
  align-items: end;
  gap: 8px;
}

.mini-chart i {
  width: 17px;
  border-radius: 5px 5px 0 0;
  background: #fb923c;
}

.mini-chart i:nth-child(1) {
  height: 14px;
}

.mini-chart i:nth-child(2) {
  height: 23px;
}

.mini-chart i:nth-child(3) {
  height: 32px;
}

/* PPT */
.slide-main,
.slide-thumb {
  position: absolute;
  border: 1px solid #fecaca;
  border-radius: 13px;
  background: #fff;
  box-shadow: 0 16px 34px rgba(220, 38, 38, 0.1);
}

.slide-main {
  inset: 24px 74px;
  padding: 16px;
  display: grid;
  align-content: center;
  justify-items: start;
  gap: 8px;
}

.slide-main svg {
  width: 22px;
  height: 22px;
  color: #dc2626;
}

.slide-main strong,
.slide-main span {
  height: 7px;
  border-radius: 999px;
}

.slide-main strong {
  width: 58%;
  background: #dc2626;
}

.slide-main span {
  background: #fee2e2;
}

.slide-main span:nth-child(3) {
  width: 82%;
}

.slide-main span:nth-child(4) {
  width: 64%;
}

.slide-thumb {
  width: 52px;
  height: 38px;
  opacity: 0.85;
}

.slide-thumb.t1 {
  left: 28px;
  top: 26px;
}

.slide-thumb.t2 {
  right: 28px;
  bottom: 26px;
}

/* Video */
.video-screen {
  position: absolute;
  inset: 24px 52px 48px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #111827, #334155);
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.18);
}

.video-screen svg {
  width: 38px;
  height: 38px;
  color: #fff;
}

.video-track {
  position: absolute;
  left: 52px;
  right: 52px;
  bottom: 26px;
  display: grid;
  grid-template-columns: 1.4fr 0.8fr 1fr;
  gap: 8px;
}

.video-track span {
  height: 7px;
  border-radius: 999px;
  background: #c7d2fe;
}

/* Card body */
.card-body {
  flex: 1;
  padding: 12px 16px 0;
}

.card-body p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.65;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.tag-row {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-row span {
  height: 22px;
  padding: 0 9px;
  border: 1px solid #dbe4ef;
  border-radius: 999px;
  background: #f8fafc;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  font-weight: 800;
}

.card-footer {
  min-height: 45px;
  margin-top: 12px;
  padding: 0 16px;
  border-top: 1px solid #edf2f7;
  color: #2563eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 900;
}

.card-footer svg {
  width: 17px;
  height: 17px;
  transition: transform 0.18s ease;
}

.resource-card:hover .card-footer svg {
  transform: translateX(3px);
}

/* Empty */
.empty-state {
  min-height: 360px;
  border: 1px dashed #cbd5e1;
  border-radius: 20px;
  background: #fff;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  text-align: center;
}

.empty-icon {
  width: 42px;
  height: 42px;
  color: #94a3b8;
}

.empty-state h2 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
  font-weight: 950;
}

.empty-state p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.empty-state button {
  height: 34px;
  padding: 0 16px;
  border: 1px solid #dbe4ef;
  border-radius: 999px;
  background: #fff;
  color: #334155;
  cursor: pointer;
  font-size: 13px;
  font-weight: 900;
}

/* Error */
.error-state {
  min-height: 520px;
  display: grid;
  place-items: center;
}

.error-card {
  width: min(460px, 100%);
  padding: 44px 36px;
  border: 1px solid #e1e8f2;
  border-radius: 24px;
  background: #fff;
  text-align: center;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.error-icon {
  width: 42px;
  height: 42px;
  color: #f59e0b;
}

.error-card h2 {
  margin: 12px 0 0;
  font-size: 18px;
  font-weight: 950;
}

.error-card p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.7;
}

.error-actions {
  margin-top: 22px;
  display: flex;
  justify-content: center;
  gap: 10px;
}

.btn-primary,
.btn-ghost {
  height: 36px;
  padding: 0 18px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 900;
}

.btn-primary {
  border: none;
  background: #2563eb;
  color: #fff;
}

.btn-ghost {
  border: 1px solid #dbe4ef;
  background: #fff;
  color: #475569;
}

/* Loading */
.loading-state {
  display: grid;
  gap: 16px;
}

.loading-toolbar {
  height: 54px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e4eaf3;
  display: flex;
  align-items: center;
  gap: 12px;
}

.loading-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.loading-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.loading-card {
  height: 348px;
  padding: 16px;
  border: 1px solid #e1e8f2;
  border-radius: 20px;
  background: #fff;
}

.sk {
  border-radius: 999px;
  background: linear-gradient(90deg, #eef2f7 25%, #e2e8f0 50%, #eef2f7 75%);
  background-size: 400% 100%;
  animation: shimmer 1.35s ease infinite;
}

.sk-back {
  width: 74px;
  height: 32px;
}

.sk-title {
  width: 132px;
  height: 24px;
}

.sk-pill {
  width: 82px;
  height: 24px;
}

.sk-meta {
  width: 158px;
  height: 30px;
}

.sk-filter {
  width: 112px;
  height: 34px;
  border-radius: 12px;
}

.sk-card-head {
  width: 74%;
  height: 20px;
  margin-bottom: 14px;
}

.sk-card-preview {
  height: 136px;
  border-radius: 16px;
  margin-bottom: 16px;
}

.sk-line {
  height: 12px;
  width: 72%;
  margin-bottom: 10px;
}

.sk-line.long {
  width: 100%;
}

.sk-footer {
  width: 120px;
  height: 14px;
  margin-top: 28px;
}

@keyframes shimmer {
  0% {
    background-position: 100% 50%;
  }

  100% {
    background-position: 0% 50%;
  }
}

/* Responsive */
@media (max-width: 1180px) {
  .resource-grid,
  .loading-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .result-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar-right {
    justify-content: flex-start;
  }
}

@media (max-width: 760px) {
  .resource-result-page {
    padding: 12px 14px 28px;
  }

  .toolbar-left {
    width: 100%;
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }

  .title-block p {
    max-width: 100%;
  }

  .filter-row {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding-bottom: 4px;
  }

  .filter-row button {
    flex: 0 0 auto;
  }

  .resource-grid,
  .loading-grid {
    grid-template-columns: 1fr;
  }
}
</style>