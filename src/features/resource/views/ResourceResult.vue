<template>
  <div class="phase-view results-view resource-package-page">
    <header class="package-hero-card">
      <div class="package-hero-title">
        <div class="hero-kicker-row">
          <span class="hero-status-pill" :class="{ warning: !!resultWarning }">
            <el-icon><CircleCheckFilled /></el-icon>
            {{ resultWarning ? '部分完成' : '生成完成' }}
          </span>
          <span class="hero-kicker">RESOURCE PACKAGE</span>
        </div>
        <h1>{{ bundleTitle }}</h1>
        <p>{{ learningNeedText }}</p>
      </div>

      <div class="hero-metric-strip">
        <div class="hero-metric-pill">
          <span>资源</span>
          <strong>{{ resourceCards.length }}</strong>
        </div>
        <div v-if="totalEstimatedMinutes > 0" class="hero-metric-pill">
          <span>预计</span>
          <strong>{{ totalEstimatedMinutes }}min</strong>
        </div>
        <div v-if="studyPathSteps.length" class="hero-metric-pill">
          <span>路径</span>
          <strong>{{ studyPathSteps.length }}步</strong>
        </div>
      </div>

      <div class="hero-side-panel">
        <div class="hero-action-row">
          <el-button v-if="studyPathSteps.length" round type="primary" class="hero-primary-btn" @click="scrollToPath">
            按路径学习
            <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
          <el-button round plain @click="emit('reset')">
            <el-icon><RefreshLeft /></el-icon>
            新建任务
          </el-button>
        </div>
      </div>
    </header>


    <main class="package-result-body">
      <section v-if="studyPathSteps.length" ref="pathSectionRef" class="learning-path-section package-section-card">
        <div class="section-heading-row path-heading">
          <div>
            <span class="section-eyebrow">LEARNING PATH</span>
            <h2>推荐学习顺序</h2>
          </div>
          <span class="section-summary-pill">
            {{ studyPathSteps.length }} 步<span v-if="studyPathEstimatedMinutes"> · {{ studyPathEstimatedMinutes }} 分钟</span>
          </span>
        </div>

        <div class="path-step-track">
          <article
            v-for="step in studyPathSteps"
            :key="`${step.order}-${step.resource_type}-${step.title}`"
            class="path-step-card"
            :class="getResourceToneClass(normalizeType(step.resource_type))"
            @click="openResourceByType(normalizeType(step.resource_type))"
          >
            <div class="path-step-index">{{ step.order }}</div>
            <div class="path-step-main">
              <div class="path-step-topline">
                <span class="path-resource-type">{{ getResourceTypeLabel(normalizeType(step.resource_type)) }}</span>
                <span v-if="step.estimated_time" class="path-time-badge">
                  <el-icon><Clock /></el-icon>
                  {{ step.estimated_time }}min
                </span>
              </div>
              <h3>{{ step.title }}</h3>
              <p v-if="step.reason">{{ step.reason }}</p>
              <div class="path-focus-list" v-if="step.focus_points?.length">
                <span v-for="point in step.focus_points.slice(0, 2)" :key="point">{{ point }}</span>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section class="resource-board-section">
        <div class="section-heading-row board-heading">
          <div>
            <span class="section-eyebrow">RESOURCE CARDS</span>
            <h2>多模态资源卡片</h2>
            <p>{{ heroSummary }}</p>
          </div>
          <div class="board-filter-pills">
            <span>文档</span>
            <span>导图</span>
            <span>题库</span>
            <span>实操</span>
            <span>PPT</span>
          </div>
        </div>

        <div v-if="resourceCards.length" class="resource-card-grid-v2">
          <article
            v-for="card in resourceCards"
            :key="card.id || `${card.type}-${card.title}`"
            class="resource-result-card"
            :class="[getResourceToneClass(card.type), { featured: card.type === primaryCardType }]"
            tabindex="0"
            role="button"
            :aria-label="`预览 ${card.title}`"
            @click="openPreview(card)"
            @keydown.enter.prevent="openPreview(card)"
            @keydown.space.prevent="openPreview(card)"
          >
            <header class="resource-card-header">
              <div class="resource-icon-shell">
                <el-icon><component :is="getAgentMeta(card.type).icon" /></el-icon>
              </div>
              <div class="resource-header-text">
                <span>{{ getResourceTypeLabel(card.type) }}</span>
                <strong>{{ card.format }}</strong>
              </div>
              <span class="resource-status-badge" :class="card.status">
                {{ getStatusLabel(card.status) }}
              </span>
            </header>

            <div
              class="resource-cover"
              :class="`cover-${card.type}`"
              :style="{ backgroundImage: getResourceCoverImage(card.type) }"
            >
              <span class="cover-type-badge">{{ getCardVisualLabel(card.type) }}</span>
            </div>

            <div class="resource-card-body">
              <h3>{{ getShortCardTitle(card) }}</h3>
              <p v-if="card.summary">{{ card.summary }}</p>
            </div>

            <div class="resource-tag-row">
              <span v-for="tag in getResourceHighlights(card)" :key="`${card.id}-${tag}`">
                {{ tag }}
              </span>
            </div>

            <div v-if="card.metadata?.difficulty || card.estimatedMinutes || getResourceHighlights(card).length" class="resource-meta-grid">
              <span v-if="card.metadata?.difficulty">
                <el-icon><Odometer /></el-icon>
                {{ getDifficultyLabel(card.metadata?.difficulty) }}
              </span>
              <span v-if="card.estimatedMinutes">
                <el-icon><Clock /></el-icon>
                {{ card.estimatedLabel }}
              </span>
              <span v-if="getResourceHighlights(card).length">
                {{ getResourceHighlights(card)[0] }}
              </span>
            </div>

            <footer class="resource-card-actions" @click.stop>
              <button class="card-action-button secondary" type="button" @click="openPreview(card)">
                查看内容
              </button>
              <button class="card-action-button primary" type="button" @click="startLearning(card)">
                开始学习
                <el-icon><ArrowRight /></el-icon>
              </button>
            </footer>
          </article>
        </div>

        <div v-else class="empty-resource-board">
          <el-icon><WarningFilled /></el-icon>
          <strong>暂无可展示资源</strong>
          <p>当前任务未返回资源项，可重新生成或查看运行日志定位问题。</p>
          <el-button round type="primary" @click="emit('reset')">重新生成</el-button>
        </div>
      </section>
    </main>
  </div>
