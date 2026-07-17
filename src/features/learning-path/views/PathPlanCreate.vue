<template>
  <main class="page-container path-planner-page">
    <div class="planner-unified-container">
      <header class="workspace-brand-header">
        <div class="header-headline-group">
          <span class="agent-eyebrow">
            PATH PLANNER AI ENGINE
          </span>

          <h1>创建学习路径</h1>

          <p class="cognitive-subtext">
            自定义学习主题、目标与偏好，智能引擎将结合学习画像构建阶段清晰、依赖合理的个性化学习路径。
          </p>
        </div>

        <div class="header-action-group">
          <button
              class="planner-history-action"
              type="button"
              :disabled="isPlanning"
              @click="goHistory"
          >
            <span>历史路径记录</span>

            <ph-arrow-right
                class="arrow-symbol"
                :size="14"
                weight="bold"
            />
          </button>
        </div>
      </header>

      <div class="workspace-content-flow">
        <section
            class="horizontal-templates-gallery"
            aria-labelledby="template-gallery-title"
        >
          <div class="gallery-title-strip">
            <h2 id="template-gallery-title">
              常用路径模板
            </h2>

            <span>一键载入常见学习场景的参数配置</span>
          </div>

          <div class="templates-horizontal-grid">
            <button
                v-for="item in examples"
                :key="item.title"
                type="button"
                class="micro-template-gallery-card"
                :class="[
                item.tone,
                {
                  'is-selected': isExampleActive(item),
                },
              ]"
                :aria-pressed="isExampleActive(item)"
                @click="applyExample(item)"
            >
              <span
                  class="category-glow-dot"
                  aria-hidden="true"
              ></span>

              <span class="micro-card-meta">
                <strong>{{ item.title }}</strong>
                <span>{{ item.topic }}</span>
              </span>

              <span
                  v-if="isExampleActive(item)"
                  class="template-selected-mark"
                  aria-hidden="true"
              >
                <ph-check
                    :size="12"
                    weight="bold"
                />
              </span>
            </button>
          </div>
        </section>

        <section
            class="structured-form-panel"
            aria-label="学习路径参数配置"
        >
          <div class="form-grid-row">
            <div class="row-meta-pane">
              <span class="row-badge-num">
                01
              </span>

              <div class="row-headline-group">
                <h2 class="row-title-group">
                  <ph-tag
                      :size="17"
                      class="title-icon"
                  />

                  <span>学习主题</span>
                </h2>

                <p>
                  确定需要学习、复习或深入研究的核心科目与技术方向。
                </p>
              </div>
            </div>

            <div class="row-control-pane">
              <div class="input-container-box">
                <input
                    id="topic"
                    v-model.trim="form.topic"
                    maxlength="60"
                    type="text"
                    autocomplete="off"
                    placeholder="例如：操作系统、数据结构、计算机网络、Vue3"
                />
              </div>
            </div>
          </div>

          <div class="form-grid-row">
            <div class="row-meta-pane">
              <span class="row-badge-num">
                02
              </span>

              <div class="row-headline-group">
                <h2 class="row-title-group">
                  <ph-target
                      :size="17"
                      class="title-icon"
                  />

                  <span>学习目标</span>
                </h2>

                <p>
                  描述学习目的、重点内容和期望达到的掌握程度。
                </p>
              </div>
            </div>

            <div class="row-control-pane">
              <div class="textarea-container-box">
                <textarea
                    id="goal"
                    ref="goalRef"
                    v-model.trim="form.goal"
                    maxlength="500"
                    rows="3"
                    placeholder="例如：系统复习操作系统核心考点，重点掌握进程同步、死锁、内存管理和页面置换，用来准备期末考试。"
                    @input="autoResize"
                />

                <div class="textarea-info-bar">
                  <span>
                    建议包含学习目的、重点范围和预期掌握程度。
                  </span>

                  <span class="char-counter">
                    {{ form.goal.length }}/500
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div class="form-grid-row">
            <div class="row-meta-pane">
              <span class="row-badge-num">
                03
              </span>

              <div class="row-headline-group">
                <h2 class="row-title-group">
                  <ph-brain
                      :size="17"
                      class="title-icon"
                  />

                  <span>当前基础</span>
                </h2>

                <p>
                  添加已经掌握的先修知识，使路径起点与当前基础更贴合。
                </p>
              </div>
            </div>

            <div class="row-control-pane">
              <div class="tag-input-bezel-box">
                <div class="tag-inner-flex">
                  <span
                      v-for="item in form.currentKnowledge"
                      :key="item"
                      class="custom-tag-node"
                      :style="getKnowledgeToneStyle(item)"
                  >
                    <span
                        class="knowledge-tag-dot"
                        aria-hidden="true"
                    ></span>

                    <span class="knowledge-tag-label">
                      {{ item }}
                    </span>

                    <button
                        type="button"
                        class="tag-close-trigger"
                        :aria-label="`删除 ${item}`"
                        @click="removeKnowledge(item)"
                    >
                      <ph-x :size="11" />
                    </button>
                  </span>

                  <input
                      v-model.trim="knowledgeInput"
                      type="text"
                      autocomplete="off"
                      placeholder="输入后按 Enter 或失去焦点添加"
                      @keydown.enter.prevent="addKnowledge"
                      @keydown.backspace="removeLastKnowledge"
                      @blur="addKnowledge"
                  />
                </div>
              </div>

              <div
                  class="quick-tags-container"
                  aria-label="常用基础标签"
              >
                <button
                    v-for="item in quickKnowledge"
                    :key="item"
                    type="button"
                    class="planner-knowledge-option"
                    :class="{
                    'is-selected': form.currentKnowledge.includes(item),
                  }"
                    :style="getKnowledgeToneStyle(item)"
                    :aria-pressed="form.currentKnowledge.includes(item)"
                    @click="toggleKnowledge(item)"
                >
                  <span
                      class="knowledge-option-indicator"
                      aria-hidden="true"
                  >
                    <ph-check
                        v-if="form.currentKnowledge.includes(item)"
                        :size="11"
                        weight="bold"
                    />

                    <span v-else></span>
                  </span>

                  <span>{{ item }}</span>
                </button>
              </div>
            </div>
          </div>

          <div class="form-grid-row form-grid-row-last">
            <div class="row-meta-pane">
              <span class="row-badge-num">
                04
              </span>

              <div class="row-headline-group">
                <h2 class="row-title-group">
                  <ph-sliders
                      :size="17"
                      class="title-icon"
                  />

                  <span>学习偏好</span>
                </h2>

                <p>
                  调整学习场景、推进节奏、路径粒度和规划重点。
                </p>
              </div>
            </div>

            <div class="row-control-pane preferences-matrix">
              <div class="preference-flex-line">
                <span class="pref-field-label">
                  学习场景
                </span>

                <div
                    class="planner-option-group"
                    role="group"
                    aria-label="学习场景"
                >
                  <button
                      v-for="item in sceneOptions"
                      :key="item.value"
                      type="button"
                      class="planner-option"
                      :class="{
                      'is-selected': form.scene === item.value,
                    }"
                      :aria-pressed="form.scene === item.value"
                      @click="form.scene = item.value"
                  >
                    {{ item.label }}
                  </button>
                </div>
              </div>

              <div class="preference-flex-line">
                <span class="pref-field-label">
                  学习节奏
                </span>

                <div
                    class="planner-option-group"
                    role="group"
                    aria-label="学习节奏"
                >
                  <button
                      v-for="item in paceOptions"
                      :key="item.value"
                      type="button"
                      class="planner-option"
                      :class="{
                      'is-selected': form.pace === item.value,
                    }"
                      :aria-pressed="form.pace === item.value"
                      @click="form.pace = item.value"
                  >
                    {{ item.label }}
                  </button>
                </div>
              </div>

              <div class="preference-flex-line">
                <span class="pref-field-label">
                  路径粒度
                </span>

                <div
                    class="planner-option-group"
                    role="group"
                    aria-label="路径粒度"
                >
                  <button
                      v-for="item in granularityOptions"
                      :key="item.value"
                      type="button"
                      class="planner-option"
                      :class="{
                      'is-selected': form.granularity === item.value,
                    }"
                      :aria-pressed="form.granularity === item.value"
                      @click="form.granularity = item.value"
                  >
                    {{ item.label }}
                  </button>
                </div>
              </div>

              <div class="preference-flex-line">
                <span class="pref-field-label">
                  规划重点
                </span>

                <div
                    class="planner-option-group planner-focus-group"
                    role="group"
                    aria-label="规划重点"
                >
                  <button
                      v-for="item in focusOptions"
                      :key="item.value"
                      type="button"
                      class="planner-focus-option"
                      :class="{
                      'is-selected': form.focus.includes(item.value),
                    }"
                      :aria-pressed="form.focus.includes(item.value)"
                      @click="toggleFocus(item.value)"
                  >
                    <ph-check
                        v-if="form.focus.includes(item.value)"
                        :size="12"
                        weight="bold"
                    />

                    <span>{{ item.label }}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <footer class="form-action-footer">
            <div
                class="ai-readiness-inline-dashboard"
                :class="{
                'is-ready': canSubmit,
              }"
            >
              <div
                  class="dashboard-visual-pulse"
                  aria-hidden="true"
              >
                <div class="pulse-ring"></div>
                <div class="pulse-center-core"></div>
              </div>

              <div class="dashboard-inline-meta">
                <template v-if="canSubmit">
                  <strong>{{ submitStateTitle }}</strong>
                  <p>{{ submitStateDesc }}</p>
                </template>

                <template v-else>
                  <strong>规划参数未就绪</strong>

                  <p>
                    请补全
                    <span
                        :class="{
                        lack: !form.topic.trim(),
                      }"
                    >
                      学习主题
                    </span>
                    与
                    <span
                        :class="{
                        lack: form.goal.trim().length < 8,
                      }"
                    >
                      目标诉求
                    </span>
                    以激活路径规划引擎。
                  </p>
                </template>
              </div>
            </div>

            <div class="footer-buttons-cluster">
              <button
                  class="planner-secondary-action"
                  type="button"
                  :disabled="isSubmitting"
                  @click="resetForm"
              >
                <ph-arrow-clockwise :size="15" />
                <span>重置</span>
              </button>

              <button
                  class="planner-primary-action"
                  type="button"
                  :disabled="!canSubmit || isSubmitting"
                  @click="handleSubmit"
              >
                <ph-sparkle
                    v-if="!isSubmitting"
                    :size="15"
                    weight="fill"
                />

                <span v-if="!isSubmitting">
                  生成学习路径
                </span>

                <span v-else>
                  正在规划结构
                </span>
              </button>
            </div>
          </footer>
        </section>

        <footer class="workspace-flow-footnote">
          <div class="agile-notice-banner-box">
            <span class="mini-badge">
              NODE-ON-DEMAND GENERATION
            </span>

            <p>
              当前步骤仅构建学习阶段、核心节点顺序和前置依赖。进入具体节点后，系统再按需生成教程、知识图谱、视频、实操代码和自测题，避免一次性生成造成等待时间过长。
            </p>
          </div>
        </footer>
      </div>

      <transition name="modal-fade">
        <div
            v-if="isPlanning && isPlanningModalVisible"
            class="student-planning-modal-backdrop"
        >
          <section
              class="student-planning-modal-content"
              role="dialog"
              aria-modal="true"
              aria-labelledby="planning-modal-title"
              aria-describedby="planning-modal-description"
          >
            <template v-if="planningError">
              <div class="planning-result-state planning-error-state">
                <div
                    class="planning-state-icon error-icon"
                    aria-hidden="true"
                >
                  <ph-warning-circle
                      :size="30"
                      weight="fill"
                  />
                </div>

                <div class="planning-result-copy">
                  <h2 id="planning-modal-title">
                    学习路径生成失败
                  </h2>

                  <p id="planning-modal-description">
                    规划过程中遇到了问题，请检查参数后重新尝试。
                  </p>
                </div>

                <div class="planning-error-detail">
                  <strong>失败原因</strong>
                  <p>{{ planningError }}</p>
                </div>

                <div class="planning-result-actions">
                  <button
                      type="button"
                      class="modal-secondary-action"
                      @click="resetPlanningState"
                  >
                    返回修改参数
                  </button>

                  <button
                      type="button"
                      class="modal-primary-action"
                      @click="retryPlanning"
                  >
                    重新规划
                  </button>
                </div>
              </div>
            </template>

            <template v-else-if="isPlanningComplete">
              <div class="planning-result-state planning-success-state">
                <div
                    class="planning-state-icon success-icon"
                    aria-hidden="true"
                >
                  <ph-check
                      :size="30"
                      weight="bold"
                  />
                </div>

                <div class="planning-result-copy">
                  <h2 id="planning-modal-title">
                    学习路径已生成
                  </h2>

                  <p id="planning-modal-description">
                    路径阶段、知识节点与前置依赖已经编排完成。
                  </p>
                </div>

                <div class="success-summary-line">
                  <span class="success-summary-dot"></span>
                  <span>正在打开学习路径总览</span>
                </div>

                <div class="success-progress-track">
                  <div class="success-progress-fill"></div>
                </div>
              </div>
            </template>

            <template v-else>
              <header class="modal-loading-header">
                <div
                    class="premium-path-loader"
                    aria-hidden="true"
                >
                  <div class="spinner-double-ring"></div>

                  <ph-sparkle
                      :size="21"
                      class="sparkle-center-icon"
                      weight="fill"
                  />
                </div>

                <h2 id="planning-modal-title">
                  AI 正在构建您的学习路径
                </h2>

                <p id="planning-modal-description">
                  正在结合学习目标、当前基础和学习偏好编排知识节点。
                </p>
              </header>

              <div class="student-timeline-track">
                <div
                    v-for="(step, index) in planningSteps"
                    :key="step.key"
                    class="student-timeline-node"
                    :class="{
                    'is-active': currentPlanningIndex === index,
                    'is-done': currentPlanningIndex > index,
                  }"
                    :style="getPlanningStepStyle(step, index)"
                    :aria-current="currentPlanningIndex === index ? 'step' : undefined"
                >
                  <div class="node-circle-indicator">
                    <ph-check
                        v-if="currentPlanningIndex > index"
                        :size="12"
                        weight="bold"
                    />

                    <span v-else>
                      {{ index + 1 }}
                    </span>
                  </div>

                  <span class="node-text-label">
                    {{ step.title }}
                  </span>

                  <div
                      v-if="index < planningSteps.length - 1"
                      class="node-connecting-dash"
                  ></div>
                </div>
              </div>

              <div class="student-progress-dashboard">
                <div class="progress-stage-header">
                  <div class="progress-stage-copy">
                    <span class="progress-stage-label">
                      当前阶段
                    </span>

                    <strong>
                      {{ currentPlanningStepTitle }}
                    </strong>
                  </div>

                  <div class="progress-step-count">
                    第 {{ currentPlanningStepNumber }}
                    / {{ planningSteps.length }} 步
                  </div>
                </div>

                <div
                    class="progress-bar-minimal"
                    role="progressbar"
                    :aria-valuenow="Math.round(planningProgress)"
                    aria-valuemin="0"
                    aria-valuemax="100"
                    :aria-label="currentPlanningStepTitle"
                >
                  <div
                      class="progress-bar-minimal-fill"
                      :style="{
                      transform: `scaleX(${planningProgress / 100})`,
                    }"
                  ></div>
                </div>
              </div>

              <div
                  class="student-friendly-log-box"
                  aria-live="polite"
                  aria-atomic="true"
              >
                <div
                    v-for="log in visiblePlanningLogs"
                    :key="log.sequence"
                    class="friendly-log-row"
                >
                  <span class="friendly-log-dot"></span>

                  <span class="friendly-log-text">
                    {{ log.message }}
                  </span>
                </div>
              </div>

              <div class="planning-result-actions">
                <button
                    type="button"
                    class="modal-secondary-action"
                    @click="minimizePlanningToBackground"
                >
                  后台运行（前往路径历史）
                </button>
              </div>
            </template>
          </section>
        </div>
      </transition>
    </div>
  </main>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  reactive,
  ref,
} from 'vue'
import type { CSSProperties } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { createLearningPath } from '@/features/learning-path/api/path'

