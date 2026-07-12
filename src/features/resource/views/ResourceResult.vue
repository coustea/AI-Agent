<template>
  <div class="resource-result-page">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <header class="loading-header">
        <div class="sk skeleton-back"></div>

        <div class="loading-heading">
          <div class="sk skeleton-title"></div>
          <div class="sk skeleton-subtitle"></div>
        </div>

        <div class="sk skeleton-meta"></div>
      </header>

      <div class="loading-grid">
        <article
          v-for="index in 5"
          :key="index"
          class="loading-card"
        >
          <div class="loading-card-meta">
            <div class="sk skeleton-kind"></div>
            <div class="sk skeleton-format"></div>
          </div>

          <div class="sk skeleton-card-title"></div>
          <div class="sk skeleton-card-title short"></div>
          <div class="sk skeleton-preview"></div>
          <div class="sk skeleton-line"></div>
          <div class="sk skeleton-line short"></div>
          <div class="sk skeleton-action"></div>
        </article>
      </div>
    </div>

    <!-- 请求失败 -->
    <div v-else-if="error" class="error-state">
      <div class="error-panel">
        <PhWarningCircle class="error-icon" />

        <h2>资源加载失败</h2>

        <p>
          暂时无法获取本次生成的学习资源，请检查网络连接后重新加载。
        </p>

        <div class="error-actions">
          <button
            type="button"
            class="secondary-button"
            @click="goBack"
          >
            返回上一页
          </button>

          <button
            type="button"
            class="primary-button"
            @click="loadResource"
          >
            重新加载
          </button>
        </div>
      </div>
    </div>

    <!-- 资源内容 -->
    <template v-else-if="bundle">
      <header class="result-header">
        <div class="header-main">
          <button
            type="button"
            class="back-button"
            @click="goBack"
          >
            <PhArrowLeft />
            <span>返回</span>
          </button>

          <div class="header-title">
            <div class="title-row">
              <h1>个性化学习资源包</h1>

              <button
                v-if="isPartial"
                type="button"
                class="generation-status partial"
                title="查看部分完成说明"
                @click="showPartialInfo"
              >
                <i></i>
                部分完成
              </button>

              <span
                v-else
                class="generation-status completed"
              >
                <PhCheckCircle />
                生成完成
              </span>
            </div>

            <p :title="bundleSubtitle">
              {{ bundleSubtitle }}
            </p>
          </div>
        </div>

        <div class="header-meta">
          <span>
            <strong>{{ resourceCards.length }}</strong>
            项资源
          </span>

          <i></i>

          <span v-if="createdAt">
            <PhClock />
            {{ createdAt }}
          </span>
        </div>
      </header>

      <main class="resource-main">
        <section
          v-if="resourceCards.length"
          class="resource-grid"
        >
          <article
            v-for="card in resourceCards"
            :key="card.id"
            class="resource-card"
            :class="`type-${card.type}`"
            tabindex="0"
            role="button"
            :aria-label="`查看${card.title}`"
            @click="openPreview(card)"
            @keydown.enter.prevent="openPreview(card)"
            @keydown.space.prevent="openPreview(card)"
          >
            <header class="card-header">
              <div class="card-meta-row">
                <span class="resource-kind">
                  <i></i>
                  {{ getArtifactLabel(card.type) }}
                </span>

                <span class="format-label">
                  {{ card.format }}
                </span>
              </div>

              <h2 :title="card.title">
                {{ card.title }}
              </h2>
            </header>

            <div
              class="resource-cover"
              :class="`cover-${card.type}`"
              aria-hidden="true"
            >
              <!-- 课程讲解 -->
              <div
                v-if="card.type === 'content'"
                class="content-preview"
              >
                <div class="content-index">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>

                <div class="content-page">
                  <strong></strong>
                  <span></span>
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>

              <!-- 思维导图 -->
              <div
                v-else-if="card.type === 'mindmap'"
                class="mindmap-preview"
              >
                <span class="mindmap-center"></span>

                <span class="mindmap-node node-left-top"></span>
                <span class="mindmap-node node-left-bottom"></span>
                <span class="mindmap-node node-right-top"></span>
                <span class="mindmap-node node-right-bottom"></span>

                <i class="mindmap-line line-left-top"></i>
                <i class="mindmap-line line-left-bottom"></i>
                <i class="mindmap-line line-right-top"></i>
                <i class="mindmap-line line-right-bottom"></i>
              </div>

              <!-- 随堂练习 -->
              <div
                v-else-if="card.type === 'quiz'"
                class="quiz-preview"
              >
                <div class="quiz-question">
                  <b>01</b>
                  <span></span>
                </div>

                <div class="quiz-option">
                  <i>A</i>
                  <span></span>
                </div>

                <div class="quiz-option">
                  <i>B</i>
                  <span></span>
                </div>

                <div class="quiz-option correct">
                  <i>C</i>
                  <span></span>
                  <em>✓</em>
                </div>
              </div>

              <!-- 代码实操 -->
              <div
                v-else-if="card.type === 'code'"
                class="code-preview"
              >
                <div class="code-toolbar">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>

                <div class="code-body">
                  <div class="code-numbers">
                    <span>1</span>
                    <span>2</span>
                    <span>3</span>
                    <span>4</span>
                  </div>

                  <div class="code-content">
                    <i></i>
                    <i></i>
                    <i></i>
                    <i></i>
                  </div>
                </div>
              </div>

              <!-- 拓展阅读 -->
              <div
                v-else-if="card.type === 'reading'"
                class="reading-preview"
              >
                <div class="reading-page page-left">
                  <strong></strong>
                  <span></span>
                  <span></span>
                  <span></span>
                </div>

                <div class="reading-page page-right">
                  <strong></strong>
                  <span></span>

                  <div class="reading-chart">
                    <i></i>
                    <i></i>
                    <i></i>
                  </div>
                </div>
              </div>

              <!-- 教学课件 -->
              <div
                v-else-if="card.type === 'ppt'"
                class="ppt-preview"
              >
                <div class="ppt-slide slide-back-left"></div>
                <div class="ppt-slide slide-back-right"></div>

                <div class="ppt-slide slide-main">
                  <strong></strong>
                  <span></span>
                  <span></span>

                  <div class="ppt-chart">
                    <i></i>
                    <i></i>
                    <i></i>
                  </div>
                </div>
              </div>

              <!-- 动画讲解 -->
              <div
                v-else
                class="cartoon-preview"
              >
                <div class="cartoon-screen">
                  <span class="play-shape"></span>
                </div>

                <div class="cartoon-controls">
                  <i></i>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>

            <div class="card-content">
              <p>
                {{ card.summary }}
              </p>
            </div>

            <footer class="card-action">
              <span>
                {{ getActionText(card.type) }}
              </span>

              <PhArrowRight />
            </footer>
          </article>
        </section>

        <section v-else class="empty-state">
          <PhMagnifyingGlass />

          <h2>暂无可展示资源</h2>

          <p>
            当前资源包中没有已成功生成且可正常使用的学习内容。
          </p>

          <button
            type="button"
            @click="goBack"
          >
            返回上一页
          </button>
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
import {
  computed,
  onMounted,
  ref,
  shallowRef,
} from 'vue'