</template>


<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  ArrowRight,
  CircleCheckFilled,
  Clock,
  Odometer,
  RefreshLeft,
  WarningFilled,
} from '@element-plus/icons-vue'
import {
  getAgentMeta,
  getResourceTypeLabel,
  getDifficultyLabel,
  getResourceToneClass,
} from '@/features/resource/model/ResourceGeneratorConstants'
import { parsePptDocument } from '@/features/resource/components/ppt-engine/types/ppt'

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
}

type StudyPathStepLike = {
  order: number
  resource_type: string
  title: string
  reason?: string
  estimated_time?: number | null
  focus_points?: string[]
}

const props = defineProps<{
  finalBundle: any | null
  resultWarning: string
}>()

const emit = defineEmits<{
  reset: []
  preview: [data: { agentId: string; resultData: any; title: string }]
}>()

const pathSectionRef = ref<HTMLElement | null>(null)

const RESOURCE_ORDER = ['content', 'mindmap', 'quiz', 'code', 'reading', 'ppt', 'video']
const RESOURCE_TYPES = new Set(RESOURCE_ORDER)

const rawResources = computed<GeneratedResourceItem[]>(() => {
  const resources = props.finalBundle?.resources
  return Array.isArray(resources) ? resources : []
})

const resourceCards = computed<ResourceCard[]>(() => {
  return rawResources.value
    .map((resource, index) => normalizeResource(resource, index))
    .filter((resource): resource is ResourceCard => resource !== null)
    .sort((a, b) => {
      const orderA = RESOURCE_ORDER.indexOf(a.type)
      const orderB = RESOURCE_ORDER.indexOf(b.type)
      return (orderA === -1 ? 99 : orderA) - (orderB === -1 ? 99 : orderB)
    })
})

const primaryCardType = computed(() => {
  const preferred = resourceCards.value.find(item => item.type === 'content')
  return preferred?.type || resourceCards.value[0]?.type || 'content'
})

const bundleTitle = computed(() => props.finalBundle?.title || '个性化学习资源包')

const learningNeedText = computed(() => {
  return String(props.finalBundle?.learning_need || '')
})

const heroSummary = computed(() => {
  const count = resourceCards.value.length
  if (!count) return '本次任务暂未生成可展示资源，建议重新生成或查看任务日志。'
  const types = resourceCards.value.map(item => getResourceTypeLabel(item.type)).filter(Boolean).slice(0, 6).join('、')
  return `已生成 ${count} 类学习资源：${types}。`
})

const totalEstimatedMinutes = computed(() => {
  return resourceCards.value.reduce((sum, card) => sum + (card.estimatedMinutes || 0), 0)
})

const studyPathSteps = computed<StudyPathStepLike[]>(() => {
  const path = props.finalBundle?.study_path
  if (!Array.isArray(path) || !path.length) {
    return []
  }
  return path
    .map((step: any, index: number) => ({
      order: Number(step.order || index + 1),
      resource_type: normalizeType(step.resource_type),
      title: String(step.title || ''),
      reason: step.reason || '',
      estimated_time: typeof step.estimated_time === 'number' ? step.estimated_time : null,
      focus_points: Array.isArray(step.focus_points) ? step.focus_points.map(String) : [],
    }))
    .filter(step => RESOURCE_TYPES.has(step.resource_type) && step.title.trim().length > 0)
    .sort((a, b) => a.order - b.order)
})

const studyPathEstimatedMinutes = computed(() => {
  return studyPathSteps.value.reduce((sum, step) => sum + (step.estimated_time || 0), 0)
})