import type {
  PathRequest,
} from '@/features/learning-path/model/path'
import type { PathEvent } from '@/features/learning-path/model/pathEvent'
import { usePathEvents } from '@/features/learning-path/composables/usePathEvents'

type Scene =
    | 'exam'
    | 'beginner'
    | 'project'
    | 'interview'
    | 'general'

type Pace =
    | 'slow'
    | 'normal'
    | 'fast'

type Granularity =
    | 'coarse'
    | 'standard'
    | 'fine'

type Focus =
    | 'foundation'
    | 'key_points'
    | 'practice'
    | 'weakness'

type ExampleTone =
    | 'teal'
    | 'blue'
    | 'amber'
    | 'violet'

interface ExampleItem {
  title: string
  topic: string
  goal: string
  currentKnowledge: string[]
  scene: Scene
  pace: Pace
  granularity: Granularity
  focus: Focus[]
  tone: ExampleTone
}

interface PlanningStepTone {
  start: string
  end: string
  soft: string
  text: string
  glow: string
}

interface PlanningStep {
  key: string
  title: string
  threshold: number
  tone: PlanningStepTone
}

interface PlanningLog {
  sequence: number
  message: string
}

const router = useRouter()

const goalRef = ref<HTMLTextAreaElement | null>(null)
const knowledgeInput = ref('')

const isSubmitting = ref(false)
const isPlanning = ref(false)
const isPlanningModalVisible = ref(false)

const planningProgress = ref(0)
const planningLogs = ref<PlanningLog[]>([])
const planningError = ref('')

const pathEvents = usePathEvents()
let isUnmounted = false
let hasTerminalEvent = false
let pathWaitController: AbortController | null = null
let pendingPlanningEvents: PathEvent[] = []
let planningEventFrame: number | null = null
let planningAttempt = 0

const form = reactive({
  topic: '',
  goal: '',
  currentKnowledge: [] as string[],
  scene: 'general' as Scene,
  pace: 'normal' as Pace,
  granularity: 'standard' as Granularity,
  focus: ['key_points'] as Focus[],
})

const sceneOptions = [
  {
    label: '通用学习',
    value: 'general' as Scene,
  },
  {
    label: '考试复习',
    value: 'exam' as Scene,
  },
  {
    label: '基础入门',
    value: 'beginner' as Scene,
  },
  {
    label: '项目实战',
    value: 'project' as Scene,
  },
  {
    label: '面试准备',
    value: 'interview' as Scene,
  },
]

