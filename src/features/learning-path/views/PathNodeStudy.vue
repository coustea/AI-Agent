<template>
  <main class="node-study-page">
    <!-- 页面加载状态 -->
    <section
        v-if="loading && !isGeneratingTutorial"
        class="state-card"
    >
      <div class="state-spinner"></div>
      <h2>正在准备学习内容</h2>
      <p>正在读取当前节点、教程和学习资源。</p>
    </section>

    <!-- 节点异常状态 -->
    <section
        v-else-if="!workspace && !isGeneratingTutorial"
        class="state-card"
    >
      <div class="state-icon state-icon-error">
        <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
            stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="9"></circle>
          <line x1="12" y1="8" x2="12" y2="13"></line>
          <circle cx="12" cy="17" r="0.7" fill="currentColor"></circle>
        </svg>
      </div>

      <h2>节点不存在或已经失效</h2>
      <p>请返回路径总览，重新选择需要学习的节点。</p>

      <button
          class="primary-action-button"
          type="button"
          @click="router.push('/path-planner')"
      >
        返回路径总览
      </button>
    </section>

    <!-- 教程生成过程 -->
    <section
        v-else-if="isGeneratingTutorial"
        class="generating-view"
    >
      <div class="generate-panel">
        <div
            class="generate-loader"
            aria-hidden="true"
        >
          <div class="generate-loader-ring"></div>

          <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
          >
            <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21.5v-16Z"></path>
            <path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5a2.5 2.5 0 0 1 2.5 2.5v-16Z"></path>
          </svg>
        </div>

        <div class="generate-copy">
          <span class="generate-kicker">
            NODE TUTORIAL
          </span>

          <h1>正在生成节点教程</h1>

          <p>
            系统正在结合学习目标、当前基础和节点内容组织本节教程。
          </p>
        </div>

        <div class="generate-stage-panel">
          <div class="generate-stage-head">
            <div>
              <span>当前阶段</span>
              <strong>
                {{ currentGenerationStep }}
              </strong>
            </div>

            <em>
              第 {{ generationStepNumber }} /
              {{ tutorialGenerationSteps.length }} 步
            </em>
          </div>

          <div class="generate-progress-track">
            <div
                class="generate-progress-fill"
                :style="{
                transform: `scaleX(${generationProgress / 100})`,
              }"
            ></div>
          </div>
        </div>

        <div
            class="generate-step-list"
            aria-live="polite"
        >
          <div
              v-for="(step, index) in tutorialGenerationSteps"
              :key="step"
              class="generate-step-item"
              :class="{
              'is-complete': index < generatingStep,
              'is-current': index === generatingStep,
            }"
          >
            <span class="generate-step-indicator">
              <svg
                  v-if="index < generatingStep"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
              >
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>

              <span v-else>{{ index + 1 }}</span>
            </span>

            <span>{{ step }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 节点学习工作区 -->
    <template v-else-if="workspace">
      <nav class="node-toolbar">
        <div class="toolbar-left">
          <button
              class="back-button"
              type="button"
              @click="
              router.push(
                `/path-planner/overview/${workspace.path.id}`,
              )
            "
          >
            <svg
                class="back-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2.2"
                stroke-linecap="round"
                stroke-linejoin="round"
            >
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>

            <span>返回路径总览</span>
          </button>

          <div class="toolbar-title">
            <span class="toolbar-kicker">
              学习节点
            </span>

            <h1>{{ workspace.node.title }}</h1>
          </div>
        </div>

        <div class="toolbar-right">
          <span
              class="status-pill"
              :class="workspace.node.status"
          >
            <i></i>
            {{ statusText(workspace.node.status) }}
          </span>
        </div>
      </nav>

      <section class="study-workspace">
        <!-- 左侧目录 -->
        <aside class="toc-panel">
          <div class="side-head">
            <span class="side-kicker">
              CONTENTS
            </span>

            <strong>教程目录</strong>
          </div>

          <div
              v-if="tutorialToc.length"
              class="toc-list"
          >
            <button
                v-for="item in tutorialToc"
                :key="item.id"
                type="button"
                class="toc-item"
                :class="[
                `level-${item.level}`,
                {
                  active:
                    activeHeadingId === item.id,
                },
              ]"
                :title="item.title"
                @click="scrollToHeading(item.id)"
            >
              {{ item.title }}
            </button>
          </div>

          <div
              v-else
              class="toc-empty"
          >
            <p>暂无教程目录</p>
            <span>
              教程加载后将自动识别章节标题。
            </span>
          </div>
        </aside>

        <!-- 中间教程正文 -->
        <article class="tutorial-main">
          <header class="tutorial-head">
            <div class="tutorial-head-copy">
              <span class="section-kicker">
                NODE TUTORIAL
              </span>

              <h2>
                {{
                  displayedTutorial?.title ||
                  workspace.node.title
                }}
              </h2>

              <p>
                完成本节教程后，可进行知识掌握度诊断，并根据结果继续下一学习节点。
              </p>
            </div>

            <div
                v-if="workspace.tutorials.length > 1"
                class="tutorial-tabs"
                aria-label="教程版本"
            >
              <button
                  v-for="item in workspace.tutorials"
                  :key="item.id"
                  type="button"
                  class="tutorial-tab"
                  :class="{
                  'is-selected':
                    item.id === displayedTutorial?.id,
                  'is-current':
                    item.id ===
                    (workspace.current_tutorial?.id ||
                      null),
                }"
                  @click="selectedTutorialId = item.id"
              >
                <span>
                  {{
                    tutorialTypeLabel(
                        item.tutorial_type,
                    )
                  }}
                </span>

                <em>v{{ item.version_no }}</em>
              </button>
            </div>
          </header>

          <section class="tutorial-reader">
            <div
                v-if="displayedTutorial"
                ref="contentEl"
                class="markdown-shell markdown-body"
            >
              <Markdown
                  :result-data="{
                  content: tutorialMarkdown,
                }"
              />
            </div>

            <div
                v-else
                class="tutorial-empty"
            >
              <h3>暂无节点教程</h3>
              <p>
                系统将为当前学习节点生成个性化教程。
              </p>
            </div>
          </section>

          <!-- 知识诊断入口 -->
          <section class="tutorial-native-quiz">
            <div class="content-divider"></div>

            <header class="quiz-native-head">
              <span class="section-kicker">
                KNOWLEDGE CHECK
              </span>

              <h2>知识掌握度诊断</h2>

              <p>
                完成本节学习后，可通过 5 道题检查概念理解、原理掌握、实际应用和常见易错点。
              </p>
            </header>

            <div class="quiz-native-preload">
              <div class="diagnostic-dimensions">
                <span class="dimension-label">
                  评估维度
                </span>

                <span class="dimension-tag">
                  概念理解
                </span>

                <span class="dimension-tag">
                  原理掌握
                </span>

                <span class="dimension-tag">
                  实际应用
                </span>

                <span class="dimension-tag">
                  易错点
                </span>
              </div>

              <div class="quiz-action-trigger-zone">
                <button
                    class="primary-action-button quiz-trigger-button"
                    type="button"
                    :disabled="quizLoading"
                    @click="loadQuiz"
                >
                  <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2.1"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                  >
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                  </svg>

                  <span>
                    {{
                      quizLoading
                          ? '正在生成诊断题'
                          : quizRound
                              ? '查看诊断结果'
                              : '开始知识诊断'
                    }}
                  </span>
                </button>
              </div>
            </div>
          </section>
        </article>

        <!-- 右侧学习资源 -->
        <aside class="resource-panel">
          <div class="side-head">
            <span class="side-kicker">
              LEARNING RESOURCES
            </span>

            <strong>学习资源</strong>
          </div>

          <p class="push-desc">
            根据当前教程按需生成辅助学习资源。
          </p>

          <div class="resource-list">
            <article
                v-for="item in resourcePushItems"
                :key="item.type"
                class="resource-item"
                :class="[
                item.type,
                {
                  generated: isResourceReady(item.resource),
                  active: isResourceGenerating(item),
                },
              ]"
            >
              <div class="resource-icon-wrapper">
                <svg
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                    fill="currentColor"
                >
                  <path :d="item.icon" />
                </svg>
              </div>

              <div class="resource-copy">
                <strong>{{ item.title }}</strong>
                <span>{{ item.desc }}</span>

                <em
                    class="status-label"
                    :class="{
                    fail: isResourceFailed(item.resource),
                    wait: !item.resource && !isResourceGenerating(item),
                    running: isResourceGenerating(item),
                  }"
                >
                  {{ resourceStatusText(item) }}
                </em>
              </div>

              <button
                  type="button"
                  class="resource-action-button"
                  :disabled="isResourceGenerating(item)"
                  @click="handleResourceAction(item)"
              >
                {{ resourceActionText(item) }}
              </button>
            </article>
          </div>
        </aside>
      </section>
    </template>

    <!-- 资源查看器 -->
    <Teleport to="body">
      <transition name="viewer-fade">
        <div
            v-if="showViewer"
            class="viewer-overlay"
            @click.self="closeViewer"
        >
          <section
              class="viewer-shell"
              role="dialog"
              aria-modal="true"
              aria-label="学习资源查看器"
          >
            <nav class="viewer-nav">
              <button
                  class="nav-back-button"
                  type="button"
                  @click="closeViewer"
              >
                <svg
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                    fill="currentColor"
                >
                  <path
                      d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.42-1.41L7.83 13H20v-2Z"
                  />
                </svg>

                <span>返回教程</span>
              </button>

              <div class="viewer-nav-right">
                <div
                    v-if="viewerResource"
                    class="viewer-nav-status"
                >
                  <span
                      class="status-dot"
                      :class="
                      viewerResource.status ||
                      'completed'
                    "
                  ></span>

                  {{
                    viewerResource.status === 'failed'
                        ? '资源生成失败'
                        : '资源已就绪'
                  }}
                </div>

                <button
                    class="viewer-close-button"
                    type="button"
                    aria-label="关闭资源查看器"
                    @click="closeViewer"
                >
                  <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                  >
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </div>
            </nav>

            <section
                v-if="viewerLoading"
                class="viewer-state"
            >
              <div class="state-spinner"></div>
              <p>正在加载资源内容</p>
            </section>

            <section
                v-else-if="
                viewerResource &&
                viewerResource.status === 'failed'
              "
                class="viewer-state"
            >
              <div class="state-icon state-icon-error">
                <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.8"
                >
                  <circle cx="12" cy="12" r="9"></circle>
                  <line x1="12" y1="8" x2="12" y2="13"></line>
                  <circle cx="12" cy="17" r="0.7" fill="currentColor"></circle>
                </svg>
              </div>

              <h2>资源生成失败</h2>

              <p>
                {{
                  viewerResource.error_message ||
                  '生成过程中出现问题，请稍后重新生成。'
                }}
              </p>
            </section>

            <template v-else-if="viewerResource">
              <section class="viewer-workspace">
                <article class="viewer-content">
                  <header class="viewer-head">
                    <div class="viewer-title">
                      <span class="section-kicker">
                        {{
                          resourceTypeLabel(
                              viewerResource.resource_type,
                          )
                        }}
                      </span>

                      <h1>
                        {{ viewerResource.title }}
                      </h1>

                      <p
                          v-if="viewerResource.summary"
                      >
                        {{ viewerResource.summary }}
                      </p>
                    </div>

                    <div class="viewer-meta">
                      <span>
                        v{{ viewerResource.version_no }}
                      </span>

                      <span>
                        {{
                          formatTime(
                              viewerResource.created_at,
                          )
                        }}
                      </span>
                    </div>
                  </header>

                  <div class="viewer-body">
                    <ArtifactRenderer
                        :type="viewerResource.resource_type"
                        :content="viewerContent"
                        :resource="viewerResource"
                    />
                  </div>
                </article>
              </section>
            </template>
          </section>
        </div>
      </transition>
    </Teleport>

    <!-- 诊断评估弹窗 -->
    <Teleport to="body">
      <transition name="quiz-fade">
        <div
            v-if="showQuizOverlay && quizRound"
            class="quiz-overlay"
            @click.self="closeQuiz"
        >
          <section
              class="quiz-shell"
              role="dialog"
              aria-modal="true"
              aria-label="知识掌握度诊断"
          >
            <nav class="quiz-nav">
              <div class="quiz-nav-left">
                <span class="agent-eyebrow">
                  KNOWLEDGE CHECK
                </span>

                <strong>
                  第 {{ quizRound.round_no }} 轮诊断
                </strong>
              </div>

              <button
                  class="nav-back-button"
                  type="button"
                  @click="closeQuiz"
              >
                <svg
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                    fill="currentColor"
                >
                  <path
                      d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.42-1.41L7.83 13H20v-2Z"
                  />
                </svg>

                <span>返回教程</span>
              </button>
            </nav>

            <section class="quiz-body">
              <div class="quiz-banner">
                <h2>完成本节知识诊断</h2>
                <p>
                  请完成以下单项选择题，提交后将显示正确答案、解析和薄弱知识点。
                </p>
              </div>

              <div class="quiz-question-list">
                <article
                    v-for="(
                    question, index
                  ) in quizRound.questions"
                    :key="question.id"
                    class="quiz-question-node"
                >
                  <h3 class="quiz-question-title">
                    <span class="quiz-question-number">
                      {{ index + 1 }}
                    </span>

                    <span>
                      {{ question.question }}
                    </span>
                  </h3>

                  <div class="quiz-choices-stack">
                    <label
                        v-for="choice in choiceEntries(
                        question.choice,
                      )"
                        :key="choice[0]"
                        class="quiz-choice-row"
                        :class="{
                        selected:
                          answers[question.id] ===
                          choice[0],
                        correct:
                          isQuizSubmitted &&
                          choice[0] ===
                            question.answer,
                        incorrect:
                          isQuizSubmitted &&
                          answers[question.id] ===
                            choice[0] &&
                          choice[0] !==
                            question.answer,
                      }"
                    >
                      <input
                          v-model="answers[question.id]"
                          type="radio"
                          :name="`q-${question.id}`"
                          :value="choice[0]"
                          :disabled="isQuizSubmitted"
                      />

                      <span class="quiz-choice-box">
                        {{ choice[0] }}
                      </span>

                      <span class="quiz-choice-content">
                        {{ choice[1] }}
                      </span>
                    </label>
                  </div>

                  <div
                      v-if="isQuizSubmitted"
                      class="quiz-analysis-box"
                  >
                    <div class="quiz-analysis-meta">
                      正确答案：
                      <strong>
                        {{ question.answer }}
                      </strong>
                    </div>

                    <p
                        v-if="question.analysis"
                        class="cognitive-note"
                    >
                      {{ question.analysis }}
                    </p>
                  </div>
                </article>
              </div>

              <div
                  v-if="quizResult"
                  class="quiz-result-report"
              >
                <div class="report-top">
                  <div class="report-score">
                    <span class="agent-eyebrow">
                      SCORE
                    </span>

                    <strong>
                      {{ quizResult.score }}
                      <small>/ 5</small>
                    </strong>
                  </div>

                  <div class="report-text">
                    <h4>诊断结果</h4>
                    <p>
                      {{
                        resultText(
                            quizResult.outcome,
                        )
                      }}
                    </p>
                  </div>
                </div>

                <div
                    v-if="
                    quizResult.weak_knowledge_points
                      ?.length
                  "
                    class="report-weak-zone"
                >
                  <label>建议复习</label>

                  <div class="report-weak-tags">
                    <span
                        v-for="point in quizResult.weak_knowledge_points"
                        :key="point"
                        class="weak-tag"
                    >
                      {{ point }}
                    </span>
                  </div>
                </div>

              </div>
            </section>

            <footer
                v-if="!isQuizSubmitted"
                class="quiz-submit-bar"
            >
              <span>
                已完成
                {{ answeredQuestionCount }} /
                {{ quizRound.questions.length }}
                题
              </span>

              <button
                  class="primary-action-button"
                  type="button"
                  :disabled="submitLoading"
                  @click="submitQuiz"
              >
                {{
                  submitLoading
                      ? '正在评估'
                      : '提交答案'
                }}
              </button>
            </footer>
          </section>
        </div>
      </transition>
    </Teleport>
  </main>