function normalizeResource(resource: GeneratedResourceItem, index: number): ResourceCard | null {
  const type = normalizeType(resource.type)
  const rawStatus = String(resource.status || '').toLowerCase()
  if (!RESOURCE_TYPES.has(type) || !['finished', 'completed'].includes(rawStatus)) {
    console.error('Invalid persisted resource artifact omitted', {
      index,
      resourceId: resource.id,
      type: resource.type,
      status: resource.status,
    })
    return null
  }
  if (!hasContent(resource.content)) {
    console.error('Empty persisted resource artifact omitted', { index, resourceId: resource.id, type })
    return null
  }
  if (type === 'ppt') {
    const parsed = parsePptDocument(resource.content)
    if (!parsed.ok) {
      console.error('Invalid persisted PPT artifact omitted', {
        resourceId: resource.id,
        reason: parsed.reason,
        details: parsed.details,
      })
      return null
    }
  }
  if (resource.id == null || typeof resource.title !== 'string' || !resource.title.trim() || typeof resource.format !== 'string' || !resource.format.trim()) {
    console.error('Incomplete persisted resource artifact omitted', { index, resourceId: resource.id, type })
    return null
  }
  const metadata = isPlainObject(resource.metadata) ? resource.metadata : {}
  const estimatedMinutes = getEstimatedMinutes(metadata)
  return {
    ...resource,
    id: String(resource.id),
    type,
    title: resource.title.trim(),
    summary: typeof resource.summary === 'string' ? resource.summary : '',
    format: resource.format.trim(),
    status: 'completed',
    estimatedMinutes,
    estimatedLabel: estimatedMinutes ? `${estimatedMinutes} 分钟` : '',
    metadata,
  }
}

function normalizeType(type: unknown) {
  return typeof type === 'string' ? type.trim().toLowerCase() : ''
}

function openPreview(card: ResourceCard) {
  emit('preview', {
    agentId: card.type,
    resultData: card.content,
    title: card.title,
  })
}

function startLearning(card: ResourceCard) {
  openPreview(card)
}

function openResourceByType(type: string) {
  const target = resourceCards.value.find(card => card.type === type)
  if (target) openPreview(target)
}

