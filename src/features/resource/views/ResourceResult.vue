<template>
  <div class="phase-view results-view resource-result-page">

    <!-- Ambient Blur Glows for Immersive Atelier Vibe -->
    <div class="result-ambient-glows" aria-hidden="true">
      <div class="glow-sphere glow-primary"></div>
      <div class="glow-sphere glow-secondary"></div>
    </div>

    <!-- Bento Workspace Grid -->
    <div class="result-workspace-grid">

      <!-- HEADER BRIEF CARD: Task Brief Card (智源任务概要卡) - 全宽 -->
      <section class="bento-card atelier-brief-card col-span-3">
        <div class="brief-glass-backdrop"></div>
        <div class="brief-content">
          <div class="brief-header">
            <span class="result-status-badge" :class="{ warning: isPartialResult }">
              <el-icon aria-hidden="true">
                <component :is="isPartialResult ? WarningFilled : CircleCheckFilled" />
              </el-icon>
              {{ isPartialResult ? '部分工位就绪' : '工坊汇编完成' }}
            </span>
            <span class="result-package-label">COGNITIVE COMPILING BLUEPRINT</span>
          </div>
          <h1>{{ bundleTitle }}</h1>
          <p class="prompt-text-quote">{{ learningNeedText || heroSummary }}</p>

          <!-- Stats inline in brief card -->
          <div class="brief-stats-row">
            <div class="stat-chip">
              <span class="stat-label">交付产物</span>
              <strong class="stat-val">{{ resourceCards.length }}<small>项</small></strong>
            </div>
            <div class="stat-chip">
              <span class="stat-label">认知媒介</span>
              <strong class="stat-val">{{ generatedTypeCount }}<small>种</small></strong>
            </div>
            <div v-if="totalEstimatedMinutes" class="stat-chip">
              <span class="stat-label">研习周期</span>
              <strong class="stat-val">{{ totalEstimatedMinutes }}<small>分</small></strong>
            </div>
          </div>
        </div>
      </section>

      <!-- Partial Result Alert Banner -->
      <section v-if="resultWarning" class="bento-card partial-result-banner col-span-3">
        <div class="partial-banner-icon-box">
          <el-icon aria-hidden="true"><WarningFilled /></el-icon>
        </div>
        <div class="banner-body-text">
          <strong>协同链路受阻 (Collaboration Interrupted)</strong>
          <p>{{ resultWarning }}</p>
        </div>
        <span class="banner-hint-note">部分并行工位协同受限，已就绪的成果已通过质量校验，可正常开启研习。</span>
      </section>

      <!-- Bento-Style Recommended Hero Card (Large Card) - 2/3宽度，占据2行 -->
      <section v-if="recommendedCard" class="bento-card recommended-hero-card col-span-2 row-span-2">
        <div class="recommended-hero-content">
          <span class="section-kicker">RECOMMENDED START</span>
          <h2>以此开启学习探索</h2>
          <p class="recommended-intro">认知架构师建议优先从此项核心精解讲义切入，梳理整体概念脉络，再结合其他认知媒介完成知识闭环。</p>

          <!-- Recommended card preview -->
          <div class="recommended-preview-card">
            <div class="preview-card-header">
              <div class="preview-type-badge" :class="`type-${recommendedCard.type}`">
                <span class="type-icon">{{ getResourceIcon(recommendedCard.type) }}</span>
                <span>{{ getResourceTypeLabel(recommendedCard.type) }}</span>
              </div>
              <span class="preview-format-tag">{{ recommendedCard.format }}</span>
            </div>
            <h3 class="preview-title">{{ recommendedCard.title }}</h3>
            <p class="preview-summary">{{ recommendedCard.summary || getDefaultSummary(recommendedCard.type) }}</p>
            <div class="preview-meta-row">
              <span v-if="recommendedCard.estimatedLabel" class="meta-pill">
                <el-icon aria-hidden="true"><Clock /></el-icon>
                {{ recommendedCard.estimatedLabel }}
              </span>
              <span v-for="tag in getResourceHighlights(recommendedCard).slice(0, 2)" :key="tag" class="meta-pill highlight">
                {{ tag }}
              </span>
            </div>
          </div>

          <div class="recommended-actions">
            <button type="button" class="start-learning-hero-btn" @click="startLearning(recommendedCard)">
              <span>即刻开启研习</span>
              <el-icon aria-hidden="true"><ArrowRight /></el-icon>
            </button>
            <button type="button" class="preview-btn-secondary" @click="openPreview(recommendedCard)">
              <el-icon aria-hidden="true"><View /></el-icon>
              <span>预览</span>
            </button>
          </div>
        </div>
      </section>

      <!-- Cognitive Profile Calibration Bento Card - 1/3宽度 -->
      <section class="bento-card glassmorphic-panel cognitive-profile-calibration col-span-1">
        <span class="panel-eyebrow">PROFILE CALIBRATION</span>
        <h3 class="panel-title">学情画像映射修正</h3>
        <p class="calibration-desc">本次生成的资源包已根据以下维度校正您的动态画像：</p>

        <div class="calibration-dimension-list">
          <div class="dimension-row-widget">
            <div class="dim-info">
              <span class="dim-label">学习风格映射</span>
              <strong class="dim-value">{{ getScenarioCalibration.style }}</strong>
            </div>
            <div class="dim-bar-progress"><span class="progress-fill" style="width: 85%"></span></div>
          </div>
          <div class="dimension-row-widget">
            <div class="dim-info">
              <span class="dim-label">关注聚焦重点</span>
              <strong class="dim-value">{{ getScenarioCalibration.focus }}</strong>
            </div>
            <div class="dim-bar-progress"><span class="progress-fill" style="width: 90%"></span></div>
          </div>
          <div class="dimension-row-widget highlight-emerald">
            <div class="dim-info">
              <span class="dim-label">画像提升幅度</span>
              <strong class="dim-value text-emerald">+2% 认知熟练度</strong>
            </div>
            <div class="dim-bar-progress"><span class="progress-fill fill-emerald" style="width: 100%"></span></div>
          </div>
        </div>
      </section>

      <!-- MAS Workflow Timeline Bento Card - 1/3宽度 -->
      <section class="bento-card glassmorphic-panel mas-process-timeline col-span-1">
        <span class="panel-eyebrow">COLLABORATIVE LINEAGE</span>
        <h3 class="panel-title">工位协同工序谱系</h3>

        <div class="workflow-steps-vertical">
          <div class="step-timeline-item completed">
            <div class="step-bullet"><span>✓</span></div>
            <div class="step-info">
              <strong>认知架构工位</strong>
              <p>分析目标与场景</p>
            </div>
          </div>
          <div class="step-timeline-item completed">
            <div class="step-bullet"><span>✓</span></div>
            <div class="step-info">
              <strong>协同中枢工位</strong>
              <p>任务并发调度</p>
            </div>
          </div>
          <div class="step-timeline-item completed">
            <div class="step-bullet"><span>✓</span></div>
            <div class="step-info">
              <strong>并发协同成果</strong>
              <p>多媒介同步研制</p>
            </div>
          </div>
          <div class="step-timeline-item completed">
            <div class="step-bullet"><span>✓</span></div>
            <div class="step-info">
              <strong>汇编归档工位</strong>
              <p>跨格式校验归档</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Filters Section - 全宽 -->
      <section class="bento-card filters-section col-span-3">
        <div class="filters-header">
          <h3 class="filters-title">已就绪成果名录</h3>
          <div v-if="resourceCards.length > 1" class="resource-pill-filters">
            <button
                type="button"
                :class="{ active: activeFilter === 'all' }"
                @click="activeFilter = 'all'"
            >
              全部 ({{ resourceCards.length }})
            </button>
            <button
                v-for="filter in availableFilters"
                :key="filter.type"
                type="button"
                :class="{ active: activeFilter === filter.type }"
                @click="activeFilter = filter.type"
            >
              {{ filter.label }} ({{ filter.count }})
            </button>
          </div>
        </div>
      </section>

      <!-- Main Resources Bento Grid - 全宽 -->
      <section class="bento-card resources-gallery col-span-3">
        <!-- Bento Grid of Visual Interactive Cards -->
        <div v-if="filteredResourceCards.length" class="resource-card-bento-grid">
          <article
              v-for="card in filteredResourceCards"
              :key="card.id"
              class="visual-resource-card"
              :class="[`type-${card.type}`, { 'is-recommended': card.id === recommendedCard?.id }]"
              tabindex="0"
              role="button"
              :aria-label="`查看${card.title}`"
              @click="openPreview(card)"
              @keydown.enter.prevent="openPreview(card)"
              @keydown.space.prevent="openPreview(card)"
          >
            <!-- Card Cover Artwork with Custom Thematic Visuals -->
            <div class="card-visual-header">
              <div class="card-glow-bg"></div>
              <ResourceArtwork :type="card.type" />
              <div class="visual-top-overlay">
                <span class="card-type-indicator">
                  <span class="type-icon">{{ getResourceIcon(card.type) }}</span>
                  {{ getResourceTypeLabel(card.type) }}
                </span>
                <span class="card-status-dot-pill"><i></i>就绪</span>
              </div>
              <span class="visual-format-badge">{{ card.format }}</span>
            </div>

            <!-- Card Body -->
            <div class="card-body-content">
              <h3 class="card-title-text">{{ card.title }}</h3>
              <p class="card-summary-text">{{ card.summary || getDefaultSummary(card.type) }}</p>

              <div v-if="getResourceHighlights(card).length" class="card-tags-row">
                <span v-for="tag in getResourceHighlights(card)" :key="`${card.id}-${tag}`" class="card-tag-badge">
                  {{ tag }}
                </span>
              </div>
            </div>

            <!-- Card Footer Actions -->
            <footer class="card-footer-actions">
              <button type="button" class="action-btn preview-btn" @click.stop="openPreview(card)">
                <el-icon aria-hidden="true"><View /></el-icon>
                预览
              </button>
              <button type="button" class="action-btn learn-btn" @click.stop="startLearning(card)">
                <span>开启学习</span>
                <el-icon aria-hidden="true"><ArrowRight /></el-icon>
              </button>
            </footer>
          </article>
        </div>

        <!-- Empty filter state -->
        <div v-else class="empty-state-box">
          <div class="empty-state-icon-wrapper">
            <el-icon aria-hidden="true"><WarningFilled /></el-icon>
          </div>
          <h3>当前筛选下无就绪成果</h3>
          <p>该分类下暂无已生成的资源，请选择其他类别或查看全部成果。</p>
          <button type="button" class="clear-filter-btn" @click="activeFilter = 'all'">查看全部</button>
        </div>
      </section>

      <!-- New Task Action Card - 全宽 -->
      <section class="bento-card new-task-action-card col-span-3">
        <div class="action-box">
          <h4>准备好进行下一阶段规划了吗？</h4>
          <p>重置当前工坊运行参数，重新输入新的学习需求意向。</p>
          <button
              type="button"
              class="rebuild-action-btn"
              @click="emit('reset')"
          >
            <el-icon aria-hidden="true"><RefreshLeft /></el-icon>
            <span>发起新探索任务</span>
          </button>
        </div>
      </section>

    </div>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  defineComponent,
  h,
  ref,
  type PropType,
} from 'vue'

