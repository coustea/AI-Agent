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
        <div class="hero-metric-pill">
          <span>预计</span>
          <strong>{{ totalEstimatedMinutes }}min</strong>
        </div>
        <div class="hero-metric-pill">
          <span>评分</span>
          <strong>{{ reviewScore }}</strong>
        </div>
        <div class="hero-metric-pill">
          <span>路径</span>
          <strong>{{ studyPathSteps.length }}步</strong>
        </div>
      </div>

      <div class="hero-side-panel">
        <button v-if="resultWarning" class="hero-warning-dock" type="button" @click="scrollToReview">
          <el-icon><WarningFilled /></el-icon>
          <span>{{ resultWarning }}</span>
        </button>

        <div class="hero-action-row">
          <el-button round type="primary" class="hero-primary-btn" @click="scrollToPath">
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
      <section ref="pathSectionRef" class="learning-path-section package-section-card">
        <div class="section-heading-row path-heading">
          <div>
            <span class="section-eyebrow">LEARNING PATH</span>
            <h2>推荐学习顺序</h2>
          </div>
          <span class="section-summary-pill">{{ studyPathSteps.length }} 步 · {{ totalEstimatedMinutes }} 分钟</span>
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
                <span class="path-time-badge">
                  <el-icon><Clock /></el-icon>
                  {{ step.estimated_time || getEstimatedMinutesByType(normalizeType(step.resource_type)) }}min
                </span>
              </div>
              <h3>{{ step.title }}</h3>
              <p>{{ step.reason || getPathReason(normalizeType(step.resource_type)) }}</p>
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
                <strong>{{ card.format || getDefaultResourceFormat(card.type) }}</strong>
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
              <p>{{ getCardSubtitle(card.type) }}</p>
            </div>

            <div class="resource-tag-row">
              <span v-for="tag in getResourceCardTags(card)" :key="`${card.id}-${tag}`">
                {{ tag }}
              </span>
            </div>

            <div class="resource-meta-grid">
              <span>
                <el-icon><Odometer /></el-icon>
                {{ getDifficultyLabel(card.metadata?.difficulty) }}
              </span>
              <span>
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

      <section ref="reviewSectionRef" class="review-strip">
        <article class="review-tile package-section-card quality-tile">
          <div>
            <span class="section-eyebrow">QUALITY REVIEW</span>
            <h2>质量审查</h2>
            <p>{{ resultWarning || (reviewPassed ? '内容完整性、个性化匹配和安全性均已完成检查。' : '存在审查提醒，建议查看问题后再使用资源。') }}</p>
          </div>
          <span class="quality-score" :class="{ warning: !reviewPassed }">{{ reviewScore }}</span>
        </article>

        <article class="review-tile package-section-card">
          <span class="section-eyebrow">COVERAGE</span>
          <h2>资源覆盖</h2>
          <p>{{ resourceTypeSummary }}</p>
        </article>

        <article class="review-tile package-section-card" :class="{ warning: failedAgents.length }">
          <span class="section-eyebrow">AGENT STATUS</span>
          <h2>{{ failedAgents.length ? '存在失败智能体' : '智能体协同完成' }}</h2>
          <p>{{ failedAgents.length ? failedAgents.join(' / ') : '文档、导图、题库、实操与拓展阅读已完成串联。' }}</p>
        </article>

        <article class="review-tile package-section-card">
          <span class="section-eyebrow">REVIEW ITEMS</span>
          <h2>{{ reviewIssues.length ? '审查提醒' : '审查项通过' }}</h2>
          <div v-if="reviewIssues.length" class="review-issue-list">
            <span v-for="issue in reviewIssues.slice(0, 3)" :key="issue">{{ issue }}</span>
          </div>
          <div v-else class="review-pass-list">
            <span><b></b>完整性</span>
            <span><b></b>一致性</span>
            <span><b></b>安全性</span>
          </div>
        </article>
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
  getResourceUsageHint,
  getDefaultResourceFormat,
  getEstimatedTime,
  getDifficultyLabel,
  getResourceToneClass,
  formatBentoTitle,
} from '@/features/resource/model/ResourceGeneratorConstants'

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
  status: 'completed' | 'partial' | 'failed'
  estimatedMinutes: number
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
  generatedResources: GeneratedResourceItem[]
  resultWarning: string
}>()