function scrollToPath() {
  pathSectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function getEstimatedMinutes(metadata: Record<string, any>) {
  const raw = metadata.estimated_minutes ?? metadata.estimated_time
  if (typeof raw === 'number') return raw
  const parsed = Number(String(raw || '').match(/\d+/)?.[0])
  if (Number.isFinite(parsed) && parsed > 0) return parsed
  return null
}

function getStatusLabel(status: ResourceCard['status']) {
  const map = {
    completed: '已完成',
    partial: '部分完成',
    failed: '生成失败',
  }
  return map[status]
}

function getShortCardTitle(card: ResourceCard) {
  const topic = getMainTopic(card)
  if (topic && topic !== '当前知识主题') return topic
  return getResourceTypeLabel(card.type) || card.title
}

function getMainTopic(card: ResourceCard) {
  const summaryData = isPlainObject(card.metrics) ? card.metrics : {}
  const raw = summaryData.topic || card.metadata?.topic || card.title
  return typeof raw === 'string' ? raw.trim() : ''
}

function getCardVisualLabel(type: string) {
  const map: Record<string, string> = {
    content: 'COURSE NOTE',
    mindmap: 'KNOWLEDGE MAP',
    quiz: 'QUIZ CHECK',
    code: 'CODE LAB',
    reading: 'READING LIST',
    ppt: 'SLIDE DECK',
    video: 'ANIMATION',
  }
  return map[type] || 'RESOURCE'
}

function getResourceCoverImage(type: string) {
  const svg = getCoverSvg(type || 'content')
  const encoded = encodeURIComponent(svg)
  return `url("data:image/svg+xml;charset=UTF-8,${encoded}")`
}

function getCoverSvg(type: string): string {
  const commonDefs = `
    <defs>
      <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%">
        <feDropShadow dx="0" dy="14" stdDeviation="14" flood-color="#0f172a" flood-opacity="0.12"/>
      </filter>
      <linearGradient id="blue" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#dbeafe"/><stop offset="1" stop-color="#bfdbfe"/></linearGradient>
      <linearGradient id="mint" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#d1fae5"/><stop offset="1" stop-color="#a7f3d0"/></linearGradient>
      <linearGradient id="violet" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#ede9fe"/><stop offset="1" stop-color="#c4b5fd"/></linearGradient>
      <linearGradient id="rose" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#ffe4e6"/><stop offset="1" stop-color="#fecdd3"/></linearGradient>
      <linearGradient id="amber" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#fef3c7"/><stop offset="1" stop-color="#93c5fd"/></linearGradient>
    </defs>`

  const svgMap: Record<string, string> = {
    content: `
      <svg xmlns="http://www.w3.org/2000/svg" width="560" height="320" viewBox="0 0 560 320">
        ${commonDefs}
        <rect width="560" height="320" rx="34" fill="#eff6ff"/>
        <circle cx="90" cy="70" r="48" fill="#dbeafe" opacity=".9"/>
        <circle cx="450" cy="80" r="70" fill="#bfdbfe" opacity=".45"/>
        <path d="M66 244c58-46 132-47 206-8s145 37 222-19v68H66z" fill="#dbeafe" opacity=".65"/>
        <g filter="url(#shadow)">
          <rect x="176" y="58" width="244" height="188" rx="24" fill="white"/>
          <rect x="212" y="92" width="146" height="14" rx="7" fill="#bfdbfe"/>
          <rect x="212" y="124" width="174" height="10" rx="5" fill="#cbd5e1"/>
          <rect x="212" y="150" width="132" height="10" rx="5" fill="#cbd5e1"/>
          <rect x="212" y="176" width="158" height="10" rx="5" fill="#cbd5e1"/>
          <rect x="212" y="202" width="84" height="10" rx="5" fill="#818cf8"/>
        </g>
        <g filter="url(#shadow)">
          <rect x="84" y="112" width="108" height="136" rx="22" fill="url(#blue)" transform="rotate(-9 138 180)"/>
          <path d="M116 146h44M111 174h54M108 202h45" stroke="white" stroke-width="12" stroke-linecap="round" opacity=".8"/>
        </g>
        <rect x="82" y="250" width="102" height="18" rx="9" fill="#93c5fd"/>
        <rect x="58" y="268" width="136" height="18" rx="9" fill="#67e8f9" opacity=".75"/>
        <path d="M360 264l92-20" stroke="#60a5fa" stroke-width="12" stroke-linecap="round"/>
      </svg>`,
    mindmap: `
      <svg xmlns="http://www.w3.org/2000/svg" width="560" height="320" viewBox="0 0 560 320">
        ${commonDefs}
        <rect width="560" height="320" rx="34" fill="#f5f3ff"/>
        <circle cx="430" cy="72" r="74" fill="#ede9fe"/>
        <circle cx="92" cy="244" r="64" fill="#dbeafe" opacity=".72"/>
        <g opacity=".28" stroke="#c4b5fd" stroke-width="2"><path d="M0 72h560M0 144h560M0 216h560M112 0v320M224 0v320M336 0v320M448 0v320"/></g>
        <g filter="url(#shadow)">
          <circle cx="280" cy="160" r="42" fill="url(#violet)"/>
          <path d="M252 158c14 22 44 22 56 0" stroke="white" stroke-width="8" stroke-linecap="round" fill="none"/>
          <circle cx="264" cy="148" r="5" fill="white"/><circle cx="300" cy="148" r="5" fill="white"/>
        </g>
        <g stroke="#8b5cf6" stroke-width="5" stroke-linecap="round" opacity=".55">
          <path d="M242 146L146 96M244 174l-116 50M318 143l96-48M320 177l104 58M280 118V58M280 202v58"/>
        </g>
        <g filter="url(#shadow)">
          <rect x="74" y="70" width="112" height="48" rx="16" fill="#dbeafe"/><rect x="68" y="202" width="124" height="48" rx="16" fill="#bfdbfe"/>
          <rect x="374" y="70" width="126" height="48" rx="16" fill="#ddd6fe"/><rect x="368" y="214" width="132" height="48" rx="16" fill="#c4b5fd"/>
          <circle cx="280" cy="58" r="22" fill="#a7f3d0"/><circle cx="280" cy="262" r="22" fill="#93c5fd"/>
        </g>
      </svg>`,
    quiz: `
      <svg xmlns="http://www.w3.org/2000/svg" width="560" height="320" viewBox="0 0 560 320">
        ${commonDefs}
        <rect width="560" height="320" rx="34" fill="#ecfdf5"/>
        <circle cx="450" cy="72" r="82" fill="#a7f3d0" opacity=".45"/>
        <circle cx="98" cy="246" r="70" fill="#bfdbfe" opacity=".35"/>
        <g filter="url(#shadow)">
          <rect x="122" y="58" width="292" height="210" rx="28" fill="white"/>
          <rect x="166" y="102" width="28" height="28" rx="8" fill="#dcfce7" stroke="#10b981" stroke-width="3"/>
          <path d="M173 116l8 8 18-22" stroke="#10b981" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <rect x="218" y="107" width="138" height="12" rx="6" fill="#cbd5e1"/>
          <rect x="166" y="154" width="28" height="28" rx="8" fill="#dcfce7" stroke="#10b981" stroke-width="3"/>
          <path d="M173 168l8 8 18-22" stroke="#10b981" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          <rect x="218" y="159" width="160" height="12" rx="6" fill="#cbd5e1"/>
          <rect x="166" y="206" width="28" height="28" rx="8" fill="white" stroke="#94a3b8" stroke-width="3"/>
          <rect x="218" y="211" width="108" height="12" rx="6" fill="#cbd5e1"/>
        </g>
        <g filter="url(#shadow)">
          <circle cx="408" cy="226" r="46" fill="url(#mint)"/>
          <path d="M400 208c3-15 28-13 28 4 0 18-20 17-20 31" stroke="white" stroke-width="10" stroke-linecap="round" fill="none"/>
          <circle cx="408" cy="256" r="5" fill="white"/>
        </g>
      </svg>`,
    code: `
      <svg xmlns="http://www.w3.org/2000/svg" width="560" height="320" viewBox="0 0 560 320">
        ${commonDefs}
        <rect width="560" height="320" rx="34" fill="#fff1f2"/>
        <circle cx="100" cy="82" r="62" fill="#ffe4e6"/>
        <circle cx="450" cy="244" r="76" fill="#bfdbfe" opacity=".42"/>
        <g filter="url(#shadow)">
          <rect x="88" y="70" width="380" height="206" rx="24" fill="white"/>
          <rect x="88" y="70" width="380" height="38" rx="24" fill="#f8fafc"/>
          <circle cx="116" cy="90" r="7" fill="#fb7185"/><circle cx="140" cy="90" r="7" fill="#fbbf24"/><circle cx="164" cy="90" r="7" fill="#818cf8"/>
          <rect x="118" y="136" width="220" height="10" rx="5" fill="#60a5fa"/>
          <rect x="118" y="164" width="154" height="10" rx="5" fill="#a78bfa"/>
          <rect x="118" y="192" width="250" height="10" rx="5" fill="#818cf8"/>
          <rect x="118" y="220" width="186" height="10" rx="5" fill="#fb7185"/>
          <rect x="352" y="126" width="76" height="34" rx="12" fill="#dbeafe"/>
          <text x="368" y="149" fill="#2563eb" font-family="Arial" font-weight="800" font-size="18">Py</text>
        </g>
        <g filter="url(#shadow)">
          <rect x="386" y="216" width="80" height="58" rx="18" fill="#fecdd3"/>
          <path d="M416 232l26 13-26 13z" fill="#fb7185"/>
        </g>
      </svg>`,
    reading: `
      <svg xmlns="http://www.w3.org/2000/svg" width="560" height="320" viewBox="0 0 560 320">
        ${commonDefs}
        <rect width="560" height="320" rx="34" fill="#eff6ff"/>
        <circle cx="92" cy="78" r="62" fill="#dbeafe"/><circle cx="460" cy="78" r="58" fill="#bfdbfe" opacity=".5"/>
        <g filter="url(#shadow)">
          <path d="M116 76h142c34 0 58 24 58 58v126H172c-32 0-56-24-56-56z" fill="white"/>
          <path d="M316 134c0-34 24-58 58-58h70v128c0 32-24 56-56 56H316z" fill="#f8fafc"/>
          <path d="M336 76h42v78l-21-14-21 14z" fill="#2563eb" opacity=".85"/>
          <rect x="158" y="126" width="96" height="10" rx="5" fill="#cbd5e1"/><rect x="158" y="156" width="112" height="10" rx="5" fill="#cbd5e1"/><rect x="158" y="186" width="76" height="10" rx="5" fill="#cbd5e1"/>
          <rect x="348" y="126" width="72" height="10" rx="5" fill="#cbd5e1"/><rect x="348" y="156" width="58" height="10" rx="5" fill="#cbd5e1"/>
        </g>
        <g filter="url(#shadow)">
          <rect x="96" y="172" width="96" height="98" rx="22" fill="url(#amber)"/>
          <path d="M118 232l26-34 18 24 12-14 22 24z" fill="white" opacity=".78"/>
        </g>
        <circle cx="426" cy="228" r="42" fill="none" stroke="#60a5fa" stroke-width="16" opacity=".76"/>
        <path d="M456 258l42 42" stroke="#60a5fa" stroke-width="16" stroke-linecap="round" opacity=".76"/>
      </svg>`,
  }

  return svgMap[type] ?? svgMap.content ?? ''
}

function getResourceHighlights(card: ResourceCard) {
  const metrics = isPlainObject(card.metrics) ? card.metrics : {}
  const candidates = [
    metrics.question_count ? `${metrics.question_count} 题` : '',
    metrics.node_count ? `${metrics.node_count} 节点` : '',
    metrics.page_count ? `${metrics.page_count} 页` : '',
    metrics.language ? String(metrics.language) : '',
    card.metadata?.programming_language ? String(card.metadata.programming_language) : '',
  ]
  return candidates.filter(Boolean).slice(0, 3)
}

function hasContent(value: unknown): boolean {
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.length > 0
  return isPlainObject(value) && Object.keys(value).length > 0
}

function isPlainObject(value: unknown): value is Record<string, any> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}
</script>