import {
  ArrowRight,
  CircleCheckFilled,
  RefreshLeft,
  WarningFilled,
  Clock,
  View,
} from '@element-plus/icons-vue'

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

const props = defineProps<{
  finalBundle: any | null
  resultWarning: string
}>()

const emit = defineEmits<{
  reset: []
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

const activeFilter = ref('all')

const SCENARIO_CALIBRATION_MAP: Record<string, { style: string; focus: string; dim: string }> = {
  exam_prep: { style: '考试强化型 (Exam Oriented)', focus: '自测查漏与重难点剖析', dim: '认知深度与应试大纲映射' },
  daily_review: { style: '循序渐进型 (Incremental)', focus: '知识点微反馈与概念建构', dim: '认知宽度与记忆连存率' },
  project_practice: { style: '工程实训型 (Project Driven)', focus: '沙箱实验与真实代码实训', dim: '操作效能与工程系统思维' },
  self_study: { style: '自主探索型 (Self Guided)', focus: '前置依赖关系检索与全局大纲', dim: '新领域知识图谱完备度' },
}

const getScenarioCalibration = computed<{ style: string; focus: string; dim: string }>(() => {
  const sc = props.finalBundle?.scenario || props.finalBundle?.learningScenario || 'daily_review'
  const fallback = { style: '循序渐进型 (Incremental)', focus: '知识点微反馈与概念建构', dim: '认知宽度与记忆连存率' }
  return SCENARIO_CALIBRATION_MAP[sc] || fallback
})

const ResourceArtwork = defineComponent({
  name: 'ResourceArtwork',

  props: {
    type: {
      type: String as PropType<string>,
      required: true,
    },

    large: {
      type: Boolean,
      default: false,
    },
  },

  setup(componentProps) {
    return () =>
        h(
            'div',
            {
              class: [
                'artwork',
                `artwork-${componentProps.type}`,
                {
                  'is-large': componentProps.large,
                },
              ],
              'aria-hidden': 'true',
            },
            createArtworkNodes(componentProps.type),
        )
  },
})

function createArtworkNodes(type: string) {
  if (type === 'mindmap') {
    return [
      h('span', { class: 'map-center' }, 'AI'),

      ...[1, 2, 3, 4].map(index =>
          h('i', {
            class: `map-node node-${index}`,
          }),
      ),

      ...[1, 2, 3, 4].map(index =>
          h('b', {
            class: `map-line line-${index}`,
          }),
      ),
    ]
  }

  if (type === 'quiz') {
    return [
      h('span', { class: 'quiz-sheet' }, [
        h('i'),
        h('i'),
        h('i'),
        h('b'),
        h('b'),
        h('b'),
      ]),

      h('span', { class: 'quiz-score' }, 'A+'),
    ]
  }

  if (type === 'code') {
    return [
      h('span', { class: 'code-window' }, [
        h('i', { class: 'code-dots' }),
        h('b', { class: 'code-line line-a' }),
        h('b', { class: 'code-line line-b' }),
        h('b', { class: 'code-line line-c' }),
        h('b', { class: 'code-line line-d' }),
      ]),

      h('span', { class: 'code-badge' }, '</>'),
    ]
  }

  if (type === 'reading') {
    return [
      h('span', {
        class: 'book book-back',
      }),

      h(
          'span',
          {
            class: 'book book-front',
          },
          [
            h('i'),
            h('b'),
          ],
      ),

      h(
          'span',
          {
            class: 'reading-mark',
          },
          '↗',
      ),
    ]
  }

  if (type === 'ppt') {
    return [
      h('span', {
        class: 'slide slide-back',
      }),

      h(
          'span',
          {
            class: 'slide slide-front',
          },
          [
            h('i'),
            h('b'),
            h('em'),
          ],
      ),

      h(
          'span',
          {
            class: 'slide-number',
          },
          '12',
      ),
    ]
  }

  if (type === 'video') {
    return [
      h(
          'span',
          {
            class: 'video-screen',
          },
          [
            h('i', {
              class: 'play-button',
            }),
          ],
      ),

      h(
          'span',
          {
            class: 'video-track',
          },
          [
            h('i'),
          ],
      ),

      h(
          'span',
          {
            class: 'video-time',
          },
          '03:00',
      ),
    ]
  }

  return [
    h('span', {
      class: 'document-back',
    }),

    h(
        'span',
        {
          class: 'document-front',
        },
        [
          h('i', {
            class: 'document-title',
          }),
          h('b'),
          h('b'),
          h('b'),
          h('em'),
        ],
    ),

    h('span', {
      class: 'document-pen',
    }),
  ]
}

const rawResources = computed<GeneratedResourceItem[]>(() => {
  const resources =
      props.finalBundle?.resources ??
      props.finalBundle?.items

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

const recommendedCard = computed(() => {
  return (
      resourceCards.value.find(
          card => card.type === 'content',
      ) ||
      resourceCards.value.find(
          card => card.type === 'mindmap',
      ) ||
      resourceCards.value[0] ||
      null
  )
})

const bundleTitle = computed(() => {
  return String(
      props.finalBundle?.title ||
      props.finalBundle?.name ||
      '个性化学习资源包',
  )
})

const learningNeedText = computed(() => {
  return String(
      props.finalBundle?.learning_need ||
      props.finalBundle?.learningNeed ||
      '',
  ).trim()
})

const heroSummary = computed(() => {
  const count = resourceCards.value.length

  if (!count) {
    return '本次任务暂未生成可展示资源。'
  }

  const typeNames = availableFilters.value
      .map(item => item.label)
      .slice(0, 7)
      .join('、')

  return `已生成 ${count} 项资源，包含${typeNames}，可按需要选择查看。`
})

const generatedTypeCount = computed(() => {
  return new Set(
      resourceCards.value.map(card => card.type),
  ).size
})

const totalEstimatedMinutes = computed(() => {
  const total = resourceCards.value.reduce(
      (sum, card) =>
          sum + (card.estimatedMinutes || 0),
      0,
  )

  return total > 0
      ? total
      : null
})

const isPartialResult = computed(() => {
  return Boolean(props.resultWarning?.trim())
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

function startLearning(card: ResourceCard) {
  openPreview(card)
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
/* ================= PAGE BASE ================= */
.resource-detail-page,
.resource-result-page {
  --font-sans: var(--font-ui);
  --agent-body-font: var(--font-body);

  background: #F4F7FB;
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
  font-family: var(--font-sans);
}

/* Ambient background glow */
.resource-result-page::before {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 100%; height: 500px;
  background: linear-gradient(180deg, rgba(224, 231, 255, 0.6) 0%, rgba(244, 247, 251, 0) 100%);
  pointer-events: none;
  z-index: 0;
}

/* Ambient glow spheres */
.result-ambient-glows {
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.glow-sphere {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.15;
  animation: float-glow 8s ease-in-out infinite;
}

.glow-primary {
  width: 400px; height: 400px;
  background: #6366F1;
  top: -100px; left: 10%;
}

.glow-secondary {
  width: 350px; height: 350px;
  background: #3B82F6;
  top: 200px; right: 5%;
  animation-delay: 4s;
}

@keyframes float-glow {
  0%, 100% { opacity: 0.15; }
  50% { opacity: 0.25; }
}

/* ================= BENTO GRID SYSTEM ================= */
.result-workspace-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  padding: 60px;
  position: relative;
  z-index: 1;
  max-width: 1400px;
  margin: 0 auto;
}

.col-span-1 { grid-column: span 1; }
.col-span-2 { grid-column: span 2; }
.col-span-3 { grid-column: span 3; }
.row-span-2 { grid-row: span 2; }

@media (max-width: 1200px) {
  .result-workspace-grid {
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    padding: 40px;
  }
  .col-span-3 { grid-column: span 2; }
}

@media (max-width: 768px) {
  .result-workspace-grid {
    grid-template-columns: 1fr;
    gap: 16px;
    padding: 20px;
  }
  .col-span-1, .col-span-2, .col-span-3 { grid-column: span 1; }
  .row-span-2 { grid-row: span 1; }
}

/* ================= BENTO CARD BASE ================= */
.bento-card {
  position: relative;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 24px;
  background: #ffffff;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
  padding: 32px;
  overflow: hidden;
  animation: card-fade-in 0.5s ease-out backwards;
}

@keyframes card-fade-in {
  0% { opacity: 0; transform: translateY(12px); }
  100% { opacity: 1; transform: translateY(0); }
}

/* ================= BRIEF CARD ================= */
.atelier-brief-card {
  padding: 40px 48px;
}

.brief-glass-backdrop {
  position: absolute;
  top: 0; right: 0; bottom: 0; left: 0;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.03) 0%, rgba(59, 130, 246, 0.03) 100%);
  pointer-events: none;
}

.brief-content {
  position: relative;
  z-index: 1;
}

.brief-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.result-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.result-status-badge.warning {
  background: rgba(245, 158, 11, 0.1);
  color: #D97706;
  border-color: rgba(245, 158, 11, 0.2);
}

.result-package-label {
  font-family: var(--font-mono, monospace);
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.15em;
  color: #6366f1;
  text-transform: uppercase;
}

.atelier-brief-card h1 {
  margin: 0;
  font-size: 2rem;
  font-weight: 900;
  color: var(--color-text);
  letter-spacing: -0.02em;
  line-height: 1.3;
}

.prompt-text-quote {
  margin: 12px 0 0 0;
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  font-family: var(--agent-body-font);
}

/* Brief stats inline */
.brief-stats-row {
  display: flex;
  gap: 16px;
  margin-top: 20px;
  flex-wrap: wrap;
}

.stat-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.04);
  border: 1px solid rgba(15, 23, 42, 0.06);
}

.stat-chip .stat-label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-weight: 700;
}

.stat-chip .stat-val {
  font-size: 1.1rem;
  color: var(--color-text);
  font-weight: 900;
}

.stat-chip .stat-val small {
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--color-text-muted);
  margin-left: 2px;
}

