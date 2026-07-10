<template>
  <main class="node-study-page">
    <!-- 全局加载与异常卡片状态 -->
    <section v-if="loading && !isGeneratingTutorial" class="state-card">
      <div class="state-spinner"></div>
      <p>正在准备节点学习空间...</p>
    </section>

    <section v-else-if="!workspace && !isGeneratingTutorial" class="state-card">
      <h2>节点不存在或已经失效</h2>
      <p>请返回路径总览重新选择学习节点。</p>
      <button class="btn btn-primary" @click="router.push('/path-planner')">返回路径总览</button>
    </section>

    <!-- AI 推进智能体调用大屏 -->
    <section v-else-if="isGeneratingTutorial" class="generating-view">
      <div class="generate-panel">
        <div class="generate-loader">
          <span></span>
          <span></span>
          <span></span>
        </div>

        <div class="generate-copy">
          <p>AI Tutorial Agent</p>
          <h1>正在生成节点主教程</h1>
          <span>后端正在调用学习推进智能体，结合画像、路径目标和当前节点生成定制讲义。</span>
        </div>

        <transition-group name="log" tag="div" class="generate-log">
          <div v-for="(msg, index) in generatingLogs" :key="`${msg}-${index}`" class="log-item">
            <i></i>
            <span>{{ msg }}</span>
          </div>
        </transition-group>
      </div>
    </section>

    <!-- 主工作台区 -->
    <template v-else-if="workspace">
      <!-- 扁平化极简顶部通栏：修复了文字拆行与图标重叠的问题 -->
      <nav class="node-toolbar">
        <div class="toolbar-left">
          <button class="back-button" type="button" @click="router.push(`/path-planner/overview/${workspace.path.id}`)">
            <svg class="back-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
            返回路径总览
          </button>
          <span class="toolbar-divider">/</span>
          <div class="toolbar-title">
            <span class="agent-eyebrow">Knowledge Node</span>
            <h1>{{ workspace.node.title }}</h1>
          </div>
        </div>

        <div class="toolbar-right">
          <span class="status-pill" :class="workspace.node.status">
            <i></i>
            {{ statusText(workspace.node.status) }}
          </span>
        </div>
      </nav>

      <!-- 核心三栏式空间布局 -->
      <section class="study-workspace">

        <!-- LEFT: 教程目录导航 -->
        <aside class="toc-panel">
          <div class="toc-card">
            <div class="side-head">
              <span class="eyebrow">Contents</span>
              <strong>教程目录</strong>
            </div>

            <div v-if="tutorialToc.length" class="toc-list">
              <button
                  v-for="item in tutorialToc"
                  :key="item.id"
                  type="button"
                  :class="['toc-item', `level-${item.level}`, { active: activeHeadingId === item.id }]"
                  @click="scrollToHeading(item.id)"
              >
                {{ item.title }}
              </button>
            </div>

            <div v-else class="toc-empty">
              <p>暂未识别到标题目录</p>
              <span>AI 讲义会自动加载于视窗中央</span>
            </div>
          </div>
        </aside>

        <!-- CENTER: 主教程阅读区与原生的章节诊断测试 -->
        <article class="tutorial-main">
          <!-- 教程正文头部 -->
          <header class="tutorial-head">
            <div>
              <span class="section-kicker">AI Custom Tutorial</span>
              <h2>{{ displayedTutorial?.title || workspace.node.title }}</h2>
              <p>请沉浸式完成当前核心讲义。学完后可在文档流末尾触发阶段性通关诊断测试。</p>
            </div>

            <!-- 主教程多版本卡片式标签切换 -->
            <div v-if="workspace.tutorials.length > 1" class="tutorial-tabs">
              <button
                  v-for="item in workspace.tutorials"
                  :key="item.id"
                  type="button"
                  :class="['btn-pill', { active: item.id === displayedTutorial?.id, current: item.id === (workspace.current_tutorial?.id || null) }]"
                  @click="selectedTutorialId = item.id"
              >
                {{ tutorialTypeLabel(item.tutorial_type) }}
                <em>v{{ item.version_no }}</em>
              </button>
            </div>
          </header>

          <!-- Markdown 文档实体阅读区 -->
          <section class="tutorial-reader">
            <div v-if="displayedTutorial" ref="contentEl" class="markdown-shell markdown-body">
              <Markdown :result-data="{ content: tutorialMarkdown }" />
            </div>

            <div v-else class="tutorial-empty">
              <h3>暂无核心教程</h3>
              <p>系统将自动调用学习推进智能体为您构建主讲义。</p>
            </div>
          </section>

          <!-- 💡 课后诊断评估：弹窗式主动触发 -->
          <section class="tutorial-native-quiz">
            <div class="divider"></div>

            <header class="quiz-native-head">
              <h2>6. 知识掌握度诊断评估</h2>
              <p>核心讲义学习完毕。点击下方触发诊断，智能体将为您构建 5 道多维考频映射题，精准捕获您的盲区隐患。</p>
            </header>

            <!-- 主动触发入口 -->
            <div class="quiz-native-preload">
              <div class="diagnostic-flow-text">
                <span class="dim-label">评估覆盖维度：</span>
                <span class="dim-tag c-tutor">概念理解</span>·
                <span class="dim-tag c-eval">原理推导</span>·
                <span class="dim-tag c-resource">工程映射</span>·
                <span class="dim-tag c-path">边界防御</span>·
                <span class="dim-tag c-rose">易错陷阱</span>
              </div>

              <div class="quiz-action-trigger-zone">
                <button
                    class="btn btn-primary"
                    type="button"
                    :disabled="quizLoading"
                    @click="loadQuiz"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width:1.1em;height:1.1em;margin-right:6px;">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                  </svg>
                  {{ quizLoading ? '智能体正在加密组织诊断维度...' : (quizRound ? '查看诊断评测' : '激活本节课后诊断评测') }}
                </button>
              </div>
            </div>
          </section>
        </article>

        <!-- RIGHT: 多智能体高级微光线框辅助工具箱 -->
        <aside class="resource-panel">
          <section class="resource-workbench-card">
            <div class="side-head workbench-head">
              <span class="eyebrow">Multi-Agent System</span>
              <strong>认知衍生工具箱</strong>
            </div>

            <p class="push-desc">
              点击下方工具即可调遣专属垂直智能体对主讲义内容进行深层认知重组。
            </p>

            <div class="workbench-section">
              <div class="resource-list">
                <article
                    v-for="item in resourcePushItems"
                    :key="item.type"
                    :class="['resource-item', item.type, { generated: Boolean(item.resource), active: resourceLoading === item.type }]"
                >
                  <div class="resource-icon-wrapper">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path :d="item.icon" />
                    </svg>
                  </div>

                  <div class="resource-copy">
                    <strong>{{ item.title }}</strong>
                    <span>{{ item.desc }}</span>
                    <em v-if="item.resource" class="status-lbl" :class="{ fail: item.resource.status === 'failed' }">
                      {{ item.resource.status === 'failed' ? '构建失败' : '随时就绪' }}
                    </em>
                    <em v-else class="status-lbl wait">可按需唤醒</em>
                  </div>

                  <button
                      type="button"
                      class="btn-ghost btn-action-trigger"
                      :disabled="resourceLoading === item.type"
                      @click="item.resource ? openResourceDetail(item.resource.id) : createResource(item.type)"
                  >
                    {{ resourceLoading === item.type ? '生成中' : item.resource ? '查看' : '唤醒' }}
                  </button>
                </article>
              </div>
            </div>
          </section>
        </aside>
      </section>
    </template>

    <!-- ~ 全局轻量化内嵌资源查看器弹窗 ~ -->
    <Teleport to="body">
      <transition name="viewer-fade">
        <div v-if="showViewer" class="viewer-overlay" @click.self="closeViewer">
          <section class="viewer-shell">
            <nav class="viewer-nav">
              <div class="viewer-nav-left">
                <button class="nav-back-btn" type="button" @click="closeViewer">
                  <svg viewBox="0 0 24 24" aria-hidden="true" style="width:16px;height:16px">
                    <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.42-1.41L7.83 13H20v-2Z" />
                  </svg>
                  返回主工作空间
                </button>
              </div>
              <div v-if="viewerResource" class="viewer-nav-status">
                <span :class="['status-dot', viewerResource.status || 'completed']"></span>
                {{ viewerResource.status === 'failed' ? '智能体中断' : '资源就绪' }}
              </div>
            </nav>

            <section v-if="viewerLoading" class="viewer-state">
              <div class="state-spinner"></div>
              <p>认知视图渲染中...</p>
            </section>

            <section v-else-if="viewerResource && viewerResource.status === 'failed'" class="viewer-state">
              <h2>资源视图生成中断</h2>
              <p>{{ viewerResource.error_message || '智能体处理出现临时阻断，请尝试重新调度唤醒。' }}</p>
            </section>

            <template v-else-if="viewerResource">
              <section class="viewer-workspace">
                <article class="viewer-content">
                  <header class="viewer-head">
                    <div class="viewer-title">
                      <span class="section-kicker">{{ resourceTypeLabel(viewerResource.resource_type) }}</span>
                      <h1>{{ viewerResource.title }}</h1>
                      <p v-if="viewerResource.summary">{{ viewerResource.summary }}</p>
                    </div>
                    <div class="viewer-meta">
                      <span>REV v{{ viewerResource.version_no }}</span>
                      <span>{{ formatTime(viewerResource.created_at) }}</span>
                    </div>
                  </header>

                  <div class="viewer-body">
                    <MindMap v-if="viewerResource.resource_type === 'mindmap'" :result-data="viewerContent" />
                    <Markdown v-else-if="viewerResource.resource_type === 'code'" :result-data="viewerContent" />
                    <Slides v-else-if="viewerResource.resource_type === 'ppt'" :resource="viewerResource" />
                    <Reading v-else-if="viewerResource.resource_type === 'reading'" :result-data="viewerContent" />
                    <Markdown v-else :result-data="viewerContent" />
                  </div>
                </article>
              </section>
            </template>
          </section>
        </div>
      </transition>
    </Teleport>

    <!-- ~ 题目弹窗：诊断评估答题流 ~ -->
    <Teleport to="body">
      <transition name="quiz-fade">
        <div v-if="showQuizOverlay && quizRound" class="quiz-overlay" @click.self="closeQuiz">
          <section class="quiz-shell">
            <nav class="quiz-nav">
              <div class="quiz-nav-left">
                <span class="agent-eyebrow">Diagnostic Assessment</span>
                <strong>第 {{ quizRound.round_no }} 轮评测</strong>
              </div>
              <button class="nav-back-btn" type="button" @click="closeQuiz">
                <svg viewBox="0 0 24 24" aria-hidden="true" style="width:16px;height:16px">
                  <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.42-1.41L7.83 13H20v-2Z" />
                </svg>
                返回教程
              </button>
            </nav>

            <section class="quiz-body">
              <div class="quiz-banner">
                <p>请完成以下单项选择以提交多智能体画像感知：</p>
              </div>

              <div class="quiz-question-list">
                <article v-for="(question, index) in quizRound.questions" :key="question.id" class="quiz-question-node">
                  <h4 class="quiz-question-title">
                    <span class="quiz-q-num">{{ index + 1 }}.</span>
                    {{ question.question }}
                  </h4>

                  <div class="quiz-choices-stack">
                    <label
                        v-for="choice in choiceEntries(question.choice)"
                        :key="choice[0]"
                        :class="['quiz-choice-row', { selected: answers[question.id] === choice[0] }]"
                    >
                      <input
                          v-model="answers[question.id]"
                          type="radio"
                          :name="`q-${question.id}`"
                          :value="choice[0]"
                          :disabled="isQuizSubmitted"
                      />
                      <span class="quiz-choice-box">{{ choice[0] }}</span>
                      <span class="quiz-choice-content">{{ choice[1] }}</span>
                    </label>
                  </div>

                  <!-- 错题溯源深度解析 -->
                  <div v-if="isQuizSubmitted" class="quiz-analysis-box">
                    <div class="quiz-analysis-meta">
                      <span>正确基准答案: <strong>{{ question.answer }}</strong></span>
                    </div>
                    <p v-if="question.analysis" class="cognitive-note">{{ question.analysis }}</p>
                  </div>
                </article>
              </div>

              <!-- 答题提交控制 -->
              <div class="quiz-submit-bar">
                <button
                    v-if="!isQuizSubmitted"
                    class="btn btn-primary"
                    style="height: 40px; padding: 0 var(--space-6);"
                    type="button"
                    :disabled="submitLoading"
                    @click="submitQuiz"
                >
                  {{ submitLoading ? '多维诊断认知聚合中...' : '提交测试并获取诊断结论' }}
                </button>
              </div>

              <!-- 测验评估反馈成绩单 -->
              <div v-if="quizResult" class="quiz-result-report">
                <div class="report-top">
                  <div class="report-score">
                    <span class="agent-eyebrow">Diagnostic Score</span>
                    <strong>{{ quizResult.score }} <small>/ 5</small></strong>
                  </div>
                  <div class="report-text">
                    <h4>EduAgent 认知诊断结论</h4>
                    <p>{{ resultText(quizResult.outcome) }}</p>
                  </div>
                </div>

                <!-- 薄弱点反馈 -->
                <div v-if="quizResult.weak_knowledge_points?.length" class="report-weak-zone">
                  <label>知识隐患点感知</label>
                  <div class="report-weak-tags">
                    <span v-for="point in quizResult.weak_knowledge_points" :key="point" class="tag-pill">
                      {{ point }}
                    </span>
                  </div>
                </div>

                <button
                    v-if="quizResult.next_node_id"
                    class="btn btn-secondary"
                    style="width: 100%; height: 40px;"
                    type="button"
                    @click="goToNextNode(quizResult.next_node_id)"
                >
                  推进至下一个推荐知识节点
                  <svg viewBox="0 0 24 24" style="width:1.1em;height:1.1em;margin-left:4px;"><path d="M5 13h11.86l-5.43 5.43 1.42 1.42L21.14 12l-8.29-8.29-1.42 1.42L16.86 11H5v2z"/></svg>
                </button>
              </div>
            </section>
          </section>
        </div>
      </transition>
    </Teleport>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import Markdown from '@/shared/content/renderers/Markdown.vue'