<style scoped>
/* ============================================================
   Resource Result Page — Design System Compliant
   Follows: Typography scale, font weights, color tokens
   ============================================================ */

.resource-package-page {
  position: relative;
  min-height: calc(100vh - var(--navbar-height, 64px));
  padding: var(--space-4) clamp(var(--space-4), 2vw, 30px) 30px;
  overflow-y: auto;
  background:
    radial-gradient(circle at 8% 0%, rgba(59, 130, 246, 0.10), transparent 26%),
    radial-gradient(circle at 94% 8%, rgba(20, 184, 166, 0.12), transparent 28%),
    linear-gradient(180deg, var(--color-bg) 0%, #eef6ff 58%, var(--color-bg) 100%);
}

.package-hero-card,
.package-section-card,
.resource-result-card {
  border: 1px solid rgba(203, 213, 225, 0.78);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: var(--shadow-xl);
  backdrop-filter: blur(18px);
}

.package-hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) auto auto;
  align-items: center;
  gap: var(--space-5);
  width: min(100%, 1760px);
  margin: 0 auto;
  border-radius: var(--radius-2xl);
  padding: var(--space-4) var(--space-5);
}

.package-hero-title {
  min-width: 0;
}

.hero-kicker-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.hero-status-pill,
.section-summary-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1_5);
  height: 26px;
  padding: 0 10px;
  border-radius: var(--radius-pill);
  background: var(--color-success-soft);
  color: var(--color-success);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
  border: 1px solid rgba(16, 185, 129, 0.24);
  white-space: nowrap;
}