/* ================= PARTIAL BANNER ================= */
.partial-result-banner {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 16px;
  align-items: center;
  padding: 20px 24px;
  background: rgba(254, 243, 199, 0.5);
  border-color: rgba(245, 158, 11, 0.3);
}

.partial-banner-icon-box {
  display: grid;
  place-items: center;
  width: 40px; height: 40px;
  border-radius: 12px;
  background: rgba(245, 158, 11, 0.15);
  color: #D97706;
  font-size: 20px;
}

.banner-body-text strong {
  display: block;
  font-size: 0.95rem;
  color: #92400E;
  font-weight: 800;
}

.banner-body-text p {
  margin: 4px 0 0 0;
  font-size: 0.85rem;
  color: #B45309;
}

.banner-hint-note {
  font-size: 0.8rem;
  color: #D97706;
  text-align: right;
}

/* ================= RECOMMENDED HERO CARD ================= */
.recommended-hero-card {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(59, 130, 246, 0.08) 100%);
  padding: 0;
  display: flex;
  flex-direction: column;
}

.recommended-hero-content {
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.section-kicker {
  display: block;
  font-family: var(--font-mono, monospace);
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #6366f1;
  text-transform: uppercase;
}

.recommended-hero-card h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 900;
  color: var(--color-text);
}