import MindMap from '@/shared/content/renderers/MindMap.vue'
import Reading from '@/shared/content/renderers/Reading.vue'
import Slides from '@/shared/content/renderers/Slides.vue'

import {
  generateNodeResource,
  generateNodeQuestions,
  getNodeQuestions,
  generateTutorial,
  getLearningNodeWorkspace,
  startLearning,
  submitNodeQuiz,
} from '@/features/learning-path/api/path'
import { recordPathLearningEvent } from '@/features/evaluation/api/evaluation'
import type {
  LearningPathResource,
  LearningPathTutorial,
  LearningPathWorkspace,
  PathQuizRound,
  PathQuizSubmitResponse,
} from '@/features/learning-path/model/path'
import { getErrorMessage } from '@/shared/api/http'
import { startTracking, stopTracking } from '@/features/evaluation/model/useLearningTracker'

type TocItem = {
  id: string
  title: string
  level: number
}

type ResourceKind = 'mindmap' | 'code' | 'ppt' | 'reading' | 'cartoon'

type ResourcePushItem = {
  type: ResourceKind
  title: string
  desc: string
  icon: string
  resource: LearningPathWorkspace['resources'][number] | null
}

const route = useRoute()
const router = useRouter()

// 页面全局加载状态与生成/提交加载标识
const loading = ref(false)
const quizLoading = ref(false)
const submitLoading = ref(false)
const resourceLoading = ref<ResourceKind | ''>('')