.hero-status-pill.warning {
  background: var(--color-warning-soft);
  color: var(--color-warning);
  border-color: rgba(245, 158, 11, 0.28);
}

.hero-kicker,
.section-eyebrow {
  font-size: var(--text-xs);
  letter-spacing: 0.12em;
  font-weight: var(--weight-extrabold);
  color: var(--cat-tutor);
}

.package-hero-card h1 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: clamp(var(--text-xl), 2.1vw, var(--text-3xl));
  line-height: var(--leading-tight);
  font-weight: var(--weight-extrabold);
  letter-spacing: -0.035em;
}

.package-hero-title p {
  display: -webkit-box;
  max-width: 860px;
  margin: var(--space-2) 0 0;
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
}

.hero-metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(86px, 1fr));
  gap: var(--space-2);
}

.hero-metric-pill {
  display: grid;
  place-items: center;
  min-width: 86px;
  height: 54px;
  padding: var(--space-1_5) 10px;
  border-radius: var(--radius-lg);
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid var(--color-border-light);
}

.hero-metric-pill span {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
}

.hero-metric-pill strong {
  color: var(--color-text-strong);
  font-size: var(--text-md);
  font-weight: var(--weight-extrabold);
  line-height: 1.1;
}

.hero-action-row {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2_5);
  flex-wrap: wrap;
}

.hero-primary-btn {
  background: linear-gradient(135deg, var(--cat-tutor), var(--color-success));
  border: none;
}

.hero-side-panel {
  display: grid;
  justify-items: end;
  gap: var(--space-2_5);
  min-width: 260px;
}


.package-result-body {
  width: min(100%, 1760px);
  margin: var(--space-3_5) auto 0;
  display: grid;
  gap: var(--space-3_5);
}

.package-section-card {
  border-radius: var(--radius-2xl);
  padding: var(--space-4);
}

.section-heading-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3_5);
  margin-bottom: var(--space-3_5);
}

.section-heading-row h2,
.review-tile h2 {
  margin: var(--space-0_5) 0 0;
  color: var(--color-text-strong);
  font-size: var(--text-lg);
  font-weight: var(--weight-extrabold);
  letter-spacing: -0.02em;
}

.section-summary-pill {
  background: var(--cat-tutor-soft);
  color: var(--cat-tutor);
  border-color: rgba(59, 130, 246, 0.22);
}

.learning-path-section {
  padding: var(--space-4) var(--space-5) var(--space-5);
}

.path-heading {
  align-items: center;
}

.path-step-track {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-2_5);
}

.path-step-card {
  position: relative;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: var(--space-2_5);
  min-height: 138px;
  padding: var(--space-3);
  overflow: hidden;
  border-radius: var(--radius-xl);
  background: rgba(248, 250, 252, 0.84);
  border: 1px solid rgba(226, 232, 240, 0.88);
  cursor: pointer;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease, background 0.22s ease;
}

.path-step-card::after {
  position: absolute;
  inset: auto var(--space-3) 0 56px;
  height: 3px;
  border-radius: var(--radius-pill) var(--radius-pill) 0 0;
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.24), rgba(20, 184, 166, 0.24));
  content: '';
}

.path-step-card:hover {
  transform: translateY(-3px);
  border-color: rgba(59, 130, 246, 0.32);
  background: rgba(255, 255, 255, 0.98);
  box-shadow: var(--shadow-lg);
}

.path-step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.14), rgba(20, 184, 166, 0.14));
  color: var(--cat-tutor);
  font-size: var(--text-base);
  font-weight: var(--weight-extrabold);
}

.path-step-main {
  min-width: 0;
}

.path-step-topline {
  display: flex;
  align-items: center;
  gap: var(--space-1_5);
  min-width: 0;
}

.path-resource-type {
  display: inline-flex;
  max-width: 98px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--cat-tutor-soft);
  color: var(--cat-tutor);
  font-size: 11px;
  font-weight: var(--weight-extrabold);
}

.path-time-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  margin-left: auto;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
  white-space: nowrap;
}