const paceOptions = [
  {
    label: '慢速细学',
    value: 'slow' as Pace,
  },
  {
    label: '正常节奏',
    value: 'normal' as Pace,
  },
  {
    label: '快速推进',
    value: 'fast' as Pace,
  },
]

const granularityOptions = [
  {
    label: '粗略路径',
    value: 'coarse' as Granularity,
  },
  {
    label: '标准路径',
    value: 'standard' as Granularity,
  },
  {
    label: '细节点路径',
    value: 'fine' as Granularity,
  },
]

const focusOptions = [
  {
    label: '补基础',
    value: 'foundation' as Focus,
  },
  {
    label: '抓重点',
    value: 'key_points' as Focus,
  },
  {
    label: '多练习',
    value: 'practice' as Focus,
  },
  {
    label: '补薄弱点',
    value: 'weakness' as Focus,
  },
]

const quickKnowledge = [
  'Python',
  'C++',
  'Java',
  '数据结构基础',
  '操作系统基础',
  '计算机网络基础',
  '数据库基础',
  'Linux',
]

const knowledgeTones = [
  {
    start: '#5b87d8',
    end: '#7ca2e5',
    soft: '#f3f7fd',
    border: '#c8d8ef',
    text: '#3f6398',
    glow: 'rgba(91, 135, 216, 0.12)',
  },
  {
    start: '#786ccc',
    end: '#998fe0',
    soft: '#f6f4fd',
    border: '#d2cced',
    text: '#5c52a0',
    glow: 'rgba(120, 108, 204, 0.12)',
  },
  {
    start: '#d1844c',
    end: '#e2a06e',
    soft: '#fff7f1',
    border: '#efd0b7',
    text: '#9b6139',
    glow: 'rgba(209, 132, 76, 0.12)',
  },
  {
    start: '#c3982f',
    end: '#d6b65f',
    soft: '#fffbef',
    border: '#eadcae',
    text: '#896b20',
    glow: 'rgba(195, 152, 47, 0.12)',
  },
  {
    start: '#cf7863',
    end: '#df9988',
    soft: '#fff5f2',
    border: '#edc8bf',
    text: '#985747',
    glow: 'rgba(207, 120, 99, 0.12)',
  },
  {
    start: '#896fc2',
    end: '#a690d2',
    soft: '#f8f5fc',
    border: '#d8cdec',
    text: '#665292',
    glow: 'rgba(137, 111, 194, 0.12)',
  },
  {
    start: '#3b95a2',
    end: '#66aeb8',
    soft: '#f1f9fa',
    border: '#badde1',
    text: '#2a6c75',
    glow: 'rgba(59, 149, 162, 0.12)',
  },
  {
    start: '#4f9472',
    end: '#77ad8e',
    soft: '#f2f9f5',
    border: '#bfddcc',
    text: '#386b52',
    glow: 'rgba(79, 148, 114, 0.12)',
  },
] as const

const knowledgeToneAliases: Record<string, number> = {
  python: 0,
  css: 0,
  '计算机网络': 0,
  '计算机网络基础': 0,
  'c++': 1,
  '数据结构': 5,
  '数据结构基础': 5,
  '数组': 5,
  '链表': 5,
  java: 2,
  '操作系统': 2,
  '操作系统基础': 2,
  javascript: 3,
  js: 3,
  html: 4,
  'c语言': 4,
  '数据库': 6,
  '数据库基础': 6,
  sql: 6,
  linux: 7,
}

const planningSteps: PlanningStep[] = [
  {
    key: 'profile',
    title: '结合学习画像',
    threshold: 10,
    tone: {
      start: '#4f8cf7',
      end: '#70b1ff',
      soft: '#edf5ff',
      text: '#356eb8',
      glow: 'rgba(79, 140, 247, 0.18)',
    },
  },
  {
    key: 'stage',
    title: '拆解学习阶段',
    threshold: 30,
    tone: {
      start: '#796fe8',
      end: '#a88bff',
      soft: '#f2efff',
      text: '#6252b8',
      glow: 'rgba(121, 111, 232, 0.18)',
    },
  },
  {
    key: 'node',
    title: '编排知识节点',
    threshold: 52,
    tone: {
      start: '#ee9154',
      end: '#f3be69',
      soft: '#fff4e8',
      text: '#a76032',
      glow: 'rgba(238, 145, 84, 0.19)',
    },
  },
  {
    key: 'validate',
    title: '校验路径依赖',
    threshold: 74,
    tone: {
      start: '#d96d9c',
      end: '#ef9cbe',
      soft: '#fff0f6',
      text: '#a54f78',
      glow: 'rgba(217, 109, 156, 0.18)',
    },
  },
  {
    key: 'save',
    title: '保存路径结构',
    threshold: 90,
    tone: {
      start: '#1fa899',
      end: '#56c7b9',
      soft: '#eaf9f6',
      text: '#14766d',
      glow: 'rgba(31, 168, 153, 0.19)',
    },
  },
]

const examples: ExampleItem[] = [
  {
    title: '操作系统期末复习',
    topic: '操作系统',
    goal: '系统复习操作系统核心考点，重点掌握进程同步、死锁、内存管理和页面置换，用来准备期末考试。',
    currentKnowledge: [
      '进程基础',
      'C语言',
    ],
    scene: 'exam',
    pace: 'normal',
    granularity: 'fine',
    focus: [
      'key_points',
      'weakness',
      'practice',
    ],
    tone: 'amber',
  },
  {
    title: '数据结构刷题路线',
    topic: '数据结构与算法',
    goal: '掌握栈、队列、树、图、排序和搜索等基础数据结构与算法，并能完成基础编程题。',
    currentKnowledge: [
      'Python',
      '数组',
      '链表',
    ],
    scene: 'general',
    pace: 'normal',
    granularity: 'standard',
    focus: [
      'key_points',
      'practice',
    ],
    tone: 'teal',
  },
  {
    title: '计算机网络入门',
    topic: '计算机网络',
    goal: '从基础开始学习计算机网络，理解分层模型、TCP/IP、HTTP、DNS 和常见网络协议。',
    currentKnowledge: [],
    scene: 'beginner',
    pace: 'slow',
    granularity: 'fine',
    focus: [
      'foundation',
      'key_points',
    ],
    tone: 'blue',
  },
  {
    title: 'Vue 项目学习路线',
    topic: 'Vue3',
    goal: '通过项目实战学习 Vue3，掌握组件、路由、状态管理、接口请求和页面样式设计。',
    currentKnowledge: [
      'HTML',
      'CSS',
      'JavaScript',
    ],
    scene: 'project',
    pace: 'normal',
    granularity: 'standard',
    focus: [
      'practice',
      'key_points',
    ],
    tone: 'violet',
  },
]

const canSubmit = computed(() => {
  return (
      form.topic.trim().length > 0 &&
      form.goal.trim().length >= 8
  )
})

const submitStateTitle = computed(() => {
  if (!form.topic.trim()) {
    return '请先填写学习主题'
  }

  if (form.goal.trim().length < 8) {
    return '请补充学习目标'
  }

  return '规划参数已完整'
})

const submitStateDesc = computed(() => {
  if (!form.topic.trim()) {
    return '学习主题用于确定路径的知识范围与结构边界。'
  }

  if (form.goal.trim().length < 8) {
    return '请至少输入 8 个字以上的学习目标描述。'
  }

  return '系统将结合学习画像、已有基础和偏好生成路径骨架。'
})

const currentPlanningIndex = computed(() => {
  for (
      let index = planningSteps.length - 1;
      index >= 0;
      index -= 1
  ) {
    const step = planningSteps[index]

    if (
        step &&
        planningProgress.value >= step.threshold
    ) {
      return index
    }
  }

  return 0
})

const isPlanningComplete = computed(() => {
  return planningProgress.value >= 100
})

const currentPlanningStepTitle = computed(() => {
  if (isPlanningComplete.value) {
    return '路径结构已生成'
  }

  return (
      planningSteps[currentPlanningIndex.value]?.title ||
      '准备规划任务'
  )
})

const currentPlanningStepNumber = computed(() => {
  if (isPlanningComplete.value) {
    return planningSteps.length
  }

  return Math.min(
      currentPlanningIndex.value + 1,
      planningSteps.length,
  )
})

const visiblePlanningLogs = computed(() => {
  return planningLogs.value.slice(-3)
})

function getPlanningStepStyle(
    step: PlanningStep,
    index: number,
): CSSProperties {
  const nextStep =
      planningSteps[index + 1] ?? step

  return {
    '--timeline-node-start': step.tone.start,
    '--timeline-node-end': step.tone.end,
    '--timeline-node-soft': step.tone.soft,
    '--timeline-node-text': step.tone.text,
    '--timeline-node-glow': step.tone.glow,
    '--timeline-next-start': nextStep.tone.start,
  } as CSSProperties
}

function getKnowledgeToneStyle(
    value: string,
): CSSProperties {
  const normalized = value.trim().toLowerCase()
  const mappedIndex = knowledgeToneAliases[normalized]

  let toneIndex = mappedIndex

  if (toneIndex === undefined) {
    let hash = 0

    for (const char of normalized) {
      hash = (
          hash * 31 +
          char.codePointAt(0)!
      ) >>> 0
    }

    toneIndex = hash % knowledgeTones.length
  }

  const tone = knowledgeTones[toneIndex]!

  return {
    '--knowledge-tone-start': tone.start,
    '--knowledge-tone-end': tone.end,
    '--knowledge-tone-soft': tone.soft,
    '--knowledge-tone-border': tone.border,
    '--knowledge-tone-text': tone.text,
    '--knowledge-tone-glow': tone.glow,
  } as CSSProperties
}