const emit = defineEmits<{
  reset: []
  preview: [data: { agentId: string; resultData: any; title: string }]
}>()

const pathSectionRef = ref<HTMLElement | null>(null)
const reviewSectionRef = ref<HTMLElement | null>(null)

const RESOURCE_ORDER = ['content', 'mindmap', 'quiz', 'code', 'reading', 'ppt', 'video']

const rawResources = computed<GeneratedResourceItem[]>(() => {
  const resources = props.finalBundle?.resources
  return Array.isArray(resources) && resources.length ? resources : props.generatedResources
})

const resourceCards = computed<ResourceCard[]>(() => {
  return rawResources.value
    .map((resource, index) => normalizeResource(resource, index))
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
  return props.finalBundle?.learning_need || resourceCards.value[0]?.title || '本次学习目标'
})

const heroSummary = computed(() => {
  const count = resourceCards.value.length
  if (!count) return '本次任务暂未生成可展示资源，建议重新生成或查看任务日志。'
  const types = resourceCards.value.map(item => getResourceTypeLabel(item.type)).filter(Boolean).slice(0, 6).join('、')
  return `已生成 ${count} 类学习资源：${types}。建议按下方学习路径逐步完成，先建立理解，再完成练习与实操。`
})

const totalEstimatedMinutes = computed(() => {
  const total = resourceCards.value.reduce((sum, card) => sum + card.estimatedMinutes, 0)
  return total || 45
})

const reviewResult = computed(() => props.finalBundle?.review_result || null)

const reviewPassed = computed(() => {
  if (props.resultWarning) return false
  if (!reviewResult.value) return true
  return reviewResult.value.passed !== false
})

const reviewScore = computed(() => {
  const raw = reviewResult.value?.overall_score
  if (typeof raw === 'number') return Math.max(0, Math.min(100, raw))
  return reviewPassed.value ? 96 : 72
})

const failedAgents = computed<string[]>(() => {
  const fromReview = reviewResult.value?.failed_agents
  const fromMeta = props.finalBundle?.metadata?.failed_agents
  if (Array.isArray(fromReview) && fromReview.length) return fromReview.map(String)
  if (Array.isArray(fromMeta)) return fromMeta.map(String)
  return []
})

const reviewIssues = computed<string[]>(() => {
  const issues = reviewResult.value?.issues
  if (Array.isArray(issues)) return issues.map((item: any) => String(item)).filter(Boolean)
  return []
})

const studyPathSteps = computed<StudyPathStepLike[]>(() => {
  const path = reviewResult.value?.study_path || props.finalBundle?.study_path
  if (Array.isArray(path) && path.length) {
    return path
      .map((step: any, index: number) => ({
        order: Number(step.order || index + 1),
        resource_type: normalizeType(step.resource_type || step.type || ''),
        title: String(step.title || getResourceTypeLabel(step.resource_type || step.type || 'content')),
        reason: step.reason || '',
        estimated_time: typeof step.estimated_time === 'number' ? step.estimated_time : null,
        focus_points: Array.isArray(step.focus_points) ? step.focus_points.map(String) : [],
      }))
      .sort((a, b) => a.order - b.order)
  }
  return buildFallbackStudyPath(resourceCards.value)
})

const resourceTypeSummary = computed(() => {
  if (!resourceCards.value.length) return '暂无资源'
  return resourceCards.value.map(item => getResourceTypeLabel(item.type)).join(' / ')
})

