<template>
  <div class="resource-bundle-view">
    <header class="result-header">
      <div class="result-heading">
        <span class="result-complete-mark" :class="{ warning }">
          <component :is="warning ? WarningFilled : CircleCheckFilled" class='w-4 h-4' />
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
          <ArrowLeft v-if="actionKind === 'back'" aria-hidden="true" />
          <RefreshLeft v-else aria-hidden="true" />
          {{ actionLabel }}
        </button>
      </div>
    </header>

    <div v-if="warning" class="partial-result-notice" role="status">
      <WarningFilled class='w-4 h-4 inline-block align-middle' />
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
        <Card
          v-for="card in filteredResourceCards"
          :key="card.id"
          :type="card.type"
          :title="card.title"
          :summary="card.summary"
          :format="card.format"
          :status="card.status"
          :estimated-label="card.estimatedLabel"
          :highlights="getResourceHighlights(card)"
          :card-data="card"
          @click="openPreview"
        />
      </div>

      <div v-else class="empty-result-state">
        <WarningFilled class='w-4 h-4 inline-block align-middle' />
        <h2>当前分类暂无资源</h2>
        <p>选择其他类型，或返回查看全部生成结果。</p>
        <button type="button" @click="activeFilter = 'all'">查看全部</button>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  PhArrowLeft as ArrowLeft,
  PhCheckCircle as CircleCheckFilled,
  PhArrowCounterClockwise as RefreshLeft,
  PhWarningCircle as WarningFilled
} from '@phosphor-icons/vue'

import Card from './Card.vue'
import { getDifficultyLabel } from '../../model/catalog'
import { getArtifactLabel } from '@/shared/content/kind'

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