// 核心数据：节点工作空间、测验轮次、判分结果、用户答案
const workspace = ref<LearningPathWorkspace | null>(null)
const quizRound = ref<PathQuizRound | null>(null)
const quizResult = ref<PathQuizSubmitResponse | null>(null)
const answers = ref<Record<number, string>>({})
const hasStartedTracking = ref(false)
const showQuizOverlay = ref(false)

// 教程与目录导航状态
const selectedTutorialId = ref<number | null>(null)
const isGeneratingTutorial = ref(false)
const generatingLogs = ref<string[]>([])
const contentEl = ref<HTMLElement | null>(null)
const activeHeadingId = ref('')
const isQuizSubmitted = ref(false)

// 资源查看器弹窗状态
const showViewer = ref(false)
const viewerLoading = ref(false)
const viewerResource = ref<LearningPathResource | null>(null)
const viewerContent = ref<string>('')

// 打开辅助资源查看器
function openViewer(resource: LearningPathResource) {
  viewerResource.value = resource
  viewerContent.value = resource.content_text || (resource.content_json ? JSON.stringify(resource.content_json, null, 2) : '')
  showViewer.value = true
}

// 关闭资源查看器（延迟清空数据以保留过渡动画）
function closeViewer() {
  showViewer.value = false
  setTimeout(() => {
    viewerResource.value = null
    viewerContent.value = ''
  }, 200)
}

// 关闭测验弹窗，保留题目数据以便重新打开
function closeQuiz() {
  showQuizOverlay.value = false
}

function resourceTypeLabel(type: string) {
  const map: Record<string, string> = {
    mindmap: '思维导图',
    code: '代码实操',
    ppt: 'PPT 课件',
    reading: '拓展阅读',
    cartoon: '动画讲解',
    quiz: '节点测验',
  }
  return map[type] || type
}

function tutorialTypeLabel(value?: string | null) {
  if (value === 'remediation') return '补救教程'
  if (value === 'reinforced') return '强化教程'
  return '主讲义'
}

function formatTime(iso: string | undefined | null) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// 从路由参数获取当前节点 ID
const nodeId = computed(() => Number(route.params.nodeId || 0))

// 当前展示的教程（按用户选择的版本或最新的 current_tutorial）
const displayedTutorial = computed<LearningPathTutorial | null>(() => {
  if (!workspace.value) return null
  if (selectedTutorialId.value) {
    return workspace.value.tutorials.find((item) => item.id === selectedTutorialId.value)
        || workspace.value.current_tutorial
  }
  return workspace.value.current_tutorial
})

// 预处理后的 Markdown 教程内容
const tutorialMarkdown = computed(() => preprocessTutorialMarkdown(displayedTutorial.value?.content_markdown || ''))

/**
 * 预处理教程 Markdown 内容：
 * 1. 剥离 YAML frontmatter（--- 包裹的块）— 兼容旧教程
 * 2. 美化 Markdown 元数据标题块 — 将 blockquote 中的摘要/知识点/类型转为可读结构
 */
function preprocessTutorialMarkdown(raw: string): string {
  if (!raw) return ''
  let text = raw.trim()

  // 1. 剥离 YAML frontmatter（兼容旧教程格式）
  if (text.startsWith('---')) {
    const endMatch = text.indexOf('\n---', 3)
    if (endMatch !== -1) {
      text = text.slice(endMatch + 4).trim()
    }
  }

  // 2. 解析 Markdown 元数据标题块：
  //    # 标题
  //    > **摘要**：...
  //    > **知识点**：...
  //    > **类型**：...
  //    将其转换为更美观的 HTML 渲染友好格式
  const metaBlockRegex = /^#\s+(.+?)\s*\n\n((?:>.*\n?)+)/
  const metaMatch = metaBlockRegex.exec(text)
  if (metaMatch) {
    const title = metaMatch[1]!
    const blockquoteLines = metaMatch[2]!

    let summary = ''
    let knowledgePoints = ''
    let tutorialType = ''

    const bqText = blockquoteLines
      .split('\n')
      .map((line: string) => line.replace(/^>\s*/, '').trim())
      .filter(Boolean)
      .join(' ')

    const summaryMatch = bqText.match(/\*\*摘要\*\*[：:]\s*(.+?)(?=\s*\*\*|$)/)
    if (summaryMatch) summary = summaryMatch[1]!.trim()

    const kpMatch = bqText.match(/\*\*知识点\*\*[：:]\s*(.+?)(?=\s*\*\*|$)/)
    if (kpMatch) knowledgePoints = kpMatch[1]!.trim()

    const typeMatch = bqText.match(/\*\*类型\*\*[：:]\s*(\w+)/)
    if (typeMatch) tutorialType = typeMatch[1]!.trim()

    // 替换元数据块为美观的渲染格式
    const typeLabel: Record<string, string> = {
      primary: '首次学习',
      remediation: '薄弱点巩固',
      reinforced: '强化补漏',
    }

    const renderedMeta = [
      `# ${title}`,
      '',
      `<div class="tutorial-meta-banner">`,
      `  <div class="meta-summary">${summary}</div>`,
      knowledgePoints ? `  <div class="meta-kp"><strong>知识点：</strong>${knowledgePoints}</div>` : '',
      tutorialType ? `  <div class="meta-type"><span class="type-badge type-${tutorialType}">${typeLabel[tutorialType] || tutorialType}</span></div>` : '',
      `</div>`,
      '',
    ].filter(Boolean).join('\n')

    text = renderedMeta + text.slice(metaMatch.index! + metaMatch[0]!.length)
  }

  return text
}