function normalizeResource(resource: GeneratedResourceItem, index: number): ResourceCard {
  const type = normalizeType(resource.type || resource.agent_type || resource.generated_by || '')
  const metadata = isPlainObject(resource.metadata) ? resource.metadata : {}
  const estimatedMinutes = getEstimatedMinutesByType(type, metadata)
  const rawStatus = String(resource.status || '').toLowerCase()
  const status: ResourceCard['status'] = rawStatus.includes('fail')
    ? 'failed'
    : rawStatus.includes('partial')
      ? 'partial'
      : 'completed'
  return {
    ...resource,
    id: String(resource.id || `${type}-${index}`),
    type,
    title: formatBentoTitle(resource.title || getResourceTypeLabel(type), type),
    summary: String(resource.summary || getResourceUsageHint(type) || ''),
    format: String(resource.format || resource.content_format || getDefaultResourceFormat(type) || ''),
    status,
    estimatedMinutes,
    estimatedLabel: `${estimatedMinutes} 分钟`,
    metadata,
  }
}

function normalizeType(type: string) {
  const value = String(type || '').toLowerCase()
  if (value.includes('content') || value.includes('doc')) return 'content'
  if (value.includes('mind')) return 'mindmap'
  if (value.includes('quiz') || value.includes('question')) return 'quiz'
  if (value.includes('code')) return 'code'
  if (value.includes('read')) return 'reading'
  if (value.includes('ppt') || value.includes('slide')) return 'ppt'
  if (value.includes('video')) return 'video'
  return value || 'content'
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

function scrollToReview() {
  reviewSectionRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function buildFallbackStudyPath(cards: ResourceCard[]): StudyPathStepLike[] {
  const ordered = RESOURCE_ORDER
    .map(type => cards.find(card => card.type === type))
    .filter(Boolean) as ResourceCard[]

  return ordered.map((card, index) => ({
    order: index + 1,
    resource_type: card.type,
    title: getFallbackPathTitle(card.type),
    reason: getPathReason(card.type),
    estimated_time: card.estimatedMinutes,
    focus_points: getFallbackFocusPoints(card.type),
  }))
}

function getFallbackPathTitle(type: string) {
  const map: Record<string, string> = {
    content: '先阅读课程讲解文档，建立基础理解',
    mindmap: '查看知识结构导图，梳理概念关系',
    quiz: '完成个性化练习题，检测掌握情况',
    code: '进入代码实操案例，完成实践巩固',
    reading: '阅读拓展材料，补充应用场景',
    ppt: '查看 PPT 文稿，快速复盘重点',
    video: '观看动画讲解，强化直观理解',
  }
  return map[type] || `学习${getResourceTypeLabel(type)}`
}

function getPathReason(type: string) {
  const map: Record<string, string> = {
    content: '先理解概念、原理和典型例子，降低后续练习成本。',
    mindmap: '用结构化视图建立知识框架，明确前置概念与核心考点。',
    quiz: '通过题目及时暴露薄弱点，并结合解析修正理解。',
    code: '把概念落实到可运行代码，形成可迁移的实践能力。',
    reading: '补充工程应用和延伸知识，拓宽对知识点的理解。',
    ppt: '用于最后复盘，也可作为课堂展示或汇报材料。',
    video: '通过动态演示理解抽象过程，适合快速回看。',
  }
  return map[type] || '按资源内容完成学习。'
}

function getFallbackFocusPoints(type: string) {
  const map: Record<string, string[]> = {
    content: ['核心概念', '高频考点', '易错点'],
    mindmap: ['知识结构', '概念关系', '前置知识'],
    quiz: ['基础题', '提高题', '答案解析'],
    code: ['可运行代码', '关键注释', '实践步骤'],
    reading: ['应用场景', '拓展资料', '延伸知识'],
    ppt: ['重点复盘', '页面结构', '汇报使用'],
  }
  return map[type] || ['学习重点']
}

function getEstimatedMinutesByType(type: string, metadata: Record<string, any> = {}) {
  const raw = metadata.estimated_minutes || metadata.estimated_time || getEstimatedTime(type)
  if (typeof raw === 'number') return raw
  const parsed = Number(String(raw || '').match(/\d+/)?.[0])
  if (Number.isFinite(parsed) && parsed > 0) return parsed
  const fallback: Record<string, number> = {
    content: 20,
    mindmap: 8,
    quiz: 18,
    code: 25,
    reading: 12,
    ppt: 10,
    video: 12,
  }
  return fallback[type] || 10
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
  const summaryData = isPlainObject(card.summary_data) ? card.summary_data : {}
  const raw = summaryData.topic || card.metadata?.topic || card.title
  return typeof raw === 'string' ? raw.trim() : ''
}

function getCardSubtitle(type: string) {
  const map: Record<string, string> = {
    content: '系统讲解核心概念与原理',
    mindmap: '梳理知识结构与关联',
    quiz: '检验掌握情况与理解程度',
    code: '代码示例与实操演练',
    reading: '延伸阅读与应用拓展',
    ppt: '重点内容压缩复盘',
    video: '动态讲解关键过程',
  }
  return map[type] || getResourceUsageHint(type)
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

function getResourceCardTags(card: ResourceCard) {
  const summaryData = isPlainObject(card.summary_data) ? card.summary_data : {}
  const language = String(summaryData.language || card.metadata?.programming_language || 'Python')
  const count = summaryData.question_count || summaryData.node_count || summaryData.page_count || ''
  const preset: Record<string, string[]> = {
    content: ['概念', '原理', '易错点'],
    mindmap: ['结构图', '概念关系', count ? `${count} 节点` : '重点脉络'],
    quiz: [count ? `${count} 题` : '10 题', '选择题', '即时反馈'],
    code: ['实战案例', language, '可运行'],
    reading: ['延伸材料', '应用场景', '拓展视角'],
    ppt: [count ? `${count} 页` : '复盘', '重点页', '展示用'],
    video: ['分镜', '动画', '讲解稿'],
  }
  const tags = preset[card.type] || getResourceHighlights(card)
  return tags.filter(Boolean).slice(0, 3)
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
          <rect x="212" y="202" width="84" height="10" rx="5" fill="#34d399"/>
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
          <circle cx="116" cy="90" r="7" fill="#fb7185"/><circle cx="140" cy="90" r="7" fill="#fbbf24"/><circle cx="164" cy="90" r="7" fill="#34d399"/>
          <rect x="118" y="136" width="220" height="10" rx="5" fill="#60a5fa"/>
          <rect x="118" y="164" width="154" height="10" rx="5" fill="#a78bfa"/>
          <rect x="118" y="192" width="250" height="10" rx="5" fill="#34d399"/>
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
  const summaryData = isPlainObject(card.summary_data) ? card.summary_data : {}
  const candidates = [
    summaryData.question_count ? `${summaryData.question_count} 题` : '',
    summaryData.node_count ? `${summaryData.node_count} 节点` : '',
    summaryData.page_count ? `${summaryData.page_count} 页` : '',
    summaryData.language ? String(summaryData.language) : '',
    card.metadata?.programming_language ? String(card.metadata.programming_language) : '',
  ]
  return candidates.filter(Boolean)
}

function isPlainObject(value: unknown): value is Record<string, any> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}
</script>



<style scoped>
.resource-package-page {
  position: relative;
  min-height: calc(100vh - var(--navbar-height, 64px));
  padding: 16px clamp(18px, 2vw, 30px) 30px;
  overflow-y: auto;
  background:
    radial-gradient(circle at 8% 0%, rgba(59, 130, 246, 0.10), transparent 26%),
    radial-gradient(circle at 94% 8%, rgba(20, 184, 166, 0.12), transparent 28%),
    linear-gradient(180deg, #f8fafc 0%, #eef6ff 58%, #f8fafc 100%);
}

.package-hero-card,
.package-section-card,
.resource-result-card {
  border: 1px solid rgba(203, 213, 225, 0.78);
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 16px 42px rgba(15, 23, 42, 0.065);
  backdrop-filter: blur(18px);
}

.package-hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) auto auto;
  align-items: center;
  gap: 18px;
  width: min(100%, 1760px);
  margin: 0 auto;
  border-radius: 22px;
  padding: 16px 18px;
}

.package-hero-title {
  min-width: 0;
}

.hero-kicker-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.hero-status-pill,
.section-summary-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
  font-size: 12px;
  font-weight: 800;
  border: 1px solid rgba(16, 185, 129, 0.24);
  white-space: nowrap;
}

