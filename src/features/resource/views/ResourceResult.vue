<template>
  <div class="detail-page">

    <!-- Loading skeleton -->
    <div v-if="loading" class="state-shell">
      <div class="skeleton-grid">
        <div v-for="i in 6" :key="i" class="skeleton-card">
          <div class="sk-cover"></div>
          <div class="sk-body">
            <div class="sk-line w-1/3"></div>
            <div class="sk-line w-3/4"></div>
            <div class="sk-line w-full"></div>
            <div class="sk-line w-2/3"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="state-shell state-error">
      <div class="error-card">
        <PhWarningCircle class="error-icon" />
        <h2>资源包加载失败</h2>
        <p>请检查网络连接后重试，或返回个人中心。</p>
        <div class="error-actions">
          <button class="btn-outline" @click="goBack">返回个人中心</button>
          <button class="btn-primary" @click="loadResource">重新加载</button>
        </div>
      </div>
    </div>

    <!-- Resource bundle content -->
    <template v-else-if="bundle">

      <!-- Page header -->
      <header class="detail-header">
        <div class="header-inner">
          <button class="back-btn" type="button" @click="goBack" aria-label="返回">
            <PhArrowLeft class="w-4 h-4" />
            <span>返回个人中心</span>
          </button>

          <div class="header-title-row">
            <span class="header-status-badge" :class="isPartial ? 'badge-warn' : 'badge-ok'">
              <PhWarningCircle v-if="isPartial" class="w-3.5 h-3.5" />
              <PhCheckCircle v-else class="w-3.5 h-3.5" />
              {{ isPartial ? '部分完成' : '生成完成' }}
            </span>
            <h1>{{ bundleTitle }}</h1>
            <p v-if="learningNeed">{{ learningNeed }}</p>
          </div>

          <div class="header-meta">
            <span v-if="createdAt">创建于 {{ createdAt }}</span>
            <span>{{ resourceCards.length }} 项资源</span>
          </div>
        </div>

        <div v-if="isPartial" class="partial-notice">
          <PhWarningCircle class="w-4 h-4 shrink-0" />
          <span>部分资源未能完成，以下已生成内容仍可正常查看。</span>
        </div>
      </header>

      <!-- Filter bar -->
      <div class="filter-bar" v-if="resourceCards.length > 1">
        <div class="filter-label">
          <strong>学习资源</strong>
          <span>{{ filteredCards.length }} 项</span>
        </div>
        <div class="filter-pills">
          <button
            type="button"
            :class="{ active: activeFilter === 'all' }"
            @click="activeFilter = 'all'"
          >全部</button>
          <button
            v-for="f in availableFilters"
            :key="f.type"
            type="button"
            :class="{ active: activeFilter === f.type }"
            @click="activeFilter = f.type"
          >{{ f.label }} <span>{{ f.count }}</span></button>
        </div>
      </div>

      <!-- Cards grid -->
      <main class="cards-area">
        <div class="cards-grid" v-if="filteredCards.length">
          <!-- Each resource card — one per agent -->
          <article
            v-for="card in filteredCards"
            :key="card.id"
            class="resource-card"
            tabindex="0"
            role="button"
            :aria-label="`预览 ${card.title}`"
            @click="openPreview(card)"
            @keydown.enter.prevent="openPreview(card)"
            @keydown.space.prevent="openPreview(card)"
          >
            <!-- Cover -->
            <div class="card-cover">
              <img :src="getCoverImage(card.type)" :alt="card.type" loading="lazy" />
              <span class="cover-type-badge">{{ getIcon(card.type) }} {{ getLabel(card.type) }}</span>
              <span class="cover-format-badge">{{ card.format }}</span>
            </div>

            <!-- Body -->
            <div class="card-body">
              <h2 class="card-title">{{ card.title }}</h2>
              <p class="card-summary">{{ card.summary }}</p>
              <div class="card-tags" v-if="card.highlights.length">
                <span v-for="tag in card.highlights" :key="tag">{{ tag }}</span>
              </div>
            </div>

            <!-- Footer -->
            <footer class="card-footer">
              <span>查看完整内容</span>
              <div class="card-footer-btn">
                <PhArrowRight class="w-3.5 h-3.5" />
              </div>
            </footer>
          </article>
        </div>

        <div v-else class="empty-state">
          <PhMagnifyingGlass class="empty-icon" />
          <h2>当前分类暂无资源</h2>
          <p>选择其他类型，或查看全部生成结果。</p>
          <button type="button" @click="activeFilter = 'all'">查看全部</button>
        </div>
      </main>
    </template>

    <!-- Preview Dialog -->
    <PreviewDialog
      v-model:activeAgent="activePreviewAgent"
      :data="previewData"
      :resource="previewResource"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import {
  PhArrowLeft,
  PhArrowRight,
  PhCheckCircle,
  PhWarningCircle,
  PhMagnifyingGlass,
} from '@phosphor-icons/vue'