// 从 Markdown 正文中解析 h2/h3 标题，生成教程目录导航
const tutorialToc = computed<TocItem[]>(() => {
  const markdown = tutorialMarkdown.value
  if (!markdown) return []

  const result: TocItem[] = []
  const used = new Map<string, number>()
  const headingRegex = /^(#{2,3})\s+(.+)$/gm

  let match: RegExpExecArray | null

  while ((match = headingRegex.exec(markdown)) !== null) {
    const rawLevel = match[1]
    const rawTitle = match[2]
    if (!rawLevel || !rawTitle) continue

    const level = rawLevel.length
    const title = rawTitle.replace(/[#*_`>]/g, '').trim()
    if (!title) continue

    const base = slugify(title)
    const count = used.get(base) || 0
    used.set(base, count + 1)

    result.push({
      id: count ? `${base}-${count + 1}` : base,
      title,
      level,
    })
  }
  return result.slice(0, 18)
})

const resourcePushItems = computed<ResourcePushItem[]>(() => [
  {
    type: 'mindmap',
    title: '思维导图',
    desc: '抽取讲义核心概念层级图。',
    icon: 'M11 3h2v4h-2V3Zm-7 8h6v2H4v-2Zm10 0h6v2h-6v-2ZM5 17h5v2H5v-2Zm9 0h5v2h-5v-2ZM11 8h2v3h-2V8Zm0 5h2v3h-2v-3Z',
    resource: latestResourceByType('mindmap'),
  },
  {
    type: 'code',
    title: '代码实操',
    desc: '转换成工程案例与模拟实验。',
    icon: 'm8.7 16.3-4.3-4.3 4.3-4.3L7.3 6.3 1.6 12l5.7 5.7 1.4-1.4Zm6.6 0 4.3-4.3-4.3-4.3 1.4-1.4 5.7 5.7-5.7 5.7-1.4-1.4ZM10.8 20 13.4 4h2l-2.6 16h-2Z',
    resource: latestResourceByType('code'),
  },
  {
    type: 'ppt',
    title: 'PPT 课件',
    desc: '提炼供展示复习的学术幻灯。',
    icon: 'M4 3h16v18H4V3Zm2 2v14h12V5H6Zm2 3h8v2H8V8Zm0 4h8v2H8v-2Zm0 4h5v2H8v-2Z',
    resource: latestResourceByType('ppt'),
  },
  {
    type: 'reading',
    title: '拓展阅读',
    desc: '聚合同步资料与全球前沿文献。',
    icon: 'M12 6.5A5.5 5.5 0 0 0 6.5 1H3v18h4.5A4.5 4.5 0 0 1 12 23a4.5 4.5 0 0 1 4.5-4H21V1h-3.5A5.5 5.5 0 0 0 12 6.5ZM5 3h1.5A3.5 3.5 0 0 1 10 6.5v11.2A6.5 6.5 0 0 0 7.5 17H5V3Zm14 14h-2.5a6.5 6.5 0 0 0-2.5.7V6.5A3.5 3.5 0 0 1 17.5 3H19v14Z',
    resource: latestResourceByType('reading'),
  },
  {
    type: 'cartoon',
    title: '动画讲解',
    desc: '智能配音的动态演进原理解释。',
    icon: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z',
    resource: latestResourceByType('cartoon'),
  },
])

// 根据资源类型获取最新版本的辅助资源
function latestResourceByType(type: string) {
  if (!workspace.value) return null
  const matched = workspace.value.resources
      .filter((item) => item.resource_type === type)
      .sort((a, b) => b.version_no - a.version_no)
  return matched[0] || null
}

function slugify(value: string) {
  return value
          .toLowerCase()
          .replace(/[^\w\u4e00-\u9fa5]+/g, '-')
          .replace(/^-+|-+$/g, '')
      || `heading-${Math.random().toString(36).slice(2, 8)}`
}

// 同步目录锚点：为 Markdown 中的 h2/h3 元素注入 id，支持滚动定位
async function syncHeadingAnchors() {
  await nextTick()
  window.setTimeout(() => {
    const root = contentEl.value
    if (!root) return
    const headings = Array.from(root.querySelectorAll('h2, h3')) as HTMLElement[]
    const toc = tutorialToc.value

    headings.forEach((heading, index) => {
      const item = toc[index]
      if (!item) return
      heading.id = item.id
      heading.classList.add('tutorial-anchor-heading')
    })
  }, 80)
}

// 点击目录项时平滑滚动到对应标题

function scrollToHeading(id: string) {
  activeHeadingId.value = id
  const root = contentEl.value
  const target = root?.querySelector(`#${CSS.escape(id)}`) as HTMLElement | null
  if (target) {
    target.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// 加载节点学习空间：获取工作区数据，无教程则自动生成
async function loadWorkspace() {
  if (!nodeId.value) return
  loading.value = true
  try {
    const res = await getLearningNodeWorkspace(nodeId.value)
    workspace.value = res.data.data

    if (workspace.value && !workspace.value.current_tutorial) {
      // 教程不存在时调用生成接口（后端幂等：已有教程则直接返回，不会重复生成）
      await generatePrimaryTutorial()
    } else if (workspace.value?.current_tutorial) {
      selectedTutorialId.value = workspace.value.current_tutorial.id
    }

    await startLearningTracking()
    await syncHeadingAnchors()
  } catch (error) {
    toast.error(getErrorMessage(error, '加载节点学习空间失败'))
  } finally {
    loading.value = false
    isGeneratingTutorial.value = false
  }
}

// 调用后端生成主教程（首次生成），含轮播日志动画提示用户等待

async function generatePrimaryTutorial() {
  isGeneratingTutorial.value = true
  loading.value = false
  generatingLogs.value = ['正在呼叫后端多智能体系统...']

  const logs = [
    '正在连接 LangGraph 学习推进智能体...',
    '正在读取当前路径目标与节点前置依赖...',
    '正在结合学习画像裁剪讲解深度...',
    '正在组织教程目录、例子和易错点...',
    '正在写入主教程并刷新学习空间...',
  ]

  let index = 0
  const interval = window.setInterval(() => {
    if (index < logs.length) {
      const log = logs[index]
      if (log) generatingLogs.value.push(log)
      if (generatingLogs.value.length > 5) generatingLogs.value.shift()
      index += 1
    } else {
      window.clearInterval(interval)
    }
  }, 1600)

  try {
    await startLearning(nodeId.value)
    const tutorialRes = await generateTutorial(nodeId.value)
    workspace.value = tutorialRes.data.data

    if (workspace.value?.current_tutorial) {
      selectedTutorialId.value = workspace.value.current_tutorial.id
      // 💡 恢复主动触发心智：移除此处原有自动调用 loadQuiz() 的逻辑
    }
  } finally {
    window.clearInterval(interval)
    isGeneratingTutorial.value = false
  }
}

// 开始学习行为追踪：记录进入节点的时间与上下文
async function startLearningTracking() {
  if (!workspace.value || hasStartedTracking.value) return
  hasStartedTracking.value = true

  startTracking({
    sourcePage: 'path_node',
    pathId: workspace.value.path.id,
    pathNodeId: workspace.value.node.id,
    nodeId: workspace.value.node.node_id,
    course: workspace.value.path.title,
    topic: workspace.value.node.title,
  })

  await recordPathLearningEvent(workspace.value.path.id, {
    module: 'path',
    event_type: 'resource_viewed',
    course: workspace.value.path.title,
    topic: workspace.value.node.title,
    event_metadata: {
      path_id: workspace.value.path.id,
      path_node_id: workspace.value.node.id,
      node_id: workspace.value.node.node_id,
    },
  })
}

// 加载或重新打开节点测验题目
async function loadQuiz() {
  if (!workspace.value) return

  // 如果弹窗已打开（quizRound 有数据且 overlay 可见），不做任何操作
  if (showQuizOverlay.value && quizRound.value) return

  // 如果 quizRound 已有数据（用户之前关闭了弹窗），直接重新打开
  if (quizRound.value) {
    showQuizOverlay.value = true
    return
  }

  quizLoading.value = true
  quizResult.value = null
  isQuizSubmitted.value = false

  try {
    // 如果后端已有题目（current_round > 0），GET 获取已有题目
    if (workspace.value.current_round > 0) {
      const res = await getNodeQuestions(workspace.value.node.id)
      const data = res.data.data
      if (data) {
        quizRound.value = data
        answers.value = {}
        showQuizOverlay.value = true
        return
      }
    }

    // 首次生成题目
    const res = await generateNodeQuestions(workspace.value.node.id)
    quizRound.value = res.data.data
    answers.value = {}
    showQuizOverlay.value = true

    // 刷新 workspace 以更新 current_round 和 quiz_available
    const resWorkspace = await getLearningNodeWorkspace(nodeId.value)
    workspace.value = resWorkspace.data.data
  } catch (error) {
    toast.error(getErrorMessage(error, '生成节点测验失败'))
  } finally {
    quizLoading.value = false
  }
}

// 提交节点测验答案：判分后刷新 workspace 并记录学习事件
async function submitQuiz() {
  if (!workspace.value || !quizRound.value) return
  const payload = {
    answers: quizRound.value.questions.map((question) => ({
      question_id: question.id,
      response: answers.value[question.id] || '',
    })),
  }

  if (payload.answers.some((item) => !item.response)) {
    toast.warning('请先完成全部诊断题目')
    return
  }
  submitLoading.value = true

  try {
    const res = await submitNodeQuiz(workspace.value.node.id, payload)
    quizResult.value = res.data.data
    isQuizSubmitted.value = true

    await recordPathLearningEvent(workspace.value.path.id, {
      module: 'path',
      event_type: 'quiz_submitted',
      course: workspace.value.path.title,
      topic: workspace.value.node.title,
      score: Number(((quizResult.value.score / 5) * 100).toFixed(0)),
      event_metadata: {
        path_id: workspace.value.path.id,
        path_node_id: workspace.value.node.id,
        node_id: workspace.value.node.node_id,
        outcome: quizResult.value.outcome,
        weak_knowledge_points: quizResult.value.weak_knowledge_points,
      },
    })

    const resWorkspace = await getLearningNodeWorkspace(nodeId.value)
    workspace.value = resWorkspace.data.data
    if (workspace.value?.current_tutorial) {
      selectedTutorialId.value = workspace.value.current_tutorial.id
    }
  } catch (error) {
    toast.error(getErrorMessage(error, '提交节点测验失败'))
  } finally {
    submitLoading.value = false
  }
}

const resourceApiMap: Record<ResourceKind, (nodeId: number) => Promise<any>> = {
  mindmap: (id) => generateNodeResource(id, 'mindmap'),
  code: (id) => generateNodeResource(id, 'code'),
  ppt: (id) => generateNodeResource(id, 'ppt'),
  reading: (id) => generateNodeResource(id, 'reading'),
  cartoon: (id) => generateNodeResource(id, 'cartoon'),
}

// 调用后端生成辅助资源（如思维导图、代码、PPT 等），生成后打开查看器
async function createResource(type: ResourceKind) {
  if (!workspace.value) return
  resourceLoading.value = type
  try {
    const apiFn = resourceApiMap[type]
    const res = await apiFn(workspace.value.node.id)
    openViewer(res.data.data)

    const resWorkspace = await getLearningNodeWorkspace(nodeId.value)
    workspace.value = resWorkspace.data.data
  } catch (error) {
    toast.error(getErrorMessage(error, '生成辅助资源失败'))
  } finally {
    resourceLoading.value = ''
  }
}

function openResourceDetail(resourceId: number) {
  if (!workspace.value) return
  const resource = workspace.value.resources.find((item) => item.id === resourceId)
  if (resource) {
    openViewer(resource)
  } else {
    toast.warning('资源不存在')
  }
}

function goToNextNode(nextNodeId: number) {
  router.push(`/path-planner/node/${nextNodeId}`)
}

function choiceEntries(choice: Record<string, string> | undefined | null) {
  return Object.entries(choice || {})
}

function statusText(status: string) {
  switch (status) {
    case 'available': return '可开始'
    case 'in_progress': return '学习中'
    case 'remediation': return '专项巩固中'
    case 'reinforced': return '强化学习中'
    case 'completed': return '已通过'
    case 'completed_with_gaps': return '带缺口完成'
    default: return status
  }
}

function resultText(outcome: string) {
  switch (outcome) {
    case 'completed':
    case 'passed':
      return '认知指标达标，下一路径节点已解锁。'
    case 'remediation':
      return '存在知识隐患，系统将围绕薄弱点为您动态注入专项巩固讲义。'
    case 'reinforced':
      return '已开启极限强化模式，智能体正在针对易错盲区进行追踪阻击。'
    case 'completed_with_gaps':
      return '带缺口通关，允许继续向前推进，但强烈建议回溯下方弱项。'
    default:
      return outcome
  }
}

// 路由节点 ID 变化时重置状态并重新加载工作空间
watch(() => route.params.nodeId, (newId) => {
  if (!newId) return
  workspace.value = null
  quizRound.value = null
  quizResult.value = null
  answers.value = {}
  selectedTutorialId.value = null
  isQuizSubmitted.value = false
  showQuizOverlay.value = false
  hasStartedTracking.value = false
  loadWorkspace()
})

// 教程 Markdown 变化时重新同步锚点
watch(tutorialMarkdown, () => {
  syncHeadingAnchors()
})

// 页面挂载时加载工作空间，卸载时停止追踪
onMounted(loadWorkspace)
onBeforeUnmount(() => {
  stopTracking()
})
</script>

<style scoped>
/* ============================================================
   Layout Base & Flat Fluid Breadcrumbs Toolbar
   ============================================================ */
.node-study-page {
  min-height: calc(100vh - 72px);
  padding: 16px var(--space-6) var(--space-8);
  background-color: var(--color-bg);
}

.node-toolbar {
  max-width: var(--page-max-width);
  width: 100%;
  margin: 0 auto var(--space-4);
  padding: var(--space-2) var(--space-1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-width: 0;
}

/* 彻底解决大图标错合及文字垂直折行堆叠的工业级高精按钮 */
.back-button {
  height: 34px;
  padding: 0 var(--space-3.5);
  color: var(--color-text-secondary);
  font-weight: var(--weight-semibold);
  font-size: var(--text-sm);
  border-radius: var(--radius-sm);
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  cursor: pointer;
  box-shadow: var(--shadow-xs);
  white-space: nowrap; /* 强效杜绝垂直断开 */
  transition: var(--btn-transition);
  flex-shrink: 0;
}

.back-button:hover {
  color: var(--color-primary-text);
  background: var(--color-surface-hover);
  border-color: var(--color-border-hover);
}

/* 精细低饱和度线框后退矢量 */
.back-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.toolbar-divider {
  color: var(--color-border-hover);
  font-size: var(--text-md);
  user-select: none;
  flex-shrink: 0;
}

.toolbar-title {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.toolbar-title h1 {
  color: var(--color-text-strong);
  font-size: var(--text-md);
  font-weight: var(--weight-bold);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-pill {
  height: 28px;
  padding: 0 var(--space-3);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1_5);
  border-radius: var(--radius-sm);
  color: var(--color-warning);
  background: var(--color-warning-soft);
  border: 1px solid var(--color-border);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
}

.status-pill i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}

.status-pill.completed,
.status-pill.completed_with_gaps {
  color: var(--color-success);
  background: var(--color-success-soft);
}

.status-pill.remediation,
.status-pill.reinforced {
  color: var(--cat-tutor);
  background: var(--cat-tutor-soft);
}

.status-pill.available {
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
}

/* ============================================================
   Workspace Grid Definition
   ============================================================ */
.study-workspace {
  max-width: var(--page-max-width);
  width: 100%;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 260px 1fr 340px;
  gap: var(--space-5);
  align-items: start;
}

.toc-panel,
.resource-panel {
  position: sticky;
  top: var(--space-4);
  max-height: calc(100vh - 120px);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.toc-card,
.tutorial-main,
.resource-workbench-card {
  border-radius: var(--radius-md);
  background-color: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
}

.toc-card,
.resource-workbench-card {
  padding: var(--space-5);
}

/* ============================================================
   TOC Directory Tree
   ============================================================ */
.toc-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.toc-item {
  width: 100%;
  padding: var(--space-1_5) var(--space-2_5);
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  text-align: left;
  cursor: pointer;
  line-height: var(--leading-tight);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: var(--btn-transition);
}

.toc-item.level-3 {
  padding-left: var(--space-5);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.toc-item:hover {
  color: var(--color-primary-text);
  background: var(--color-surface-hover);
}

.toc-item.active {
  color: var(--color-primary-text);
  background: var(--color-primary-soft);
  font-weight: var(--weight-bold);
}

/* ============================================================
   Center Column - Academic Textbook Layout
   ============================================================ */
.tutorial-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.tutorial-head {
  padding: var(--space-6) var(--space-7);
  border-bottom: 1px solid var(--color-border);
  background: linear-gradient(180deg, #ffffff 0%, var(--color-surface) 100%);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.section-kicker {
  font-family: var(--font-mono);
  color: var(--color-primary-text);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.tutorial-head h2 {
  margin: var(--space-1) 0 var(--space-2);
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
}

.tutorial-head p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
  font-size: var(--text-sm);
}

.tutorial-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-4);
}

.tutorial-tabs button.active {
  box-shadow: var(--shadow-xs);
}

.tutorial-tabs em {
  font-style: normal;
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  opacity: 0.7;
}

.tutorial-tabs button.current em {
  color: var(--color-success);
  font-weight: var(--weight-bold);
}

.tutorial-reader {
  padding: var(--space-6) var(--space-7) var(--space-4);
}

.markdown-shell {
  min-height: 480px;
}

/* --- 教程元数据横幅（摘要 / 知识点 / 类型）--- */
.markdown-shell :deep(.tutorial-meta-banner) {
  margin: 0 0 20px;
  padding: 16px 20px;
  border-radius: 10px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.markdown-shell :deep(.tutorial-meta-banner .meta-summary) {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  line-height: 1.55;
}

.markdown-shell :deep(.tutorial-meta-banner .meta-kp) {
  color: var(--color-text);
  font-size: 0.85rem;
  line-height: 1.5;
}

.markdown-shell :deep(.tutorial-meta-banner .meta-kp strong) {
  color: var(--color-text-strong);
  font-weight: 700;
}

.markdown-shell :deep(.tutorial-meta-banner .meta-type) {
  display: flex;
  align-items: center;
  gap: 6px;
}

.markdown-shell :deep(.tutorial-meta-banner .type-badge) {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 700;
}

.markdown-shell :deep(.tutorial-meta-banner .type-primary) {
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border: 1px solid var(--color-primary-border);
}

.markdown-shell :deep(.tutorial-meta-banner .type-remediation) {
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
}

.markdown-shell :deep(.tutorial-meta-banner .type-reinforced) {
  color: #5b6ee1;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
}

/* ============================================================
   💡 原生章节流测试主动触发排版
   ============================================================ */
.tutorial-native-quiz {
  padding: 0 var(--space-7) var(--space-8);
  background: transparent;
}

.quiz-native-head {
  margin: var(--space-6) 0 var(--space-5);
}

.quiz-native-head h2 {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
  margin: 0 0 var(--space-2) 0;
}

.quiz-native-head p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.quiz-native-preload {
  padding: var(--space-2) 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.diagnostic-flow-text {
  font-size: var(--text-sm);
  color: var(--color-text-faint);
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-1_5);
}

.diagnostic-flow-text .dim-label {
  font-weight: var(--weight-semibold);
  color: var(--color-text-muted);
}

.diagnostic-flow-text .dim-tag {
  font-weight: var(--weight-medium);
  padding: 0 4px;
}
.diagnostic-flow-text .dim-tag.c-tutor { color: var(--cat-tutor); }
.diagnostic-flow-text .dim-tag.c-eval { color: var(--cat-eval); }
.diagnostic-flow-text .dim-tag.c-resource { color: var(--cat-resource); }
.diagnostic-flow-text .dim-tag.c-path { color: var(--cat-path); }
.diagnostic-flow-text .dim-tag.c-rose { color: var(--cat-rose); }

.quiz-action-trigger-zone {
  display: flex;
  justify-content: flex-start;
  margin-top: var(--space-1);
}

.quiz-action-trigger-zone .btn {
  height: 40px;
  padding: 0 var(--space-5);
  font-size: var(--text-sm);
  box-shadow: var(--shadow-sm);
}

/* ============================================================
   💡 题目弹窗：诊断评估答题流
   ============================================================ */
.quiz-overlay {
  position: fixed;
  inset: 0;
  z-index: 9998;
  display: grid;
  place-items: center;
  background: rgba(23, 59, 66, 0.32);
  backdrop-filter: blur(8px);
  padding: var(--space-6);
}

.quiz-shell {
  width: min(800px, 100%);
  max-height: calc(100vh - 48px);
  display: grid;
  grid-template-rows: auto 1fr;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.quiz-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg);
}

.quiz-nav-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.quiz-nav-left strong {
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
}

.quiz-body {
  padding: var(--space-6) var(--space-7) var(--space-8);
  overflow-y: auto;
}

.quiz-banner {
  margin-bottom: var(--space-5);
}

.quiz-banner p {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.quiz-question-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.quiz-question-node {
  padding-bottom: var(--space-5);
  border-bottom: 1px dashed var(--color-border-light);
}
.quiz-question-node:last-child {
  border-bottom: none;
}

.quiz-question-title {
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
  line-height: var(--leading-normal);
  margin: 0 0 var(--space-4) 0;
  display: flex;
  gap: var(--space-2);
}

.quiz-q-num {
  font-family: var(--font-mono);
  color: var(--color-primary-text);
}

.quiz-choices-stack {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-left: var(--space-4);
}

.quiz-choice-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2.5) var(--space-4);
  border-radius: 4px;
  border: 1px solid var(--color-border-light);
  background: var(--color-surface);
  cursor: pointer;
  transition: var(--btn-transition);
}

.quiz-choice-row:hover {
  background: var(--color-surface-hover);
  border-color: var(--color-border);
}

.quiz-choice-row.selected {
  background: var(--color-primary-soft);
  border-color: var(--color-primary-border);
}

.quiz-choice-row input {
  margin: 0;
  accent-color: var(--color-primary-text);
}

.quiz-choice-box {
  height: 22px;
  width: 22px;
  display: grid;
  place-items: center;
  border-radius: 4px;
  color: var(--color-primary-text);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  font-family: var(--font-mono);
  flex-shrink: 0;
}

.quiz-choice-row.selected .quiz-choice-box {
  background: var(--color-primary-text);
  color: var(--color-surface);
  border-color: var(--color-primary-text);
}

.quiz-choice-content {
  color: var(--color-text);
  font-size: var(--text-sm);
  line-height: 1.4;
}

.quiz-analysis-box {
  margin: var(--space-4) 0 0 var(--space-4);
  padding: var(--space-2) var(--space-4);
  background-color: var(--color-bg);
  border-left: 3px solid var(--color-success);
}

.quiz-analysis-meta {
  font-size: var(--text-sm);
  color: var(--color-text-strong);
}
.quiz-analysis-meta strong {
  color: var(--color-success);
  font-family: var(--font-mono);
  font-size: var(--text-md);
}

.quiz-submit-bar {
  display: flex;
  justify-content: flex-start;
  margin-top: var(--space-5);
  padding-left: var(--space-4);
}

/* 测试结果报告单 */
.quiz-result-report {
  margin-top: var(--space-6);
  padding: var(--space-5);
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, var(--color-primary-soft) 0%, var(--color-surface) 100%);
  border: 1px solid var(--color-primary-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.report-top {
  display: flex;
  align-items: flex-start;
  gap: var(--space-6);
}

.report-score {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.report-score strong {
  font-size: var(--text-3xl);
  font-weight: var(--weight-extrabold);
  color: var(--color-primary-text);
  line-height: 1;
  margin-top: var(--space-1);
}
.report-score strong small {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--color-text-muted);
}

.report-text h4 {
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
  margin-bottom: 2px;
}
.report-text p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.report-weak-zone label {
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--color-danger);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  display: block;
  margin-bottom: var(--space-2);
}

.report-weak-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1_5);
}

/* ============================================================
   RIGHT PANEL: 多维微光线框工具箱（精细微色彩流）
   ============================================================ */
.push-desc {
  margin: 0 0 var(--space-4);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}

.resource-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.resource-item {
  padding: var(--space-3);
  display: grid;
  grid-template-columns: 36px 1fr auto;
  gap: var(--space-3);
  align-items: center;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-xs);
  transition: var(--btn-transition);
}

.resource-icon-wrapper {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 4px;
  font-size: var(--text-md);
  border: 1px solid transparent;
  transition: var(--btn-transition);
}

.resource-item.mindmap .resource-icon-wrapper { color: var(--cat-eval); background: var(--cat-eval-soft); border-color: rgba(139, 92, 246, 0.15); }
.resource-item.code .resource-icon-wrapper { color: var(--color-primary-text); background: var(--color-primary-soft); border-color: var(--color-primary-border); }
.resource-item.ppt .resource-icon-wrapper { color: var(--cat-path); background: var(--cat-path-soft); border-color: rgba(245, 158, 11, 0.15); }
.resource-item.reading .resource-icon-wrapper { color: var(--cat-resource); background: var(--cat-resource-soft); border-color: rgba(16, 185, 129, 0.15); }
.resource-item.cartoon .resource-icon-wrapper { color: var(--cat-rose); background: var(--cat-rose-soft); border-color: rgba(244, 63, 94, 0.15); }

.resource-item:hover {
  transform: translateY(-0.5px);
  box-shadow: var(--shadow-sm);
}
.resource-item.mindmap:hover { border-color: var(--cat-eval); }
.resource-item.code:hover { border-color: var(--color-primary); }
.resource-item.ppt:hover { border-color: var(--cat-path); }
.resource-item.reading:hover { border-color: var(--cat-resource); }
.resource-item.cartoon:hover { border-color: var(--cat-rose); }

.resource-copy {
  min-width: 0;
}

.resource-copy strong {
  display: block;
  margin-bottom: 2px;
  color: var(--color-text-strong);
  font-size: var(--text-sm);
  font-weight: var(--weight-bold);
}

.resource-copy span {
  display: block;
  color: var(--color-text-faint);
  font-size: var(--text-xs);
  line-height: var(--leading-tight);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-lbl {
  display: inline-flex;
  margin-top: var(--space-1);
  padding: 0 4px;
  border-radius: 2px;
  background: var(--color-bg);
  color: var(--color-text-muted);
  font-size: 10px;
  font-style: normal;
  font-weight: var(--weight-bold);
}

.resource-item.generated .status-lbl {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.resource-item.generated .status-lbl.fail {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.btn-action-trigger {
  height: 28px;
  padding: 0 var(--space-2_5);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  border-radius: 4px;
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: var(--btn-transition);
}

.btn-action-trigger:hover {
  background: var(--color-surface-hover);
  color: var(--color-text-strong);
  border-color: var(--color-border-hover);
}

.resource-item.generated .btn-action-trigger {
  background: var(--color-surface);
  color: var(--color-text-strong);
}
.resource-item.mindmap.generated .btn-action-trigger { border-color: var(--cat-eval); }
.resource-item.code.generated .btn-action-trigger { border-color: var(--color-primary-border); }
.resource-item.ppt.generated .btn-action-trigger { border-color: var(--cat-path); }
.resource-item.reading.generated .btn-action-trigger { border-color: var(--cat-resource); }
.resource-item.cartoon.generated .btn-action-trigger { border-color: var(--cat-rose); }

.resource-item.generated .btn-action-trigger:hover {
  background: var(--color-surface-hover);
}

/* ============================================================
   Viewer & Loader Modals Global Override
   ============================================================ */
.state-card {
  max-width: 460px;
  width: 100%;
  margin: 140px auto 0;
  padding: var(--space-8) var(--space-6);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  text-align: center;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-lg);
}

.state-card h2 {
  font-size: var(--text-md);
  font-weight: var(--weight-bold);
}

.state-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border-light);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.75s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

.generating-view {
  min-height: calc(100vh - 160px);
  display: grid;
  place-items: center;
}

.generate-panel {
  width: min(520px, 100%);
  padding: var(--space-10) var(--space-7);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(20px);
  text-align: center;
}

.generate-loader {
  width: 64px;
  height: 64px;
  margin: 0 auto var(--space-6);
  position: relative;
  display: grid;
  place-items: center;
}

.generate-loader::before {
  content: "";
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-action));
  animation: floatBlock 2s ease-in-out infinite;
}

.generate-loader span {
  position: absolute;
  inset: 0;
  border: 1px solid rgba(70, 184, 180, 0.15);
  border-radius: 50%;
  animation: pulseRing 2.4s cubic-bezier(0.215, 0.610, 0.355, 1) infinite;
}

.generate-loader span:nth-child(2) { inset: 8px; }
.generate-loader span:nth-child(3) { inset: 16px; }

.generate-copy h1 {
  margin: var(--space-2) 0 var(--space-1_5);
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
}

.generate-copy span {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.generate-log {
  margin-top: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.log-item {
  display: flex;
  align-items: center;
  gap: var(--space-2_5);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  font-size: var(--text-sm);
  box-shadow: var(--shadow-xs);
}

.log-item i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-soft);
  flex-shrink: 0;
}

/* ============================================================
   Viewer Overlay Modal Sheet
   ============================================================ */
.viewer-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: grid;
  place-items: center;
  background: rgba(23, 59, 66, 0.3);
  backdrop-filter: blur(8px);
  padding: var(--space-6);
}

.viewer-shell {
  width: min(1200px, 100%);
  max-height: calc(100vh - 48px);
  display: grid;
  grid-template-rows: auto 1fr;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-xl);
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.viewer-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg);
}

