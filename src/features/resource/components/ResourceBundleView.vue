<template>
  <div class="resource-bundle-view">
    <header class="result-header">
      <div class="result-heading">
        <span class="result-complete-mark" :class="{ warning }">
          <el-icon aria-hidden="true">
            <component :is="warning ? WarningFilled : CircleCheckFilled" />
          </el-icon>
        </span>
        <div>
          <h1>{{ bundleTitle }}</h1>
          <p>{{ learningNeedText || `已生成 ${resourceCards.length} 项学习资源，可直接打开查看。` }}</p>
          <small v-if="contextLabel && contextValue">{{ contextLabel }} · {{ contextValue }}</small>
        </div>
      </div>

      <div class="result-header-actions">
        <span><strong>{{ resourceCards.length }}</strong> 项资源</span>
        <button v-if="actionLabel" type="button" class="bundle-action-button" @click="emit('action')">
          <el-icon aria-hidden="true">
            <ArrowLeft v-if="actionKind === 'back'" />
            <RefreshLeft v-else />
          </el-icon>
          {{ actionLabel }}
        </button>
      </div>
    </header>

    <div v-if="warning" class="partial-result-notice" role="status">
      <el-icon aria-hidden="true"><WarningFilled /></el-icon>
      <span>{{ warning }}</span>
      <em>已完成资源仍可正常使用</em>
    </div>

    <nav class="resource-filter-bar" aria-label="资源类型筛选">
      <div>
        <strong>学习资源</strong>
        <span>{{ filteredResourceCards.length }} 项</span>
      </div>

      <div v-if="resourceCards.length > 1" class="resource-filters">
        <button
          type="button"
          :class="{ active: activeFilter === 'all' }"
          @click="activeFilter = 'all'"
        >
          全部
        </button>
        <button
          v-for="filter in availableFilters"
          :key="filter.type"
          type="button"
          :class="{ active: activeFilter === filter.type }"
          @click="activeFilter = filter.type"
        >
          {{ filter.label }} <span>{{ filter.count }}</span>
        </button>
      </div>
    </nav>

    <main class="resources-gallery">
      <div v-if="filteredResourceCards.length" class="resource-card-grid">
        <article
          v-for="card in filteredResourceCards"
          :key="card.id"
          class="resource-result-card"
          tabindex="0"
          role="button"
          :aria-label="`打开${card.title}`"
          @click="openPreview(card)"
          @keydown.enter.prevent="openPreview(card)"
          @keydown.space.prevent="openPreview(card)"
        >
          <div class="resource-card-cover">
            <img :src="getResourceCover(card.type)" alt="" loading="lazy" />
            <span class="resource-type-label">
              {{ getResourceIcon(card.type) }} {{ getResourceTypeLabel(card.type) }}
            </span>
            <span class="resource-format-label">{{ card.format }}</span>
          </div>

          <div class="resource-card-content">
            <div class="resource-card-status"><i></i> 已就绪</div>
            <h2>{{ card.title }}</h2>
            <p>{{ card.summary || getDefaultSummary(card.type) }}</p>

            <div class="resource-card-meta">
              <span v-if="card.estimatedLabel">{{ card.estimatedLabel }}</span>
              <span v-for="tag in getResourceHighlights(card)" :key="`${card.id}-${tag}`">{{ tag }}</span>
            </div>
          </div>

          <footer class="resource-card-footer">
            <span>查看完整内容</span>
            <button type="button" :aria-label="`打开${card.title}`" @click.stop="openPreview(card)">
              <el-icon aria-hidden="true"><ArrowRight /></el-icon>
            </button>
          </footer>
        </article>
      </div>

      <div v-else class="empty-result-state">
        <el-icon aria-hidden="true"><WarningFilled /></el-icon>
        <h2>当前分类暂无资源</h2>
        <p>选择其他类型，或返回查看全部生成结果。</p>
        <button type="button" @click="activeFilter = 'all'">查看全部</button>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  ref,
} from 'vue'

import {
  ArrowLeft,
  ArrowRight,
  CircleCheckFilled,
  RefreshLeft,
  WarningFilled,
} from '@element-plus/icons-vue'

import contentCover from '@/features/resource/assets/result-covers/online-learning.svg'
import mindmapCover from '@/features/resource/assets/result-covers/visual-explanation.svg'
import quizCover from '@/features/resource/assets/result-covers/exam-prep.svg'
import codeCover from '@/features/resource/assets/result-covers/web-developer.svg'
import readingCover from '@/features/resource/assets/result-covers/open-book.svg'
import pptCover from '@/features/resource/assets/result-covers/presentation.svg'
import videoCover from '@/features/resource/assets/result-covers/video-tutorial.svg'