.path-step-card h3 {
  display: -webkit-box;
  margin: var(--space-2_5) 0 0;
  overflow: hidden;
  color: var(--color-text-strong);
  font-size: var(--text-sm);
  font-weight: var(--weight-extrabold);
  line-height: 1.42;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.path-step-card p {
  display: -webkit-box;
  margin: var(--space-1_5) 0 0;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.path-focus-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-top: var(--space-2);
}

.path-focus-list span {
  padding: 3px 7px;
  border-radius: var(--radius-pill);
  background: rgba(241, 245, 249, 0.96);
  color: var(--color-text-secondary);
  font-size: 11px;
  font-weight: var(--weight-extrabold);
}

.resource-board-section {
  min-width: 0;
}

.board-heading {
  align-items: flex-end;
  margin: var(--space-1) 0 var(--space-3);
}

.board-heading p {
  display: -webkit-box;
  max-width: 900px;
  margin: var(--space-1_5) 0 0;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
}

.board-filter-pills {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  justify-content: flex-end;
}

.board-filter-pills span {
  padding: 7px 10px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(226, 232, 240, 0.92);
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
}

.resource-card-grid-v2 {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space-3);
}

.resource-result-card {
  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 374px;
  overflow: hidden;
  border-radius: var(--radius-2xl);
  padding: var(--space-3_5);
  cursor: pointer;
  animation: cardRise 0.42s ease backwards;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
}

.resource-result-card:nth-child(1) { animation-delay: 0.02s; }
.resource-result-card:nth-child(2) { animation-delay: 0.06s; }
.resource-result-card:nth-child(3) { animation-delay: 0.10s; }
.resource-result-card:nth-child(4) { animation-delay: 0.14s; }
.resource-result-card:nth-child(5) { animation-delay: 0.18s; }
.resource-result-card:nth-child(6) { animation-delay: 0.22s; }

@keyframes cardRise {
  from { opacity: 0; transform: translateY(12px) scale(0.99); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.resource-result-card:hover,
.resource-result-card:focus-visible {
  transform: translateY(-4px);
  border-color: rgba(37, 99, 235, 0.32);
  box-shadow: var(--shadow-xl);
  outline: none;
}

.resource-card-header,
.resource-card-body,
.resource-insight-box,
.resource-meta-grid,
.resource-card-actions,
.resource-preview-panel {
  position: relative;
  z-index: 1;
}

.resource-card-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.resource-icon-shell {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  border-radius: var(--radius-lg);
  background: var(--cat-tutor-soft);
  color: var(--cat-tutor);
  font-size: var(--text-lg);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.12);
}

.resource-header-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.resource-header-text span {
  color: var(--color-text-strong);
  font-size: var(--text-sm);
  font-weight: var(--weight-extrabold);
}

.resource-header-text strong {
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: var(--weight-extrabold);
}

.resource-status-badge {
  margin-left: auto;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--color-success-soft);
  color: var(--color-success);
  font-size: 11px;
  font-weight: var(--weight-extrabold);
  white-space: nowrap;
}

.resource-status-badge.partial {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

.resource-status-badge.failed {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.resource-preview-panel {
  margin: var(--space-3) 0;
  padding: var(--space-3);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, rgba(248, 250, 252, 0.96), rgba(255, 255, 255, 0.92));
  border: 1px solid rgba(226, 232, 240, 0.92);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.preview-panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2_5);
  margin-bottom: var(--space-2);
}

.preview-panel-title span {
  color: var(--color-text-strong);
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
}

.preview-panel-title strong {
  padding: 3px 7px;
  border-radius: var(--radius-pill);
  background: var(--cat-tutor-soft);
  color: var(--cat-tutor);
  font-size: 11px;
  font-weight: var(--weight-extrabold);
  white-space: nowrap;
}

.preview-row-list {
  display: grid;
  gap: var(--space-1_5);
  margin: 0;
}

.preview-row {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: var(--space-2);
  align-items: start;
  min-height: 24px;
}

.preview-row dt {
  color: var(--cat-tutor);
  font-size: 11px;
  font-weight: var(--weight-extrabold);
  white-space: nowrap;
}

.preview-row dd {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: 1.42;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
}

.resource-card-body h3 {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: var(--color-text-strong);
  font-size: var(--text-base);
  font-weight: var(--weight-extrabold);
  line-height: 1.38;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.resource-card-body p {
  display: -webkit-box;
  margin: var(--space-2) 0 0;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: var(--text-xs);
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
}

.resource-insight-box {
  margin-top: var(--space-2_5);
  padding: var(--space-2) var(--space-2_5);
  border-radius: var(--radius-lg);
  background: rgba(248, 250, 252, 0.86);
  border: 1px solid rgba(226, 232, 240, 0.82);
}

.resource-insight-box span {
  display: block;
  margin-bottom: var(--space-0_5);
  color: var(--cat-tutor);
  font-size: 11px;
  font-weight: var(--weight-extrabold);
}

.resource-insight-box p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: 1.42;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.resource-meta-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1_5);
  margin-top: auto;
  padding-top: var(--space-2_5);
}

.resource-meta-grid span {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  background: rgba(241, 245, 249, 0.9);
  color: var(--color-text-secondary);
  font-size: 11px;
  font-weight: var(--weight-extrabold);
}

.resource-card-actions {
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: var(--space-2);
  margin-top: var(--space-2_5);
  padding-top: var(--space-2_5);
  border-top: 1px solid rgba(226, 232, 240, 0.82);
}