.recommended-intro {
  margin: 0;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* Recommended preview card */
.recommended-preview-card {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.6);
  border-radius: 20px;
  padding: 24px;
  margin-top: 12px;
}

.preview-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.preview-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
  background: rgba(99, 102, 241, 0.1);
  color: #6366f1;
}

.preview-type-badge.type-content { background: rgba(59, 130, 246, 0.1); color: #3B82F6; }
.preview-type-badge.type-mindmap { background: rgba(139, 92, 246, 0.1); color: #8B5CF6; }
.preview-type-badge.type-quiz { background: rgba(16, 185, 129, 0.1); color: #059669; }
.preview-type-badge.type-code { background: rgba(244, 63, 94, 0.1); color: #F43F5E; }
.preview-type-badge.type-ppt { background: rgba(245, 158, 11, 0.1); color: #D97706; }
.preview-type-badge.type-video { background: rgba(6, 182, 212, 0.1); color: #06B6D4; }

.preview-type-badge .type-icon {
  font-size: 1rem;
}

.preview-format-tag {
  font-family: var(--font-mono, monospace);
  font-size: 0.7rem;
  font-weight: 800;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.04);
}

.preview-title {
  margin: 0 0 8px 0;
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--color-text);
}

.preview-summary {
  margin: 0;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.preview-meta-row {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.meta-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 0.75rem;
  font-weight: 700;
  background: rgba(15, 23, 42, 0.04);
  color: var(--color-text-secondary);
}

.meta-pill.highlight {
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
}

/* Recommended actions */
.recommended-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.start-learning-hero-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 14px 28px;
  border-radius: 14px;
  font-weight: 700;
  font-size: 0.95rem;
  color: #ffffff;
  background: #6366f1;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
  transition: all 0.25s ease;
}

.start-learning-hero-btn:hover {
  background: #4f46e5;
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
  transform: translateY(-2px);
}

.preview-btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  border-radius: 14px;
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--color-text);
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.8);
  cursor: pointer;
  transition: all 0.25s ease;
}

.preview-btn-secondary:hover {
  border-color: rgba(99, 102, 241, 0.3);
  color: #6366f1;
}

/* ================= GLASSMORPHIC PANELS ================= */
.glassmorphic-panel {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 28px;
}

.panel-eyebrow {
  display: block;
  font-family: var(--font-mono, monospace);
  color: #6366f1;
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.panel-title {
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--color-text);
  margin: 0 0 12px 0;
}

/* Profile calibration */
.calibration-desc {
  margin: 0 0 16px 0;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.calibration-dimension-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dimension-row-widget {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(226, 232, 240, 0.5);
}

.dim-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.dim-label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  font-weight: 700;
}

.dim-value {
  font-size: 0.75rem;
  color: var(--color-text);
  font-weight: 800;
}

.dim-bar-progress {
  height: 4px;
  width: 100%;
  background: #e2e8f0;
  border-radius: 2px;
  overflow: hidden;
}

.dim-bar-progress .progress-fill {
  display: block;
  height: 100%;
  background: #6366f1;
  border-radius: 2px;
}

.dim-bar-progress .progress-fill.fill-emerald {
  background: #10b981;
}

.highlight-emerald {
  border-color: rgba(16, 185, 129, 0.2);
  background: rgba(16, 185, 129, 0.05);
}

.text-emerald {
  color: #10b981 !important;
}

/* ================= WORKFLOW TIMELINE ================= */
.workflow-steps-vertical {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
  margin-top: 12px;
}

.step-timeline-item {
  display: grid;
  grid-template-columns: 20px 1fr;
  gap: 12px;
  align-items: start;
}

.step-bullet {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(16, 185, 129, 0.1);
  border: 2px solid #10b981;
  color: #10b981;
  font-size: 10px;
  font-weight: 700;
}

.step-info strong {
  display: block;
  font-size: 0.8rem;
  color: var(--color-text);
  font-weight: 800;
}

.step-info p {
  margin: 2px 0 0 0;
  font-size: 0.7rem;
  color: var(--color-text-secondary);
}

/* ================= FILTERS SECTION ================= */
.filters-section {
  padding: 24px 32px;
  background: rgba(255, 255, 255, 0.9);
}

.filters-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.filters-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-text);
}