import PreviewDialog from '@/shared/content/PreviewDialog.vue'
import { getGeneratedResourceDetail } from '@/features/resource/api/history'
import type { GeneratedResourceBundle } from '@/features/resource/api/history'
import { getDifficultyLabel } from '@/features/resource/model/catalog'
import { getArtifactLabel } from '@/shared/content/kind'

import contentCover  from '@/features/resource/assets/result-covers/online-learning.svg'
import mindmapCover  from '@/features/resource/assets/result-covers/visual-explanation.svg'
import quizCover     from '@/features/resource/assets/result-covers/exam-prep.svg'
import codeCover     from '@/features/resource/assets/result-covers/web-developer.svg'
import readingCover  from '@/features/resource/assets/result-covers/open-book.svg'
import pptCover      from '@/features/resource/assets/result-covers/presentation.svg'
import cartoonCover  from '@/features/resource/assets/result-covers/video-tutorial.svg'
import videoCover    from '@/features/resource/assets/result-covers/video-tutorial.svg'

// ── Types ────────────────────────────────────────────────────────────────────
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

// ── State ────────────────────────────────────────────────────────────────────
const route  = useRoute()
const router = useRouter()

const loading  = ref(true)
const error    = ref(false)
const bundle   = shallowRef<GeneratedResourceBundle | null>(null)

const activeFilter       = ref('all')
const activePreviewAgent = ref<string | null>(null)
const previewData        = ref<any>(null)
const previewResource    = ref<any>(null)

// ── Load ─────────────────────────────────────────────────────────────────────
const resourceId = computed(() => Number(route.params.id) || null)
onMounted(loadResource)

async function loadResource() {
  if (!resourceId.value) { loading.value = false; error.value = true; return }
  loading.value = true
  error.value = false
  try {
    const res = await getGeneratedResourceDetail(resourceId.value)
    bundle.value = res.data?.data || null
    error.value  = !bundle.value
  } catch (e) {
    console.error('Failed to load resource detail:', e)
    error.value = true
    toast.error('加载资源详情失败')
  } finally {
    loading.value = false
  }
}

// ── Bundle meta ───────────────────────────────────────────────────────────────
const bundleTitle   = computed(() => String(bundle.value?.title || '个性化学习资源包'))
const learningNeed  = computed(() => String(bundle.value?.learning_need || '').trim())
const isPartial     = computed(() => bundle.value?.status === 'partial_completed')
const createdAt     = computed(() => formatTime(bundle.value?.created_at || null))

// ── Resource card normalization ───────────────────────────────────────────────
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
      return ((oa === -1 ? 99 : oa) - (ob === -1 ? 99 : ob))
    })
)

const filteredCards = computed(() =>
  activeFilter.value === 'all'
    ? resourceCards.value
    : resourceCards.value.filter(c => c.type === activeFilter.value)
)

const availableFilters = computed(() =>
  RESOURCE_ORDER
    .map(type => ({ type, label: getArtifactLabel(type), count: resourceCards.value.filter(c => c.type === type).length }))
    .filter(f => f.count > 0)
)