.card-action-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1_5);
  height: 34px;
  border-radius: var(--radius-lg);
  border: 1px solid transparent;
  font-size: var(--text-xs);
  font-weight: var(--weight-extrabold);
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.card-action-button:hover {
  transform: translateY(-1px);
}

.card-action-button.secondary {
  background: rgba(248, 250, 252, 0.92);
  border-color: rgba(203, 213, 225, 0.9);
  color: var(--color-text-secondary);
}

.card-action-button.secondary:hover {
  background: var(--color-surface);
  border-color: rgba(37, 99, 235, 0.28);
  color: var(--cat-tutor);
}

.card-action-button.primary {
  background: linear-gradient(135deg, var(--cat-tutor), var(--color-success));
  color: var(--color-surface);
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.18);
}

.card-action-button.primary:hover {
  box-shadow: 0 14px 26px rgba(37, 99, 235, 0.24);
}


.resource-cover {
  position: relative;
  z-index: 1;
  height: 166px;
  margin: var(--space-3) 0 var(--space-3);
  overflow: hidden;
  border-radius: var(--radius-xl);
  background-position: center;
  background-size: cover;
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.resource-cover::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 50%, rgba(15, 23, 42, 0.08));
  content: '';
  pointer-events: none;
}

.resource-result-card:hover .resource-cover {
  transform: translateY(-1px);
}

.cover-type-badge {
  position: absolute;
  left: 10px;
  top: 10px;
  z-index: 2;
  max-width: calc(100% - 20px);
  padding: var(--space-1) 9px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(226, 232, 240, 0.88);
  color: var(--cat-tutor);
  font-size: 10px;
  font-weight: var(--weight-extrabold);
  letter-spacing: 0.04em;
  backdrop-filter: blur(10px);
}

.resource-tag-row {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1_5);
  margin-top: var(--space-2_5);
}

.resource-tag-row span {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  background: var(--cat-tutor-soft);
  color: var(--cat-tutor);
  font-size: 11px;
  font-weight: var(--weight-bold);
}

.resource-result-card.tone-purple .resource-tag-row span { background: var(--cat-eval-soft); color: var(--cat-eval); }
.resource-result-card.tone-emerald .resource-tag-row span,
.resource-result-card.tone-green .resource-tag-row span { background: var(--color-success-soft); color: var(--color-success); }
.resource-result-card.tone-rose .resource-tag-row span,
.resource-result-card.tone-pink .resource-tag-row span { background: var(--cat-rose-soft); color: var(--cat-rose); }
.resource-result-card.tone-orange .resource-tag-row span { background: rgba(255, 237, 213, 0.92); color: #ea580c; }

.empty-resource-board {
  display: flex;
  min-height: 260px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  border-radius: var(--radius-2xl);
  background: rgba(255, 255, 255, 0.78);
  border: 1px dashed rgba(148, 163, 184, 0.65);
  color: var(--color-text-muted);
}

.empty-resource-board .el-icon {
  font-size: 42px;
  color: var(--color-warning);
}

.empty-resource-board strong {
  color: var(--color-text-strong);
  font-size: var(--text-xl);
}

.empty-resource-board p {
  margin: 0;
}

.resource-result-card.tone-emerald .resource-icon-shell,
.resource-result-card.tone-green .resource-icon-shell { background: var(--color-success-soft); color: var(--color-success); }
.resource-result-card.tone-blue .resource-icon-shell { background: var(--cat-tutor-soft); color: var(--cat-tutor); }
.resource-result-card.tone-purple .resource-icon-shell { background: var(--cat-eval-soft); color: var(--cat-eval); }
.resource-result-card.tone-rose .resource-icon-shell { background: var(--cat-rose-soft); color: var(--cat-rose); }
.resource-result-card.tone-indigo .resource-icon-shell { background: var(--cat-resource-soft); color: var(--cat-resource); }
.resource-result-card.tone-pink .resource-icon-shell { background: rgba(219, 39, 119, 0.12); color: #db2777; }
.resource-result-card.tone-orange .resource-icon-shell { background: rgba(249, 115, 22, 0.12); color: #ea580c; }

@media (max-width: 1500px) {
  .package-hero-card {
    grid-template-columns: minmax(0, 1fr);
  }

  .hero-metric-strip {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .hero-side-panel {
    justify-items: start;
    min-width: 0;
  }

  .hero-action-row {
    justify-content: flex-start;
  }

  .path-step-track,
  .resource-card-grid-v2 {
    grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  }
}

@media (max-width: 1080px) {
  .path-step-track {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .resource-package-page {
    padding: var(--space-3_5);
  }

  .package-hero-card,
  .package-section-card {
    border-radius: var(--radius-xl);
  }

  .section-heading-row,
  .board-heading {
    flex-direction: column;
    align-items: stretch;
  }

  .board-filter-pills {
    justify-content: flex-start;
  }

  .hero-metric-strip,
  .path-step-track,
  .resource-card-grid-v2 {
    grid-template-columns: 1fr;
  }

  .hero-action-row {
    flex-direction: column;
    align-items: stretch;
  }

  .resource-card-actions {
    grid-template-columns: 1fr;
  }
}
</style>