function autoResize() {
  if (!goalRef.value) {
    return
  }

  goalRef.value.style.height = 'auto'
  goalRef.value.style.height =
      `${Math.min(goalRef.value.scrollHeight, 150)}px`
}

function addKnowledge() {
  const value = knowledgeInput.value.trim()

  if (!value) {
    return
  }

  if (form.currentKnowledge.includes(value)) {
    toast.warning('请勿重复添加相同的先修知识')
    knowledgeInput.value = ''
    return
  }

  form.currentKnowledge.push(value)
  knowledgeInput.value = ''
}

function removeKnowledge(value: string) {
  form.currentKnowledge =
      form.currentKnowledge.filter(
          item => item !== value,
      )
}

function removeLastKnowledge() {
  if (
      knowledgeInput.value ||
      !form.currentKnowledge.length
  ) {
    return
  }

  form.currentKnowledge.pop()
}

function toggleKnowledge(value: string) {
  if (form.currentKnowledge.includes(value)) {
    removeKnowledge(value)
    return
  }

  form.currentKnowledge.push(value)
}

function toggleFocus(value: Focus) {
  if (form.focus.includes(value)) {
    if (form.focus.length === 1) {
      toast.warning('至少保留一个规划重点')
      return
    }

    form.focus = form.focus.filter(
        item => item !== value,
    )

    return
  }

  form.focus.push(value)
}

function isExampleActive(item: ExampleItem) {
  return (
      form.topic === item.topic &&
      form.goal === item.goal
  )
}

function applyExample(item: ExampleItem) {
  form.topic = item.topic
  form.goal = item.goal
  form.currentKnowledge = [
    ...item.currentKnowledge,
  ]
  form.scene = item.scene
  form.pace = item.pace
  form.granularity = item.granularity
  form.focus = [
    ...item.focus,
  ]

  nextTick(autoResize)
}

function resetForm() {
  if (isSubmitting.value) {
    return
  }

  form.topic = ''
  form.goal = ''
  form.currentKnowledge = []
  form.scene = 'general'
  form.pace = 'normal'
  form.granularity = 'standard'
  form.focus = ['key_points']
  knowledgeInput.value = ''

  nextTick(autoResize)
}

function goHistory() {
  router.push('/path-planner/history')
}

function buildPayload(): PathRequest {
  return {
    goal: form.goal.trim(),
    topic: form.topic.trim(),
    current_knowledge: [
      ...form.currentKnowledge,
    ],
    preferences: {
      use_profile: true,
      scene: form.scene,
      pace: form.pace,
      granularity: form.granularity,
      focus: [
        ...form.focus,
      ],
    },
  }
}

function clearPendingPlanningEvents() {
  pendingPlanningEvents = []

  if (planningEventFrame !== null) {
    window.cancelAnimationFrame(planningEventFrame)
    planningEventFrame = null
  }
}

function flushPlanningEvents() {
  if (!pendingPlanningEvents.length) {
    return
  }

  const events = pendingPlanningEvents
  pendingPlanningEvents = []

  const displayedSequences = new Set(
      planningLogs.value.map(log => log.sequence),
  )
  const nextLogs = [...planningLogs.value]
  let nextProgress = planningProgress.value

  for (const event of events) {
    if (typeof event.progress === 'number') {
      nextProgress = Math.max(
          nextProgress,
          Math.min(event.progress, 100),
      )
    }

    if (
        event.message &&
        !displayedSequences.has(event.sequence)
    ) {
      displayedSequences.add(event.sequence)
      nextLogs.push({
        sequence: event.sequence,
        message: event.message,
      })
    }
  }

  planningProgress.value = nextProgress
  planningLogs.value = nextLogs
}

function queuePlanningEvent(event: PathEvent) {
  pendingPlanningEvents.push(event)

  if (planningEventFrame !== null) {
    return
  }

  planningEventFrame = window.requestAnimationFrame(() => {
    planningEventFrame = null
    flushPlanningEvents()
  })
}

function startPlanningProgress() {
  clearPendingPlanningEvents()
  planningProgress.value = 0
  planningLogs.value = [
    {
      sequence: 0,
      message: '规划任务已提交，正在连接实时进度。',
    },
  ]
}

function resetPlanningState() {
  planningAttempt += 1
  pathWaitController?.abort()
  pathWaitController = null
  pathEvents.reset()
  clearPendingPlanningEvents()
  hasTerminalEvent = false

  isPlanning.value = false
  isSubmitting.value = false
  planningProgress.value = 0
  planningLogs.value = []
  planningError.value = ''
}

function minimizePlanningToBackground() {
  isPlanningModalVisible.value = false
  router.push('/path-planner/history')
}

async function retryPlanning() {
  resetPlanningState()

  await nextTick()
  await handleSubmit()
}

function delay(ms: number) {
  return new Promise<void>(resolve => {
    window.setTimeout(resolve, ms)
  })
}

function handleSSEEvent(event: PathEvent) {
  queuePlanningEvent(event)
}

async function waitForPathReady(
    pathId: number,
    runId: string,
) {
  pathWaitController?.abort()
  const controller = new AbortController()
  pathWaitController = controller
  hasTerminalEvent = false

  try {
    await new Promise<void>((resolve, reject) => {
      const cleanup = () => {
        controller.signal.removeEventListener(
            'abort',
            handleAbort,
        )
      }

      const handleAbort = () => {
        cleanup()
        resolve()
      }

      const completePlanning = async (event: PathEvent) => {
        if (hasTerminalEvent) {
          return
        }

        hasTerminalEvent = true
        handleSSEEvent(event)
        flushPlanningEvents()
        planningProgress.value = 100
        pathEvents.close()

        try {
          await nextTick()
          await delay(450)

          if (!isUnmounted) {
            await router.replace({
              path: `/path-planner/overview/${pathId}`,
              query: { run_id: runId },
            })
          }

          resolve()
        } catch (error) {
          reject(error)
        } finally {
          cleanup()
        }
      }

      const failPlanning = (error: Error, event: PathEvent) => {
        if (hasTerminalEvent) {
          return
        }

        hasTerminalEvent = true
        handleSSEEvent(event)
        flushPlanningEvents()
        pathEvents.close()
        planningError.value =
            error.message ||
            '路径规划未能完成，请调整参数后重试。'
        toast.error(planningError.value)
        cleanup()
        resolve()
      }

      controller.signal.addEventListener(
          'abort',
          handleAbort,
          { once: true },
      )

      pathEvents.connect(pathId, runId, {
        onEvent: handleSSEEvent,
        onCompleted: completePlanning,
        onFailed: failPlanning,
      })
    })
  } finally {
    if (pathWaitController === controller) {
      pathWaitController = null
    }
  }
}

async function handleSubmit() {
  if (
      isSubmitting.value ||
      isPlanning.value
  ) {
    return
  }

  if (!form.topic.trim()) {
    toast.warning('请输入学习主题')
    return
  }

  if (!form.goal.trim()) {
    toast.warning('请输入学习目标')
    return
  }

  if (form.goal.trim().length < 8) {
    toast.warning(
        '学习目标太短，请补充学习内容或预期目标',
    )
    return
  }

  const attempt = ++planningAttempt
  isSubmitting.value = true
  isPlanning.value = true
  isPlanningModalVisible.value = true
  planningError.value = ''

  startPlanningProgress()

  try {
    const response =
        await createLearningPath(
            buildPayload(),
        )

    const data = response.data.data
    const pathId = data.id
    const runId = data.run_id || ''

    if (!pathId) {
      throw new Error(
          '服务器未返回有效的路径标识，请稍后重试。',
      )
    }

    if (!runId) {
      throw new Error(
          '服务器未返回实时任务标识，请稍后重试。',
      )
    }

    await waitForPathReady(pathId, runId)
  } catch (error) {
    planningProgress.value =
        Math.min(
            planningProgress.value,
            96,
        )

    planningError.value =
        error instanceof Error
            ? error.message
            : '路径规划未能完成，请稍后重试。'

    toast.error(planningError.value)

    if (!isPlanningModalVisible.value) {
      resetPlanningState()
    }
  } finally {
    if (attempt === planningAttempt) {
      isSubmitting.value = false
    }
  }
}

onBeforeUnmount(() => {
  isUnmounted = true
  planningAttempt += 1
  hasTerminalEvent = true
  pathWaitController?.abort()
  pathWaitController = null
  pathEvents.close()
  clearPendingPlanningEvents()
})
</script>

<style scoped>
.path-planner-page {
  --planner-accent: #159a94;
  --planner-accent-hover: #10847f;
  --planner-accent-soft: #eaf7f6;
  --planner-accent-softer: #f4fbfa;
  --planner-accent-border: #82cbc7;
  --planner-accent-text: #176b67;
  --planner-focus-ring: rgba(21, 154, 148, 0.14);

  --planner-text: #26383c;
  --planner-text-strong: #172d31;
  --planner-text-secondary: #607277;
  --planner-text-muted: #839397;
  --planner-text-faint: #9ca9ac;

  --planner-border: #dce7e6;
  --planner-border-light: #e9efee;
  --planner-surface: #ffffff;
  --planner-background: #f8faf9;

  --planner-font-heading: 25px;
  --planner-font-section: 15px;
  --planner-font-body: 14px;
  --planner-font-control: 13px;
  --planner-font-help: 12px;
  --planner-font-micro: 11px;

  --planner-line-heading: 1.3;
  --planner-line-body: 1.65;
  --planner-line-control: 1.45;
  --planner-line-help: 1.6;

  min-height: 100%;
  box-sizing: border-box;
  background:
      radial-gradient(
          circle at 84% 4%,
          rgba(21, 154, 148, 0.035),
          transparent 34rem
      ),
      var(--planner-background);
  color: var(--planner-text);
  font-size: var(--planner-font-body);
  line-height: var(--planner-line-body);
}