function normalizeCard(r: any): ResourceCard | null {
  const type   = String(r.type || r.agent_type || r.agentId || '').trim().toLowerCase()
  const status = String(r.status || 'completed').toLowerCase()
  if (!RESOURCE_TYPES.has(type))                                       return null
  if (!['finished', 'completed', 'success'].includes(status))         return null
  if (!hasContent(r.content, type))                                    return null

  const metadata = isPlainObj(r.metadata_json) ? r.metadata_json : isPlainObj(r.metadata) ? r.metadata : {}
  const metrics  = isPlainObj(r.metrics) ? r.metrics : {}

  return {
    id:         String(r.id ?? type),
    type,
    title:      getTitle(r, type),
    summary:    getSummary(r, type),
    format:     getFormat(r, type),
    highlights: getHighlights(metadata, metrics),
    content:    r.content,
    resource:   r,
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
    content: '围绕本次学习目标组织的系统讲解，帮助建立完整知识框架。',
    mindmap: '将核心概念、关系和层级整理为可视化知识结构。',
    quiz:    '通过不同题型检查理解程度，用于学习后的即时巩固。',
    code:    '提供可阅读、可实践的代码案例，帮助将概念转化为操作能力。',
    reading: '补充可靠的课程资料与延伸阅读，便于继续深入学习。',
    ppt:     '整合基础资源形成结构化教学课件，适合快速复习和演示。',
    cartoon: '通过知识图形、同步动画、配音和字幕讲清概念与执行过程。',
    video:   '基于基础资源生成讲解视频，以场景叙事方式呈现核心知识。',
  })[type] ?? '根据本次学习需求生成的个性化学习资源。'
}

function getFormat(r: any, type: string) {
  const raw = r.format || r.file_type || r.fileType
  if (typeof raw === 'string' && raw.trim()) return raw.trim().toUpperCase()
  return ({ content: 'MARKDOWN', mindmap: 'MARKMAP', quiz: 'JSON', code: 'CODE', reading: 'LINKS', ppt: 'SLIDES', cartoon: 'MP4', video: 'MP4' })[type] ?? 'RESOURCE'
}

function getHighlights(metadata: any, metrics: any): string[] {
  const candidates = [
    metrics.question_count   ? `${metrics.question_count} 道题`   : '',
    metrics.node_count       ? `${metrics.node_count} 个节点`     : '',
    metrics.slide_count      ? `${metrics.slide_count} 页课件`    : '',
    metrics.resource_count   ? `${metrics.resource_count} 条资料` : '',
    metrics.language         ? String(metrics.language)           : '',
    metadata.programming_language ? String(metadata.programming_language) : '',
    metadata.difficulty      ? getDifficultyLabel(metadata.difficulty)   : '',
  ]
  return [...new Set(candidates.filter(Boolean))].slice(0, 3)
}

function hasContent(value: unknown, type?: string) {
  if (type === 'ppt' || type === 'cartoon') return true
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value))     return value.length > 0
  return isPlainObj(value) && Object.keys(value).length > 0
}

function isPlainObj(v: unknown): v is Record<string, any> {
  return !!v && typeof v === 'object' && !Array.isArray(v)
}

// ── Cover / icon / label helpers ──────────────────────────────────────────────
const coverMap: Record<string, string> = {
  content: contentCover, mindmap: mindmapCover, quiz: quizCover,
  code: codeCover, reading: readingCover, ppt: pptCover, cartoon: cartoonCover, video: videoCover,
}
function getCoverImage(type: string) { return coverMap[type] ?? contentCover }
function getIcon(type: string) {
  return ({ content: '📘', mindmap: '🧠', quiz: '✅', code: '💻', reading: '📚', ppt: '📊', cartoon: '🎬', video: '🎥' })[type] ?? '✨'
}
function getLabel(type: string) { return getArtifactLabel(type) }

// ── Preview ───────────────────────────────────────────────────────────────────
function openPreview(card: ResourceCard) {
  activePreviewAgent.value = card.type
  previewData.value        = card.content
  previewResource.value    = card.resource
}

// ── Navigation ────────────────────────────────────────────────────────────────
function goBack() { router.push({ name: 'Profile' }) }

function formatTime(time: string | null) {
  if (!time) return ''
  const d = new Date(time)
  if (isNaN(d.getTime())) return ''
  return new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(d)
}
</script>