import {
  getDifficultyLabel,
  getResourceTypeLabel,
} from '@/features/resource/model/ResourceGeneratorConstants'

import {
  parsePptDocument,
} from '@/features/resource/components/ppt-engine/types/ppt'

type GeneratedResourceItem = Record<string, any> & {
  generatedAt?: string
  displayOrder?: number
}

type ResourceCard = GeneratedResourceItem & {
  id: string
  type: string
  title: string
  summary: string
  format: string
  status: 'completed'
  estimatedMinutes: number | null
  estimatedLabel: string
  metadata: Record<string, any>
  metrics: Record<string, any>
}

const props = withDefaults(defineProps<{
  bundle: any | null
  warning?: string
  actionLabel?: string
  actionKind?: 'back' | 'reset'
  contextLabel?: string
  contextValue?: string
}>(), {
  warning: '',
  actionLabel: '',
  actionKind: 'reset',
  contextLabel: '',
  contextValue: '',
})

const {
  warning,
  actionLabel,
  actionKind,
  contextLabel,
  contextValue,
} = props

const emit = defineEmits<{
  action: []
  preview: [
    data: {
      agentId: string
      resultData: any
      title: string
    },
  ]
}>()

const RESOURCE_ORDER = [
  'content',
  'mindmap',
  'quiz',
  'code',
  'reading',
  'ppt',
  'video',
]

const RESOURCE_TYPES = new Set(RESOURCE_ORDER)

const RESOURCE_COVERS: Record<string, string> = {
  content: contentCover,
  mindmap: mindmapCover,
  quiz: quizCover,
  code: codeCover,
  reading: readingCover,
  ppt: pptCover,
  video: videoCover,
}

const activeFilter = ref('all')

const rawResources = computed<GeneratedResourceItem[]>(() => {
  const resources =
      props.bundle?.resources ??
      props.bundle?.items

  return Array.isArray(resources)
      ? resources
      : []
})

const resourceCards = computed<ResourceCard[]>(() => {
  return rawResources.value
      .map((resource, index) =>
          normalizeResource(resource, index),
      )
      .filter(
          (resource): resource is ResourceCard =>
              resource !== null,
      )
      .sort((a, b) => {
        const orderA = RESOURCE_ORDER.indexOf(a.type)
        const orderB = RESOURCE_ORDER.indexOf(b.type)

        if (orderA !== orderB) {
          return (
              (orderA === -1 ? 99 : orderA) -
              (orderB === -1 ? 99 : orderB)
          )
        }

        return (
            Number(a.displayOrder || 0) -
            Number(b.displayOrder || 0)
        )
      })
})

const filteredResourceCards = computed(() => {
  if (activeFilter.value === 'all') {
    return resourceCards.value
  }

  return resourceCards.value.filter(
      card => card.type === activeFilter.value,
  )
})

const availableFilters = computed(() => {
  return RESOURCE_ORDER
      .map(type => ({
        type,
        label: getResourceTypeLabel(type),
        count: resourceCards.value.filter(
            card => card.type === type,
        ).length,
      }))
      .filter(item => item.count > 0)
})

const bundleTitle = computed(() => {
  return String(
      props.bundle?.title ||
      props.bundle?.name ||
      '个性化学习资源包',
  )
})

const learningNeedText = computed(() => {
  return String(
      props.bundle?.learning_need ||
      props.bundle?.learningNeed ||
      '',
  ).trim()
})

function normalizeResource(
    resource: GeneratedResourceItem,
    index: number,
): ResourceCard | null {
  const type = normalizeType(
      resource.type ||
      resource.agent_type ||
      resource.agentId,
  )

  const rawStatus = String(
      resource.status || 'completed',
  ).toLowerCase()

  if (
      !RESOURCE_TYPES.has(type) ||
      ![
        'finished',
        'completed',
        'success',
      ].includes(rawStatus)
  ) {
    console.warn(
        '[ResourceResult] 忽略不可展示资源',
        {
          index,
          resourceId: resource.id,
          type,
          status: resource.status,
        },
    )

    return null
  }

  if (!hasContent(resource.content)) {
    console.warn(
        '[ResourceResult] 忽略空资源',
        {
          index,
          resourceId: resource.id,
          type,
        },
    )

    return null
  }

  if (type === 'ppt') {
    const parsed = parsePptDocument(
        resource.content,
    )

    if (!parsed.ok) {
      console.warn(
          '[ResourceResult] 忽略无效 PPT 资源',
          {
            resourceId: resource.id,
            reason: parsed.reason,
          },
      )

      return null
    }
  }

  const metadata = isPlainObject(resource.metadata)
      ? resource.metadata
      : {}

  const metrics = isPlainObject(resource.metrics)
      ? resource.metrics
      : {}

  const title = getResourceTitle(resource, type)
  const format = getResourceFormat(resource, type)

  const estimatedMinutes = getEstimatedMinutes(
      metadata,
      metrics,
  )

  return {
    ...resource,
    id: String(
        resource.id ??
        `${type}-${index}`,
    ),
    type,
    title,
    summary: getResourceSummary(resource, type),
    format,
    status: 'completed',
    estimatedMinutes,
    estimatedLabel: estimatedMinutes
        ? `${estimatedMinutes} 分钟`
        : '',
    metadata,
    metrics,
  }
}