.nav-back-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1_5) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  cursor: pointer;
  transition: var(--btn-transition);
}

.nav-back-btn:hover {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
}

.viewer-nav-status {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1_5);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  color: var(--color-text-secondary);
}

.viewer-nav-status .status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-success);
}
.viewer-nav-status .status-dot.failed { background: var(--color-danger); }

.viewer-state {
  padding: var(--space-16) var(--space-6);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2_5);
  text-align: center;
}

.viewer-workspace {
  overflow-y: auto;
}

.viewer-head {
  padding: var(--space-7) var(--space-8) var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.viewer-title h1 {
  margin: var(--space-1) 0;
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
}

.viewer-title p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.viewer-meta {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.viewer-meta span {
  padding: 1px var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  font-family: var(--font-mono);
}

.viewer-body {
  padding: var(--space-6) var(--space-8) var(--space-10);
}

/* ============================================================
   Framework Micro Animations & Breakpoints
   ============================================================ */
.log-enter-active, .log-leave-active { transition: all 0.2s ease; }
.log-enter-from, .log-leave-to { opacity: 0; transform: translateY(-4px); }

.viewer-fade-enter-active, .viewer-fade-leave-active { transition: opacity 0.15s ease; }
.viewer-fade-enter-active .viewer-shell, .viewer-fade-leave-active .viewer-shell { transition: transform 0.15s ease; }
.viewer-fade-enter-from, .viewer-fade-leave-to { opacity: 0; }
.viewer-fade-enter-from .viewer-shell, .viewer-fade-leave-to .viewer-shell { transform: scale(0.99); }

.quiz-fade-enter-active, .quiz-fade-leave-active { transition: opacity 0.2s ease; }
.quiz-fade-enter-active .quiz-shell, .quiz-fade-leave-active .quiz-shell { transition: transform 0.2s ease; }
.quiz-fade-enter-from, .quiz-fade-leave-to { opacity: 0; }
.quiz-fade-enter-from .quiz-shell, .quiz-fade-leave-to .quiz-shell { transform: scale(0.97) translateY(8px); }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulseRing { 0% { opacity: 0.5; transform: scale(0.85); } 100% { opacity: 0; transform: scale(1.1); } }
@keyframes floatBlock { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }

@media (max-width: 1400px) {
  .study-workspace {
    grid-template-columns: 220px 1fr 310px;
    gap: var(--space-4);
  }
}

@media (max-width: 1200px) {
  .study-workspace {
    grid-template-columns: 1fr 320px;
  }
  .toc-panel {
    display: none;
  }
}

@media (max-width: 900px) {
  .study-workspace {
    grid-template-columns: 1fr;
  }
  .toc-panel, .resource-panel {
    position: static;
    max-height: none;
  }
}

@media (max-width: 640px) {
  .node-study-page { padding: var(--space-3); }
  .node-toolbar { flex-direction: column; align-items: flex-start; gap: var(--space-2); }
  .toolbar-title { flex-direction: column; align-items: flex-start; gap: 2px; }
  .toolbar-divider { display: none; }
  .toolbar-right { align-self: flex-end; }
  .tutorial-head { padding: var(--space-4) var(--space-5); }
  .tutorial-reader, .tutorial-native-quiz { padding: var(--space-4) var(--space-5); }
  .resource-item { grid-template-columns: 36px 1fr; }
  .resource-item button { grid-column: 1 / -1; width: 100%; margin-top: 4px; }
}
</style>