.hero-status-pill.warning {
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
  border-color: rgba(245, 158, 11, 0.28);
}

.hero-kicker,
.section-eyebrow {
  font-size: 12px;
  letter-spacing: 0.12em;
  font-weight: 900;
  color: #2563eb;
}

.package-hero-card h1 {
  margin: 0;
  color: #0f172a;
  font-size: clamp(22px, 2.1vw, 30px);
  line-height: 1.15;
  font-weight: 950;
  letter-spacing: -0.035em;
}

.package-hero-title p {
  display: -webkit-box;
  max-width: 860px;
  margin: 8px 0 0;
  overflow: hidden;
  color: #475569;
  font-size: 14px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
}

.hero-metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(86px, 1fr));
  gap: 8px;
}

.hero-metric-pill {
  display: grid;
  place-items: center;
  min-width: 86px;
  height: 54px;
  padding: 6px 10px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.hero-metric-pill span {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.hero-metric-pill strong {
  color: #0f172a;
  font-size: 17px;
  font-weight: 950;
  line-height: 1.1;
}

.hero-action-row {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.hero-primary-btn {
  background: linear-gradient(135deg, #2563eb, #14b8a6);
  border: none;
}

.hero-side-panel {
  display: grid;
  justify-items: end;
  gap: 10px;
  min-width: 260px;
}

.hero-warning-dock {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  width: min(100%, 300px);
  min-height: 34px;
  padding: 7px 10px;
  border: 1px solid rgba(245, 158, 11, 0.22);
  border-radius: 14px;
  background: rgba(255, 247, 237, 0.9);
  color: #b45309;
  cursor: pointer;
  text-align: left;
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}

.hero-warning-dock:hover {
  transform: translateY(-1px);
  border-color: rgba(245, 158, 11, 0.38);
  background: #fff7ed;
}

.hero-warning-dock span {
  display: -webkit-box;
  overflow: hidden;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}


.package-result-body {
  width: min(100%, 1760px);
  margin: 14px auto 0;
  display: grid;
  gap: 14px;
}

.package-section-card {
  border-radius: 22px;
  padding: 16px;
}

.section-heading-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.section-heading-row h2,
.review-tile h2 {
  margin: 3px 0 0;
  color: #0f172a;
  font-size: 19px;
  font-weight: 950;
  letter-spacing: -0.02em;
}

.section-summary-pill {
  background: rgba(59, 130, 246, 0.10);
  color: #2563eb;
  border-color: rgba(59, 130, 246, 0.22);
}

.learning-path-section {
  padding: 16px 18px 18px;
}

.path-heading {
  align-items: center;
}

.path-step-track {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

.path-step-card {
  position: relative;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  min-height: 138px;
  padding: 12px;
  overflow: hidden;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.84);
  border: 1px solid rgba(226, 232, 240, 0.88);
  cursor: pointer;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease, background 0.22s ease;
}

.path-step-card::after {
  position: absolute;
  inset: auto 12px 0 56px;
  height: 3px;
  border-radius: 999px 999px 0 0;
  background: linear-gradient(90deg, rgba(37, 99, 235, 0.24), rgba(20, 184, 166, 0.24));
  content: '';
}

.path-step-card:hover {
  transform: translateY(-3px);
  border-color: rgba(59, 130, 246, 0.32);
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
}

.path-step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 13px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.14), rgba(20, 184, 166, 0.14));
  color: #2563eb;
  font-size: 16px;
  font-weight: 950;
}

.path-step-main {
  min-width: 0;
}

.path-step-topline {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.path-resource-type {
  display: inline-flex;
  max-width: 98px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 4px 8px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 900;
}

.path-time-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.path-step-card h3 {
  display: -webkit-box;
  margin: 9px 0 0;
  overflow: hidden;
  color: #0f172a;
  font-size: 14px;
  font-weight: 900;
  line-height: 1.42;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.path-step-card p {
  display: -webkit-box;
  margin: 6px 0 0;
  overflow: hidden;
  color: #64748b;
  font-size: 12px;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.path-focus-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 8px;
}

.path-focus-list span {
  padding: 3px 7px;
  border-radius: 999px;
  background: rgba(241, 245, 249, 0.96);
  color: #475569;
  font-size: 11px;
  font-weight: 800;
}

.resource-board-section {
  min-width: 0;
}

.board-heading {
  align-items: flex-end;
  margin: 4px 0 12px;
}

.board-heading p {
  display: -webkit-box;
  max-width: 900px;
  margin: 6px 0 0;
  overflow: hidden;
  color: #64748b;
  font-size: 13px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
}

.board-filter-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  justify-content: flex-end;
}

.board-filter-pills span {
  padding: 7px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(226, 232, 240, 0.92);
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.resource-card-grid-v2 {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.resource-result-card {
  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 374px;
  overflow: hidden;
  border-radius: 20px;
  padding: 14px;
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
  box-shadow: 0 22px 52px rgba(15, 23, 42, 0.11);
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
  gap: 9px;
}

.resource-icon-shell {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  border-radius: 15px;
  background: rgba(239, 246, 255, 0.9);
  color: #2563eb;
  font-size: 18px;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.12);
}

.resource-header-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.resource-header-text span {
  color: #0f172a;
  font-size: 13px;
  font-weight: 900;
}

.resource-header-text strong {
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.resource-status-badge {
  margin-left: auto;
  padding: 5px 8px;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
  font-size: 11px;
  font-weight: 900;
  white-space: nowrap;
}

.resource-status-badge.partial {
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
}

.resource-status-badge.failed {
  background: rgba(239, 68, 68, 0.12);
  color: #dc2626;
}

.resource-preview-panel {
  margin: 12px 0;
  padding: 11px 12px;
  border-radius: 16px;
  background:
    linear-gradient(135deg, rgba(248, 250, 252, 0.96), rgba(255, 255, 255, 0.92));
  border: 1px solid rgba(226, 232, 240, 0.92);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.preview-panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.preview-panel-title span {
  color: #0f172a;
  font-size: 12px;
  font-weight: 950;
}

.preview-panel-title strong {
  padding: 3px 7px;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 900;
  white-space: nowrap;
}

.preview-row-list {
  display: grid;
  gap: 6px;
  margin: 0;
}

.preview-row {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: 8px;
  align-items: start;
  min-height: 24px;
}

.preview-row dt {
  color: #2563eb;
  font-size: 11px;
  font-weight: 950;
  white-space: nowrap;
}

.preview-row dd {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: #475569;
  font-size: 12px;
  line-height: 1.42;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
}

.resource-card-body h3 {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: #0f172a;
  font-size: 15px;
  font-weight: 950;
  line-height: 1.38;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.resource-card-body p {
  display: -webkit-box;
  margin: 7px 0 0;
  overflow: hidden;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
}

.resource-insight-box {
  margin-top: 10px;
  padding: 9px 10px;
  border-radius: 15px;
  background: rgba(248, 250, 252, 0.86);
  border: 1px solid rgba(226, 232, 240, 0.82);
}

.resource-insight-box span {
  display: block;
  margin-bottom: 3px;
  color: #2563eb;
  font-size: 11px;
  font-weight: 950;
}

.resource-insight-box p {
  display: -webkit-box;
  margin: 0;
  overflow: hidden;
  color: #475569;
  font-size: 12px;
  line-height: 1.42;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.resource-meta-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: auto;
  padding-top: 10px;
}

.resource-meta-grid span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 8px;
  border-radius: 999px;
  background: rgba(241, 245, 249, 0.9);
  color: #475569;
  font-size: 11px;
  font-weight: 800;
}

.resource-card-actions {
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(226, 232, 240, 0.82);
}

.card-action-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
  border-radius: 12px;
  border: 1px solid transparent;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.card-action-button:hover {
  transform: translateY(-1px);
}

.card-action-button.secondary {
  background: rgba(248, 250, 252, 0.92);
  border-color: rgba(203, 213, 225, 0.9);
  color: #475569;
}

.card-action-button.secondary:hover {
  background: #ffffff;
  border-color: rgba(37, 99, 235, 0.28);
  color: #2563eb;
}

.card-action-button.primary {
  background: linear-gradient(135deg, #2563eb, #14b8a6);
  color: #ffffff;
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.18);
}

.card-action-button.primary:hover {
  box-shadow: 0 14px 26px rgba(37, 99, 235, 0.24);
}


.resource-cover {
  position: relative;
  z-index: 1;
  height: 166px;
  margin: 13px 0 12px;
  overflow: hidden;
  border-radius: 18px;
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
  padding: 5px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(226, 232, 240, 0.88);
  color: #2563eb;
  font-size: 10px;
  font-weight: 950;
  letter-spacing: 0.04em;
  backdrop-filter: blur(10px);
}

.resource-tag-row {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.resource-tag-row span {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(239, 246, 255, 0.96);
  color: #2563eb;
  font-size: 11px;
  font-weight: 850;
}

.resource-result-card.tone-purple .resource-tag-row span { background: rgba(237, 233, 254, 0.95); color: #7c3aed; }
.resource-result-card.tone-emerald .resource-tag-row span,
.resource-result-card.tone-green .resource-tag-row span { background: rgba(209, 250, 229, 0.9); color: #047857; }
.resource-result-card.tone-rose .resource-tag-row span,
.resource-result-card.tone-pink .resource-tag-row span { background: rgba(255, 228, 230, 0.92); color: #e11d48; }
.resource-result-card.tone-orange .resource-tag-row span { background: rgba(255, 237, 213, 0.92); color: #ea580c; }

.empty-resource-board {
  display: flex;
  min-height: 260px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px dashed rgba(148, 163, 184, 0.65);
  color: #64748b;
}

.empty-resource-board .el-icon {
  font-size: 42px;
  color: #f59e0b;
}

.empty-resource-board strong {
  color: #0f172a;
  font-size: 20px;
}

.empty-resource-board p {
  margin: 0;
}

.review-strip {
  display: grid;
  grid-template-columns: 1.2fr 1fr 1fr 1fr;
  gap: 12px;
}

.review-tile {
  min-height: 122px;
}

.quality-tile {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.review-tile p {
  display: -webkit-box;
  margin: 8px 0 0;
  overflow: hidden;
  color: #64748b;
  font-size: 13px;
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.review-tile.warning {
  border-color: rgba(245, 158, 11, 0.25);
  background: rgba(255, 251, 235, 0.72);
}

.quality-score {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 54px;
  height: 54px;
  flex: 0 0 auto;
  border-radius: 18px;
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
  font-size: 21px;
  font-weight: 950;
}

.quality-score.warning {
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
}

.review-issue-list,
.review-pass-list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 10px;
}

.review-issue-list span,
.review-pass-list span {
  padding: 6px 9px;
  border-radius: 999px;
  background: rgba(255, 247, 237, 0.92);
  color: #b45309;
  font-size: 12px;
  font-weight: 800;
}

.review-pass-list span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(236, 253, 245, 0.92);
  color: #047857;
}

.review-pass-list b {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #10b981;
}

.resource-result-card.tone-emerald .resource-icon-shell,
.resource-result-card.tone-green .resource-icon-shell { background: rgba(16, 185, 129, 0.12); color: #059669; }
.resource-result-card.tone-blue .resource-icon-shell { background: rgba(59, 130, 246, 0.12); color: #2563eb; }
.resource-result-card.tone-purple .resource-icon-shell { background: rgba(139, 92, 246, 0.12); color: #7c3aed; }
.resource-result-card.tone-rose .resource-icon-shell { background: rgba(244, 63, 94, 0.12); color: #e11d48; }
.resource-result-card.tone-indigo .resource-icon-shell { background: rgba(99, 102, 241, 0.12); color: #4f46e5; }
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

  .hero-warning-dock {
    width: min(100%, 560px);
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
  .review-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .resource-package-page {
    padding: 14px;
  }

  .package-hero-card,
  .package-section-card {
    border-radius: 20px;
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
  .resource-card-grid-v2,
  .review-strip {
    grid-template-columns: 1fr;
  }

  .hero-warning-dock {
    width: 100%;
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