import {
  useRoute,
  useRouter,
} from 'vue-router'

import { toast } from 'vue-sonner'

import {
  PhArrowLeft,
  PhArrowRight,
  PhCheckCircle,
  PhClock,
  PhMagnifyingGlass,
  PhWarningCircle,
} from '@phosphor-icons/vue'

import PreviewDialog from '@/shared/content/PreviewDialog.vue'

import {
  getGeneratedResourceDetail,
  type GeneratedResourceBundle,
} from '@/features/resource/api/history'

import {
  getArtifactLabel,
} from '@/shared/content/kind'
import { recordLearningEvent } from '@/features/evaluation/api/evaluation'

type ResourceCard = {
  id: string
  type: string
  title: string
  summary: string
  format: string
  content: unknown
  resource: Record<string, any>
}

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref(false)

const bundle =
  shallowRef<GeneratedResourceBundle | null>(
    null,
  )

const activePreviewAgent =
  ref<string | null>(null)

const previewData = ref<unknown>(null)

const previewResource =
  ref<Record<string, any> | null>(null)

const reportedViewedResources = new Set<number>()

const RESOURCE_ORDER = [
  'content',
  'mindmap',
  'quiz',
  'code',
  'reading',
  'ppt',
  'cartoon',
] as const

const RESOURCE_TYPES = new Set<string>(
  RESOURCE_ORDER,
)

const resourceId = computed(() => {
  const id = Number(route.params.id)

  return Number.isFinite(id) && id > 0
    ? id
    : null
})

const isPartial = computed(
  () =>
    bundle.value?.status ===
    'partial_completed',
)

const createdAt = computed(() =>
  formatTime(
    bundle.value?.created_at || null,
  ),
)

const bundleSubtitle = computed(() => {
  const title = String(
    bundle.value?.title || '',
  ).trim()

  if (
    title &&
    title !== '个性化学习资源包'
  ) {
    return title
  }

  return '本次生成的课程讲解、练习与拓展内容已整理完成'
})

const rawResources = computed<
  Record<string, any>[]
>(() => {
  const resources =
    bundle.value?.resources ??
    (bundle.value as any)?.items

  return Array.isArray(resources)
    ? resources
    : []
})

const resourceCards = computed<
  ResourceCard[]
>(() =>
  rawResources.value
    .map(normalizeCard)
    .filter(
      (
        card,
      ): card is ResourceCard =>
        card !== null,
    )
    .sort((first, second) => {
      const firstIndex =
        RESOURCE_ORDER.indexOf(
          first.type as (
            typeof RESOURCE_ORDER
          )[number],
        )

      const secondIndex =
        RESOURCE_ORDER.indexOf(
          second.type as (
            typeof RESOURCE_ORDER
          )[number],
        )

      return (
        (firstIndex === -1
          ? 99
          : firstIndex) -
        (secondIndex === -1
          ? 99
          : secondIndex)
      )
    }),
)

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
    const response =
      await getGeneratedResourceDetail(
        resourceId.value,
      )

    bundle.value =
      response.data?.data || null

    error.value = !bundle.value
    if (bundle.value) {
      recordResourceViewed(resourceId.value)
    }
  } catch (exception) {
    console.error(
      'Failed to load resource detail:',
      exception,
    )

    bundle.value = null
    error.value = true

    toast.error('加载资源详情失败')
  } finally {
    loading.value = false
  }
}