.resource-pill-filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.resource-pill-filters button {
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
  background: rgba(15, 23, 42, 0.04);
  border: 1px solid transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
}

.resource-pill-filters button:hover {
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
}

.resource-pill-filters button.active {
  background: #6366f1;
  color: #ffffff;
  border-color: #6366f1;
}

/* ================= RESOURCES GALLERY ================= */
.resources-gallery {
  padding: 0;
  background: transparent;
  border: none;
  box-shadow: none;
}

.resource-card-bento-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  padding: 32px;
}

/* ================= VISUAL RESOURCE CARD ================= */
.visual-resource-card {
  position: relative;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 20px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
  outline: none;
}

.visual-resource-card:hover,
.visual-resource-card:focus-visible {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

.visual-resource-card.is-recommended {
  border-color: rgba(99, 102, 241, 0.3);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.02) 0%, rgba(255, 255, 255, 0.95) 100%);
}

/* Card visual header */
.card-visual-header {
  position: relative;
  height: 140px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.02) 0%, rgba(15, 23, 42, 0.05) 100%);
  overflow: hidden;
}

.card-glow-bg {
  position: absolute;
  top: -20px; right: -20px;
  width: 100px; height: 100px;
  border-radius: 50%;
  filter: blur(40px);
  opacity: 0.15;
  background: #6366f1;
}