function normalizeType(type: unknown) {
  return typeof type === 'string'
      ? type.trim().toLowerCase()
      : ''
}

function getResourceTitle(
    resource: GeneratedResourceItem,
    type: string,
) {
  const title =
      typeof resource.title === 'string'
          ? resource.title.trim()
          : ''

  if (title) {
    return title
  }

  return `${getResourceTypeLabel(type)} · ${bundleTitle.value}`
}

function getResourceSummary(
    resource: GeneratedResourceItem,
    type: string,
) {
  const candidates = [
    resource.summary,
    resource.description,
    resource.metadata?.summary,
  ]

  const summary = candidates.find(
      value =>
          typeof value === 'string' &&
          value.trim(),
  )

  return typeof summary === 'string'
      ? summary.trim()
      : getDefaultSummary(type)
}

function getResourceFormat(
    resource: GeneratedResourceItem,
    type: string,
) {
  const raw =
      resource.format ||
      resource.file_type ||
      resource.fileType

  if (
      typeof raw === 'string' &&
      raw.trim()
  ) {
    return raw.trim().toUpperCase()
  }

  const fallback: Record<string, string> = {
    content: 'MARKDOWN',
    mindmap: 'MARKMAP',
    quiz: 'JSON',
    code: 'CODE',
    reading: 'LINKS',
    ppt: 'SLIDES',
    video: 'VIDEO',
  }

  return fallback[type] || 'RESOURCE'
}

function getEstimatedMinutes(
    metadata: Record<string, any>,
    metrics: Record<string, any>,
) {
  const raw =
      metadata.estimated_minutes ??
      metadata.estimated_time ??
      metrics.estimated_minutes ??
      metrics.estimated_time

  if (
      typeof raw === 'number' &&
      raw > 0
  ) {
    return Math.round(raw)
  }

  const parsed = Number(
      String(raw || '').match(/\d+/)?.[0],
  )

  return Number.isFinite(parsed) &&
  parsed > 0
      ? parsed
      : null
}

function openPreview(card: ResourceCard) {
  emit('preview', {
    agentId: card.type,
    resultData: card.content,
    title: card.title,
  })
}

function getResourceCover(type: string) {
  return RESOURCE_COVERS[type] || contentCover
}

function getResourceIcon(type: string) {
  const icons: Record<string, string> = {
    content: '📘',
    mindmap: '🧠',
    quiz: '✅',
    code: '💻',
    reading: '📚',
    ppt: '📊',
    video: '🎬',
  }

  return icons[type] || '✨'
}

function getDefaultSummary(type: string) {
  const map: Record<string, string> = {
    content:
        '围绕本次学习目标组织的系统讲解，帮助建立完整知识框架。',
    mindmap:
        '将核心概念、关系和层级整理为可视化知识结构。',
    quiz:
        '通过不同题型检查理解程度，并用于学习后的即时巩固。',
    code:
        '提供可阅读、可实践的代码案例，帮助将概念转化为操作能力。',
    reading:
        '补充可靠的课程资料与延伸阅读，便于继续深入学习。',
    ppt:
        '整合基础资源形成结构化教学课件，适合快速复习和演示。',
    video:
        '以分镜和讲解节奏组织知识内容，适合视听化学习。',
  }

  return (
      map[type] ||
      '根据本次学习需求生成的个性化学习资源。'
  )
}