function recordResourceViewed(id: number) {
  if (reportedViewedResources.has(id)) return
  reportedViewedResources.add(id)

  recordLearningEvent({
    module: 'resource',
    entity_id: String(id),
    event_type: 'resource_viewed',
    client_event_id: typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : 'evt-' + Math.random().toString(36).slice(2, 11) + '-' + Date.now(),
    occurred_at: new Date().toISOString(),
    event_metadata: {
      resource_id: id,
      resource_types: resourceCards.value.map(card => card.type),
    },
  }).catch(() => {})
}

function normalizeCard(
  resource: Record<string, any>,
): ResourceCard | null {
  const type = String(
    resource.type ||
      resource.agent_type ||
      resource.agentId ||
      '',
  )
    .trim()
    .toLowerCase()

  const status = String(
    resource.status || 'completed',
  )
    .trim()
    .toLowerCase()

  if (!RESOURCE_TYPES.has(type)) {
    return null
  }

  if (
    ![
      'finished',
      'completed',
      'success',
    ].includes(status)
  ) {
    return null
  }

  if (
    !hasContent(
      resource.content,
      type,
    )
  ) {
    return null
  }

  return {
    id: String(resource.id ?? type),
    type,
    title: getTitle(resource, type),
    summary: getSummary(
      resource,
      type,
    ),
    format: getFormat(
      resource,
      type,
    ),
    content: resource.content,
    resource,
  }
}

function getTitle(
  resource: Record<string, any>,
  type: string,
) {
  const resourceTitle =
    typeof resource.title === 'string'
      ? resource.title.trim()
      : ''

  if (resourceTitle) {
    return resourceTitle
  }

  return `${getArtifactLabel(type)} · ${
    bundleSubtitle.value
  }`
}