.visual-top-overlay {
  position: absolute;
  top: 12px; left: 12px; right: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-type-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.9);
  color: var(--color-text);
}

.card-type-indicator .type-icon {
  font-size: 1rem;
}

.card-status-dot-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
}

.card-status-dot-pill i {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #10b981;
}

.visual-format-badge {
  position: absolute;
  bottom: 12px; right: 12px;
  font-family: var(--font-mono, monospace);
  font-size: 0.65rem;
  font-weight: 800;
  text-transform: uppercase;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--color-text-secondary);
}

/* Card body */
.card-body-content {
  padding: 20px;
}

.card-title-text {
  margin: 0 0 8px 0;
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--color-text);
  line-height: 1.4;
}

.card-summary-text {
  margin: 0;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-tags-row {
  display: flex;
  gap: 6px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.card-tag-badge {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.7rem;
  font-weight: 700;
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
}

/* Card footer actions */
.card-footer-actions {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px;
  padding: 16px 20px;
  border-top: 1px solid rgba(226, 232, 240, 0.4);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.action-btn.preview-btn {
  background: rgba(15, 23, 42, 0.04);
  color: var(--color-text-secondary);
}

.action-btn.preview-btn:hover {
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
}

.action-btn.learn-btn {
  justify-content: flex-end;
  background: transparent;
  color: #6366f1;
}

.action-btn.learn-btn:hover {
  color: #4f46e5;
}

.action-btn.learn-btn span {
  transition: transform 0.2s ease;
}

.action-btn.learn-btn:hover span {
  transform: translateX(4px);
}

/* ================= EMPTY STATE ================= */
.empty-state-box {
  display: grid;
  place-items: center;
  align-content: center;
  min-height: 280px;
  padding: 40px;
  border: 2px dashed #cbd5e1;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.5);
  text-align: center;
  margin: 32px;
}

.empty-state-icon-wrapper {
  display: grid;
  place-items: center;
  width: 48px; height: 48px;
  border-radius: 14px;
  color: var(--color-text-faint);
  background: #f1f5f9;
  font-size: 24px;
}

.empty-state-box h3 {
  margin: 16px 0 0 0;
  font-size: 1rem;
  font-weight: 800;
  color: var(--color-text);
}

.empty-state-box p {
  max-width: 400px;
  margin: 8px 0 20px 0;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.clear-filter-btn {
  padding: 10px 24px;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 700;
  color: #6366f1;
  background: transparent;
  border: 1px solid #6366f1;
  cursor: pointer;
  transition: all 0.2s ease;
}

.clear-filter-btn:hover {
  background: rgba(99, 102, 241, 0.08);
}

/* ================= NEW TASK ACTION CARD ================= */
.new-task-action-card {
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border: none;
  color: #ffffff;
  text-align: center;
  padding: 32px;
}

.new-task-action-card h4 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 800;
  color: #ffffff;
}

.new-task-action-card p {
  margin: 12px 0 24px 0;
  font-size: 0.85rem;
  color: #94a3b8;
  line-height: 1.5;
}

.rebuild-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 14px 32px;
  border-radius: 14px;
  font-weight: 700;
  font-size: 0.95rem;
  color: #ffffff;
  background: #6366f1;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);
  transition: all 0.25s ease;
}

.rebuild-action-btn:hover {
  background: #4f46e5;
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
  transform: translateY(-2px);
}

/* ================= TYPE-SPECIFIC CARD COLORS ================= */
.visual-resource-card.type-content:hover { border-color: rgba(59, 130, 246, 0.3); }
.visual-resource-card.type-mindmap:hover { border-color: rgba(139, 92, 246, 0.3); }
.visual-resource-card.type-quiz:hover { border-color: rgba(16, 185, 129, 0.3); }
.visual-resource-card.type-code:hover { border-color: rgba(244, 63, 94, 0.3); }
.visual-resource-card.type-reading:hover { border-color: rgba(99, 102, 241, 0.3); }
.visual-resource-card.type-ppt:hover { border-color: rgba(245, 158, 11, 0.3); }
.visual-resource-card.type-video:hover { border-color: rgba(6, 182, 212, 0.3); }

/* ================= ARTWORK COMPONENT ================= */
.artwork {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.artwork.is-large {
  width: 120px;
  height: 120px;
}

/* Mindmap artwork */
.artwork-mindmap .map-center {
  position: absolute;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(139, 92, 246, 0.15);
  border: 2px solid rgba(139, 92, 246, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.65rem;
  font-weight: 800;
  color: #8B5CF6;
}

.artwork-mindmap .map-node {
  position: absolute;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(139, 92, 246, 0.1);
  border: 1px solid rgba(139, 92, 246, 0.2);
}

.artwork-mindmap .node-1 { top: 8px; left: 50%; }
.artwork-mindmap .node-2 { top: 50%; left: 8px; }
.artwork-mindmap .node-3 { top: 50%; right: 8px; }
.artwork-mindmap .node-4 { bottom: 8px; left: 50%; }

.artwork-mindmap .map-line {
  position: absolute;
  height: 1px;
  background: rgba(139, 92, 246, 0.2);
}

.artwork-mindmap .line-1 { width: 20px; top: 24px; left: 50%; }
.artwork-mindmap .line-2 { width: 20px; top: 50%; left: 24px; }
.artwork-mindmap .line-3 { width: 20px; top: 50%; right: 24px; }
.artwork-mindmap .line-4 { width: 20px; bottom: 24px; left: 50%; }

/* Quiz artwork */
.artwork-quiz .quiz-sheet {
  position: absolute;
  width: 48px;
  height: 56px;
  background: rgba(16, 185, 129, 0.05);
  border: 1px solid rgba(16, 185, 129, 0.15);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
}

.artwork-quiz .quiz-sheet i {
  width: 100%;
  height: 3px;
  background: rgba(16, 185, 129, 0.1);
}

.artwork-quiz .quiz-sheet b {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  background: rgba(16, 185, 129, 0.15);
}

.artwork-quiz .quiz-score {
  position: absolute;
  bottom: 8px;
  right: 8px;
  font-size: 0.6rem;
  font-weight: 900;
  color: #10b981;
}

/* Code artwork */
.artwork-code .code-window {
  position: absolute;
  width: 48px;
  height: 40px;
  background: rgba(244, 63, 94, 0.05);
  border: 1px solid rgba(244, 63, 94, 0.15);
  border-radius: 6px;
  overflow: hidden;
}

.artwork-code .code-dots {
  display: flex;
  gap: 3px;
  padding: 4px;
}

.artwork-code .code-dots::before,
.artwork-code .code-dots::after {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(244, 63, 94, 0.3);
}

.artwork-code .code-line {
  height: 2px;
  margin: 2px 4px;
  background: rgba(244, 63, 94, 0.1);
}

.artwork-code .code-badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  font-size: 0.55rem;
  font-weight: 800;
  color: #F43F5E;
  background: rgba(244, 63, 94, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

/* Reading artwork */
.artwork-reading .book {
  position: absolute;
  width: 32px;
  height: 40px;
  border-radius: 3px;
}

.artwork-reading .book-back {
  background: rgba(99, 102, 241, 0.1);
  border: 1px solid rgba(99, 102, 241, 0.2);
  left: -4px;
}

.artwork-reading .book-front {
  background: rgba(99, 102, 241, 0.05);
  border: 1px solid rgba(99, 102, 241, 0.15);
  left: 4px;
}

.artwork-reading .reading-mark {
  position: absolute;
  bottom: 4px;
  right: 8px;
  font-size: 0.7rem;
  color: #6366f1;
}

/* PPT artwork */
.artwork-ppt .slide {
  position: absolute;
  width: 36px;
  height: 24px;
  background: rgba(245, 158, 11, 0.05);
  border: 1px solid rgba(245, 158, 11, 0.15);
  border-radius: 3px;
}

.artwork-ppt .slide-back {
  top: 0;
  left: -4px;
}

.artwork-ppt .slide-front {
  top: 8px;
  left: 4px;
}

.artwork-ppt .slide-number {
  position: absolute;
  bottom: 8px;
  right: 8px;
  font-size: 0.55rem;
  font-weight: 800;
  color: #D97706;
}

/* Video artwork */
.artwork-video .video-screen {
  position: absolute;
  width: 48px;
  height: 32px;
  background: rgba(6, 182, 212, 0.05);
  border: 1px solid rgba(6, 182, 212, 0.15);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.artwork-video .play-button {
  width: 12px;
  height: 12px;
  background: rgba(6, 182, 212, 0.2);
  border-radius: 50%;
}

.artwork-video .video-track {
  position: absolute;
  bottom: 4px;
  width: 40px;
  height: 3px;
  background: rgba(6, 182, 212, 0.1);
  border-radius: 1px;
}

.artwork-video .video-time {
  position: absolute;
  bottom: 8px;
  right: 8px;
  font-size: 0.55rem;
  font-weight: 800;
  color: #06B6D4;
}

/* Content (document) artwork */
.artwork-content .document-back,
.artwork-content .document-front {
  position: absolute;
  width: 36px;
  height: 44px;
  border-radius: 4px;
}

.artwork-content .document-back {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  left: -4px;
}

.artwork-content .document-front {
  background: rgba(59, 130, 246, 0.05);
  border: 1px solid rgba(59, 130, 246, 0.15);
  left: 4px;
}

/* ================= RESPONSIVE ================= */
@media (max-width: 680px) {
  .brief-stats-row {
    flex-direction: column;
  }

  .recommended-actions {
    flex-direction: column;
  }

  .resource-card-bento-grid {
    grid-template-columns: 1fr;
  }
}
</style>