<style scoped>
/* ── Page shell ───────────────────────────────────────── */
.detail-page {
  width: 100%;
  min-height: 100%;
  background: #f4f7fb;
  font-family: var(--font-ui, system-ui);
}

/* ── State shells ─────────────────────────────────────── */
.state-shell {
  width: min(1180px, calc(100% - 48px));
  margin: 0 auto;
  padding: 48px 0;
}

.state-error {
  display: grid;
  min-height: 70vh;
  place-items: center;
}

.error-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 56px 40px;
  background: #fff;
  border: 1px solid #e1e6ec;
  border-radius: 20px;
  max-width: 480px;
  text-align: center;
  box-shadow: 0 4px 24px rgba(16, 24, 40, 0.06);
}

.error-icon { width: 40px; height: 40px; color: #f59e0b; }

.error-card h2 { margin: 0; font-size: 18px; font-weight: 760; color: #0f172a; }
.error-card p  { margin: 0; font-size: 13px; color: #64748b; }

.error-actions { display: flex; gap: 10px; margin-top: 4px; }

.btn-outline {
  padding: 9px 20px; border: 1.5px solid #cbd5e1; border-radius: 9px;
  background: #fff; color: #475569; font-size: 13px; font-weight: 700; cursor: pointer;
}
.btn-primary {
  padding: 9px 20px; border: none; border-radius: 9px;
  background: var(--color-primary, #6366f1); color: #fff;
  font-size: 13px; font-weight: 700; cursor: pointer;
}

/* ── Skeleton ─────────────────────────────────────────── */
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  padding-top: 60px;
}

.skeleton-card {
  border-radius: 16px;
  overflow: hidden;
  background: #fff;
  border: 1px solid #e8ecf2;
}

.sk-cover {
  width: 100%;
  aspect-ratio: 2 / 1;
  background: linear-gradient(90deg, #f1f5f9 25%, #e8ecf2 50%, #f1f5f9 75%);
  background-size: 400% 100%;
  animation: shimmer 1.4s ease infinite;
}

.sk-body { padding: 18px; display: flex; flex-direction: column; gap: 10px; }

.sk-line {
  height: 13px;
  border-radius: 4px;
  background: linear-gradient(90deg, #f1f5f9 25%, #e8ecf2 50%, #f1f5f9 75%);
  background-size: 400% 100%;
  animation: shimmer 1.4s ease infinite;
}
.w-1\/3 { width: 33%; }
.w-3\/4 { width: 75%; }
.w-full { width: 100%; }
.w-2\/3 { width: 66%; }

@keyframes shimmer {
  0%   { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* ── Header ───────────────────────────────────────────── */
.detail-header {
  background: #fff;
  border-bottom: 1px solid #e8ecf2;
  padding: 0 0 0;
}

.header-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 20px clamp(16px, 3vw, 40px) 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid #e0e5eb;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  width: fit-content;
  transition: border-color 0.18s ease, color 0.18s ease;
}
.back-btn:hover { border-color: #9db5cc; color: #1e293b; }

.header-title-row { display: flex; flex-direction: column; gap: 6px; }

.header-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 800;
  width: fit-content;
  border: 1px solid;
}
.badge-ok   { color: #168357; background: #eef9f3; border-color: #b8dcc9; }
.badge-warn { color: #a66a12; background: #fff8e8; border-color: #ead39d; }

.header-title-row h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.02em;
  line-height: 1.25;
}

.header-title-row p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: #94a3b8;
  font-weight: 600;
}

.partial-notice {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px clamp(16px, 3vw, 40px);
  background: #fffbeb;
  border-top: 1px solid #fde68a;
  color: #92400e;
  font-size: 12px;
  font-weight: 600;
}

/* ── Filter bar ───────────────────────────────────────── */
.filter-bar {
  max-width: 1280px;
  margin: 20px auto 0;
  padding: 0 clamp(16px, 3vw, 40px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-label {
  display: flex;
  align-items: baseline;
  gap: 7px;
}
.filter-label strong { font-size: 14px; font-weight: 760; color: #0f172a; }
.filter-label span   { font-size: 11px; color: #94a3b8; }

.filter-pills { display: flex; flex-wrap: wrap; gap: 5px; }

.filter-pills button {
  height: 30px;
  padding: 0 12px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  border-radius: 999px;
  background: #fff;
  color: #475569;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}
.filter-pills button:hover { background: #f8fafc; border-color: #cbd5e1; }
.filter-pills button.active {
  background: var(--color-primary, #6366f1);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 3px 10px rgba(99, 102, 241, 0.25);
}
.filter-pills button span { margin-left: 3px; font-size: 9px; opacity: 0.75; }

/* ── Cards area ───────────────────────────────────────── */
.cards-area {
  max-width: 1280px;
  margin: 16px auto 0;
  padding: 0 clamp(16px, 3vw, 40px) 48px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}

/* ── Single resource card ─────────────────────────────── */
.resource-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #fff;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.05);
  cursor: pointer;
  transition: transform 0.22s cubic-bezier(0.3, 0.7, 0.1, 1),
              box-shadow 0.22s cubic-bezier(0.3, 0.7, 0.1, 1),
              border-color 0.22s ease;
}

.resource-card:hover {
  transform: translateY(-3px);
  border-color: rgba(15, 23, 42, 0.14);
  box-shadow: 0 10px 28px rgba(16, 24, 40, 0.09);
}

.resource-card:focus-visible {
  outline: 2px solid var(--color-primary, #6366f1);
  outline-offset: 2px;
}

/* Cover */
.card-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 2 / 1;
  background: #f8fafc;
  overflow: hidden;
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.resource-card:hover .card-cover img { transform: scale(1.04); }

.cover-type-badge,
.cover-format-badge {
  position: absolute;
  z-index: 1;
  top: 10px;
  display: inline-flex;
  height: 22px;
  align-items: center;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(12px);
  font-size: 10px;
  font-weight: 700;
}

.cover-type-badge   { left: 10px; gap: 5px; padding: 0 9px; color: #344054; }
.cover-format-badge { right: 10px; padding: 0 8px; color: #64748b; font-size: 9px; letter-spacing: 0.04em; }

/* Body */
.card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 18px 20px;
}

.card-title {
  margin: 0 0 7px;
  font-size: 15px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.01em;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.card-summary {
  margin: 0;
  font-size: 12px;
  color: #475569;
  line-height: 1.65;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: auto;
  padding-top: 14px;
}

.card-tags span {
  padding: 3px 8px;
  border: 1px solid rgba(15, 23, 42, 0.05);
  border-radius: 6px;
  background: #f8fafc;
  color: #475569;
  font-size: 10px;
  font-weight: 600;
}

/* Footer */
.card-footer {
  display: flex;
  min-height: 44px;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px 8px 20px;
  border-top: 1px solid rgba(15, 23, 42, 0.04);
  background: #fafafb;
  border-bottom-left-radius: 16px;
  border-bottom-right-radius: 16px;
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
}

.card-footer-btn {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid #cdd9e9;
  border-radius: 7px;
  background: #f4f8fe;
  color: #2c5f9f;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.resource-card:hover .card-footer-btn {
  background: #eaf2fd;
  border-color: #8eacd3;
}

/* ── Empty state ──────────────────────────────────────── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 60px 24px;
  text-align: center;
}

.empty-icon { width: 40px; height: 40px; color: #cbd5e1; }
.empty-state h2 { margin: 0; font-size: 17px; font-weight: 760; color: #0f172a; }
.empty-state p  { margin: 0; font-size: 13px; color: #64748b; }
.empty-state button {
  margin-top: 4px;
  padding: 8px 20px;
  border: 1.5px solid rgba(15, 23, 42, 0.12);
  border-radius: 999px;
  background: #fff;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

/* ── Responsive ───────────────────────────────────────── */
@media (max-width: 980px) {
  .cards-grid { grid-template-columns: repeat(2, 1fr); }
  .skeleton-grid { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 600px) {
  .cards-grid { grid-template-columns: 1fr; }
  .skeleton-grid { grid-template-columns: 1fr; }
  .filter-bar { flex-direction: column; align-items: flex-start; }
}
</style>