function getResourceHighlights(card: ResourceCard) {
  const candidates = [
    card.metrics.question_count
        ? `${card.metrics.question_count} 道题`
        : '',

    card.metrics.node_count
        ? `${card.metrics.node_count} 个节点`
        : '',

    card.metrics.page_count
        ? `${card.metrics.page_count} 页`
        : '',

    card.metrics.slide_count
        ? `${card.metrics.slide_count} 页课件`
        : '',

    card.metrics.scene_count
        ? `${card.metrics.scene_count} 个场景`
        : '',

    card.metrics.resource_count
        ? `${card.metrics.resource_count} 条资料`
        : '',

    card.metrics.language
        ? String(card.metrics.language)
        : '',

    card.metadata.programming_language
        ? String(card.metadata.programming_language)
        : '',

    card.metadata.difficulty
        ? getDifficultyLabel(
            card.metadata.difficulty,
        )
        : '',
  ]

  return [
    ...new Set(
        candidates.filter(Boolean),
    ),
  ].slice(0, 3)
}

function hasContent(value: unknown): boolean {
  if (typeof value === 'string') {
    return value.trim().length > 0
  }

  if (Array.isArray(value)) {
    return value.length > 0
  }

  return (
      isPlainObject(value) &&
      Object.keys(value).length > 0
  )
}

function isPlainObject(
    value: unknown,
): value is Record<string, any> {
  return (
      !!value &&
      typeof value === 'object' &&
      !Array.isArray(value)
  )
}
</script>

<style scoped>
/* Result gallery v2: lightweight header, card-first content hierarchy */
.resource-bundle-view {
  --agent-body-font: var(--font-body);

  width: 100%;
  min-height: 100%;
  padding: 24px clamp(18px, 3vw, 42px) 36px;
  overflow-y: auto;
  background: #f5f6f8;
  color: #172033;
  font-family: var(--font-ui);
}

.resource-bundle-view::before {
  display: none;
}

.result-header {
  display: flex;
  max-width: 1280px;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin: 0 auto;
  padding: 0 2px 18px;
  border-bottom: 1px solid #dfe3e8;
}

.result-heading {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12px;
}

.result-complete-mark {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  place-items: center;
  border: 1px solid #b8dcc9;
  border-radius: 10px;
  color: #168357;
  background: #eef9f3;
  font-size: 18px;
}

.result-complete-mark.warning {
  border-color: #ead39d;
  color: #a66a12;
  background: #fff8e8;
}