.path-planner-page *,
.path-planner-page *::before,
.path-planner-page *::after {
  box-sizing: border-box;
}

.path-planner-page button,
.path-planner-page input,
.path-planner-page textarea {
  font-family: inherit;
}

.planner-unified-container {
  width: min(
      var(--content-max-width, 1120px),
      calc(100% - 40px)
  );
  margin: 0 auto;
  padding: 24px 0 40px;
}

.workspace-content-flow {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.workspace-brand-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 32px;
  padding: 10px 4px 22px;
}

.header-headline-group {
  max-width: 720px;
}

.agent-eyebrow {
  display: block;
  color: var(--planner-accent);
  font-family: var(--font-mono, monospace);
  font-size: var(--planner-font-micro);
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: 0.11em;
  text-transform: uppercase;
}

.workspace-brand-header h1 {
  margin: 5px 0 7px;
  color: var(--planner-text-strong);
  font-size: var(--planner-font-heading);
  font-weight: 800;
  line-height: var(--planner-line-heading);
  letter-spacing: -0.025em;
}

.cognitive-subtext {
  margin: 0;
  color: var(--planner-text-secondary);
  font-size: var(--planner-font-control);
  line-height: var(--planner-line-body);
}

.header-action-group {
  flex-shrink: 0;
}

.planner-history-action {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 15px;
  border: 1px solid var(--planner-border);
  border-radius: 7px;
  background: var(--planner-surface);
  color: var(--planner-accent-text);
  font-size: var(--planner-font-control);
  font-weight: 700;
  line-height: var(--planner-line-control);
  cursor: pointer;
  transition:
      border-color 180ms ease,
      background-color 180ms ease,
      color 180ms ease,
      transform 180ms ease;
}

.planner-history-action:hover:not(:disabled) {
  border-color: var(--planner-accent-border);
  background: var(--planner-accent-softer);
  color: var(--planner-accent-hover);
}

.planner-history-action:focus-visible {
  outline: 3px solid var(--planner-focus-ring);
  outline-offset: 2px;
}

.planner-history-action:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.arrow-symbol {
  transition: transform 180ms ease;
}

.planner-history-action:hover:not(:disabled)
.arrow-symbol {
  transform: translateX(2px);
}

.horizontal-templates-gallery {
  display: flex;
  flex-direction: column;
  gap: 11px;
  padding: 0 4px;
}

.gallery-title-strip {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.gallery-title-strip h2 {
  margin: 0;
  color: var(--planner-text-strong);
  font-size: var(--planner-font-control);
  font-weight: 800;
  line-height: var(--planner-line-control);
  letter-spacing: 0.035em;
}

.gallery-title-strip > span {
  color: var(--planner-text-faint);
  font-size: var(--planner-font-help);
  line-height: var(--planner-line-help);
}

.templates-horizontal-grid {
  display: grid;
  grid-template-columns:
    repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.micro-template-gallery-card {
  --template-tone: #159a94;
  --template-tone-end: #47bdb5;
  --template-tone-soft: #eef9f8;
  --template-tone-softer: #f7fcfb;
  --template-tone-border: #91d4d0;
  --template-tone-text: #176b67;
  --template-tone-glow: rgba(21, 154, 148, 0.15);

  position: relative;
  display: grid;
  grid-template-columns:
    8px minmax(0, 1fr) 20px;
  align-items: center;
  gap: 10px;
  min-width: 0;
  height: 64px;
  padding: 10px 13px;
  overflow: hidden;
  border: 1px solid var(--planner-border);
  border-radius: 8px;
  background: var(--planner-surface);
  color: var(--template-tone);
  text-align: left;
  cursor: pointer;
  isolation: isolate;
  transition:
      border-color 180ms ease,
      background 180ms ease,
      box-shadow 180ms ease,
      transform 180ms ease;
}

.micro-template-gallery-card::before {
  position: absolute;
  z-index: -1;
  top: 0;
  bottom: 0;
  left: 0;
  width: 3px;
  background:
      linear-gradient(
          180deg,
          var(--template-tone),
          var(--template-tone-end)
      );
  content: '';
  opacity: 0;
  transform: scaleY(0.4);
  transform-origin: center;
  transition:
      opacity 180ms ease,
      transform 180ms ease;
}

.micro-template-gallery-card:hover {
  border-color: var(--template-tone-border);
  background:
      linear-gradient(
          135deg,
          var(--template-tone-softer),
          #ffffff 72%
      );
  box-shadow:
      0 5px 14px
      var(--template-tone-glow);
  transform: translateY(-1px);
}

.micro-template-gallery-card:hover::before {
  opacity: 0.52;
  transform: scaleY(0.72);
}

.micro-template-gallery-card:focus-visible {
  outline: 3px solid var(--template-tone-glow);
  outline-offset: 2px;
}

.micro-template-gallery-card.is-selected {
  border-color: var(--template-tone);
  background:
      linear-gradient(
          135deg,
          var(--template-tone-soft),
          #ffffff 76%
      );
  box-shadow:
      0 0 0 2px
      var(--template-tone-glow),
      0 7px 18px
      var(--template-tone-glow);
  transform: translateY(-1px);
}

.micro-template-gallery-card.is-selected::before {
  opacity: 1;
  transform: scaleY(1);
}

.micro-template-gallery-card.teal {
  --template-tone: #159a94;
  --template-tone-end: #47bdb5;
  --template-tone-soft: #eef9f8;
  --template-tone-softer: #f7fcfb;
  --template-tone-border: #91d4d0;
  --template-tone-text: #176b67;
  --template-tone-glow: rgba(21, 154, 148, 0.15);
}

.micro-template-gallery-card.blue {
  --template-tone: #4d83ba;
  --template-tone-end: #75a8db;
  --template-tone-soft: #eff6fc;
  --template-tone-softer: #f7fbfe;
  --template-tone-border: #a9c9e8;
  --template-tone-text: #35658f;
  --template-tone-glow: rgba(77, 131, 186, 0.15);
}

.micro-template-gallery-card.amber {
  --template-tone: #d4922a;
  --template-tone-end: #efb24d;
  --template-tone-soft: #fff7e8;
  --template-tone-softer: #fffaf2;
  --template-tone-border: #efc77e;
  --template-tone-text: #9a6418;
  --template-tone-glow: rgba(212, 146, 42, 0.16);
}

.micro-template-gallery-card.violet {
  --template-tone: #8068b5;
  --template-tone-end: #a18bd1;
  --template-tone-soft: #f5f1fb;
  --template-tone-softer: #faf8fd;
  --template-tone-border: #c9b9e4;
  --template-tone-text: #654c97;
  --template-tone-glow: rgba(128, 104, 181, 0.15);
}

.category-glow-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background:
      linear-gradient(
          135deg,
          var(--template-tone),
          var(--template-tone-end)
      );
  box-shadow:
      0 0 0 3px
      var(--template-tone-glow);
  transition:
      box-shadow 180ms ease,
      transform 180ms ease;
}

.micro-template-gallery-card:hover
.category-glow-dot,
.micro-template-gallery-card.is-selected
.category-glow-dot {
  box-shadow:
      0 0 0 4px
      var(--template-tone-glow);
  transform: scale(1.08);
}

.micro-card-meta {
  display: block;
  min-width: 0;
}

.micro-card-meta strong {
  display: block;
  overflow: hidden;
  color: var(--planner-text-strong);
  font-size: var(--planner-font-control);
  font-weight: 700;
  line-height: var(--planner-line-control);
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 180ms ease;
}

.micro-card-meta > span {
  display: block;
  overflow: hidden;
  margin-top: 3px;
  color: var(--planner-text-muted);
  font-size: var(--planner-font-help);
  line-height: var(--planner-line-control);
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 180ms ease;
}

.micro-template-gallery-card.is-selected
.micro-card-meta strong {
  color: var(--template-tone-text);
}

.micro-template-gallery-card.is-selected
.micro-card-meta > span {
  color: var(--template-tone-text);
  opacity: 0.76;
}

.template-selected-mark {
  display: inline-flex;
  width: 20px;
  height: 20px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background:
      linear-gradient(
          135deg,
          var(--template-tone),
          var(--template-tone-end)
      );
  color: #ffffff;
  box-shadow:
      0 4px 10px
      var(--template-tone-glow);
  animation:
      template-mark-enter
      220ms cubic-bezier(0.16, 1, 0.3, 1);
}

.structured-form-panel {
  display: flex;
  flex-direction: column;
  padding: 27px 30px 25px;
  border: 1px solid var(--planner-border-light);
  border-radius: 12px;
  background: var(--planner-surface);
  box-shadow:
      0 2px 8px
      rgba(26, 65, 68, 0.035);
}

.form-grid-row {
  display: grid;
  grid-template-columns:
    195px minmax(0, 1fr);
  gap: 28px;
  padding: 21px 0;
  border-bottom: 1px solid
  var(--planner-border-light);
}

.form-grid-row:first-child {
  padding-top: 0;
}

.form-grid-row-last {
  padding-bottom: 22px;
  border-bottom: 0;
}

.row-meta-pane {
  display: flex;
  align-items: flex-start;
  gap: 11px;
}

.row-badge-num {
  display: grid;
  width: 27px;
  height: 27px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid
  var(--planner-accent-border);
  border-radius: 5px;
  background: var(--planner-accent-soft);
  color: var(--planner-accent-text);
  font-family: var(--font-mono, monospace);
  font-size: var(--planner-font-micro);
  font-weight: 700;
  line-height: 1;
}

.row-headline-group {
  min-width: 0;
}

.row-title-group {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 1px 0 0;
  color: var(--planner-text-strong);
  font-size: var(--planner-font-section);
  font-weight: 750;
  line-height: var(--planner-line-control);
}

.title-icon {
  flex-shrink: 0;
  color: var(--planner-accent-text);
}

.row-headline-group p {
  margin: 7px 0 0;
  color: var(--planner-text-muted);
  font-size: var(--planner-font-help);
  line-height: var(--planner-line-help);
}

.row-control-pane {
  min-width: 0;
}

.input-container-box input,
.textarea-container-box textarea {
  width: 100%;
  border: 1px solid var(--planner-border);
  border-radius: 6px;
  outline: none;
  background: var(--planner-surface);
  color: var(--planner-text);
  font-size: var(--planner-font-body);
  line-height: var(--planner-line-body);
  transition:
      border-color 180ms ease,
      box-shadow 180ms ease,
      background-color 180ms ease;
}

.input-container-box input {
  height: 42px;
  padding: 0 14px;
}

.textarea-container-box textarea {
  min-height: 94px;
  max-height: 150px;
  padding: 12px 14px;
  resize: none;
}

.input-container-box input::placeholder,
.textarea-container-box textarea::placeholder,
.tag-inner-flex input::placeholder {
  color: #a4b0b2;
}

.input-container-box input:hover,
.textarea-container-box textarea:hover,
.tag-input-bezel-box:hover {
  border-color: #bdcdcb;
}

.input-container-box input:focus,
.textarea-container-box textarea:focus {
  border-color: var(--planner-accent);
  box-shadow:
      0 0 0 3px
      var(--planner-focus-ring);
}

.textarea-info-bar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-top: 7px;
  color: var(--planner-text-faint);
  font-size: var(--planner-font-help);
  line-height: var(--planner-line-help);
}