</template>

<script setup lang="ts">
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue'
import {
  onBeforeRouteLeave,
  useRoute,
  useRouter,
} from 'vue-router'
import { toast } from 'vue-sonner'

import Markdown from '@/shared/content/renderers/Markdown.vue'
import ArtifactRenderer from '@/shared/content/ArtifactRenderer.vue'

import {
  generateNodeResource,
  generateNodeQuestions,
  getNodeQuestions,
  generateTutorial,
  getLearningNodeWorkspace,
  startLearning,
  submitNodeQuiz,
} from '@/features/learning-path/api/path'

import {
  recordPathLearningEvent,
} from '@/features/evaluation/api/evaluation'

import type {
  LearningPathResource,
  LearningPathTutorial,
  LearningPathWorkspace,
  PathQuizRound,
  PathQuizSubmitResponse,
} from '@/features/learning-path/model/path'

import {
  getErrorMessage,
} from '@/shared/api/http'

type TocItem = {
  id: string
  title: string
  level: number
}

type ResourceKind =
    | 'mindmap'
    | 'code'
    | 'ppt'
    | 'reading'
    | 'cartoon'

type ResourcePushItem = {
  type: ResourceKind
  title: string
  desc: string
  icon: string
  resource:
      | LearningPathWorkspace['resources'][number]
      | null
}

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const quizLoading = ref(false)
const submitLoading = ref(false)

const resourceStarting =
    ref<Set<ResourceKind>>(new Set())

const workspace =
    ref<LearningPathWorkspace | null>(null)

const quizRound =
    ref<PathQuizRound | null>(null)

const quizResult =
    ref<PathQuizSubmitResponse | null>(null)

const answers =
    ref<Record<number, string>>({})

const hasStartedTracking = ref(false)
const showQuizOverlay = ref(false)

const selectedTutorialId =
    ref<number | null>(null)

const isGeneratingTutorial = ref(false)
const generatingStep = ref(0)

const contentEl =
    ref<HTMLElement | null>(null)

const activeHeadingId = ref('')
const isQuizSubmitted = ref(false)

const showViewer = ref(false)
const viewerLoading = ref(false)

const viewerResource =
    ref<LearningPathResource | null>(null)

const viewerContent = ref('')

let headingObserver:
    | IntersectionObserver
    | null = null

let generationTimer:
    | number
    | null = null

let resourcePollTimer:
    | number
    | null = null

let resourcePollInFlight = false
let isPageActive = false

const RESOURCE_POLL_INTERVAL_MS = 2500

const resourceKinds: ResourceKind[] = [
  'mindmap',
  'code',
  'ppt',
  'reading',
  'cartoon',
]

const tutorialGenerationSteps = [
  '读取学习目标与当前基础',
  '分析节点知识范围',
  '组织教程章节结构',
  '补充示例与易错点',
  '保存教程并准备学习空间',
]

const nodeId = computed(() => {
  return Number(
      route.params.nodeId || 0,
  )
})

const generationStepNumber = computed(() => {
  return Math.min(
      generatingStep.value + 1,
      tutorialGenerationSteps.length,
  )
})

const currentGenerationStep = computed(() => {
  return (
      tutorialGenerationSteps[
          generatingStep.value
          ] ||
      tutorialGenerationSteps[
      tutorialGenerationSteps.length - 1
          ]
  )
})

const generationProgress = computed(() => {
  return Math.min(
      100,
      Math.max(
          8,
          (generationStepNumber.value /
              tutorialGenerationSteps.length) *
          100,
      ),
  )
})

const answeredQuestionCount = computed(() => {
  if (!quizRound.value) {
    return 0
  }

  return quizRound.value.questions.filter(
      question =>
          Boolean(answers.value[question.id]),
  ).length
})

const displayedTutorial =
    computed<LearningPathTutorial | null>(
        () => {
          if (!workspace.value) {
            return null
          }

          if (selectedTutorialId.value) {
            return (
                workspace.value.tutorials.find(
                    item =>
                        item.id ===
                        selectedTutorialId.value,
                ) ||
                workspace.value.current_tutorial
            )
          }

          return (
              workspace.value.current_tutorial
          )
        },
    )

const tutorialMarkdown = computed(() => {
  return preprocessTutorialMarkdown(
      displayedTutorial.value
          ?.content_markdown || '',
  )
})