const emit = defineEmits<{
  action: []
  preview: [
    data: {
      agentId: string
      resultData: any
      title: string
      resource?: any
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
  'cartoon',
]

const RESOURCE_TYPES = new Set(RESOURCE_ORDER)
const activeFilter = ref('all')

const rawResources = computed<GeneratedResourceItem[]>(() => {
  const resources = props.bundle?.resources ?? props.bundle?.items
  return Array.isArray(resources) ? resources : []
})

const resourceCards = computed<ResourceCard[]>(() => {
  return rawResources.value
    .map((resource, index) => normalizeResource(resource, index))
    .filter((resource): resource is ResourceCard => resource !== null)
    .sort((a, b) => {
      const orderA = RESOURCE_ORDER.indexOf(a.type)
      const orderB = RESOURCE_ORDER.indexOf(b.type)
      if (orderA !== orderB) {
        return ((orderA === -1 ? 99 : orderA) - (orderB === -1 ? 99 : orderB))
      }
      return Number(a.displayOrder || 0) - Number(b.displayOrder || 0)
    })
})

const filteredResourceCards = computed(() => {
  if (activeFilter.value === 'all') return resourceCards.value
  return resourceCards.value.filter(card => card.type === activeFilter.value)
})

const availableFilters = computed(() => {
  return RESOURCE_ORDER
    .map(type => ({
      type,
      label: getArtifactLabel(type),
      count: resourceCards.value.filter(card => card.type === type).length,
    }))
    .filter(item => item.count > 0)
})

const bundleTitle = computed(() => {
  return String(props.bundle?.title || props.bundle?.name || '个性化学习资源包')
})

const learningNeedText = computed(() => {
  return String(props.bundle?.learning_need || props.bundle?.learningNeed || '').trim()
})

function normalizeResource(resource: GeneratedResourceItem, index: number): ResourceCard | null {
  const type = normalizeType(resource.type || resource.agent_type || resource.agentId)
  const rawStatus = String(resource.status || 'completed').toLowerCase()

  if (!RESOURCE_TYPES.has(type) || !['finished', 'completed', 'success'].includes(rawStatus)) {
    console.warn('[ResourceResult] 忽略不可展示资源', { index, resourceId: resource.id, type, status: resource.status })
    return null
  }

  if (!hasContent(resource.content, type)) {
    console.warn('[ResourceResult] 忽略空资源', { index, resourceId: resource.id, type })
    return null
  }

  const metadata = isPlainObject(resource.metadata_json)
    ? resource.metadata_json
    : (isPlainObject(resource.metadata) ? resource.metadata : {})

  const metrics = isPlainObject(resource.metrics) ? resource.metrics : {}
  const title = getResourceTitle(resource, type)
  const format = getResourceFormat(resource, type)
  const estimatedMinutes = getEstimatedMinutes(metadata, metrics)

  return {
    ...resource,
    id: String(resource.id ?? `${type}-${index}`),
    type,
    title,
    summary: getResourceSummary(resource, type),
    format,
    status: 'completed',
    estimatedMinutes,
    estimatedLabel: estimatedMinutes ? `${estimatedMinutes} 分钟` : '',
    metadata,
    metadata_json: metadata,
    metrics,
  }
}

function normalizeType(type: unknown) {
  return typeof type === 'string' ? type.trim().toLowerCase() : ''
}

function getResourceTitle(resource: GeneratedResourceItem, type: string) {
  const title = typeof resource.title === 'string' ? resource.title.trim() : ''
  if (title) return title
  return `${getArtifactLabel(type)} · ${bundleTitle.value}`
}

function getResourceSummary(resource: GeneratedResourceItem, type: string) {
  const candidates = [resource.summary, resource.description, resource.metadata?.summary]
  const summary = candidates.find(value => typeof value === 'string' && value.trim())
  return typeof summary === 'string' ? summary.trim() : getDefaultSummary(type)
}

function getResourceFormat(resource: GeneratedResourceItem, type: string) {
  const raw = resource.format || resource.file_type || resource.fileType
  if (typeof raw === 'string' && raw.trim()) {
    return raw.trim().toUpperCase()
  }
  const fallback: Record<string, string> = {
    content: 'MARKDOWN',
    mindmap: 'MARKMAP',
    quiz: 'JSON',
    code: 'CODE',
    reading: 'LINKS',
    ppt: 'SLIDES',
    cartoon: 'MP4',
  }
  return fallback[type] || 'RESOURCE'
}

function getEstimatedMinutes(metadata: Record<string, any>, metrics: Record<string, any>) {
  const raw = metadata.estimated_minutes ?? metadata.estimated_time ?? metrics.estimated_minutes ?? metrics.estimated_time
  if (typeof raw === 'number' && raw > 0) {
    return Math.round(raw)
  }
  const parsed = Number(String(raw || '').match(/\d+/)?. [0])
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

function openPreview(card: ResourceCard) {
  emit('preview', {
    agentId: card.type,
    resultData: card.content,
    title: card.title,
    resource: card,
  })
}

function getDefaultSummary(type: string) {
  const map: Record<string, string> = {
    content: '围绕本次学习目标组织的系统讲解，帮助建立完整知识框架。',
    mindmap: '将核心概念、关系和层级整理为可视化知识结构。',
    quiz: '通过不同题型检查理解程度，并用于学习后的即时巩固。',
    code: '提供可阅读、可实践的代码案例，帮助将概念转化为操作能力。',
    reading: '补充可靠的课程资料与延伸阅读，便于继续深入学习。',
    ppt: '整合基础资源形成结构化教学课件，适合快速复习和演示。',
    cartoon: '通过知识图形、同步动画、配音和字幕讲清概念与执行过程。',
  }
  return map[type] || '根据本次学习需求生成的个性化学习资源。'
}

function getResourceHighlights(card: ResourceCard) {
  const candidates = [
    card.metrics.question_count ? `${card.metrics.question_count} 道题` : '',
    card.metrics.node_count ? `${card.metrics.node_count} 个节点` : '',
    card.metrics.page_count ? `${card.metrics.page_count} 页` : '',
    card.metrics.slide_count ? `${card.metrics.slide_count} 页课件` : '',
    card.metrics.scene_count ? `${card.metrics.scene_count} 个场景` : '',
    card.metrics.resource_count ? `${card.metrics.resource_count} 条资料` : '',
    card.metrics.language ? String(card.metrics.language) : '',
    card.metadata.programming_language ? String(card.metadata.programming_language) : '',
    card.metadata.difficulty ? getDifficultyLabel(card.metadata.difficulty) : '',
  ]
  return [...new Set(candidates.filter(Boolean))].slice(0, 3)
}

function hasContent(value: unknown, type?: string): boolean {
  if (type === 'ppt' || type === 'cartoon') return true
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.length > 0
  return isPlainObject(value) && Object.keys(value).length > 0
}

function isPlainObject(value: unknown): value is Record<string, any> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}
</script>

<style scoped>
.resource-bundle-view {
  --agent-body-font: var(--font-body);
  width: 100%;
  min-height: 100%;
  padding: 24px clamp(18px, 3vw, 42px) 36px;
  overflow-y: auto;
  background: #f4f7fb;
  color: #172033;
  font-family: var(--font-ui);
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
  border-radius: 8px;
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
  letter-spacing: 0;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-heading p {
  max-width: 680px;
  margin: 4px 0 0;
  overflow: hidden;
  color: #6b7483;
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
  height: 30px;
  padding: 0 12px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 99px;
  color: #475569;
  background: #ffffff;
  font-family: inherit;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
}

.resource-filters button:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #0f172a;
}

.resource-filters button.active {
  border-color: var(--color-primary);
  color: #ffffff;
  background: var(--color-primary);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
}

.resource-filters button span {
  margin-left: 4px;
  color: #94a3b8;
  font-size: 9px;
}

.resource-filters button.active span {
  color: rgba(255, 255, 255, 0.8);
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
  gap: 20px;
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