.char-counter {
  flex-shrink: 0;
  font-family: var(--font-mono, monospace);
}

.tag-input-bezel-box {
  min-height: 44px;
  padding: 7px 10px;
  border: 1px solid var(--planner-border);
  border-radius: 6px;
  background: var(--planner-surface);
  transition:
      border-color 180ms ease,
      box-shadow 180ms ease;
}

.tag-input-bezel-box:focus-within {
  border-color: var(--planner-accent);
  box-shadow:
      0 0 0 3px
      var(--planner-focus-ring);
}

.tag-inner-flex {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
}

.tag-inner-flex input {
  min-width: 190px;
  flex: 1;
  padding: 3px 2px;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--planner-text);
  font-size: var(--planner-font-body);
  line-height: var(--planner-line-control);
}

.custom-tag-node {
  --knowledge-tone-start: #159a94;
  --knowledge-tone-end: #4bbdb5;
  --knowledge-tone-soft: #f3faf9;
  --knowledge-tone-border: #bddfdd;
  --knowledge-tone-text: #176b67;
  --knowledge-tone-glow: rgba(21, 154, 148, 0.1);

  display: inline-flex;
  min-height: 28px;
  align-items: center;
  gap: 6px;
  padding: 3px 5px 3px 8px;
  border: 1px solid var(--knowledge-tone-border);
  border-radius: 6px;
  background: var(--knowledge-tone-soft);
  color: var(--knowledge-tone-text);
  font-size: var(--planner-font-control);
  font-weight: 600;
  line-height: var(--planner-line-control);
  transition:
      border-color 160ms ease,
      background-color 160ms ease;
}

.custom-tag-node:hover {
  border-color: var(--knowledge-tone-start);
}

.knowledge-tag-dot {
  width: 6px;
  height: 6px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--knowledge-tone-start);
  box-shadow: 0 0 0 3px var(--knowledge-tone-glow);
}

.knowledge-tag-label {
  min-width: 0;
  line-height: 1.35;
}

.tag-close-trigger {
  display: inline-flex;
  width: 17px;
  height: 17px;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  opacity: 0.56;
  transition:
      opacity 150ms ease,
      background-color 150ms ease;
}

.tag-close-trigger:hover {
  background: var(--knowledge-tone-glow);
  opacity: 1;
}

.quick-tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 11px;
}

.planner-knowledge-option,
.planner-option,
.planner-focus-option {
  color: var(--planner-text-secondary);
  font-size: var(--planner-font-control);
  line-height: var(--planner-line-control);
  cursor: pointer;
  transition:
      border-color 160ms ease,
      background-color 160ms ease,
      color 160ms ease,
      box-shadow 160ms ease;
}

.planner-knowledge-option {
  --knowledge-tone-start: #159a94;
  --knowledge-tone-end: #4bbdb5;
  --knowledge-tone-soft: #f3faf9;
  --knowledge-tone-border: #bddfdd;
  --knowledge-tone-text: #176b67;
  --knowledge-tone-glow: rgba(21, 154, 148, 0.1);

  display: inline-flex;
  min-height: 32px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 11px;
  border: 1px solid var(--planner-border);
  border-radius: 999px;
  background: var(--planner-surface);
  color: var(--planner-text-secondary);
  font-weight: 600;
}

.knowledge-option-indicator {
  display: grid;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  place-items: center;
  border-radius: 50%;
  color: #ffffff;
  transition:
      background 160ms ease,
      box-shadow 160ms ease;
}

.knowledge-option-indicator > span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--knowledge-tone-start);
  opacity: 0.82;
}

.planner-knowledge-option:hover {
  border-color: var(--knowledge-tone-border);
  background: var(--knowledge-tone-soft);
  color: var(--knowledge-tone-text);
}

.planner-knowledge-option.is-selected {
  border-color: var(--knowledge-tone-border);
  background: var(--knowledge-tone-soft);
  color: var(--knowledge-tone-text);
  font-weight: 700;
  box-shadow: inset 0 0 0 1px var(--knowledge-tone-glow);
}

.planner-knowledge-option.is-selected
.knowledge-option-indicator {
  background:
      linear-gradient(
          135deg,
          var(--knowledge-tone-start),
          var(--knowledge-tone-end)
      );
  box-shadow: 0 2px 5px var(--knowledge-tone-glow);
}

.planner-knowledge-option:focus-visible,
.planner-option:focus-visible,
.planner-focus-option:focus-visible {
  outline: 3px solid var(--planner-focus-ring);
  outline-offset: 2px;
}