.result-heading h1 {
  margin: 0;
  overflow: hidden;
  color: #172033;
  font-size: 19px;
  font-weight: 760;
  letter-spacing: -0.02em;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-heading p {
  max-width: 680px;
  margin: 4px 0 0;
  overflow: hidden;
  color: #6b7483;
  font-family: var(--agent-body-font);
  font-size: 11px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-heading small {
  display: block;
  margin-top: 3px;
  color: #98a2b3;
  font-size: 9px;
  line-height: 1.4;
}

.result-header-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 14px;
}

.result-header-actions > span {
  color: #737d8e;
  font-size: 10px;
  white-space: nowrap;
}

.result-header-actions > span strong {
  color: #263246;
  font-size: 14px;
}

.bundle-action-button {
  display: inline-flex;
  height: 34px;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  border: 1px solid #cfd6df;
  border-radius: 8px;
  color: #344054;
  background: #fff;
  font-family: inherit;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.bundle-action-button:hover {
  border-color: #8aa9d6;
  color: #24589d;
  background: #f7faff;
}

.partial-result-notice {
  display: flex;
  max-width: 1280px;
  min-height: 38px;
  align-items: center;
  gap: 8px;
  margin: 12px auto 0;
  padding: 8px 11px;
  border: 1px solid #ead7aa;
  border-radius: 8px;
  color: #79591f;
  background: #fffaf0;
  font-size: 10px;
}

.partial-result-notice > span {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.partial-result-notice em {
  color: #9a7a3c;
  font-size: 9px;
  font-style: normal;
  white-space: nowrap;
}

.resource-filter-bar {
  display: flex;
  max-width: 1280px;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 18px auto 12px;
}

.resource-filter-bar > div:first-child {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.resource-filter-bar > div:first-child strong {
  font-size: 14px;
  font-weight: 760;
}

.resource-filter-bar > div:first-child span {
  color: #8a94a3;
  font-size: 10px;
}

.resource-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  justify-content: flex-end;
}

.resource-filters button {
  height: 28px;
  padding: 0 9px;
  border: 1px solid transparent;
  border-radius: 7px;
  color: #687386;
  background: transparent;
  font-family: inherit;
  font-size: 10px;
  font-weight: 650;
  cursor: pointer;
}

.resource-filters button:hover {
  background: #eceff3;
}

.resource-filters button.active {
  border-color: #cbd9ee;
  color: #24589d;
  background: #edf4ff;
}

.resource-filters button span {
  margin-left: 3px;
  color: #98a2b3;
  font-size: 9px;
}

.resources-gallery {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.resource-card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.resource-result-card {
  display: flex;
  min-width: 0;
  min-height: 350px;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #dfe3e8;
  border-radius: 14px;
  outline: none;
  background: #fff;
  box-shadow: 0 4px 14px rgba(23, 32, 51, 0.04);
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.resource-result-card:hover,
.resource-result-card:focus-visible {
  border-color: #9ab6da;
  box-shadow: 0 10px 24px rgba(23, 32, 51, 0.09);
  transform: translateY(-2px);
}

.resource-result-card:focus-visible {
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.16), 0 10px 24px rgba(23, 32, 51, 0.09);
}

.resource-card-cover {
  position: relative;
  display: grid;
  height: 136px;
  flex: 0 0 136px;
  place-items: center;
  overflow: hidden;
  border-bottom: 1px solid #e5e9ef;
  background: #f3f6fa;
}

.resource-card-cover::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(35, 76, 132, 0.04));
  pointer-events: none;
}

.resource-card-cover img {
  width: 78%;
  height: 110px;
  object-fit: contain;
  object-position: center;
  transition: transform 0.25s ease;
}

.resource-result-card:hover .resource-card-cover img {
  transform: scale(1.025);
}

.resource-type-label,
.resource-format-label {
  position: absolute;
  z-index: 1;
  top: 10px;
  display: inline-flex;
  height: 24px;
  align-items: center;
  border: 1px solid rgba(205, 214, 226, 0.9);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
}

.resource-type-label {
  left: 10px;
  gap: 4px;
  padding: 0 7px;
  color: #344054;
  font-size: 9px;
  font-weight: 750;
}

.resource-format-label {
  right: 10px;
  padding: 0 6px;
  color: #64748b;
  font-size: 8px;
  font-weight: 750;
  letter-spacing: 0.03em;
}

.resource-card-content {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  padding: 13px 14px 12px;
}

.resource-card-status {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #398060;
  font-size: 9px;
  font-weight: 700;
}

.resource-card-status i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #35a06f;
}

.resource-card-content h2 {
  display: -webkit-box;
  margin: 7px 0 0;
  overflow: hidden;
  color: #172033;
  font-size: 14px;
  font-weight: 750;
  letter-spacing: -0.01em;
  line-height: 1.4;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.resource-card-content > p {
  display: -webkit-box;
  margin: 7px 0 0;
  overflow: hidden;
  color: #707a8a;
  font-family: var(--agent-body-font);
  font-size: 10px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.resource-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: auto;
  padding-top: 11px;
}

.resource-card-meta span {
  padding: 3px 6px;
  border: 1px solid #e1e6ed;
  border-radius: 5px;
  color: #667085;
  background: #f8f9fb;
  font-size: 8px;
  font-weight: 650;
}

.resource-card-footer {
  display: flex;
  min-height: 42px;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px 8px 14px;
  border-top: 1px solid #edf0f3;
  color: #596579;
  font-size: 9px;
  font-weight: 700;
}

.resource-card-footer button {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 1px solid #cdd9e9;
  border-radius: 7px;
  color: #2c5f9f;
  background: #f4f8fe;
  cursor: pointer;
}

.resource-card-footer button:hover {
  border-color: #8eacd3;
  background: #eaf2fd;
}

.empty-result-state {
  display: grid;
  min-height: 260px;
  place-items: center;
  align-content: center;
  gap: 8px;
  border: 1px dashed #ccd3dd;
  border-radius: 14px;
  color: #7a8494;
  background: #fff;
  text-align: center;
}

.empty-result-state > .el-icon {
  font-size: 24px;
}

.empty-result-state h2,
.empty-result-state p {
  margin: 0;
}

.empty-result-state h2 {
  color: #344054;
  font-size: 14px;
}

.empty-result-state p {
  font-size: 10px;
}

.empty-result-state button {
  margin-top: 4px;
  padding: 7px 12px;
  border: 1px solid #cbd7e7;
  border-radius: 7px;
  color: #285b9d;
  background: #f5f8fd;
  font-size: 10px;
  cursor: pointer;
}

@media (max-width: 980px) {
  .resource-card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 680px) {
  .resource-bundle-view {
    padding: 16px 12px 24px;
  }

  .result-header,
  .resource-filter-bar {
    align-items: flex-start;
    flex-direction: column;
  }

  .result-heading p {
    white-space: normal;
  }

  .result-header-actions,
  .resource-filters {
    width: 100%;
    justify-content: space-between;
  }

  .resource-filters {
    justify-content: flex-start;
  }

  .partial-result-notice em {
    display: none;
  }

  .resource-card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