const tutorialToc =
    computed<TocItem[]>(() => {
      const markdown =
          tutorialMarkdown.value

      if (!markdown) {
        return []
      }

      const result: TocItem[] = []
      const used =
          new Map<string, number>()

      const headingRegex =
          /^(#{2,3})\s+(.+)$/gm

      let match:
          | RegExpExecArray
          | null

      while (
          (match =
              headingRegex.exec(markdown)) !==
          null
          ) {
        const rawLevel = match[1]
        const rawTitle = match[2]

        if (!rawLevel || !rawTitle) {
          continue
        }

        const level = rawLevel.length

        const title = rawTitle
            .replace(/[#*_`>]/g, '')
            .trim()

        if (!title) {
          continue
        }

        const base = slugify(title)
        const count =
            used.get(base) || 0

        used.set(base, count + 1)

        result.push({
          id: count
              ? `${base}-${count + 1}`
              : base,
          title,
          level,
        })
      }

      return result.slice(0, 18)
    })

const resourcePushItems =
    computed<ResourcePushItem[]>(
        () => [
          {
            type: 'mindmap',
            title: '思维导图',
            desc: '梳理核心概念与关系',
            icon: 'M11 3h2v4h-2V3Zm-7 8h6v2H4v-2Zm10 0h6v2h-6v-2ZM5 17h5v2H5v-2Zm9 0h5v2h-5v-2ZM11 8h2v3h-2V8Zm0 5h2v3h-2v-3Z',
            resource:
                latestResourceByType(
                    'mindmap',
                ),
          },
          {
            type: 'code',
            title: '代码实操',
            desc: '生成代码与实践示例',
            icon: 'm8.7 16.3-4.3-4.3 4.3-4.3L7.3 6.3 1.6 12l5.7 5.7 1.4-1.4Zm6.6 0 4.3-4.3-4.3-4.3 1.4-1.4 5.7 5.7-5.7 5.7-1.4-1.4ZM10.8 20 13.4 4h2l-2.6 16h-2Z',
            resource:
                latestResourceByType('code'),
          },
          {
            type: 'ppt',
            title: 'PPT 课件',
            desc: '生成便于复习的课件',
            icon: 'M4 3h16v18H4V3Zm2 2v14h12V5H6Zm2 3h8v2H8V8Zm0 4h8v2H8v-2Zm0 4h5v2H8v-2Z',
            resource:
                latestResourceByType('ppt'),
          },
          {
            type: 'reading',
            title: '拓展阅读',
            desc: '推荐相关补充资料',
            icon: 'M12 6.5A5.5 5.5 0 0 0 6.5 1H3v18h4.5A4.5 4.5 0 0 1 12 23a4.5 4.5 0 0 1 4.5-4H21V1h-3.5A5.5 5.5 0 0 0 12 6.5ZM5 3h1.5A3.5 3.5 0 0 1 10 6.5v11.2A6.5 6.5 0 0 0 7.5 17H5V3Zm14 14h-2.5a6.5 6.5 0 0 0-2.5.7V6.5A3.5 3.5 0 0 1 17.5 3H19v14Z',
            resource:
                latestResourceByType(
                    'reading',
                ),
          },
          {
            type: 'cartoon',
            title: '动画讲解',
            desc: '动态演示知识机制',
            icon: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z',
            resource:
                latestResourceByType(
                    'cartoon',
                ),
          },
        ],
    )

function preprocessTutorialMarkdown(
    raw: string,
): string {
  if (!raw) {
    return ''
  }

  let text = normalizeTutorialMarkdown(raw)

  if (text.startsWith('---')) {
    const endMatch =
        text.indexOf('\n---', 3)

    if (endMatch !== -1) {
      text = text
          .slice(endMatch + 4)
          .trim()
    }
  }

  const metaBlockRegex =
      /^#\s+(.+?)\s*\n\n((?:>.*\n?)+)/

  const metaMatch =
      metaBlockRegex.exec(text)

  if (metaMatch) {
    const blockquoteLines =
        metaMatch[2] || ''

    let summary = ''
    let knowledgePoints = ''
    let tutorialType = ''

    const blockquoteText =
        blockquoteLines
            .split('\n')
            .map(line =>
                line
                    .replace(/^>\s*/, '')
                    .trim(),
            )
            .filter(Boolean)
            .join(' ')

    const summaryMatch =
        blockquoteText.match(
            /\*\*摘要\*\*[：:]\s*(.+?)(?=\s*\*\*|$)/,
        )

    if (summaryMatch) {
      summary =
          summaryMatch[1]?.trim() || ''
    }

    const knowledgeMatch =
        blockquoteText.match(
            /\*\*知识点\*\*[：:]\s*(.+?)(?=\s*\*\*|$)/,
        )

    if (knowledgeMatch) {
      knowledgePoints =
          knowledgeMatch[1]?.trim() || ''
    }

    const typeMatch =
        blockquoteText.match(
            /\*\*类型\*\*[：:]\s*(\w+)/,
        )

    if (typeMatch) {
      tutorialType =
          typeMatch[1]?.trim() || ''
    }

    const typeLabel:
        Record<string, string> = {
      primary: '主教程',
    }

    const renderedMeta = [
      '<div class="tutorial-meta-banner">',
      summary
          ? `  <div class="meta-summary">${summary}</div>`
          : '',
      knowledgePoints
          ? `  <div class="meta-kp"><strong>知识点：</strong>${knowledgePoints}</div>`
          : '',
      tutorialType
          ? `  <div class="meta-type"><span class="type-badge type-${tutorialType}">${typeLabel[tutorialType] || tutorialType}</span></div>`
          : '',
      '</div>',
      '',
    ]
        .filter(Boolean)
        .join('\n')

    text =
        renderedMeta +
        text.slice(
            metaMatch.index +
            metaMatch[0].length,
        )
  } else {
    text = text.replace(
        /^#\s+.+?\n+/,
        '',
    )
  }

  return text.trim()
}

function normalizeTutorialMarkdown(
    raw: string,
): string {
  const text = raw
      .trim()
      .replace(/^\uFEFF/, '')

  const opening = text.match(
      /^(`{3,}|~{3,})(?:markdown|md|text)?[ \t]*\r?\n/i,
  )

  if (!opening?.[1]) {
    return text
  }

  const fence = opening[1]
  const escapedFence = fence.replace(
      /[.*+?^${}()|[\]\\]/g,
      '\\$&',
  )
  const closing = new RegExp(
      `\\r?\\n${escapedFence}[ \\t]*$`,
  )
  const closingMatch = closing.exec(text)

  const document = text
      .slice(
          opening[0].length,
          closingMatch?.index ?? text.length,
      )
      .trim()

  if (
    /^#\s+\S/.test(document) &&
    /^##\s+\S/m.test(document)
  ) {
    return document
  }

  return text
}

function latestResourceByType(
    type: ResourceKind,
    currentWorkspace:
        LearningPathWorkspace | null = workspace.value,
): LearningPathResource | null {
  if (!currentWorkspace) {
    return null
  }

  const matched =
      currentWorkspace.resources
          .filter(
              item =>
                  item.resource_type === type,
          )
          .sort(
              (first, second) =>
                  second.version_no -
                  first.version_no,
          )

  return matched[0] || null
}

function normalizedResourceStatus(
    resource: LearningPathResource | null,
) {
  return String(
      resource?.status || '',
  ).toLowerCase()
}

function isResourceReady(
    resource: LearningPathResource | null,
) {
  return (
    normalizedResourceStatus(resource) ===
    'completed'
  )
}

function isResourceFailed(
    resource: LearningPathResource | null,
) {
  return (
    normalizedResourceStatus(resource) ===
    'failed'
  )
}

function isPersistedResourceGenerating(
    resource: LearningPathResource | null,
) {
  return [
    'pending',
    'generating',
    'processing',
  ].includes(
      normalizedResourceStatus(resource),
  )
}

function isResourceGenerating(
    item: ResourcePushItem,
) {
  return (
    resourceStarting.value.has(item.type) ||
    isPersistedResourceGenerating(
        item.resource,
    )
  )
}

function resourceStatusText(
    item: ResourcePushItem,
) {
  if (isResourceGenerating(item)) {
    return '生成中'
  }

  if (isResourceFailed(item.resource)) {
    return '生成失败'
  }

  if (isResourceReady(item.resource)) {
    return '已生成'
  }

  return '尚未生成'
}

function resourceActionText(
    item: ResourcePushItem,
) {
  if (isResourceGenerating(item)) {
    return '生成中'
  }

  if (isResourceFailed(item.resource)) {
    return '重试'
  }

  if (isResourceReady(item.resource)) {
    return '查看'
  }

  return '生成'
}

function slugify(value: string) {
  return (
      value
          .toLowerCase()
          .replace(
              /[^\w\u4e00-\u9fa5]+/g,
              '-',
          )
          .replace(/^-+|-+$/g, '') ||
      `heading-${Math.random()
          .toString(36)
          .slice(2, 8)}`
  )
}

function disconnectHeadingObserver() {
  headingObserver?.disconnect()
  headingObserver = null
}

function setupHeadingObserver() {
  disconnectHeadingObserver()

  const root = contentEl.value

  if (
      !root ||
      typeof IntersectionObserver ===
      'undefined'
  ) {
    return
  }

  const headings =
      Array.from(
          root.querySelectorAll(
              'h2, h3',
          ),
      ) as HTMLElement[]

  if (!headings.length) {
    return
  }

  headingObserver =
      new IntersectionObserver(
          entries => {
            const visibleEntries =
                entries
                    .filter(
                        entry =>
                            entry.isIntersecting,
                    )
                    .sort(
                        (first, second) =>
                            first.boundingClientRect
                                .top -
                            second.boundingClientRect
                                .top,
                    )

            const current =
                visibleEntries[0]

            if (
                current?.target instanceof
                HTMLElement
            ) {
              activeHeadingId.value =
                  current.target.id
            }
          },
          {
            rootMargin:
                '-96px 0px -68% 0px',
            threshold: [0, 1],
          },
      )

  headings.forEach(heading => {
    headingObserver?.observe(heading)
  })
}

async function syncHeadingAnchors() {
  await nextTick()

  window.setTimeout(() => {
    const root = contentEl.value

    if (!root) {
      return
    }

    const headings =
        Array.from(
            root.querySelectorAll(
                'h2, h3',
            ),
        ) as HTMLElement[]

    const toc = tutorialToc.value

    headings.forEach(
        (heading, index) => {
          const item = toc[index]

          if (!item) {
            return
          }

          heading.id = item.id

          heading.classList.add(
              'tutorial-anchor-heading',
          )
        },
    )

    if (
        !activeHeadingId.value &&
        toc[0]
    ) {
      activeHeadingId.value =
          toc[0].id
    }

    setupHeadingObserver()
  }, 100)
}

function scrollToHeading(id: string) {
  activeHeadingId.value = id

  const root = contentEl.value

  const target =
      root?.querySelector(
          `#${CSS.escape(id)}`,
      ) as HTMLElement | null

  target?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

function startGenerationAnimation() {
  stopGenerationAnimation()
  generatingStep.value = 0

  generationTimer =
      window.setInterval(() => {
        if (
            generatingStep.value <
            tutorialGenerationSteps.length -
            1
        ) {
          generatingStep.value += 1
        } else {
          stopGenerationAnimation()
        }
      }, 1800)
}

function stopGenerationAnimation() {
  if (generationTimer !== null) {
    window.clearInterval(
        generationTimer,
    )

    generationTimer = null
  }
}

async function loadWorkspace() {
  if (!nodeId.value) {
    return
  }

  loading.value = true

  try {
    const response =
        await getLearningNodeWorkspace(
            nodeId.value,
        )

    workspace.value =
        response.data.data

    resumeResourcePolling()

    if (
        workspace.value &&
        !workspace.value.current_tutorial
    ) {
      await generatePrimaryTutorial()
    } else if (
        workspace.value?.current_tutorial
    ) {
      selectedTutorialId.value =
          workspace.value.current_tutorial.id
    }

    await recordPathNodeStarted()
    await syncHeadingAnchors()
  } catch (error) {
    toast.error(
        getErrorMessage(
            error,
            '加载节点学习空间失败',
        ),
    )
  } finally {
    loading.value = false
    isGeneratingTutorial.value =
        false
    stopGenerationAnimation()
  }
}

async function generatePrimaryTutorial() {
  isGeneratingTutorial.value = true
  loading.value = false

  startGenerationAnimation()

  try {
    await startLearning(nodeId.value)

    const tutorialResponse =
        await generateTutorial(
            nodeId.value,
        )

    workspace.value =
        tutorialResponse.data.data

    generatingStep.value =
        tutorialGenerationSteps.length -
        1

    if (
        workspace.value
            ?.current_tutorial
    ) {
      selectedTutorialId.value =
          workspace.value.current_tutorial.id
    }
  } finally {
    stopGenerationAnimation()
    isGeneratingTutorial.value =
        false
  }
}

async function recordPathNodeStarted() {
  if (
      !workspace.value ||
      hasStartedTracking.value
  ) {
    return
  }

  hasStartedTracking.value = true

  await recordPathLearningEvent(
      workspace.value.path.id,
      {
        module: 'path',
        event_type:
            'path_node_started',
        course:
        workspace.value.path.title,
        topic:
        workspace.value.node.title,
        client_event_id:
            createClientEventId(),
        occurred_at:
            new Date().toISOString(),
        event_metadata: {
          path_id:
          workspace.value.path.id,
          path_node_id:
          workspace.value.node.id,
          node_id:
          workspace.value.node
              .node_id,
        },
      },
  )
}

function createClientEventId() {
  if (
      typeof crypto.randomUUID ===
      'function'
  ) {
    return crypto.randomUUID()
  }

  return `evt-${Math.random()
      .toString(36)
      .slice(2, 11)}-${Date.now()}`
}

function hydrateQuizState(
    round: PathQuizRound,
) {
  quizRound.value = round

  const nextAnswers:
      Record<number, string> = {}

  let submittedCount = 0

  for (
      const question of round.questions
      ) {
    if (question.response) {
      nextAnswers[question.id] =
          question.response
    }

    if (
        question.response ||
        question.is_correct !== null
    ) {
      submittedCount += 1
    }
  }

  answers.value = nextAnswers

  isQuizSubmitted.value =
      round.questions.length > 0 &&
      submittedCount ===
      round.questions.length
}

async function loadQuiz() {
  if (!workspace.value) {
    return
  }

  if (
      showQuizOverlay.value &&
      quizRound.value
  ) {
    return
  }

  if (quizRound.value) {
    showQuizOverlay.value = true
    return
  }

  quizLoading.value = true
  quizResult.value = null
  isQuizSubmitted.value = false

  try {
    if (
        workspace.value.current_round > 0
    ) {
      const response =
          await getNodeQuestions(
              workspace.value.node.id,
          )

      const data =
          response.data.data

      if (data) {
        hydrateQuizState(data)
        showQuizOverlay.value = true
        return
      }
    }

    const response =
        await generateNodeQuestions(
            workspace.value.node.id,
        )

    hydrateQuizState(
        response.data.data,
    )

    showQuizOverlay.value = true

    const workspaceResponse =
        await getLearningNodeWorkspace(
            nodeId.value,
        )

    workspace.value =
        workspaceResponse.data.data
  } catch (error) {
    toast.error(
        getErrorMessage(
            error,
            '生成节点测验失败',
        ),
    )
  } finally {
    quizLoading.value = false
  }
}

async function submitQuiz() {
  if (
      !workspace.value ||
      !quizRound.value
  ) {
    return
  }

  // 校验是否所有题都已作答
  const unanswered = quizRound.value.questions.some(
      question => !answers.value[question.id],
  )
  if (unanswered) {
    toast.warning(
        '请先完成全部诊断题目',
    )
    return
  }

  // ── 本地即时评分（answer 已随题目一起返回，无需等后端） ──
  const questions = quizRound.value.questions
  let correctCount = 0
  const weakPoints: string[] = []

  for (const question of questions) {
    const userAnswer = answers.value[question.id] || ''
    const isCorrect = userAnswer === question.answer
    if (isCorrect) {
      correctCount++
    } else {
      for (const point of question.knowledge_points) {
        if (!weakPoints.includes(point)) {
          weakPoints.push(point)
        }
      }
    }
  }

  const passed = correctCount >= 3
  const outcome = passed ? 'completed' : 'completed_with_gaps'

  // 立即展示结果
  quizResult.value = {
    node_id: workspace.value.node.id,
    round_no: quizRound.value.round_no,
    score: correctCount,
    passed,
    outcome,
    weak_knowledge_points: weakPoints,
    next_node_id: null,
    current_tutorial_id: null,
  }

  isQuizSubmitted.value = true

  // 后台异步提交给后端做持久化（不阻塞 UI）
  const payload = {
    answers: questions.map(question => ({
      question_id: question.id,
      response: answers.value[question.id] || '',
    })),
  }

  submitLoading.value = true

  try {
    const response =
        await submitNodeQuiz(
            workspace.value.node.id,
            payload,
        )

    // 用后端返回的权威结果覆盖本地结果（含 next_node_id 等）
    quizResult.value =
        response.data.data

    await recordPathLearningEvent(
        workspace.value.path.id,
        {
          module: 'path',
          event_type:
              'path_quiz_answered',
          course:
          workspace.value.path.title,
          topic:
          workspace.value.node.title,
          score: Number(
              (
                  (quizResult.value.score /
                      5) *
                  100
              ).toFixed(0),
          ),
          client_event_id:
              createClientEventId(),
          occurred_at:
              new Date().toISOString(),
          event_metadata: {
            path_id:
            workspace.value.path.id,
            path_node_id:
            workspace.value.node.id,
            node_id:
            workspace.value.node
                .node_id,
            is_correct:
                quizResult.value
                    .outcome ===
                'completed',
            attempt_index: 1,
            weak_knowledge_points:
            quizResult.value
                .weak_knowledge_points,
          },
        },
    )

    const submittedRound =
        await getNodeQuestions(
            workspace.value.node.id,
        )

    if (
        submittedRound.data.data
    ) {
      hydrateQuizState(
          submittedRound.data.data,
      )
    }

    const workspaceResponse =
        await getLearningNodeWorkspace(
            nodeId.value,
        )

    workspace.value =
        workspaceResponse.data.data

    if (
        workspace.value
            ?.current_tutorial
    ) {
      selectedTutorialId.value =
          workspace.value.current_tutorial.id
    }
  } catch (error) {
    toast.error(
        getErrorMessage(
            error,
            '提交节点测验失败',
        ),
    )
  } finally {
    submitLoading.value = false
  }
}

function stopResourcePolling() {
  if (resourcePollTimer !== null) {
    window.clearTimeout(
        resourcePollTimer,
    )
    resourcePollTimer = null
  }
}

function hasGeneratingResources(
    currentWorkspace:
        LearningPathWorkspace | null = workspace.value,
) {
  return resourceKinds.some(type =>
    isPersistedResourceGenerating(
        latestResourceByType(
            type,
            currentWorkspace,
        ),
    ),
  )
}

function scheduleResourcePolling(
    delay = RESOURCE_POLL_INTERVAL_MS,
) {
  stopResourcePolling()

  if (
      !isPageActive ||
      !hasGeneratingResources()
  ) {
    return
  }

  resourcePollTimer =
      window.setTimeout(() => {
        void pollResourceStatuses()
      }, delay)
}

function resumeResourcePolling() {
  if (hasGeneratingResources()) {
    scheduleResourcePolling()
  } else {
    stopResourcePolling()
  }
}

async function pollResourceStatuses() {
  resourcePollTimer = null

  if (
      resourcePollInFlight ||
      !isPageActive ||
      !nodeId.value ||
      !hasGeneratingResources()
  ) {
    return
  }

  resourcePollInFlight = true
  const polledNodeId = nodeId.value
  const previousWorkspace = workspace.value

  try {
    const response =
        await getLearningNodeWorkspace(
            nodeId.value,
        )

    const nextWorkspace =
        response.data.data

    if (
        !isPageActive ||
        nodeId.value !== polledNodeId
    ) {
      return
    }

    workspace.value = nextWorkspace

    for (const type of resourceKinds) {
      const previous = latestResourceByType(
          type,
          previousWorkspace,
      )
      const current = latestResourceByType(
          type,
          nextWorkspace,
      )

      if (
          isPersistedResourceGenerating(previous) &&
          isResourceReady(current)
      ) {
        toast.success(
            `${resourceTypeLabel(type)}生成完成`,
        )
      }

      if (
          isPersistedResourceGenerating(previous) &&
          isResourceFailed(current)
      ) {
        toast.error(
            current?.error_message ||
            `${resourceTypeLabel(type)}生成失败`,
        )
      }
    }
  } catch {
    // 保留数据库中的 generating 状态，下一轮继续确认。
  } finally {
    resourcePollInFlight = false
    resumeResourcePolling()
  }
}

async function createResource(
    type: ResourceKind,
) {
  if (!workspace.value) {
    return
  }

  // 如果该资源类型已经在生成中，不允许重复点击
  const current = latestResourceByType(type)
  if (
      resourceStarting.value.has(type) ||
      isPersistedResourceGenerating(current)
  ) {
    return
  }

  resourceStarting.value.add(type)
  const requestedNodeId =
      workspace.value.node.id

  try {
    const response =
        await generateNodeResource(
            requestedNodeId,
            type,
        )

    const task =
        response.data.data

    if (
        !isPageActive ||
        workspace.value?.node.id !==
        requestedNodeId
    ) {
      return
    }

    workspace.value = {
      ...workspace.value,
      resources: [
        ...workspace.value.resources.filter(
            item =>
                item.id !== task.resource.id,
        ),
        task.resource,
      ],
    }

    scheduleResourcePolling(800)
  } catch (error) {
    if (isPageActive) {
      toast.error(
          getErrorMessage(
              error,
              '生成辅助资源失败',
          ),
      )
    }
  } finally {
    resourceStarting.value.delete(type)
  }
}

function handleResourceAction(
    item: ResourcePushItem,
) {
  if (isResourceGenerating(item)) {
    return
  }

  if (
      item.resource &&
      isResourceReady(item.resource)
  ) {
    openResourceDetail(
        item.resource.id,
    )
    return
  }

  void createResource(item.type)
}

function openViewer(
    resource: LearningPathResource,
) {
  viewerResource.value = resource

  viewerContent.value =
      resource.content_text ||
      (resource.content_json
          ? JSON.stringify(
              resource.content_json,
              null,
              2,
          )
          : '')

  showViewer.value = true
}

function closeViewer() {
  showViewer.value = false

  window.setTimeout(() => {
    viewerResource.value = null
    viewerContent.value = ''
  }, 180)
}

function openResourceDetail(
    resourceId: number,
) {
  if (!workspace.value) {
    return
  }

  const resource =
      workspace.value.resources.find(
          item =>
              item.id === resourceId,
      )

  if (resource) {
    openViewer(resource)
    return
  }

  toast.warning('资源不存在')
}

function closeQuiz() {
  showQuizOverlay.value = false
}

function choiceEntries(
    choice:
        | Record<string, string>
        | undefined
        | null,
) {
  return Object.entries(
      choice || {},
  )
}

function resourceTypeLabel(
    type: string,
) {
  const labels:
      Record<string, string> = {
    mindmap: '思维导图',
    code: '代码实操',
    ppt: 'PPT 课件',
    reading: '拓展阅读',
    cartoon: '动画讲解',
    quiz: '节点测验',
  }

  return labels[type] || type
}

function tutorialTypeLabel(
    _value?: string | null,
) {
  return '主教程'
}

function formatTime(
    iso:
        | string
        | undefined
        | null,
) {
  if (!iso) {
    return ''
  }

  const date = new Date(iso)

  if (
      Number.isNaN(date.getTime())
  ) {
    return ''
  }

  return `${date.getFullYear()}-${String(
      date.getMonth() + 1,
  ).padStart(2, '0')}-${String(
      date.getDate(),
  ).padStart(2, '0')} ${String(
      date.getHours(),
  ).padStart(2, '0')}:${String(
      date.getMinutes(),
  ).padStart(2, '0')}`
}

function statusText(status: string) {
  switch (status) {
    case 'available':
      return '可开始'
    case 'in_progress':
      return '学习中'
    case 'completed':
      return '已通过'
    case 'completed_with_gaps':
      return '建议复习'
    default:
      return status
  }
}

function resultText(
    outcome: string,
) {
  switch (outcome) {
    case 'completed':
    case 'passed':
      return '本节知识掌握情况良好，下一学习节点已解锁。'
    case 'completed_with_gaps':
      return '已完成本节学习，建议复习薄弱知识点后再继续推进。'
    default:
      return outcome
  }
}

function handleEscape(
    event: KeyboardEvent,
) {
  if (event.key !== 'Escape') {
    return
  }

  if (showViewer.value) {
    closeViewer()
    return
  }

  if (showQuizOverlay.value) {
    closeQuiz()
  }
}

watch(
    () => route.params.nodeId,
    newId => {
      if (!newId) {
        return
      }

      disconnectHeadingObserver()
      stopResourcePolling()
      resourceStarting.value.clear()

      workspace.value = null
      quizRound.value = null
      quizResult.value = null
      answers.value = {}

      selectedTutorialId.value =
          null

      isQuizSubmitted.value = false
      showQuizOverlay.value = false
      showViewer.value = false
      hasStartedTracking.value =
          false

      activeHeadingId.value = ''

      loadWorkspace()
    },
)

watch(tutorialMarkdown, () => {
  syncHeadingAnchors()
})

watch(
    [
      showViewer,
      showQuizOverlay,
    ],
    values => {
      const hasOverlay =
          values.some(Boolean)

      document.body.style.overflow =
          hasOverlay ? 'hidden' : ''
    },
)

onMounted(() => {
  isPageActive = true

  window.addEventListener(
      'keydown',
      handleEscape,
  )

  loadWorkspace()
})

// 提交测验期间阻止离开页面，确保后端解锁下一节点完成
onBeforeRouteLeave(() => {
  if (submitLoading.value) {
    toast.warning('正在提交测验，请稍候…')
    return false
  }
})

onBeforeUnmount(() => {
  isPageActive = false

  window.removeEventListener(
      'keydown',
      handleEscape,
  )

  document.body.style.overflow = ''

  stopGenerationAnimation()
  disconnectHeadingObserver()
  stopResourcePolling()
  resourceStarting.value.clear()
})
</script>

<style scoped>
.node-study-page {
  --study-accent: #159a94;
  --study-accent-hover: #10847f;
  --study-accent-text: #176b67;
  --study-accent-soft: #eaf7f6;
  --study-accent-softer: #f4fbfa;
  --study-accent-border: #83cbc7;
  --study-focus-ring: rgba(21, 154, 148, 0.14);

  --study-text-strong: #182f33;
  --study-text: #304448;
  --study-text-secondary: #64767a;
  --study-text-muted: #849397;
  --study-text-faint: #9da9ac;

  --study-border: #dce7e6;
  --study-border-light: #e9efee;
  --study-surface: #ffffff;
  --study-background: #f8faf9;

  min-height:
      calc(
          100vh -
          var(--navbar-height, 72px)
      );
  padding: 14px 24px 40px;
  background:
      radial-gradient(
          circle at 88% 2%,
          rgba(21, 154, 148, 0.03),
          transparent 32rem
      ),
      var(--study-background);
  color: var(--study-text);
}

.node-study-page *,
.node-study-page *::before,
.node-study-page *::after {
  box-sizing: border-box;
}

.node-study-page button,
.node-study-page input {
  font-family: inherit;
}

.node-toolbar {
  display: flex;
  width: min(1480px, 100%);
  min-height: 58px;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin: 0 auto 16px;
  padding: 7px 0 13px;
  border-bottom: 1px solid
  var(--study-border-light);
}

.toolbar-left {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 15px;
}

.back-button {
  display: inline-flex;
  height: 36px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 13px;
  border: 0px solid
  var(--study-border);
  border-radius: 6px;
  background:
      var(--study-surface);
  color:
      var(--study-text-secondary);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
  transition:
      border-color 170ms ease,
      background-color 170ms ease,
      color 170ms ease;
}

.back-button:hover {
  border-color:
      var(--study-accent-border);
  background:
      var(--study-accent-softer);
  color:
      var(--study-accent-text);
}

.back-button:focus-visible,
.primary-action-button:focus-visible,
.resource-action-button:focus-visible,
.tutorial-tab:focus-visible,
.toc-item:focus-visible,
.nav-back-button:focus-visible,
.viewer-close-button:focus-visible {
  outline: 3px solid
  var(--study-focus-ring);
  outline-offset: 2px;
}

.back-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.toolbar-title {
  min-width: 0;
}

.toolbar-kicker {
  display: block;
  margin-bottom: 2px;
  color: var(--study-text-muted);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.toolbar-title h1 {
  overflow: hidden;
  margin: 0;
  color:
      var(--study-text-strong);
  font-size: 18px;
  font-weight: 760;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toolbar-right {
  flex-shrink: 0;
}

.status-pill {
  display: inline-flex;
  min-height: 28px;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  border: 0px solid
  var(--study-accent-border);
  border-radius: 6px;
  background:
      var(--study-accent-soft);
  color:
      var(--study-accent-text);
  font-size: 11px;
  font-weight: 700;
}

.status-pill i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.status-pill.completed {
  border-color: #a7dac8;
  background: #eaf7f2;
  color: #26876f;
}

.status-pill.completed_with_gaps {
  border-color: #e7d3a7;
  background: #fbf6e9;
  color: #9b7025;
}

.status-pill.available {
  border-color:
      var(--study-accent-border);
  background:
      var(--study-accent-soft);
  color:
      var(--study-accent-text);
}

.study-workspace {
  display: grid;
  grid-template-columns:
    210px minmax(620px, 1fr) 290px;
  width: min(1480px, 100%);
  align-items: start;
  gap: 16px;
  margin: 0 auto;
}

.toc-panel,
.resource-panel {
  position: sticky;
  top: 16px;
  min-width: 0;
}

.toc-panel {
  padding: 12px 14px 14px 2px;
  border-right: 1px solid
  var(--study-border-light);
}

.resource-panel {
  padding: 12px 2px 14px 14px;
  border-left: 1px solid
  var(--study-border-light);
}

.side-head {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-bottom: 13px;
}

.side-kicker,
.section-kicker,
.generate-kicker,
.agent-eyebrow {
  color:
      var(--study-accent-text);
  font-family:
      var(--font-mono, monospace);
  font-size: 10px;
  font-weight: 750;
  letter-spacing: 0.07em;
  line-height: 1.4;
}

.side-head strong {
  color:
      var(--study-text-strong);
  font-size: 14px;
  font-weight: 750;
}

.toc-list {
  display: flex;
  max-height:
      calc(100vh - 180px);
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  padding-right: 5px;
  scrollbar-width: thin;
  scrollbar-color:
      #d5e2e0 transparent;
}

.toc-item {
  position: relative;
  width: 100%;
  min-height: 32px;
  padding: 7px 8px 7px 13px;
  overflow: hidden;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color:
      var(--study-text-secondary);
  font-size: 12px;
  font-weight: 550;
  line-height: 1.45;
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  transition:
      background-color 160ms ease,
      color 160ms ease;
}

.toc-item::before {
  content: '';
  position: absolute;
  top: 7px;
  bottom: 7px;
  left: 0;
  width: 2px;
  border-radius: 2px;
  background:
      var(--study-accent);
  opacity: 0;
  transition: opacity 160ms ease;
}

.toc-item.level-3 {
  padding-left: 24px;
  color:
      var(--study-text-muted);
  font-size: 11px;
}

.toc-item:hover {
  background:
      var(--study-accent-softer);
  color:
      var(--study-accent-text);
}

.toc-item.active {
  background: transparent;
  color:
      var(--study-accent-text);
  font-weight: 700;
}

.toc-item.active::before {
  opacity: 1;
}

.toc-empty {
  padding: 14px 6px;
}

.toc-empty p {
  margin: 0 0 4px;
  color:
      var(--study-text-secondary);
  font-size: 12px;
  font-weight: 650;
}

.toc-empty span {
  color:
      var(--study-text-faint);
  font-size: 11px;
  line-height: 1.55;
}

.tutorial-main {
  min-width: 0;
  overflow: hidden;
  border: 0px solid
  var(--study-border);
  border-radius: 8px;
  background:
      var(--study-surface);
  box-shadow:
      0 2px 8px
      rgba(30, 70, 73, 0.035);
}

.tutorial-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 22px;
  padding: 24px 28px 21px;
  border-bottom: 1px solid
  var(--study-border-light);
  background: #fdfefe;
}

.tutorial-head-copy {
  min-width: 0;
}

.tutorial-head h2 {
  margin: 5px 0 7px;
  color:
      var(--study-text-strong);
  font-size: 22px;
  font-weight: 760;
  line-height: 1.35;
  letter-spacing: -0.018em;
}

.tutorial-head p {
  max-width: 720px;
  margin: 0;
  color:
      var(--study-text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

.tutorial-tabs {
  display: flex;
  flex-shrink: 0;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 7px;
}

.tutorial-tab {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  gap: 5px;
  padding: 0 10px;
  border: 0px solid
  var(--study-border);
  border-radius: 6px;
  background: #ffffff;
  color:
      var(--study-text-secondary);
  font-size: 11px;
  font-weight: 650;
  cursor: pointer;
  transition:
      border-color 160ms ease,
      background-color 160ms ease,
      color 160ms ease;
}

.tutorial-tab:hover {
  border-color:
      var(--study-accent-border);
  background:
      var(--study-accent-softer);
  color:
      var(--study-accent-text);
}

.tutorial-tab.is-selected {
  border-color:
      var(--study-accent);
  background:
      var(--study-accent-soft);
  color:
      var(--study-accent-text);
  font-weight: 700;
}

.tutorial-tab em {
  color: inherit;
  font-family:
      var(--font-mono, monospace);
  font-size: 10px;
  font-style: normal;
  opacity: 0.72;
}

.tutorial-tab.is-current em::after {
  content: '·当前';
  margin-left: 3px;
}

.tutorial-reader {
  padding: 27px 34px 22px;
}

.markdown-shell {
  min-height: 500px;
}

.markdown-shell :deep(.model-content) {
  width: min(100%, 76ch);
  margin-inline: auto;
}

.markdown-shell :deep(.markdown-body) {
  color: var(--study-text);
  font-size: 15px;
  line-height: 1.78;
}

.markdown-shell :deep(h1) {
  display: none;
}

.markdown-shell :deep(h2) {
  margin: 2.35em 0 0.9em;
  padding-bottom: 0.5em;
  border-bottom: 1px solid
  var(--study-border-light);
  color:
      var(--study-text-strong);
  font-size: 20px;
  font-weight: 750;
  line-height: 1.45;
  scroll-margin-top: 88px;
  text-wrap: balance;
}

.markdown-shell :deep(h3) {
  margin: 1.9em 0 0.75em;
  color:
      var(--study-text-strong);
  font-size: 17px;
  font-weight: 720;
  line-height: 1.5;
  scroll-margin-top: 88px;
  text-wrap: balance;
}

.markdown-shell :deep(h4) {
  margin: 1.55em 0 0.65em;
  color:
      var(--study-text-strong);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.5;
}

.markdown-shell :deep(p),
.markdown-shell :deep(li) {
  font-size: 15px;
  line-height: 1.78;
}

.markdown-shell :deep(p) {
  margin-bottom: 1em;
  text-wrap: pretty;
}

.markdown-shell :deep(ul),
.markdown-shell :deep(ol) {
  margin-bottom: 1.15em;
  padding-left: 1.55em;
}

.markdown-shell :deep(li + li) {
  margin-top: 0.38em;
}

.markdown-shell :deep(li::marker) {
  color: var(--study-accent-text);
  font-weight: 700;
}

.markdown-shell :deep(strong) {
  color:
      var(--study-text-strong);
  font-weight: 700;
}

.markdown-shell :deep(blockquote) {
  margin: 1.25em 0;
  padding: 13px 15px;
  border: 1px solid
  var(--study-accent-border);
  border-radius: 6px;
  background:
      var(--study-accent-softer);
  color:
      var(--study-text-secondary);
}

.markdown-shell :deep(table) {
  width: 100%;
  margin: 1.35em 0;
  border-collapse: separate;
  border-spacing: 0;
  border: 1px solid
  var(--study-border);
  border-radius: 6px;
}

.markdown-shell :deep(th),
.markdown-shell :deep(td) {
  padding: 9px 11px;
  border-width: 0 1px 1px 0;
  border-color:
      var(--study-border-light);
  font-size: 13px;
  line-height: 1.55;
  text-align: left;
}

.markdown-shell :deep(th) {
  background: #f4f8f7;
  color:
      var(--study-text-strong);
}

.markdown-shell :deep(tr > :last-child) {
  border-right: 0;
}

.markdown-shell :deep(tr:last-child > td) {
  border-bottom: 0;
}

.markdown-shell :deep(:not(pre) > code) {
  border-color:
      var(--study-border);
  border-radius: 4px;
  background: #f2f6f5;
  color: #145f5d;
}

.markdown-shell :deep(.code-block-wrapper) {
  margin: 1.35em 0;
  border-color:
      var(--study-border);
  border-radius: 6px;
  box-shadow: none;
}

.markdown-shell :deep(.code-block-header) {
  background: #f4f8f7;
}

.markdown-shell :deep(a) {
  color:
      var(--study-accent-text);
  text-underline-offset: 3px;
}

.markdown-shell :deep(.tutorial-meta-banner) {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0 0 24px;
  padding: 15px 17px;
  border: 1px solid
  var(--study-accent-border);
  border-radius: 6px;
  background: #f9fbfb;
}

.markdown-shell :deep(.tutorial-meta-banner + h2) {
  margin-top: 0;
}

.markdown-shell :deep(.meta-summary) {
  color:
      var(--study-text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

.markdown-shell :deep(.meta-kp) {
  color: var(--study-text);
  font-size: 12px;
  line-height: 1.6;
}

.markdown-shell :deep(.meta-kp strong) {
  color:
      var(--study-text-strong);
}

.markdown-shell :deep(.meta-type) {
  display: flex;
}

.markdown-shell :deep(.type-badge) {
  display: inline-flex;
  min-height: 23px;
  align-items: center;
  padding: 0 8px;
  border: 0px solid
  var(--study-accent-border);
  border-radius: 5px;
  background:
      var(--study-accent-soft);
  color:
      var(--study-accent-text);
  font-size: 10px;
  font-weight: 700;
}

.tutorial-empty {
  display: flex;
  min-height: 420px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color:
      var(--study-text-secondary);
  text-align: center;
}

.tutorial-empty h3 {
  margin: 0 0 6px;
  color:
      var(--study-text-strong);
  font-size: 16px;
}

.tutorial-empty p {
  margin: 0;
  font-size: 13px;
}

.tutorial-native-quiz {
  padding: 0 34px 30px;
}

.content-divider {
  height: 1px;
  background:
      var(--study-border-light);
}

.quiz-native-head {
  margin: 25px 0 16px;
}

.quiz-native-head h2 {
  margin: 4px 0 7px;
  color:
      var(--study-text-strong);
  font-size: 18px;
  font-weight: 750;
}

.quiz-native-head p {
  max-width: 760px;
  margin: 0;
  color:
      var(--study-text-secondary);
  font-size: 13px;
  line-height: 1.65;
}

.quiz-native-preload {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 14px 15px;
  border: 0px solid
  var(--study-border-light);
  border-radius: 7px;
  background: #fafcfc;
}

.diagnostic-dimensions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
}

.dimension-label {
  margin-right: 3px;
  color:
      var(--study-text-muted);
  font-size: 11px;
  font-weight: 650;
}

.dimension-tag {
  display: inline-flex;
  min-height: 25px;
  align-items: center;
  padding: 0 8px;
  border: 0px solid
  var(--study-border);
  border-radius: 5px;
  background: #ffffff;
  color:
      var(--study-text-secondary);
  font-size: 11px;
  font-weight: 600;
}

.quiz-action-trigger-zone {
  flex-shrink: 0;
}

.primary-action-button {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 15px;
  border: 0px solid
  var(--study-accent);
  border-radius: 6px;
  background:
      linear-gradient(
          135deg,
          #159a94,
          #31aaa4
      );
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  box-shadow:
      0 4px 12px
      rgba(21, 154, 148, 0.16);
  transition:
      border-color 170ms ease,
      background-color 170ms ease,
      box-shadow 170ms ease,
      transform 170ms ease;
}

.primary-action-button svg {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}

.primary-action-button:hover:not(:disabled) {
  border-color:
      var(--study-accent-hover);
  background:
      linear-gradient(
          135deg,
          #10847f,
          #249c96
      );
  box-shadow:
      0 6px 16px
      rgba(21, 154, 148, 0.2);
  transform: translateY(-1px);
}

.primary-action-button:disabled {
  cursor: not-allowed;
  box-shadow: none;
  opacity: 0.55;
}

.quiz-trigger-button {
  min-width: 132px;
}

.push-desc {
  margin: 0 0 13px;
  color:
      var(--study-text-secondary);
  font-size: 11px;
  line-height: 1.6;
}

.resource-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.resource-item {
  display: grid;
  grid-template-columns:
    34px minmax(0, 1fr) auto;
  min-height: 64px;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border: 0px solid
  var(--study-border-light);
  border-radius: 6px;
  background:
      var(--study-surface);
  transition:
      border-color 160ms ease,
      background-color 160ms ease;
}

.resource-item:hover {
  border-color:
      var(--study-accent-border);
  background:
      var(--study-accent-softer);
}

.resource-icon-wrapper {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 5px;
  background:
      var(--study-accent-soft);
  color:
      var(--study-accent-text);
}

.resource-icon-wrapper svg {
  width: 18px;
  height: 18px;
}

.resource-item.mindmap
.resource-icon-wrapper {
  background: #f2eefb;
  color: #7660a8;
}

.resource-item.ppt
.resource-icon-wrapper {
  background: #fbf4e8;
  color: #b57a26;
}

.resource-item.reading
.resource-icon-wrapper {
  background: #edf7f2;
  color: #32856d;
}

.resource-item.cartoon
.resource-icon-wrapper {
  background: #faeeee;
  color: #b86565;
}

.resource-copy {
  min-width: 0;
}

.resource-copy strong {
  display: block;
  margin-bottom: 2px;
  color:
      var(--study-text-strong);
  font-size: 12px;
  font-weight: 700;
}

.resource-copy > span {
  display: block;
  overflow: hidden;
  color:
      var(--study-text-faint);
  font-size: 10px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-label {
  display: inline-flex;
  margin-top: 4px;
  color:
      var(--study-accent-text);
  font-size: 9px;
  font-style: normal;
  font-weight: 700;
}

.status-label.wait {
  color:
      var(--study-text-muted);
}

.status-label.fail {
  color: #bd5d5d;
}

.resource-action-button {
  display: inline-flex;
  min-width: 47px;
  height: 29px;
  align-items: center;
  justify-content: center;
  padding: 0 8px;
  border: 0px solid
  var(--study-accent-border);
  border-radius: 5px;
  background: #ffffff;
  color:
      var(--study-accent-text);
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
  transition:
      border-color 160ms ease,
      background-color 160ms ease,
      color 160ms ease;
}

.resource-action-button:hover:not(:disabled) {
  border-color:
      var(--study-accent);
  background:
      var(--study-accent-soft);
}

.resource-action-button:disabled {
  border-color:
      var(--study-border);
  background: #f4f6f6;
  color:
      var(--study-text-faint);
  cursor: not-allowed;
}

.state-card {
  display: flex;
  width: min(460px, 100%);
  min-height: 270px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 11px;
  margin: 110px auto 0;
  padding: 30px 25px;
  border: 0px solid
  var(--study-border);
  border-radius: 9px;
  background:
      var(--study-surface);
  color:
      var(--study-text-secondary);
  text-align: center;
  box-shadow:
      0 8px 30px
      rgba(30, 70, 73, 0.07);
}

.state-card h2 {
  margin: 4px 0 0;
  color:
      var(--study-text-strong);
  font-size: 16px;
  font-weight: 750;
}

.state-card p {
  max-width: 360px;
  margin: 0 0 7px;
  font-size: 12px;
  line-height: 1.6;
}

.state-spinner {
  width: 31px;
  height: 31px;
  border: 3px solid
  var(--study-border-light);
  border-top-color:
      var(--study-accent);
  border-radius: 50%;
  animation:
      spin 0.8s linear infinite;
}

.state-icon {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 50%;
}

.state-icon svg {
  width: 25px;
  height: 25px;
}

.state-icon-error {
  border: 0px solid #edc6c6;
  background: #fbeeee;
  color: #bd5d5d;
}

.generating-view {
  display: grid;
  min-height:
      calc(100vh - 140px);
  place-items: center;
}

.generate-panel {
  width: min(600px, 100%);
  padding: 32px;
  border: 0px solid
  var(--study-accent-border);
  border-radius: 12px;
  background: #ffffff;
  box-shadow:
      0 18px 50px
      rgba(30, 70, 73, 0.09);
}

.generate-loader {
  position: relative;
  display: grid;
  width: 54px;
  height: 54px;
  place-items: center;
  margin: 0 auto 16px;
  color:
      var(--study-accent);
}

.generate-loader svg {
  width: 23px;
  height: 23px;
}

.generate-loader-ring {
  position: absolute;
  inset: 0;
  border: 3px solid
  rgba(21, 154, 148, 0.12);
  border-top-color:
      var(--study-accent);
  border-right-color: #69c3be;
  border-radius: 50%;
  animation:
      spin 1.1s linear infinite;
}

.generate-copy {
  text-align: center;
}

.generate-copy h1 {
  margin: 5px 0 7px;
  color:
      var(--study-text-strong);
  font-size: 20px;
  font-weight: 760;
}

.generate-copy p {
  max-width: 460px;
  margin: 0 auto;
  color:
      var(--study-text-secondary);
  font-size: 12px;
  line-height: 1.65;
}

.generate-stage-panel {
  margin-top: 24px;
  padding: 13px 14px;
  border: 0px solid
  var(--study-border-light);
  border-radius: 7px;
  background: #f9fbfb;
}

.generate-stage-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 9px;
}

.generate-stage-head > div {
  min-width: 0;
}

.generate-stage-head span {
  display: block;
  margin-bottom: 2px;
  color:
      var(--study-text-muted);
  font-size: 10px;
}

.generate-stage-head strong {
  display: block;
  overflow: hidden;
  color:
      var(--study-accent-text);
  font-size: 12px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.generate-stage-head em {
  flex-shrink: 0;
  color:
      var(--study-text-muted);
  font-family:
      var(--font-mono, monospace);
  font-size: 10px;
  font-style: normal;
}

.generate-progress-track {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: #e2eceb;
}

.generate-progress-fill {
  width: 100%;
  height: 100%;
  transform-origin: left center;
  border-radius: inherit;
  background:
      linear-gradient(
          90deg,
          #159a94,
          #5dbdb8
      );
  transition: transform 350ms ease;
}

.generate-step-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-top: 17px;
}

.generate-step-item {
  display: flex;
  align-items: center;
  gap: 9px;
  color:
      var(--study-text-faint);
  font-size: 11px;
  transition: color 180ms ease;
}

.generate-step-item.is-current {
  color:
      var(--study-accent-text);
  font-weight: 700;
}

.generate-step-item.is-complete {
  color:
      var(--study-text-secondary);
}

.generate-step-indicator {
  display: grid;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  place-items: center;
  border: 0px solid
  var(--study-border);
  border-radius: 50%;
  background: #ffffff;
  color:
      var(--study-text-faint);
  font-family:
      var(--font-mono, monospace);
  font-size: 9px;
}

.generate-step-indicator svg {
  width: 10px;
  height: 10px;
}

.generate-step-item.is-current
.generate-step-indicator {
  border-color:
      var(--study-accent);
  background:
      var(--study-accent-soft);
  color:
      var(--study-accent-text);
  box-shadow:
      0 0 0 3px
      var(--study-focus-ring);
}

.generate-step-item.is-complete
.generate-step-indicator {
  border-color:
      var(--study-accent);
  background:
      var(--study-accent);
  color: #ffffff;
}

.viewer-overlay,
.quiz-overlay {
  position: fixed;
  z-index: 9999;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 22px;
  background:
      rgba(37, 62, 65, 0.27);
  backdrop-filter: blur(4px);
}

.viewer-shell {
  display: grid;
  grid-template-rows:
    auto minmax(0, 1fr);
  width: min(1180px, 100%);
  max-height:
      calc(100vh - 44px);
  overflow: hidden;
  border-radius: 12px;
  background: #ffffff;
  box-shadow:
      0 24px 70px
      rgba(24, 55, 58, 0.18);
}

.viewer-nav,
.quiz-nav {
  display: flex;
  min-height: 52px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 9px 16px;
  background: #fafcfc;
}

.quiz-nav {
  border-bottom: 1px solid var(--study-border-light, rgba(200, 228, 227, 0.35));
}

.nav-back-button {
  display: inline-flex;
  min-height: 33px;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 0px solid
  var(--study-border);
  border-radius: 5px;
  background: #ffffff;
  color:
      var(--study-text-secondary);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.nav-back-button svg {
  width: 14px;
  height: 14px;
}

.nav-back-button:hover {
  border-color:
      var(--study-accent-border);
  background:
      var(--study-accent-soft);
  color:
      var(--study-accent-text);
}

.viewer-nav-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.viewer-nav-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color:
      var(--study-text-secondary);
  font-size: 11px;
  font-weight: 650;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2f997f;
}

.status-dot.failed {
  background: #c75f5f;
}

.viewer-close-button {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  padding: 0;
  border: 0px solid
  var(--study-border);
  border-radius: 5px;
  background: #ffffff;
  color:
      var(--study-text-muted);
  cursor: pointer;
}

.viewer-close-button:hover {
  background: #f1f5f4;
  color:
      var(--study-text-strong);
}

.viewer-close-button svg {
  width: 14px;
  height: 14px;
}

.viewer-state {
  display: flex;
  min-height: 420px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 40px 24px;
  color:
      var(--study-text-secondary);
  text-align: center;
}

.viewer-state h2 {
  margin: 5px 0 0;
  color:
      var(--study-text-strong);
  font-size: 16px;
}

.viewer-state p {
  max-width: 440px;
  margin: 0;
  font-size: 12px;
  line-height: 1.65;
}

.viewer-workspace {
  overflow-y: auto;
}

.viewer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 26px 30px 21px;
}

.viewer-title {
  min-width: 0;
}

.viewer-title h1 {
  margin: 5px 0 6px;
  color:
      var(--study-text-strong);
  font-size: 21px;
  font-weight: 760;
}

.viewer-title p {
  max-width: 760px;
  margin: 0;
  color:
      var(--study-text-secondary);
  font-size: 12px;
  line-height: 1.65;
}

.viewer-meta {
  display: flex;
  flex-shrink: 0;
  gap: 6px;
}

.viewer-meta span {
  display: inline-flex;
  min-height: 24px;
  align-items: center;
  padding: 0 7px;
  border: 0px solid
  var(--study-border-light);
  border-radius: 5px;
  background: #f7f9f9;
  color:
      var(--study-text-muted);
  font-family:
      var(--font-mono, monospace);
  font-size: 9px;
}

.viewer-body {
  padding: 26px 30px 38px;
}

.quiz-shell {
  display: grid;
  grid-template-rows:
    auto minmax(0, 1fr) auto;
  width: min(760px, 100%);
  max-height:
      calc(100vh - 44px);
  overflow: hidden;
  border-radius: 12px;
  background: #ffffff;
  box-shadow:
      0 24px 70px
      rgba(24, 55, 58, 0.18);
}

.quiz-nav-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.quiz-nav-left strong {
  color:
      var(--study-text-strong);
  font-size: 12px;
  font-weight: 700;
}

.quiz-body {
  overflow-y: auto;
  padding: 23px 27px 28px;
}

.quiz-banner {
  margin-bottom: 22px;
}

.quiz-banner h2 {
  margin: 0 0 5px;
  color:
      var(--study-text-strong);
  font-size: 17px;
  font-weight: 750;
}

.quiz-banner p {
  margin: 0;
  color:
      var(--study-text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.quiz-question-list {
  display: flex;
  flex-direction: column;
  gap: 36px;
}

.quiz-question-node {
  padding-bottom: 0;
  border-bottom: 0;
}

.quiz-question-node:last-child {
  border-bottom: 0;
}

.quiz-question-title {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  margin: 0 0 16px;
  color:
      var(--study-text-strong);
  font-size: 16px;
  font-weight: 700;
  line-height: 1.6;
}

.quiz-question-number {
  display: inline-block;
  flex-shrink: 0;
  margin-top: 2px;
  color:
      var(--study-accent-text);
  font-family:
      var(--font-mono, monospace);
  font-size: 14px;
  font-weight: 800;
}

.quiz-choices-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-left: 26px;
}

.quiz-choice-row {
  display: flex;
  min-height: 48px;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--study-border, rgba(200, 228, 227, 0.44));
  background: #ffffff;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.quiz-choice-row:hover {
  background: var(--study-accent-softer, rgba(70, 184, 180, 0.04));
  border-color: var(--study-accent-border, rgba(70, 184, 180, 0.5));
}

.quiz-choice-row:active {
  transform: scale(0.99);
}

.quiz-choice-row.selected {
  background: var(--study-accent-soft, rgba(70, 184, 180, 0.1));
  border-color: var(--study-accent, #46b8b4);
  box-shadow: 0 2px 8px rgba(70, 184, 180, 0.05);
}

.quiz-choice-row.correct {
  background: #e0f5ec;
  border-color: #a3e2c9;
}

.quiz-choice-row.incorrect {
  background: #fef2f2;
  border-color: #fca5a5;
}

.quiz-choice-row input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}

.quiz-choice-box {
  display: inline-flex;
  width: 24px;
  height: 24px;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: 50%;
  border: 1px solid var(--study-border, rgba(200, 228, 227, 0.6));
  background: #fafcfc;
  color: var(--study-text-muted, #6c858a);
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  font-weight: 800;
  transition: all 0.2s ease;
}

.quiz-choice-row:hover .quiz-choice-box {
  border-color: var(--study-accent-border, rgba(70, 184, 180, 0.5));
  background: #ffffff;
}

.quiz-choice-row.selected .quiz-choice-box {
  border-color: var(--study-accent, #46b8b4);
  background: var(--study-accent, #46b8b4);
  color: #ffffff;
}

.quiz-choice-row.selected .quiz-choice-content {
  color: var(--study-accent-text);
  font-weight: 600;
}

.quiz-choice-row.correct .quiz-choice-box {
  background: #2d7a5c;
  border-color: #2d7a5c;
  color: #ffffff;
}

.quiz-choice-row.correct .quiz-choice-content {
  color: #2d7a5c;
  font-weight: 600;
}

.quiz-choice-row.incorrect .quiz-choice-box {
  background: #a04040;
  border-color: #a04040;
  color: #ffffff;
}

.quiz-choice-row.incorrect .quiz-choice-content {
  color: #a04040;
  font-weight: 600;
}

.quiz-choice-content {
  color: var(--study-text);
  font-size: 12px;
  line-height: 1.55;
}

.quiz-analysis-box {
  margin: 16px 0 0 26px;
  padding: 14px 18px;
  border-radius: 8px;
  border: 1px solid rgba(70, 184, 180, 0.15);
  background: #f4f8f7;
}

.quiz-analysis-meta {
  color:
      var(--study-text-secondary);
  font-size: 11px;
}

.quiz-analysis-meta strong {
  color: #258269;
  font-family:
      var(--font-mono, monospace);
}

.cognitive-note {
  margin: 6px 0 0;
  color:
      var(--study-text-secondary);
  font-size: 11px;
  line-height: 1.65;
}

.quiz-submit-bar {
  display: flex;
  min-height: 62px;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 10px 20px;
  border-top: 1px solid
  var(--study-border-light);
  background: #fafcfc;
}

.quiz-submit-bar > span {
  color:
      var(--study-text-muted);
  font-size: 11px;
}

.quiz-result-report {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 24px;
  padding: 20px;
  border: 1px solid var(--study-accent-border, rgba(70, 184, 180, 0.25));
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(70, 184, 180, 0.08), rgba(255, 255, 255, 0.95));
  box-shadow: 0 4px 20px rgba(31, 76, 80, 0.04);
}

.report-top {
  display: flex;
  align-items: flex-start;
  gap: 22px;
}

.report-score {
  flex-shrink: 0;
}

.report-score strong {
  display: block;
  margin-top: 3px;
  color:
      var(--study-accent-text);
  font-size: 30px;
  font-weight: 800;
  line-height: 1;
}

.report-score small {
  color:
      var(--study-text-muted);
  font-size: 12px;
  font-weight: 500;
}

.report-text h4 {
  margin: 0 0 4px;
  color:
      var(--study-text-strong);
  font-size: 13px;
  font-weight: 700;
}

.report-text p {
  margin: 0;
  color:
      var(--study-text-secondary);
  font-size: 11px;
  line-height: 1.6;
}

.report-weak-zone label {
  display: block;
  margin-bottom: 7px;
  color: #a15252;
  font-size: 10px;
  font-weight: 700;
}

.report-weak-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.weak-tag {
  display: inline-flex;
  min-height: 25px;
  align-items: center;
  padding: 0 8px;
  border: 0px solid #e4baba;
  border-radius: 5px;
  background: #fceeee;
  color: #a65353;
  font-size: 10px;
  font-weight: 650;
}

.viewer-fade-enter-active,
.viewer-fade-leave-active,
.quiz-fade-enter-active,
.quiz-fade-leave-active {
  transition: opacity 180ms ease;
}

.viewer-fade-enter-active
.viewer-shell,
.viewer-fade-leave-active
.viewer-shell,
.quiz-fade-enter-active
.quiz-shell,
.quiz-fade-leave-active
.quiz-shell {
  transition:
      transform 180ms ease;
}

.viewer-fade-enter-from,
.viewer-fade-leave-to,
.quiz-fade-enter-from,
.quiz-fade-leave-to {
  opacity: 0;
}

.viewer-fade-enter-from
.viewer-shell,
.viewer-fade-leave-to
.viewer-shell,
.quiz-fade-enter-from
.quiz-shell,
.quiz-fade-leave-to
.quiz-shell {
  transform:
      translateY(6px) scale(0.985);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1380px) {
  .study-workspace {
    grid-template-columns:
      190px minmax(560px, 1fr) 270px;
  }
}

@media (max-width: 1180px) {
  .study-workspace {
    grid-template-columns:
      minmax(0, 1fr) 280px;
  }

  .toc-panel {
    display: none;
  }
}

@media (max-width: 900px) {
  .study-workspace {
    grid-template-columns: 1fr;
  }

  .resource-panel {
    position: static;
    padding: 18px 0 0;
    border-top: 1px solid
    var(--study-border-light);
    border-left: 0;
  }

  .resource-list {
    display: grid;
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }

  .tutorial-head {
    flex-direction: column;
  }

  .tutorial-tabs {
    justify-content: flex-start;
  }
}

@media (max-width: 680px) {
  .node-study-page {
    padding: 11px 12px 30px;
  }

  .node-toolbar {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }

  .toolbar-left {
    width: 100%;
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
  }

  .back-button {
    width: 100%;
  }

  .toolbar-right {
    align-self: flex-start;
  }

  .tutorial-head {
    padding: 20px 18px;
  }

  .tutorial-head h2 {
    font-size: 20px;
  }

  .tutorial-reader {
    padding: 21px 18px;
  }

  .tutorial-native-quiz {
    padding:
        0 18px 22px;
  }

  .quiz-native-preload {
    align-items: stretch;
    flex-direction: column;
  }

  .quiz-trigger-button {
    width: 100%;
  }

  .resource-list {
    grid-template-columns: 1fr;
  }

  .generate-panel {
    padding: 26px 18px;
  }

  .viewer-overlay,
  .quiz-overlay {
    padding: 10px;
  }

  .viewer-shell,
  .quiz-shell {
    max-height:
        calc(100vh - 20px);
  }

  .viewer-head {
    flex-direction: column;
    padding: 20px 18px;
  }

  .viewer-body {
    padding: 20px 18px 30px;
  }

  .viewer-meta {
    flex-wrap: wrap;
  }

  .quiz-body {
    padding: 20px 16px 24px;
  }

  .quiz-nav-left {
    align-items: flex-start;
    flex-direction: column;
    gap: 2px;
  }

  .quiz-choices-stack {
    padding-left: 0;
  }

  .quiz-analysis-box {
    margin-left: 0;
  }

  .quiz-submit-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .quiz-submit-bar
  .primary-action-button {
    width: 100%;
  }

  .report-top {
    flex-direction: column;
    gap: 12px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .node-study-page *,
  .node-study-page *::before,
  .node-study-page *::after {
    animation-duration:
        0.01ms !important;
    animation-iteration-count:
        1 !important;
    scroll-behavior:
        auto !important;
    transition-duration:
        0.01ms !important;
  }
}
</style>