.preferences-matrix {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.preference-flex-line {
  display: grid;
  grid-template-columns:
    76px minmax(0, 1fr);
  align-items: center;
  gap: 13px;
}

.pref-field-label {
  color: var(--planner-text-strong);
  font-size: var(--planner-font-control);
  font-weight: 700;
  line-height: var(--planner-line-control);
}

.planner-option-group {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.planner-option,
.planner-focus-option {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 0 14px;
  border: 1px solid var(--planner-border);
  border-radius: 6px;
  background: var(--planner-surface);
  font-weight: 600;
}

.planner-option:hover,
.planner-focus-option:hover {
  border-color: var(--planner-accent-border);
  background: var(--planner-accent-softer);
  color: var(--planner-accent-text);
}

.planner-option.is-selected,
.planner-focus-option.is-selected {
  border-color: var(--planner-accent);
  background: var(--planner-accent-soft);
  color: var(--planner-accent-text);
  font-weight: 700;
  box-shadow:
      0 0 0 2px
      rgba(21, 154, 148, 0.055);
}

.form-action-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 22px;
  padding-top: 22px;
  border-top: 1px solid
  var(--planner-border-light);
}

.ai-readiness-inline-dashboard {
  display: flex;
  min-width: 0;
  max-width: 650px;
  flex: 1;
  align-items: flex-start;
  gap: 11px;
  padding: 12px 14px;
  border: 1px solid
  var(--planner-border-light);
  border-radius: 8px;
  background: #f7fafa;
  transition:
      border-color 180ms ease,
      background-color 180ms ease;
}

.ai-readiness-inline-dashboard.is-ready {
  border-color: #b4ddda;
  background: #eef9f8;
}

.dashboard-visual-pulse {
  position: relative;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  margin-top: 4px;
}

.pulse-ring,
.pulse-center-core {
  position: absolute;
  border-radius: 50%;
}

.pulse-ring {
  inset: 0;
  background: #a5b2b4;
  opacity: 0.22;
}

.pulse-center-core {
  top: 3px;
  left: 3px;
  width: 8px;
  height: 8px;
  background: #94a3a6;
}

.ai-readiness-inline-dashboard.is-ready
.pulse-ring {
  background: var(--planner-accent);
  animation:
      pulse-spread 1.8s ease-out infinite;
}

.ai-readiness-inline-dashboard.is-ready
.pulse-center-core {
  background: var(--planner-accent);
}

.dashboard-inline-meta {
  min-width: 0;
}

.dashboard-inline-meta strong {
  display: block;
  margin-bottom: 3px;
  color: var(--planner-text-strong);
  font-size: var(--planner-font-control);
  font-weight: 750;
  line-height: var(--planner-line-control);
}

.dashboard-inline-meta p {
  margin: 0;
  color: var(--planner-text-secondary);
  font-size: var(--planner-font-help);
  line-height: var(--planner-line-help);
}

.ai-readiness-inline-dashboard.is-ready
.dashboard-inline-meta strong,
.ai-readiness-inline-dashboard.is-ready
.dashboard-inline-meta p {
  color: var(--planner-accent-text);
}

.dashboard-inline-meta .lack {
  margin: 0 2px;
  color: #cf5e5e;
  font-weight: 750;
}

.footer-buttons-cluster {
  display: flex;
  flex-shrink: 0;
  gap: 9px;
}

.planner-secondary-action,
.planner-primary-action {
  display: inline-flex;
  height: 40px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 17px;
  border-radius: 7px;
  font-size: var(--planner-font-control);
  font-weight: 700;
  line-height: var(--planner-line-control);
  cursor: pointer;
  transition:
      border-color 180ms ease,
      background-color 180ms ease,
      color 180ms ease,
      box-shadow 180ms ease,
      transform 180ms ease;
}

.planner-secondary-action {
  border: 1px solid var(--planner-border);
  background: var(--planner-surface);
  color: var(--planner-text-secondary);
}

.planner-secondary-action:hover:not(:disabled) {
  border-color: #bdcdcb;
  background: #f6f9f9;
  color: var(--planner-text-strong);
}

.planner-primary-action {
  min-width: 142px;
  border: 1px solid var(--planner-accent);
  background:
      linear-gradient(
          135deg,
          #159a94,
          #31aaa4
      );
  color: #ffffff;
  box-shadow:
      0 4px 12px
      rgba(21, 154, 148, 0.18);
}

.planner-primary-action:hover:not(:disabled) {
  border-color: var(--planner-accent-hover);
  background:
      linear-gradient(
          135deg,
          #10847f,
          #249d97
      );
  box-shadow:
      0 6px 16px
      rgba(21, 154, 148, 0.22);
  transform: translateY(-1px);
}

.planner-primary-action:active:not(:disabled) {
  transform: translateY(0);
}

.planner-secondary-action:focus-visible,
.planner-primary-action:focus-visible {
  outline: 3px solid var(--planner-focus-ring);
  outline-offset: 2px;
}

.planner-secondary-action:disabled,
.planner-primary-action:disabled {
  cursor: not-allowed;
  box-shadow: none;
  opacity: 0.52;
  transform: none;
}

.workspace-flow-footnote {
  padding: 0 4px 4px;
}

.agile-notice-banner-box {
  padding: 14px 17px;
  border: 1px dashed #cfdedd;
  border-radius: 8px;
  background:
      rgba(234, 247, 246, 0.35);
}

.mini-badge {
  display: block;
  margin-bottom: 4px;
  color: var(--planner-accent);
  font-family: var(--font-mono, monospace);
  font-size: var(--planner-font-micro);
  font-weight: 700;
  line-height: 1.4;
  letter-spacing: 0.055em;
}

.agile-notice-banner-box p {
  margin: 0;
  color: var(--planner-text-secondary);
  font-size: var(--planner-font-help);
  line-height: var(--planner-line-help);
}

.student-planning-modal-backdrop {
  position: fixed;
  z-index: 1000;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background:
      rgba(247, 250, 250, 0.82);
  backdrop-filter: blur(4px);
}

.student-planning-modal-content {
  width: min(680px, 100%);
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  padding: 31px 32px;
  border: 1px solid #cfe4e2;
  border-radius: 14px;
  background: #ffffff;
  box-shadow:
      0 20px 55px
      rgba(31, 76, 80, 0.1),
      0 3px 10px
      rgba(31, 76, 80, 0.035);
}

.modal-loading-header {
  text-align: center;
}

.premium-path-loader {
  position: relative;
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  margin: 0 auto 16px;
}

.spinner-double-ring {
  position: absolute;
  inset: 0;
  border: 3px solid
  rgba(21, 154, 148, 0.11);
  border-top-color:
      var(--planner-accent);
  border-right-color: #6bc3be;
  border-radius: 50%;
  animation:
      modal-spin 1.15s linear infinite;
}

.sparkle-center-icon {
  color: var(--planner-accent);
  animation:
      loader-breathe 1.6s ease-in-out
      infinite;
}

.modal-loading-header h2,
.planning-result-copy h2 {
  margin: 0;
  color: var(--planner-text-strong);
  font-size: 18px;
  font-weight: 780;
  line-height: 1.4;
  letter-spacing: -0.015em;
}

.modal-loading-header p,
.planning-result-copy p {
  margin: 7px 0 0;
  color: var(--planner-text-secondary);
  font-size: var(--planner-font-control);
  line-height: var(--planner-line-help);
}

.student-timeline-track {
  display: flex;
  justify-content: space-between;
  margin-top: 28px;
  padding: 0 7px;
}

.student-timeline-node {
  --timeline-node-start: #7f9b98;
  --timeline-node-end: #a7bfbc;
  --timeline-node-soft: #f2f7f6;
  --timeline-node-text: #58726f;
  --timeline-node-glow: rgba(73, 111, 107, 0.14);
  --timeline-next-start: #a7bfbc;

  position: relative;
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.node-circle-indicator {
  position: relative;
  z-index: 2;
  isolation: isolate;
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 2px solid transparent;
  border-radius: 50%;
  background:
      linear-gradient(#ffffff, #ffffff)
      padding-box,
      linear-gradient(
          135deg,
          var(--timeline-node-start),
          var(--timeline-node-end)
      ) border-box;
  color: var(--timeline-node-text);
  box-shadow:
      0 2px 8px
      rgba(39, 72, 75, 0.055);
  font-family: var(--font-mono, monospace);
  font-size: var(--planner-font-micro);
  font-weight: 700;
  line-height: 1;
  transition:
      color 260ms ease,
      box-shadow 260ms ease,
      transform 260ms ease,
      filter 260ms ease;
}

.node-circle-indicator::after {
  position: absolute;
  z-index: -1;
  inset: -6px;
  border-radius: inherit;
  background:
      radial-gradient(
          circle,
          var(--timeline-node-glow) 0%,
          transparent 70%
      );
  content: '';
  opacity: 0;
  transform: scale(0.76);
  transition:
      opacity 260ms ease,
      transform 260ms ease;
}

.node-circle-indicator > * {
  position: relative;
  z-index: 1;
}

.node-text-label {
  max-width: 96px;
  color: var(--planner-text-faint);
  font-size: var(--planner-font-help);
  font-weight: 550;
  line-height: var(--planner-line-control);
  text-align: center;
  transition:
      color 240ms ease,
      font-weight 240ms ease,
      transform 240ms ease;
}

.node-connecting-dash {
  position: absolute;
  z-index: 1;
  top: 14px;
  left: 50%;
  width: 100%;
  height: 2px;
  overflow: hidden;
  background: var(--planner-border-light);
  transition:
      background 320ms ease,
      box-shadow 320ms ease;
}

.student-timeline-node.is-active
.node-circle-indicator {
  background:
      linear-gradient(
          135deg,
          var(--timeline-node-soft),
          #ffffff
      ) padding-box,
      linear-gradient(
          135deg,
          var(--timeline-node-start),
          var(--timeline-node-end)
      ) border-box;
  color: var(--timeline-node-text);
  box-shadow:
      0 0 0 5px
      var(--timeline-node-glow),
      0 8px 18px
      var(--timeline-node-glow);
  transform: translateY(-1px) scale(1.04);
}

.student-timeline-node.is-active
.node-circle-indicator::after {
  opacity: 1;
  transform: scale(1);
  animation:
      timeline-node-breathe
      1.9s ease-in-out infinite;
}

.student-timeline-node.is-active
.node-text-label {
  color: var(--timeline-node-text);
  font-weight: 750;
  transform: translateY(1px);
}

.student-timeline-node.is-done
.node-circle-indicator {
  background:
      linear-gradient(
          135deg,
          var(--timeline-node-start),
          var(--timeline-node-end)
      ) border-box;
  color: #ffffff;
  box-shadow:
      0 5px 13px
      var(--timeline-node-glow);
  filter: saturate(1.02);
}

.student-timeline-node.is-done
.node-circle-indicator::after {
  opacity: 0.62;
  transform: scale(0.94);
}

.student-timeline-node.is-done
.node-text-label {
  color: var(--timeline-node-text);
  font-weight: 680;
}

.student-timeline-node.is-done
.node-connecting-dash {
  background:
      linear-gradient(
          90deg,
          var(--timeline-node-end),
          var(--timeline-next-start)
      );
  box-shadow:
      0 1px 5px
      var(--timeline-node-glow);
}

.student-progress-dashboard {
  margin-top: 25px;
  padding: 13px 15px;
  border: 1px solid #dfecea;
  border-radius: 8px;
  background: #f8fbfb;
}

.progress-stage-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.progress-stage-copy {
  min-width: 0;
}

.progress-stage-label {
  display: block;
  margin-bottom: 2px;
  color: var(--planner-text-faint);
  font-size: var(--planner-font-help);
  font-weight: 650;
  line-height: var(--planner-line-control);
}

.progress-stage-copy strong {
  display: block;
  overflow: hidden;
  color: var(--planner-accent-text);
  font-size: var(--planner-font-control);
  font-weight: 750;
  line-height: var(--planner-line-control);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.progress-step-count {
  flex-shrink: 0;
  color: var(--planner-text-muted);
  font-family: var(--font-mono, monospace);
  font-size: var(--planner-font-help);
  line-height: var(--planner-line-control);
}

.progress-bar-minimal {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: #e4eeed;
}

.progress-bar-minimal-fill {
  width: 100%;
  height: 100%;
  border-radius: inherit;
  background: var(--planner-accent);
  box-shadow:
      0 1px 5px
      rgba(21, 154, 148, 0.24);
  transform-origin: left center;
  transition: transform 320ms ease;
}

.student-friendly-log-box {
  display: flex;
  height: 108px;
  box-sizing: border-box;
  flex-direction: column;
  gap: 7px;
  margin-top: 17px;
  padding: 12px 15px;
  border-left: 2px solid
  var(--planner-accent-border);
  background: #fbfdfd;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.friendly-log-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.friendly-log-dot {
  width: 5px;
  height: 5px;
  flex-shrink: 0;
  margin-top: 7px;
  border-radius: 50%;
  background: var(--planner-accent);
}

.friendly-log-text {
  color: var(--planner-text-secondary);
  font-size: var(--planner-font-control);
  line-height: var(--planner-line-help);
}

.planning-result-state {
  display: flex;
  min-height: 310px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.planning-state-icon {
  display: grid;
  width: 62px;
  height: 62px;
  place-items: center;
  margin-bottom: 19px;
  border-radius: 50%;
}

.success-icon {
  border: 1px solid
  var(--planner-accent-border);
  background: var(--planner-accent-soft);
  color: var(--planner-accent);
  animation:
      success-enter 420ms
      cubic-bezier(0.16, 1, 0.3, 1);
}

.error-icon {
  border: 1px solid
  rgba(211, 94, 94, 0.22);
  background:
      rgba(211, 94, 94, 0.07);
  color: #cc5b5b;
}

.planning-result-copy {
  max-width: 470px;
}

.planning-error-detail {
  width: 100%;
  margin-top: 24px;
  padding: 13px 15px;
  border: 1px solid
  rgba(211, 94, 94, 0.2);
  border-radius: 8px;
  background:
      rgba(211, 94, 94, 0.045);
  text-align: left;
}

.planning-error-detail strong {
  display: block;
  margin-bottom: 4px;
  color: #b94d4d;
  font-size: var(--planner-font-control);
  font-weight: 750;
  line-height: var(--planner-line-control);
}

.planning-error-detail p {
  margin: 0;
  color: #775d5d;
  font-size: var(--planner-font-help);
  line-height: var(--planner-line-help);
  overflow-wrap: anywhere;
}

.planning-result-actions {
  display: flex;
  justify-content: center;
  gap: 9px;
  margin-top: 23px;
}

.modal-secondary-action,
.modal-primary-action {
  display: inline-flex;
  min-width: 116px;
  height: 38px;
  align-items: center;
  justify-content: center;
  padding: 0 15px;
  border-radius: 7px;
  font-size: var(--planner-font-control);
  font-weight: 700;
  line-height: var(--planner-line-control);
  cursor: pointer;
  transition:
      border-color 180ms ease,
      background-color 180ms ease,
      color 180ms ease,
      transform 180ms ease;
}

.modal-secondary-action {
  border: 1px solid var(--planner-border);
  background: #ffffff;
  color: var(--planner-text-secondary);
}

.modal-secondary-action:hover {
  border-color: #bccdca;
  background: #f7fafa;
  color: var(--planner-text-strong);
}

.modal-primary-action {
  border: 1px solid var(--planner-accent);
  background: var(--planner-accent);
  color: #ffffff;
}

.modal-primary-action:hover {
  border-color: var(--planner-accent-hover);
  background: var(--planner-accent-hover);
  transform: translateY(-1px);
}

.modal-secondary-action:focus-visible,
.modal-primary-action:focus-visible {
  outline: 3px solid var(--planner-focus-ring);
  outline-offset: 2px;
}

.success-summary-line {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 22px;
  color: var(--planner-accent-text);
  font-size: var(--planner-font-control);
  font-weight: 650;
  line-height: var(--planner-line-control);
}

.success-summary-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--planner-accent);
  animation:
      success-dot 1.1s ease-in-out
      infinite;
}

.success-progress-track {
  width: min(330px, 100%);
  height: 5px;
  overflow: hidden;
  margin-top: 16px;
  border-radius: 999px;
  background: #e3efee;
}

.success-progress-fill {
  width: 100%;
  height: 100%;
  border-radius: inherit;
  background:
      linear-gradient(
          90deg,
          var(--planner-accent),
          #65c4bf
      );
  transform-origin: left center;
  animation:
      success-progress 800ms ease-out;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 220ms ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

@keyframes template-mark-enter {
  from {
    opacity: 0;
    transform: scale(0.72);
  }

  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes timeline-node-breathe {
  0%,
  100% {
    opacity: 0.56;
    transform: scale(0.9);
  }

  50% {
    opacity: 1;
    transform: scale(1.12);
  }
}

@keyframes pulse-spread {
  0% {
    opacity: 0.42;
    transform: scale(1);
  }

  100% {
    opacity: 0;
    transform: scale(2.35);
  }
}

@keyframes modal-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes loader-breathe {
  0%,
  100% {
    opacity: 0.62;
    transform: scale(0.92);
  }

  50% {
    opacity: 1;
    transform: scale(1.05);
  }
}

@keyframes success-enter {
  from {
    opacity: 0;
    transform: scale(0.72);
  }

  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes success-dot {
  0%,
  100% {
    opacity: 0.45;
  }

  50% {
    opacity: 1;
  }
}

@keyframes success-progress {
  from {
    transform: scaleX(0);
  }

  to {
    transform: scaleX(1);
  }
}

@media (max-width: 1024px) {
  .planner-unified-container {
    width: min(
        100% - 32px,
        var(--content-max-width, 1120px)
    );
  }

  .templates-horizontal-grid {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }

  .form-grid-row {
    grid-template-columns:
      180px minmax(0, 1fr);
    gap: 22px;
  }

  .form-action-footer {
    align-items: stretch;
    flex-direction: column;
    gap: 14px;
  }

  .ai-readiness-inline-dashboard {
    max-width: none;
  }

  .footer-buttons-cluster {
    align-self: flex-end;
  }
}

@media (max-width: 760px) {
  .planner-unified-container {
    width: calc(100% - 24px);
    padding-top: 14px;
  }

  .workspace-brand-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 15px;
    padding-bottom: 19px;
  }

  .header-action-group {
    width: 100%;
  }

  .planner-history-action {
    width: 100%;
  }

  .gallery-title-strip {
    align-items: flex-start;
    flex-direction: column;
    gap: 3px;
  }

  .templates-horizontal-grid {
    grid-template-columns: 1fr;
  }

  .structured-form-panel {
    padding: 21px 18px;
  }

  .form-grid-row {
    grid-template-columns: 1fr;
    gap: 13px;
    padding: 19px 0;
  }

  .row-headline-group p {
    max-width: 520px;
  }

  .preference-flex-line {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .planner-option,
  .planner-focus-option {
    flex: 1 1 auto;
  }

  .footer-buttons-cluster {
    width: 100%;
  }

  .planner-secondary-action,
  .planner-primary-action {
    flex: 1;
  }

  .student-planning-modal-backdrop {
    padding: 12px;
  }

  .student-planning-modal-content {
    max-height: calc(100vh - 24px);
    padding: 26px 18px;
  }

  .student-timeline-track {
    align-items: stretch;
    flex-direction: column;
    gap: 12px;
    margin-top: 25px;
    padding: 0;
  }

  .student-timeline-node {
    display: grid;
    grid-template-columns:
      28px minmax(0, 1fr);
    align-items: center;
    justify-items: start;
    gap: 10px;
  }

  .node-circle-indicator {
    grid-column: 1;
  }

  .node-text-label {
    grid-column: 2;
    max-width: none;
    text-align: left;
  }

  .node-connecting-dash {
    top: 27px;
    left: 13px;
    width: 2px;
    height: 22px;
  }

  .progress-stage-header {
    align-items: flex-start;
  }

  .planning-result-actions {
    width: 100%;
    flex-direction: column;
  }

  .modal-secondary-action,
  .modal-primary-action {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .workspace-brand-header h1 {
    font-size: 22px;
  }

  .cognitive-subtext {
    font-size: var(--planner-font-help);
  }

  .textarea-info-bar {
    align-items: flex-end;
    flex-direction: column;
    gap: 3px;
  }

  .planner-option-group {
    display: grid;
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
    width: 100%;
  }

  .planner-option,
  .planner-focus-option {
    width: 100%;
    padding: 0 8px;
  }

  .footer-buttons-cluster {
    flex-direction: column;
  }

  .planner-secondary-action,
  .planner-primary-action {
    width: 100%;
  }

  .student-progress-dashboard {
    padding: 12px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .path-planner-page *,
  .path-planner-page *::before,
  .path-planner-page *::after {
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }

  .spinner-double-ring {
    border-color:
        var(--planner-accent-border);
    border-top-color:
        var(--planner-accent);
  }
}
</style>