function getSummary(
  resource: Record<string, any>,
  type: string,
) {
  const candidates = [
    resource.summary,
    resource.description,
    resource.metadata?.summary,
    resource.metadata_json?.summary,
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

function getDefaultSummary(
  type: string,
) {
  const summaries: Record<
    string,
    string
  > = {
    content:
      '围绕学习目标组织系统讲解，帮助建立完整、清晰的知识框架。',
    mindmap:
      '梳理核心概念、层级关系和知识依赖，形成直观的知识结构。',
    quiz:
      '通过不同题型检测理解程度，用于学习后的即时练习与巩固。',
    code:
      '提供可阅读、可运行的代码案例，帮助将理论知识转化为实践能力。',
    reading:
      '补充相关课程资料与拓展阅读，便于继续深入学习。',
    ppt:
      '整合重点内容形成结构化课件，适合课堂展示与快速复习。',
    cartoon:
      '通过动画呈现概念变化、执行过程与知识之间的关系。',
  }

  return (
    summaries[type] ||
    '根据本次学习需求生成的个性化学习资源。'
  )
}

function getFormat(
  resource: Record<string, any>,
  type: string,
) {
  const rawFormat =
    resource.format ||
    resource.file_type ||
    resource.fileType

  if (
    typeof rawFormat === 'string' &&
    rawFormat.trim()
  ) {
    return normalizeFormat(rawFormat)
  }

  const formats: Record<
    string,
    string
  > = {
    content: 'Markdown',
    mindmap: 'Markmap',
    quiz: 'JSON',
    code: 'Code',
    reading: 'Links',
    ppt: 'Slides',
    cartoon: 'Video',
  }

  return formats[type] || 'Resource'
}

function normalizeFormat(
  rawFormat: string,
) {
  const value = rawFormat
    .trim()
    .toLowerCase()

  const formatMap: Record<
    string,
    string
  > = {
    markdown: 'Markdown',
    md: 'Markdown',
    markmap: 'Markmap',
    json: 'JSON',
    code: 'Code',
    links: 'Links',
    pdf: 'PDF',
    ppt: 'Slides',
    pptx: 'Slides',
    slides: 'Slides',
    mp4: 'Video',
    video: 'Video',
  }

  return (
    formatMap[value] ||
    rawFormat.trim()
  )
}

function hasContent(
  value: unknown,
  type?: string,
) {
  if (
    type === 'ppt' ||
    type === 'cartoon'
  ) {
    return true
  }

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

function getActionText(
  type: string,
) {
  const actionMap: Record<
    string,
    string
  > = {
    content: '查看课程讲解',
    mindmap: '打开思维导图',
    quiz: '查看练习题',
    code: '查看代码实操',
    reading: '查看拓展阅读',
    ppt: '查看教学课件',
    cartoon: '查看动画讲解',
  }

  return (
    actionMap[type] ||
    '查看资源内容'
  )
}

function openPreview(
  card: ResourceCard,
) {
  activePreviewAgent.value = card.type
  previewData.value = card.content
  previewResource.value =
    card.resource
}

function showPartialInfo() {
  toast.warning(
    '部分资源未能完成生成，当前仅展示已经成功生成且可以正常使用的学习资源。',
  )
}

function goBack() {
  router.back()
}

function formatTime(
  time: string | null,
) {
  if (!time) {
    return ''
  }

  const date = new Date(time)

  if (
    Number.isNaN(date.getTime())
  ) {
    return ''
  }

  return new Intl.DateTimeFormat(
    'zh-CN',
    {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    },
  ).format(date)
}
</script>

<style scoped>
.resource-result-page,
.resource-result-page * {
  box-sizing: border-box;
}

.resource-result-page {
  --page-background: #f5f7fb;
  --surface: #ffffff;
  --surface-soft: #f8fafc;

  --border: #dfe6ef;
  --border-soft: #e9eef4;
  --border-strong: #c1ccda;

  --text: #172033;
  --text-secondary: #536176;
  --text-muted: #8a96a7;

  width: 100%;
  min-height: 100%;
  padding:
    18px
    clamp(14px, 2vw, 26px)
    38px;

  background: var(--page-background);
  color: var(--text);

  font-family:
    var(
      --font-ui,
      system-ui,
      -apple-system,
      BlinkMacSystemFont,
      "Segoe UI",
      sans-serif
    );
}

/* =========================
   顶部
   ========================= */

.result-header {
  min-height: 66px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;

  padding:
    0 2px
    16px;

  border-bottom:
    1px solid var(--border);
}

.header-main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 14px;
}

.back-button {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 7px;

  border:
    1px solid
    var(--border-strong);
  border-radius: 8px;
  padding: 0 11px;

  background: var(--surface);
  color: var(--text-secondary);

  font: inherit;
  font-size: 12px;
  font-weight: 750;

  white-space: nowrap;
  cursor: pointer;

  transition:
    border-color 0.18s ease,
    background-color 0.18s ease,
    color 0.18s ease;
}

.back-button:hover {
  border-color: #94acd0;
  background: #f8fbff;
  color: #2563eb;
}

.back-button svg {
  width: 15px;
  height: 15px;
}

.header-title {
  min-width: 0;
}

.title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 9px;
}

.title-row h1 {
  margin: 0;

  color: var(--text);
  font-size:
    clamp(18px, 1.6vw, 22px);
  font-weight: 850;
  line-height: 1.25;
  letter-spacing: -0.025em;
}

.header-title > p {
  max-width:
    min(720px, 52vw);

  margin: 4px 0 0;
  overflow: hidden;

  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  line-height: 1.45;

  text-overflow: ellipsis;
  white-space: nowrap;
}

.generation-status {
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  gap: 5px;

  border-radius: 6px;
  padding: 0 8px;

  font: inherit;
  font-size: 10px;
  font-weight: 800;
  white-space: nowrap;
}

button.generation-status {
  cursor: pointer;
}

.generation-status.completed {
  border: 1px solid #b8e0d0;
  background: #effaf5;
  color: #087853;
}

.generation-status.completed svg {
  width: 13px;
  height: 13px;
}

.generation-status.partial {
  border: 1px solid #f1cf95;
  background: #fff9ed;
  color: #a96612;
}

.generation-status.partial:hover {
  border-color: #e5b963;
  background: #fff3dc;
}

.generation-status.partial i {
  width: 6px;
  height: 6px;
  flex: 0 0 6px;

  border-radius: 50%;
  background: #e69124;
}

.header-meta {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 11px;

  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 650;
  white-space: nowrap;
}

.header-meta > span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.header-meta strong {
  color: var(--text);
  font-size: 12px;
  font-weight: 850;
}

.header-meta svg {
  width: 13px;
  height: 13px;
  color: var(--text-muted);
}

.header-meta > i {
  width: 1px;
  height: 15px;
  background: var(--border);
}

/* =========================
   卡片网格
   ========================= */

.resource-main {
  margin-top: 18px;
}

.resource-grid {
  display: grid;
  grid-template-columns:
    repeat(
      auto-fit,
      minmax(
        min(286px, 100%),
        1fr
      )
    );
  grid-auto-rows: 1fr;
  gap: 15px;
}

.resource-card {
  --resource-accent: #3b82f6;
  --resource-accent-soft: #eff6ff;

  position: relative;
  min-width: 0;
  min-height: 342px;
  height: 100%;

  display: flex;
  flex-direction: column;

  overflow: hidden;

  border:
    1px solid
    var(--border);
  border-radius: 13px;

  background: var(--surface);

  box-shadow:
    0 3px 12px
    rgba(25, 42, 64, 0.035);

  cursor: pointer;
  outline: none;

  transition:
    transform 0.2s ease,
    border-color 0.2s ease,
    box-shadow 0.2s ease;
}

.resource-card::before {
  content: "";

  position: absolute;
  top: 0;
  right: 16px;
  left: 16px;
  z-index: 2;

  height: 3px;
  border-radius:
    0 0 999px 999px;

  background:
    var(--resource-accent);
}

.resource-card:hover {
  transform: translateY(-2px);

  border-color: #b6c4d5;

  box-shadow:
    0 10px 25px
    rgba(25, 42, 64, 0.075);
}

.resource-card:focus-visible {
  outline:
    3px solid
    rgba(37, 99, 235, 0.2);
  outline-offset: 3px;
}

.type-content {
  --resource-accent: #3b82f6;
  --resource-accent-soft: #eff6ff;
}

.type-mindmap {
  --resource-accent: #8b5cf6;
  --resource-accent-soft: #f5f3ff;
}

.type-quiz {
  --resource-accent: #10b981;
  --resource-accent-soft: #ecfdf5;
}

.type-code {
  --resource-accent: #526174;
  --resource-accent-soft: #f1f5f9;
}

.type-reading {
  --resource-accent: #f59e0b;
  --resource-accent-soft: #fffbeb;
}

.type-ppt {
  --resource-accent: #ef5350;
  --resource-accent-soft: #fff3f2;
}

.type-cartoon {
  --resource-accent: #6366f1;
  --resource-accent-soft: #eef2ff;
}

/* =========================
   卡片标题
   ========================= */

.card-header {
  min-height: 86px;
  padding:
    16px 14px 11px;
}

.card-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.resource-kind {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 7px;

  color: var(--text-secondary);
  font-size: 10px;
  font-weight: 800;
}

.resource-kind i {
  width: 7px;
  height: 7px;
  flex: 0 0 7px;

  border-radius: 50%;

  background:
    var(--resource-accent);
}

.format-label {
  flex: 0 0 auto;
  min-height: 21px;
  display: inline-flex;
  align-items: center;

  border:
    1px solid
    var(--border);
  border-radius: 6px;
  padding: 0 7px;

  background: var(--surface-soft);
  color: var(--text-muted);

  font-size: 9px;
  font-weight: 750;
  white-space: nowrap;
}

.card-header h2 {
  margin: 9px 0 0;
  overflow: hidden;

  color: var(--text);

  font-size: 13px;
  font-weight: 850;
  line-height: 1.45;
  letter-spacing: -0.012em;

  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

/* =========================
   预览封面
   ========================= */

.resource-cover {
  position: relative;
  height: 124px;
  flex: 0 0 124px;

  margin: 0 14px;
  overflow: hidden;

  border:
    1px solid
    #e4eaf1;
  border-radius: 10px;

  background:
    linear-gradient(
      rgba(148, 163, 184, 0.06) 1px,
      transparent 1px
    ),
    linear-gradient(
      90deg,
      rgba(148, 163, 184, 0.06) 1px,
      transparent 1px
    ),
    #fafbfd;

  background-size:
    24px 24px,
    24px 24px,
    auto;
}

.resource-cover::after {
  content: "";

  position: absolute;
  inset: 0;

  pointer-events: none;

  background:
    linear-gradient(
      135deg,
      transparent 45%,
      var(--resource-accent-soft)
    );

  opacity: 0.35;
}

/* 课程讲解 */

.content-preview {
  position: absolute;
  inset: 20px 26px;
  z-index: 1;

  display: grid;
  grid-template-columns: 48px 1fr;

  overflow: hidden;

  border:
    1px solid
    #d6e4f7;
  border-radius: 11px;

  background: #ffffff;

  box-shadow:
    0 8px 18px
    rgba(37, 99, 235, 0.08);
}

.content-index {
  display: grid;
  place-content: center;
  gap: 8px;

  background:
    linear-gradient(
      180deg,
      #3679e4,
      #5795ea
    );
}

.content-index span {
  width: 21px;
  height: 4px;

  border-radius: 999px;

  background:
    rgba(255, 255, 255, 0.75);
}

.content-page {
  display: grid;
  align-content: center;
  gap: 7px;

  padding: 14px 17px;
}

.content-page strong,
.content-page span {
  height: 5px;
  border-radius: 999px;
}

.content-page strong {
  width: 48%;
  background: #3979dd;
}

.content-page span {
  background: #dde7f3;
}

.content-page span:nth-child(2) {
  width: 94%;
}

.content-page span:nth-child(3) {
  width: 78%;
}

.content-page span:nth-child(4) {
  width: 86%;
}

.content-page span:nth-child(5) {
  width: 62%;
}

/* 思维导图 */

.mindmap-preview {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.mindmap-center,
.mindmap-node {
  position: absolute;
  z-index: 2;

  border-radius: 999px;
}

.mindmap-center {
  top: 50%;
  left: 50%;

  width: 64px;
  height: 34px;

  background:
    linear-gradient(
      135deg,
      #8254e7,
      #a484f2
    );

  transform:
    translate(-50%, -50%);

  box-shadow:
    0 8px 18px
    rgba(139, 92, 246, 0.15);
}

.mindmap-center::after {
  content: "";

  position: absolute;
  top: 13px;
  left: 20px;

  width: 24px;
  height: 7px;

  border-radius: 999px;

  background:
    rgba(255, 255, 255, 0.76);
}

.mindmap-node {
  width: 51px;
  height: 22px;

  border:
    2px solid
    #c7b8f8;

  background: #ffffff;
}

.mindmap-node::after {
  content: "";

  position: absolute;
  top: 7px;
  left: 12px;

  width: 25px;
  height: 4px;

  border-radius: 999px;

  background: #ddd5fb;
}

.node-left-top {
  top: 23px;
  left: 15%;
}

.node-left-bottom {
  bottom: 23px;
  left: 17%;
}

.node-right-top {
  top: 23px;
  right: 15%;
}

.node-right-bottom {
  right: 17%;
  bottom: 23px;
}

.mindmap-line {
  position: absolute;
  z-index: 1;

  height: 2px;

  background: #b799ee;

  transform-origin: left center;
}

.line-left-top {
  top: 49px;
  left: 30%;

  width: 67px;

  transform: rotate(24deg);
}

.line-left-bottom {
  top: 73px;
  left: 30%;

  width: 67px;

  transform: rotate(-24deg);
}

.line-right-top {
  top: 49px;
  left: 54%;

  width: 67px;

  transform: rotate(-24deg);
}

.line-right-bottom {
  top: 73px;
  left: 54%;

  width: 67px;

  transform: rotate(24deg);
}

/* 练习题 */

.quiz-preview {
  position: absolute;
  inset: 16px 24px;
  z-index: 1;

  display: grid;
  gap: 7px;
}

.quiz-question,
.quiz-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quiz-question b {
  min-height: 18px;
  display: inline-flex;
  align-items: center;

  border-radius: 999px;
  padding: 0 8px;

  background: #13aa79;
  color: #ffffff;

  font-size: 8px;
  font-weight: 850;
}

.quiz-question span {
  height: 6px;
  flex: 1;

  border-radius: 999px;

  background: #96a5b7;
}

.quiz-option {
  min-height: 19px;

  border:
    1px solid
    #dce5ee;
  border-radius: 999px;
  padding: 0 8px;

  background: #ffffff;
}

.quiz-option i {
  width: 14px;
  height: 14px;
  display: grid;
  place-items: center;

  border-radius: 50%;

  background: #dcfce7;
  color: #07845d;

  font-size: 8px;
  font-style: normal;
  font-weight: 850;
}

.quiz-option span {
  height: 4px;
  flex: 1;

  border-radius: 999px;

  background: #e1e7ee;
}

.quiz-option em {
  color: #0b9a6d;

  font-size: 10px;
  font-style: normal;
  font-weight: 900;
}

.quiz-option.correct {
  border-color: #a9e5ca;
}

.quiz-option.correct span {
  background: #aee8cf;
}

/* 代码 */

.code-preview {
  position: absolute;
  inset: 16px 22px;
  z-index: 1;

  overflow: hidden;

  border-radius: 11px;

  background: #111827;

  box-shadow:
    0 9px 20px
    rgba(15, 23, 42, 0.16);
}

.code-toolbar {
  height: 21px;
  display: flex;
  align-items: center;
  gap: 5px;

  padding-left: 10px;

  background: #212c3c;
}

.code-toolbar span {
  width: 6px;
  height: 6px;

  border-radius: 50%;

  background: #68778a;
}

.code-body {
  display: grid;
  grid-template-columns: 29px 1fr;
}

.code-numbers {
  display: grid;
  justify-items: center;
  gap: 6px;

  padding-top: 10px;

  color: #66758a;
  font-size: 8px;
}

.code-content {
  display: grid;
  gap: 7px;

  padding: 12px 14px 0;
}

.code-content i {
  height: 5px;

  border-radius: 999px;
}

.code-content i:nth-child(1) {
  width: 52%;
  background: #c082ef;
}

.code-content i:nth-child(2) {
  width: 82%;
  background: #63a4ef;
}

.code-content i:nth-child(3) {
  width: 66%;
  background: #86ddbd;
}

.code-content i:nth-child(4) {
  width: 75%;
  background: #f0a2ca;
}

/* 阅读 */

.reading-preview {
  position: absolute;
  inset: 18px 24px;
  z-index: 1;

  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3px;

  transform:
    perspective(500px)
    rotateX(4deg);
}

.reading-page {
  padding: 13px;

  border:
    1px solid
    #fed3a2;

  background: #ffffff;

  box-shadow:
    0 8px 18px
    rgba(217, 119, 6, 0.075);
}

.page-left {
  border-radius:
    11px 4px 4px 11px;
}

.page-right {
  border-radius:
    4px 11px 11px 4px;
}

.reading-page strong,
.reading-page > span {
  display: block;

  height: 5px;
  margin-bottom: 7px;

  border-radius: 999px;
}

.reading-page strong {
  width: 55%;

  background: #f2a23d;
}

.reading-page > span {
  background: #dfe5ec;
}

.reading-page > span:nth-child(2) {
  width: 88%;
}

.reading-page > span:nth-child(3) {
  width: 70%;
}

.reading-page > span:nth-child(4) {
  width: 80%;
}

.reading-chart {
  height: 28px;
  display: flex;
  align-items: end;
  gap: 6px;

  margin-top: 5px;
}

.reading-chart i {
  width: 13px;

  border-radius:
    4px 4px 0 0;

  background: #fb923c;
}

.reading-chart i:nth-child(1) {
  height: 10px;
}

.reading-chart i:nth-child(2) {
  height: 19px;
}

.reading-chart i:nth-child(3) {
  height: 27px;
}

/* PPT */

.ppt-preview {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.ppt-slide {
  position: absolute;

  border:
    1px solid
    #f4b9b7;
  border-radius: 9px;

  background: #ffffff;

  box-shadow:
    0 8px 18px
    rgba(239, 83, 80, 0.075);
}

.slide-main {
  top: 20px;
  right: 22%;
  bottom: 20px;
  left: 22%;
  z-index: 2;

  display: grid;
  align-content: center;
  gap: 6px;

  padding: 13px;
}

.slide-main strong,
.slide-main > span {
  height: 5px;

  border-radius: 999px;
}

.slide-main strong {
  width: 55%;
  background: #ee6662;
}

.slide-main > span {
  background: #f8d7d5;
}

.slide-main > span:nth-child(2) {
  width: 88%;
}

.slide-main > span:nth-child(3) {
  width: 68%;
}

.slide-back-left {
  top: 30px;
  bottom: 30px;
  left: 9%;

  width: 25%;

  opacity: 0.7;
}

.slide-back-right {
  top: 30px;
  right: 9%;
  bottom: 30px;

  width: 25%;

  opacity: 0.7;
}

.ppt-chart {
  height: 25px;
  display: flex;
  align-items: end;
  gap: 5px;
}

.ppt-chart i {
  width: 10px;

  border-radius:
    3px 3px 0 0;

  background: #ef7773;
}

.ppt-chart i:nth-child(1) {
  height: 9px;
}

.ppt-chart i:nth-child(2) {
  height: 17px;
}

.ppt-chart i:nth-child(3) {
  height: 24px;
}

/* 动画 */

.cartoon-preview {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.cartoon-screen {
  position: absolute;
  top: 17px;
  right: 23px;
  bottom: 37px;
  left: 23px;

  display: grid;
  place-items: center;

  border-radius: 11px;

  background:
    linear-gradient(
      135deg,
      #182235,
      #3a485f
    );

  box-shadow:
    0 9px 20px
    rgba(15, 23, 42, 0.15);
}

.play-shape {
  width: 0;
  height: 0;

  margin-left: 4px;

  border-top:
    12px solid transparent;
  border-bottom:
    12px solid transparent;
  border-left:
    19px solid
    rgba(255, 255, 255, 0.92);
}

.cartoon-controls {
  position: absolute;
  right: 25px;
  bottom: 18px;
  left: 25px;

  display: grid;
  grid-template-columns:
    auto 1.3fr 0.7fr;
  align-items: center;
  gap: 7px;
}

.cartoon-controls i {
  width: 7px;
  height: 7px;

  border-radius: 50%;

  background: #6c73e8;
}

.cartoon-controls span {
  height: 6px;

  border-radius: 999px;

  background: #cbd0fa;
}

/* =========================
   摘要与操作
   ========================= */

.card-content {
  min-height: 74px;
  flex: 1;

  padding:
    12px 14px
    10px;
}

.card-content p {
  margin: 0;
  overflow: hidden;

  color: var(--text-secondary);

  font-size: 11px;
  line-height: 1.62;

  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.card-action {
  min-height: 43px;
  display: flex;
  align-items: center;
  justify-content: space-between;

  margin-top: auto;

  border-top:
    1px solid
    var(--border-soft);
  padding: 0 14px;

  background: #ffffff;
  color: #2563eb;

  font-size: 11px;
  font-weight: 800;

  transition:
    background-color 0.18s ease;
}

.card-action svg {
  width: 15px;
  height: 15px;

  transition:
    transform 0.18s ease;
}

.resource-card:hover
  .card-action {
  background: #f8fbff;
}

.resource-card:hover
  .card-action svg {
  transform: translateX(3px);
}

/* =========================
   空状态
   ========================= */

.empty-state {
  min-height: 380px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;

  border:
    1px dashed
    #c6d1dd;
  border-radius: 13px;

  background: var(--surface);

  text-align: center;
}

.empty-state > svg {
  width: 38px;
  height: 38px;

  color: #98a5b5;
}

.empty-state h2 {
  margin: 0;

  color: var(--text);
  font-size: 17px;
  font-weight: 850;
}

.empty-state p {
  margin: 0;

  color: var(--text-muted);
  font-size: 12px;
}

.empty-state button {
  min-height: 34px;

  border:
    1px solid
    var(--border-strong);
  border-radius: 8px;
  padding: 0 14px;

  background: var(--surface);
  color: var(--text-secondary);

  font: inherit;
  font-size: 12px;
  font-weight: 750;

  cursor: pointer;
}

/* =========================
   失败状态
   ========================= */

.error-state {
  min-height: 520px;
  display: grid;
  place-items: center;
}

.error-panel {
  width: min(430px, 100%);

  border:
    1px solid
    var(--border);
  border-radius: 15px;
  padding: 38px 32px;

  background: var(--surface);

  text-align: center;

  box-shadow:
    0 18px 44px
    rgba(15, 23, 42, 0.07);
}

.error-icon {
  width: 39px;
  height: 39px;

  color: #e6992e;
}

.error-panel h2 {
  margin: 12px 0 0;

  color: var(--text);
  font-size: 18px;
  font-weight: 850;
}

.error-panel p {
  margin: 8px 0 0;

  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.65;
}

.error-actions {
  display: flex;
  justify-content: center;
  gap: 9px;

  margin-top: 21px;
}

.primary-button,
.secondary-button {
  min-height: 36px;

  border-radius: 8px;
  padding: 0 16px;

  font: inherit;
  font-size: 12px;
  font-weight: 800;

  cursor: pointer;
}

.primary-button {
  border:
    1px solid #3b82f6;

  background: #3b82f6;
  color: #ffffff;
}

.secondary-button {
  border:
    1px solid
    var(--border-strong);

  background: var(--surface);
  color: var(--text-secondary);
}

/* =========================
   加载骨架
   ========================= */

.loading-state {
  display: grid;
  gap: 18px;
}

.loading-header {
  min-height: 66px;
  display: flex;
  align-items: center;
  gap: 13px;

  padding-bottom: 16px;

  border-bottom:
    1px solid
    var(--border);
}

.loading-heading {
  flex: 1;
  display: grid;
  gap: 7px;
}

.loading-grid {
  display: grid;
  grid-template-columns:
    repeat(
      auto-fit,
      minmax(
        min(286px, 100%),
        1fr
      )
    );
  gap: 15px;
}

.loading-card {
  min-height: 342px;

  border:
    1px solid
    var(--border);
  border-radius: 13px;
  padding: 16px 14px;

  background: var(--surface);
}

.loading-card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sk {
  border-radius: 999px;

  background:
    linear-gradient(
      90deg,
      #eef2f7 25%,
      #e1e7ef 50%,
      #eef2f7 75%
    );

  background-size: 400% 100%;

  animation:
    skeleton-shimmer
    1.35s
    ease
    infinite;
}

.skeleton-back {
  width: 64px;
  height: 34px;

  border-radius: 8px;
}

.skeleton-title {
  width: 160px;
  height: 20px;
}

.skeleton-subtitle {
  width: 300px;
  max-width: 46vw;
  height: 10px;
}

.skeleton-meta {
  width: 170px;
  height: 14px;
}

.skeleton-kind {
  width: 72px;
  height: 11px;
}

.skeleton-format {
  width: 55px;
  height: 21px;

  border-radius: 6px;
}

.skeleton-card-title {
  width: 90%;
  height: 13px;

  margin-top: 14px;
}

.skeleton-card-title.short {
  width: 62%;
  margin-top: 7px;
}

.skeleton-preview {
  height: 124px;

  margin-top: 15px;

  border-radius: 10px;
}

.skeleton-line {
  width: 100%;
  height: 9px;

  margin-top: 13px;
}

.skeleton-line.short {
  width: 68%;
  margin-top: 8px;
}

.skeleton-action {
  width: 100px;
  height: 11px;

  margin-top: 24px;
}

@keyframes skeleton-shimmer {
  0% {
    background-position: 100% 50%;
  }

  100% {
    background-position: 0% 50%;
  }
}

/* =========================
   响应式
   ========================= */

@media (min-width: 1660px) {
  .resource-grid,
  .loading-grid {
    grid-template-columns:
      repeat(5, minmax(0, 1fr));
  }
}

@media (max-width: 1380px) {
  .resource-grid,
  .loading-grid {
    grid-template-columns:
      repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1040px) {
  .resource-grid,
  .loading-grid {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 780px) {
  .result-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .header-title > p {
    max-width:
      calc(100vw - 112px);
  }

  .header-meta {
    padding-left: 48px;
  }
}

@media (max-width: 660px) {
  .resource-result-page {
    padding:
      12px
      12px
      28px;
  }

  .header-main {
    width: 100%;
    align-items: flex-start;
  }

  .back-button span {
    display: none;
  }

  .back-button {
    width: 34px;
    justify-content: center;
    padding: 0;
  }

  .title-row h1 {
    font-size: 17px;
  }

  .header-title > p {
    max-width:
      calc(100vw - 76px);
    white-space: normal;
  }

  .header-meta {
    width: 100%;
    justify-content: flex-start;
    padding-left: 0;
  }

  .resource-grid,
  .loading-grid {
    grid-template-columns: 1fr;
  }

  .resource-card {
    min-height: 335px;
  }

  .mindmap-line {
    display: none;
  }
}

@media (
  prefers-reduced-motion: reduce
) {
  .resource-result-page *,
  .resource-result-page *::before,
  .resource-result-page *::after {
    animation-duration:
      0.01ms !important;
    animation-iteration-count:
      1 !important;
    transition-duration:
      0.01ms !important;
  }

  .resource-card:hover {
    transform: none;
  }
}
</style>
