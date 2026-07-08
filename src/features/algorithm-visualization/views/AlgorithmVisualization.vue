<template>
  <main class="algorithm-visualizer-page">
    <!-- 顶部：只负责算法模板选择与运行 -->
    <header class="workspace-toolbar">
      <div class="toolbar-left">
        <div class="template-picker">
          <span class="field-label">算法模板</span>

          <button
              type="button"
              class="template-trigger"
              :disabled="generating"
              @click="templatePanelOpen = true"
          >
            <span class="template-trigger-main">
              <span class="template-name">
                {{ selectedAlgorithm?.name || '选择算法模板' }}
              </span>
              <span
                  v-if="selectedAlgorithm"
                  :class="['difficulty-tag', selectedAlgorithm.difficulty]"
              >
                {{ difficultyLabel[selectedAlgorithm.difficulty] }}
              </span>
            </span>

            <ChevronDown class="template-trigger-icon" />
          </button>

          <div
              v-if="templatePanelOpen"
              class="template-backdrop"
              @click="templatePanelOpen = false"
          />

          <section
              v-if="templatePanelOpen"
              class="template-panel"
              @click.stop
          >
            <header class="template-panel-header">
              <div>
                <h3>选择算法模板</h3>
                <p>通过搜索或分类快速选择可视化模板</p>
              </div>

              <button
                  type="button"
                  class="template-panel-close"
                  @click="templatePanelOpen = false"
              >
                <X class="close-icon" />
              </button>
            </header>

            <div class="template-search-box">
              <Search class="search-icon" />
              <input
                  v-model="searchQuery"
                  class="template-search-input"
                  type="text"
                  placeholder="搜索算法名称、分类或关键词..."
                  autofocus
              />
            </div>

            <div class="template-category-tabs">
              <button
                  v-for="tab in categoryTabs"
                  :key="tab.key"
                  type="button"
                  class="category-tab"
                  :class="{ active: selectedCategoryKey === tab.key }"
                  @click="selectedCategoryKey = tab.key"
              >
                <span>{{ tab.label }}</span>
                <span class="category-count">{{ tab.count }}</span>
              </button>
            </div>

            <div class="template-panel-list">
              <div
                  v-for="category in filteredPanelCategories"
                  :key="category.key"
                  class="template-category-block"
              >
                <div class="template-category-title">
                  {{ category.label }}
                </div>

                <button
                    v-for="item in category.algorithms"
                    :key="item.key"
                    type="button"
                    class="template-option"
                    :class="{ active: item.key === algorithm }"
                    @click="selectTemplate(item)"
                >
                  <div class="template-option-main">
                    <div class="template-option-title">
                      <span>{{ item.name }}</span>
                      <span :class="['template-option-level', item.difficulty]">
                        {{ difficultyLabel[item.difficulty] }}
                      </span>
                    </div>

                    <p>
                      {{ item.description || getTemplateFallbackDescription(category.label, item.name) }}
                    </p>
                  </div>

                  <div class="template-option-side">
                    <span>{{ getVisualLabelForTemplate(category.key, item) }}</span>
                    <Check
                        v-if="item.key === algorithm"
                        class="check-icon"
                    />
                  </div>
                </button>
              </div>

              <div
                  v-if="filteredPanelCategories.length === 0"
                  class="template-empty-result"
              >
                没有找到匹配的算法模板
              </div>
            </div>
          </section>
        </div>

        <div class="template-summary">
          <span class="summary-title">
            {{ selectedCategoryLabel || '算法分类' }}
          </span>
          <span class="summary-divider"></span>
          <span class="summary-text">
            {{ selectedVisualLabel }}
          </span>
        </div>
      </div>

      <div class="toolbar-actions">
        <Button
            variant="outline"
            class="reset-btn"
            :disabled="generating"
            @click="resetTemplate"
        >
          <RotateCcw class="btn-icon" />
          重置模板
        </Button>

        <Button
            class="run-btn"
            :disabled="generating || !code.trim()"
            @click="handleRun"
        >
          <Play
              v-if="!generating"
              class="btn-icon"
          />
          <Loader2
              v-else
              class="btn-icon spin"
          />
          {{ generating ? '运行中...' : '运行可视化' }}
        </Button>
      </div>
    </header>

    <section class="algorithm-visualizer-main">
      <!-- 左侧：算法展示画布 -->
      <section class="visualizer-left">
        <header class="visualizer-header">
          <div class="visualizer-title">
            <span class="visualizer-kicker">算法展示</span>
            <h2>{{ selectedAlgorithm?.name || '算法可视化' }}</h2>
            <p>{{ currentEvent?.message || selectedAlgorithmDescription }}</p>
          </div>

          <div class="visualizer-state">
            <span :class="['state-dot', { active: hasEvents }]"></span>
            <span>{{ visualizerStatusText }}</span>
          </div>
        </header>

        <section class="visualizer-canvas">
          <div
              v-if="generating"
              class="canvas-loading"
          >
            <div class="loading-spinner"></div>
            <p>正在运行算法代码...</p>
          </div>

          <ArrayBarsVisualizer
              v-else-if="hasEvents && visualizerType === 'array'"
              :current-event="currentEvent"
              :current-step-index="currentStepIndex"
              :events="events"
          />

          <StackQueueVisualizer
              v-else-if="hasEvents && visualizerType === 'stack-queue'"
              :current-event="currentEvent"
              :current-step-index="currentStepIndex"
              :events="events"
          />

          <LinkedListVisualizer
              v-else-if="hasEvents && visualizerType === 'linked-list'"
              :current-event="currentEvent"
              :current-step-index="currentStepIndex"
              :events="events"
          />

          <TreeVisualizer
              v-else-if="hasEvents && visualizerType === 'tree'"
              :current-event="currentEvent"
              :current-step-index="currentStepIndex"
              :events="events"
          />

          <GraphVisualizer
              v-else-if="hasEvents && visualizerType === 'graph'"
              :current-event="currentEvent"
              :current-step-index="currentStepIndex"
              :events="events"
          />

          <DpTableVisualizer
              v-else-if="hasEvents && visualizerType === 'dp-table'"
              :current-event="currentEvent"
              :current-step-index="currentStepIndex"
              :events="events"
          />

          <div
              v-else
              class="visualizer-empty-state"
          >
            <div class="empty-preview">
              <div class="preview-bars">
                <div
                    v-for="bar in previewBars"
                    :key="bar.index"
                    class="preview-bar-item"
                >
                  <span class="preview-bar-value">{{ bar.value }}</span>
                  <div
                      class="preview-bar"
                      :style="{ height: `${bar.height}px` }"
                  />
                  <span class="preview-bar-index">{{ bar.index }}</span>
                </div>
              </div>
            </div>

            <div class="empty-copy">
              <span class="empty-kicker">可视化画布</span>
              <h2>选择算法模板，编辑代码后运行</h2>
              <p>
                左侧展示运行后的算法过程，右侧选择语言并编写代码。系统会根据后端返回的可视化轨迹渲染数组、链表、树、图等结构。
              </p>
            </div>

            <ul class="empty-tips">
              <li>顶部选择算法模板</li>
              <li>右侧选择代码语言</li>
              <li>点击运行生成展示</li>
            </ul>
          </div>
        </section>

        <!-- 简化展示控制：删除上一步、下一步、速度、时间轴 -->
        <section class="visualizer-control-bar">
          <button
              class="control-btn primary"
              :disabled="!hasEvents"
              @click="handlePrimaryAction"
          >
            <component
                :is="primaryIcon"
                class="btn-icon"
            />
            <span>{{ primaryLabel }}</span>
          </button>

          <button
              class="control-btn"
              :disabled="!hasEvents"
              @click="playback.reset"
          >
            <RotateCcw class="btn-icon" />
            <span>重置展示</span>
          </button>

          <div class="run-state">
            <span class="run-state-label">状态</span>
            <span class="run-state-value">{{ runStateText }}</span>
          </div>
        </section>

        <footer class="progress-bar">
          <div class="progress-info">
            <span class="step-count">
              <template v-if="hasEvents">
                展示节点 {{ currentStepIndex + 1 }} / {{ events.length }}
              </template>
              <template v-else>
                准备就绪
              </template>
            </span>

            <span
                v-if="currentEvent?.message"
                class="step-message"
            >
              {{ currentEvent.message }}
            </span>
          </div>

          <div class="progress-track">
            <div
                class="progress-fill"
                :style="{ width: progressPercent }"
            />
          </div>
        </footer>
      </section>

      <!-- 右侧：编辑器 -->
      <aside class="visualizer-right">
        <section
            class="code-input-panel"
            :class="editorThemeClass"
        >
          <header class="editor-header">
            <div class="editor-left">
              <span class="editor-tab">代码</span>

              <Select
                  v-model="editorLanguageModel"
                  :disabled="generating"
              >
                <SelectTrigger class="editor-language-trigger">
                  <SelectValue />
                </SelectTrigger>

                <SelectContent
                    class="editor-language-content"
                    align="start"
                >
                  <SelectItem
                      v-for="item in supportedEditorLanguages"
                      :key="item.key"
                      :value="item.key"
                  >
                    {{ item.label }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div class="editor-right">
              <span class="theme-label">主题</span>
              <div class="theme-switch">
                <button
                    type="button"
                    class="theme-btn"
                    :class="{ active: editorTheme === 'light' }"
                    @click="setEditorTheme('light')"
                >
                  白色
                </button>
                <button
                    type="button"
                    class="theme-btn"
                    :class="{ active: editorTheme === 'dark' }"
                    @click="setEditorTheme('dark')"
                >
                  黑色
                </button>
              </div>
            </div>
          </header>

          <div class="editor-main">
            <div
                ref="editorContainer"
                class="monaco-container"
            />
          </div>

          <footer class="editor-statusbar">
            <div class="status-left">
              <span>{{ editorLanguageLabel }}</span>
              <span>{{ editorLineCount }} 行</span>
              <span>{{ editorCharCount }} 字符</span>
            </div>

            <div class="status-right">
              <span>Ln {{ editorCursorLine }}, Col {{ editorCursorColumn }}</span>
              <span
                  v-if="currentEvent?.line"
                  class="active-line-text"
              >
                执行行：{{ currentEvent.line }}
              </span>
              <span v-else>等待运行</span>
            </div>
          </footer>
        </section>
      </aside>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'
import type { CodeLanguage } from '@/features/algorithm-visualization/types'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import {
  Check,
  ChevronDown,
  Loader2,
  Pause,
  Play,
  RotateCcw,
  Search,
  X,
} from 'lucide-vue-next'
import ArrayBarsVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/sorting/ArrayBarsVisualizer.vue'
import StackQueueVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/structures/StackQueueVisualizer.vue'
import LinkedListVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/structures/LinkedListVisualizer.vue'
import TreeVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/trees/TreeVisualizer.vue'
import GraphVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/graphs/GraphVisualizer.vue'
import DpTableVisualizer from '@/features/algorithm-visualization/components/algorithm-visualizer/visualizers/dp/DpTableVisualizer.vue'
import { useTracePlayer } from '@/features/algorithm-visualization/composables/useTracePlayer'
import { useAlgorithmTemplate } from '@/features/algorithm-visualization/composables/useAlgorithmTemplate'
import { useAlgorithmRun } from '@/features/algorithm-visualization/composables/useAlgorithmRun'
import { useVisualizerResolver } from '@/features/algorithm-visualization/composables/useVisualizerResolver'
import { useVisualizerTimeline } from '@/features/algorithm-visualization/composables/useVisualizerTimeline'
import { algorithmCategories } from '@/features/algorithm-visualization/data/algorithmCategories'

defineOptions({
  name: 'AlgorithmVisualization',
})

type EditorTheme = 'dark' | 'light'
type Difficulty = 'easy' | 'medium' | 'hard'

interface LanguageOption {
  key: CodeLanguage
  label: string
}

interface AlgorithmTemplateItem {
  key: string
  name: string
  difficulty: Difficulty
  supportedLanguages: CodeLanguage[]
  description?: string
  visualizerType?: string
}

interface AlgorithmTemplateCategory {
  key: string
  label: string
  algorithms: AlgorithmTemplateItem[]
}

const {
  language,
  algorithm,
  code,
  languages,
  loadMeta,
  loadTemplate,
  resetTemplate,
  getCurrentVisualizerType,
} = useAlgorithmTemplate()

const {
  events,
  generating,
  run: runAlgorithm,
} = useAlgorithmRun()

const playback = useTracePlayer(() => events.value)
const resolver = useVisualizerResolver(events)

useVisualizerTimeline({
  playing: playback.playing,
  currentEvent: playback.currentEvent,
  speed: playback.speed,
  next: playback.next,
  pause: playback.pause,
})

const currentEvent = computed(() => playback.currentEvent.value)
const currentStepIndex = computed(() => playback.currentStepIndex.value)
const visualizerType = computed(() => resolver.visualizerType.value)
const hasEvents = computed(() => events.value.length > 0)

const templatePanelOpen = ref(false)
const searchQuery = ref('')
const selectedCategoryKey = ref('all')

const difficultyLabel: Record<Difficulty, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}

const previewBars = [
  { index: 0, value: 49, height: 76 },
  { index: 1, value: 38, height: 58 },
  { index: 2, value: 65, height: 104 },
  { index: 3, value: 97, height: 148 },
  { index: 4, value: 76, height: 120 },
  { index: 5, value: 13, height: 34 },
]

const typedAlgorithmCategories = computed(() => {
  return algorithmCategories as unknown as AlgorithmTemplateCategory[]
})

const allAlgorithms = computed(() => {
  return typedAlgorithmCategories.value.flatMap((category) => category.algorithms)
})

const selectedAlgorithm = computed(() => {
  return allAlgorithms.value.find((item) => item.key === algorithm.value) ?? null
})

const selectedCategoryLabel = computed(() => {
  for (const category of typedAlgorithmCategories.value) {
    if (category.algorithms.some((item) => item.key === algorithm.value)) {
      return category.label
    }
  }

  return ''
})

const selectedAlgorithmDescription = computed(() => {
  return (
      selectedAlgorithm.value?.description ||
      '运行代码后，系统会根据后端返回的轨迹展示算法执行过程。'
  )
})

const selectedVisualLabel = computed(() => {
  const selected = selectedAlgorithm.value

  if (!selected) return '选择模板后展示可视化类型'

  return getVisualLabelForTemplate(getCategoryKeyOfTemplate(selected.key), selected)
})

const categoryTabs = computed(() => {
  const tabs = typedAlgorithmCategories.value.map((category) => ({
    key: category.key,
    label: category.label,
    count: category.algorithms.length,
  }))

  return [
    {
      key: 'all',
      label: '全部',
      count: allAlgorithms.value.length,
    },
    ...tabs,
  ]
})

const filteredPanelCategories = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  return typedAlgorithmCategories.value
      .filter((category) => {
        if (selectedCategoryKey.value === 'all') return true
        return category.key === selectedCategoryKey.value
      })
      .map((category) => {
        const algorithms = category.algorithms.filter((item) => {
          if (!query) return true

          return [
            item.name,
            item.key,
            item.description ?? '',
            category.label,
            getVisualLabelForTemplate(category.key, item),
          ]
              .join(' ')
              .toLowerCase()
              .includes(query)
        })

        return {
          ...category,
          algorithms,
        }
      })
      .filter((category) => category.algorithms.length > 0)
})

const supportedEditorLanguages = computed<LanguageOption[]>(() => {
  const selected = selectedAlgorithm.value
  const source = languages.value as LanguageOption[]

  if (!selected || selected.supportedLanguages.length === 0) {
    return source
  }

  return source.filter((item) => selected.supportedLanguages.includes(item.key))
})

const editorLanguageModel = computed({
  get: () => language.value,
  set: (value: CodeLanguage) => {
    if (generating.value) return

    language.value = value
    // language watch 会自动触发 reloadAlgorithms + loadTemplate
  },
})

const visualizerStatusText = computed(() => {
  if (generating.value) return '运行中'
  if (hasEvents.value) return `已生成 ${events.value.length} 个展示节点`
  return '未运行'
})

const runStateText = computed(() => {
  if (generating.value) return '正在生成可视化'
  if (playback.playing.value) return '正在展示'
  if (hasEvents.value) return '已生成展示'
  return '等待运行'
})

const progressPercent = computed(() => {
  if (!hasEvents.value) return '0%'
  return `${(((currentStepIndex.value + 1) / events.value.length) * 100).toFixed(1)}%`
})

const primaryLabel = computed(() => {
  if (playback.playing.value) return '暂停展示'
  if (playback.finished.value) return '重新展示'
  return '开始展示'
})

const primaryIcon = computed(() => {
  return playback.playing.value ? Pause : Play
})

const editorContainer = ref<HTMLDivElement | null>(null)
const editorTheme = ref<EditorTheme>('dark')
const editorCursorLine = ref(1)
const editorCursorColumn = ref(1)

let editor: monaco.editor.IStandaloneCodeEditor | null = null
let decorationsCollection: monaco.editor.IEditorDecorationsCollection | null = null
let internalChange = false

const editorLanguageLabel = computed(() => {
  return getLanguageLabel(language.value)
})

const editorThemeClass = computed(() => {
  return editorTheme.value === 'dark' ? 'theme-dark' : 'theme-light'
})

const monacoThemeName = computed(() => {
  return editorTheme.value === 'dark' ? 'algorithm-black' : 'algorithm-white'
})

const editorLineCount = computed(() => {
  return code.value ? code.value.split('\n').length : 0
})

const editorCharCount = computed(() => {
  return code.value.length
})

onMounted(async () => {
  await loadMeta()
  normalizeInitialSelection()

  // 确保模板加载完成后再创建编辑器
  if (!code.value.trim()) {
    await loadTemplate()
  }

  await nextTick()
  createEditor()
})

onBeforeUnmount(() => {
  decorationsCollection?.clear()
  decorationsCollection = null

  editor?.dispose()
  editor = null
})

watch(
    () => code.value,
    (newCode) => {
      if (!editor || internalChange) return

      const currentValue = editor.getValue()
      if (currentValue !== newCode) {
        const position = editor.getPosition()
        editor.setValue(newCode)

        if (position) {
          editor.setPosition(position)
        }
      }
    }
)

watch(
    () => language.value,
    (newLanguage) => {
      if (!editor) return

      const model = editor.getModel()
      if (!model) return

      monaco.editor.setModelLanguage(model, mapCodeLanguage(newLanguage))
    }
)

watch(
    () => generating.value,
    (loading) => {
      editor?.updateOptions({
        readOnly: loading,
      })
    }
)

watch(
    () => currentEvent.value?.line,
    (line) => {
      updateActiveLine(line)
    }
)

watch(
    () => editorTheme.value,
    () => {
      monaco.editor.setTheme(monacoThemeName.value)
      updateActiveLine(currentEvent.value?.line)
    }
)

function normalizeInitialSelection() {
  if (!selectedAlgorithm.value && allAlgorithms.value.length > 0) {
    algorithm.value = allAlgorithms.value[0]!.key
  }

  const selected = selectedAlgorithm.value

  if (!selected) return

  if (!selected.supportedLanguages.includes(language.value)) {
    const firstSupported = selected.supportedLanguages[0]
    if (firstSupported) {
      language.value = firstSupported
    }
  }
}

function selectTemplate(item: AlgorithmTemplateItem) {
  if (generating.value) return

  const algorithmChanged = algorithm.value !== item.key
  const languageChanged = !item.supportedLanguages.includes(language.value)

  algorithm.value = item.key

  if (languageChanged) {
    const firstSupported = item.supportedLanguages[0]
    if (firstSupported) {
      language.value = firstSupported
    }
    // language watch 会触发 reloadAlgorithms + loadTemplate
  } else if (algorithmChanged) {
    // algorithm watch 会触发 loadTemplate
  } else {
    // 同一算法同一语言，手动刷新（watch 不会触发）
    loadTemplate()
  }

  templatePanelOpen.value = false
}

function getCategoryKeyOfTemplate(templateKey: string) {
  const category = typedAlgorithmCategories.value.find((item) =>
      item.algorithms.some((algorithmItem) => algorithmItem.key === templateKey)
  )

  return category?.key ?? ''
}

function getTemplateFallbackDescription(categoryLabel: string, templateName: string) {
  return `${categoryLabel}模板，用于生成${templateName}的可视化执行过程。`
}

function getVisualLabelForTemplate(categoryKey: string, item: AlgorithmTemplateItem) {
  const explicitType = item.visualizerType

  const typeMap: Record<string, string> = {
    array: '数组可视化',
    'stack-queue': '栈队列可视化',
    'linked-list': '链表可视化',
    tree: '树结构可视化',
    graph: '图结构可视化',
    'dp-table': '动态规划表格',
  }

  if (explicitType && typeMap[explicitType]) {
    return typeMap[explicitType]
  }

  const categoryMap: Record<string, string> = {
    sorting: '数组可视化',
    search: '搜索可视化',
    stack: '栈队列可视化',
    queue: '栈队列可视化',
    linked_list: '链表可视化',
    tree: '树结构可视化',
    graph: '图结构可视化',
    dp: '动态规划表格',
  }

  return categoryMap[categoryKey] ?? '算法可视化'
}

function getLanguageLabel(value: CodeLanguage | string) {
  const matched = (languages.value as LanguageOption[]).find((item) => item.key === value)

  if (matched?.label) {
    return matched.label
  }

  const fallbackMap: Record<string, string> = {
    python: 'Python',
    javascript: 'JavaScript',
    js: 'JavaScript',
    cpp: 'C++',
    c: 'C',
    java: 'Java',
  }

  return fallbackMap[String(value)] ?? String(value)
}

function handlePrimaryAction() {
  if (!hasEvents.value) return

  if (playback.playing.value) {
    playback.pause()
    return
  }

  playback.play()
}

async function handleRun() {
  if (generating.value || !code.value.trim()) return

  await runAlgorithm({
    algorithm: algorithm.value,
    visualizerType: getCurrentVisualizerType(),
    language: language.value,
    code: code.value,
  })

  playback.reset()

  if (events.value.length > 0) {
    playback.play()
  }
}

function createEditor() {
  if (!editorContainer.value) return

  configureMonaco()
  defineMonacoThemes()

  editor = monaco.editor.create(editorContainer.value, {
    value: code.value,
    language: mapCodeLanguage(language.value),
    theme: monacoThemeName.value,
    readOnly: generating.value,
    automaticLayout: true,

    fontSize: 14,
    lineHeight: 24,
    fontFamily:
        'JetBrains Mono, Fira Code, Menlo, Monaco, Consolas, "Courier New", monospace',
    fontLigatures: true,

    minimap: {
      enabled: false,
    },

    lineNumbers: 'on',
    glyphMargin: false,
    folding: true,
    foldingHighlight: false,
    lineDecorationsWidth: 12,
    lineNumbersMinChars: 3,

    scrollBeyondLastLine: false,
    smoothScrolling: true,
    cursorBlinking: 'smooth',
    cursorSmoothCaretAnimation: 'on',
    cursorWidth: 2,

    renderLineHighlight: 'line',
    roundedSelection: false,
    overviewRulerBorder: false,
    hideCursorInOverviewRuler: true,

    scrollbar: {
      verticalScrollbarSize: 8,
      horizontalScrollbarSize: 8,
      alwaysConsumeMouseWheel: false,
    },

    wordWrap: 'off',
    tabSize: 2,
    insertSpaces: true,
    detectIndentation: true,

    quickSuggestions: true,
    suggestOnTriggerCharacters: true,
    parameterHints: {
      enabled: true,
    },
    hover: {
      enabled: true,
    },

    formatOnType: false,
    formatOnPaste: false,
    wordBasedSuggestions: 'off',

    matchBrackets: 'always',
    bracketPairColorization: {
      enabled: true,
    },
    guides: {
      bracketPairs: true,
      indentation: true,
    },

    padding: {
      top: 14,
      bottom: 14,
    },
  })

  decorationsCollection = editor.createDecorationsCollection()

  editor.onDidChangeModelContent(() => {
    if (!editor) return

    internalChange = true
    code.value = editor.getValue()

    nextTick(() => {
      internalChange = false
    })
  })

  editor.onDidChangeCursorPosition((event) => {
    editorCursorLine.value = event.position.lineNumber
    editorCursorColumn.value = event.position.column
  })

  const position = editor.getPosition()
  if (position) {
    editorCursorLine.value = position.lineNumber
    editorCursorColumn.value = position.column
  }

  updateActiveLine(currentEvent.value?.line)
}

function configureMonaco() {
  // No TypeScript/JavaScript defaults configuration needed —
  // the editor is used for Python/C++/Java, not TS/JS.
  // The old monaco.languages.typescript API was deprecated.
}

function defineMonacoThemes() {
  monaco.editor.defineTheme('algorithm-black', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: '', foreground: 'd4d4d4', background: '171717' },
      { token: 'comment', foreground: '6a9955' },
      { token: 'keyword', foreground: '569cd6' },
      { token: 'number', foreground: 'b5cea8' },
      { token: 'string', foreground: 'ce9178' },
      { token: 'type', foreground: '4ec9b0' },
      { token: 'function', foreground: 'dcdcaa' },
      { token: 'variable', foreground: '9cdcfe' },
    ],
    colors: {
      'editor.background': '#171717',
      'editor.foreground': '#d4d4d4',
      'editorGutter.background': '#171717',
      'editorLineNumber.foreground': '#6b7280',
      'editorLineNumber.activeForeground': '#ffffff',
      'editorCursor.foreground': '#ffffff',
      'editor.lineHighlightBackground': '#222222',
      'editor.selectionBackground': '#264f78',
      'editor.inactiveSelectionBackground': '#333333',
      'editorIndentGuide.background1': '#2f3337',
      'editorIndentGuide.activeBackground1': '#4b5563',
      'scrollbarSlider.background': '#4b556366',
      'scrollbarSlider.hoverBackground': '#6b728088',
      'scrollbarSlider.activeBackground': '#9ca3af99',
    },
  })

  monaco.editor.defineTheme('algorithm-white', {
    base: 'vs',
    inherit: true,
    rules: [
      { token: '', foreground: '111827', background: 'ffffff' },
      { token: 'comment', foreground: '6b7280' },
      { token: 'keyword', foreground: '2563eb' },
      { token: 'number', foreground: '047857' },
      { token: 'string', foreground: 'b45309' },
      { token: 'type', foreground: '0f766e' },
      { token: 'function', foreground: '7c3aed' },
      { token: 'variable', foreground: '111827' },
    ],
    colors: {
      'editor.background': '#ffffff',
      'editor.foreground': '#111827',
      'editorGutter.background': '#ffffff',
      'editorLineNumber.foreground': '#9ca3af',
      'editorLineNumber.activeForeground': '#111827',
      'editorCursor.foreground': '#111827',
      'editor.lineHighlightBackground': '#f3f4f6',
      'editor.selectionBackground': '#bfdbfe',
      'editor.inactiveSelectionBackground': '#e5e7eb',
      'editorIndentGuide.background1': '#e5e7eb',
      'editorIndentGuide.activeBackground1': '#9ca3af',
      'scrollbarSlider.background': '#9ca3af44',
      'scrollbarSlider.hoverBackground': '#6b728066',
      'scrollbarSlider.activeBackground': '#4b556399',
    },
  })
}

function setEditorTheme(theme: EditorTheme) {
  editorTheme.value = theme
}

function mapCodeLanguage(value: CodeLanguage): string {
  const map: Partial<Record<CodeLanguage, string>> = {
    python: 'python',
    javascript: 'javascript',
    cpp: 'cpp',
    java: 'java',
    c: 'c',
  }

  return map[value] ?? 'plaintext'
}

function updateActiveLine(line?: number) {
  if (!editor || !decorationsCollection) return

  if (!line || line <= 0) {
    decorationsCollection.clear()
    return
  }

  decorationsCollection.set([
    {
      range: new monaco.Range(line, 1, line, 1),
      options: {
        isWholeLine: true,
        className: editorTheme.value === 'dark' ? 'active-line-dark' : 'active-line-light',
        linesDecorationsClassName:
            editorTheme.value === 'dark'
                ? 'active-line-gutter-dark'
                : 'active-line-gutter-light',
        overviewRuler: {
          color: editorTheme.value === 'dark' ? '#22c55e' : '#2563eb',
          position: monaco.editor.OverviewRulerLane.Full,
        },
      },
    },
  ])

  editor.revealLineInCenterIfOutsideViewport(line)
}
</script>

<style scoped>
.algorithm-visualizer-page {
  height: calc(100vh - var(--navbar-height, 72px));
  min-height: 680px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
  border-radius: 0;
}

/* 顶部工作栏 */
.workspace-toolbar {
  height: 54px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 16px;
  border-bottom: 1px solid var(--color-border);
  background: #ffffff;
  border-radius: 0;
}

.toolbar-left {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 18px;
}

.template-picker {
  position: relative;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-label {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.template-trigger {
  width: 250px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 10px;
  border: 1px solid var(--color-border);
  border-radius: 0;
  background: #ffffff;
  color: var(--color-text);
  cursor: pointer;
}

.template-trigger:hover:not(:disabled) {
  border-color: var(--color-primary);
}

.template-trigger:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.template-trigger-main {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.template-name {
  overflow: hidden;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-trigger-icon {
  width: 14px;
  height: 14px;
  flex: 0 0 auto;
  color: var(--color-text-muted);
}

.difficulty-tag {
  flex: 0 0 auto;
  padding: 1px 6px;
  border-radius: 0;
  font-size: 11px;
  font-weight: 800;
}

.difficulty-tag.easy {
  color: var(--color-success);
  background: var(--color-success-soft);
}

.difficulty-tag.medium {
  color: var(--color-warning);
  background: var(--color-warning-soft);
}

.difficulty-tag.hard {
  color: var(--color-danger);
  background: var(--color-danger-soft);
}

.template-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: transparent;
}

.template-panel {
  position: absolute;
  top: 42px;
  left: 72px;
  z-index: 60;
  width: 620px;
  max-width: min(620px, calc(100vw - 32px));
  height: min(620px, calc(100vh - 150px));
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border);
  background: #ffffff;
  box-shadow: 0 18px 46px rgba(15, 23, 42, 0.14);
  border-radius: 0;
}

.template-panel-header {
  height: 62px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 16px;
  border-bottom: 1px solid var(--color-border);
}

.template-panel-header h3 {
  margin: 0;
  color: var(--color-text);
  font-size: 15px;
  font-weight: 800;
}

.template-panel-header p {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
}

.template-panel-close {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border);
  border-radius: 0;
  background: #ffffff;
  color: var(--color-text-muted);
  cursor: pointer;
}

.template-panel-close:hover {
  border-color: var(--color-primary);
  color: var(--color-text);
}

.close-icon {
  width: 15px;
  height: 15px;
}

.template-search-box {
  height: 44px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 14px;
  border-bottom: 1px solid var(--color-border-light);
}

.search-icon {
  width: 15px;
  height: 15px;
  flex: 0 0 auto;
  color: var(--color-text-faint);
}

.template-search-input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-text);
  font-size: 13px;
}

.template-search-input::placeholder {
  color: var(--color-text-faint);
}

.template-category-tabs {
  height: 44px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  border-bottom: 1px solid var(--color-border-light);
  overflow-x: auto;
}

.category-tab {
  height: 28px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid var(--color-border);
  border-radius: 0;
  background: #ffffff;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
}

.category-tab:hover {
  border-color: var(--color-primary);
  color: var(--color-text);
}

.category-tab.active {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #ffffff;
}

.category-count {
  opacity: 0.72;
}

.template-panel-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 12px 12px;
}

.template-category-block + .template-category-block {
  margin-top: 12px;
}

.template-category-title {
  height: 28px;
  display: flex;
  align-items: center;
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 800;
}

.template-option {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--color-border-light);
  border-radius: 0;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
}

.template-option + .template-option {
  margin-top: 8px;
}

.template-option:hover {
  border-color: var(--color-primary);
  background: #f8fbfb;
}

.template-option.active {
  border-color: var(--color-primary);
  background: rgba(70, 184, 180, 0.08);
}

.template-option-main {
  min-width: 0;
}

.template-option-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 800;
}

.template-option-title span:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-option-level {
  flex: 0 0 auto;
  font-size: 11px;
  font-weight: 800;
}

.template-option-level.easy {
  color: var(--color-success);
}

.template-option-level.medium {
  color: var(--color-warning);
}

.template-option-level.hard {
  color: var(--color-danger);
}

.template-option-main p {
  margin: 5px 0 0;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-option-side {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.check-icon {
  width: 15px;
  height: 15px;
  color: var(--color-primary);
}

.template-empty-result {
  padding: 48px 0;
  color: var(--color-text-muted);
  font-size: 13px;
  text-align: center;
}

.template-summary {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 12px;
  white-space: nowrap;
}

.summary-title {
  color: var(--color-text-secondary);
  font-weight: 800;
}

.summary-divider {
  width: 1px;
  height: 14px;
  background: var(--color-border);
}

.summary-text {
  overflow: hidden;
  text-overflow: ellipsis;
}

.toolbar-actions {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.reset-btn,
.run-btn {
  height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 0 !important;
  font-size: 13px;
  font-weight: 800;
}

.reset-btn {
  padding: 0 12px;
  border: 1px solid var(--color-border);
  background: #ffffff;
  color: var(--color-text-secondary);
}

.reset-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-text);
}

.run-btn {
  padding: 0 16px;
  border: 0;
  background: var(--color-primary);
  color: #ffffff;
}

.run-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-icon {
  width: 14px;
  height: 14px;
}

.spin {
  animation: spin 1s linear infinite;
}

/* 主体 6 / 4 */
.algorithm-visualizer-main {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 6fr) minmax(0, 4fr);
  gap: 1px;
  background: var(--color-border);
  border-radius: 0;
}

.visualizer-left,
.visualizer-right {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
  border-radius: 0;
}

.visualizer-left {
  border-right: 1px solid var(--color-border);
}

/* 左侧展示区 */
.visualizer-header {
  height: 62px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 9px 16px;
  border-bottom: 1px solid var(--color-border);
  background: #ffffff;
}

.visualizer-title {
  min-width: 0;
}

.visualizer-kicker {
  display: block;
  margin-bottom: 2px;
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 800;
}

.visualizer-title h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 15px;
  line-height: 1.25;
  font-weight: 800;
}

.visualizer-title p {
  max-width: 760px;
  margin: 3px 0 0;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.visualizer-state {
  flex: 0 0 auto;
  height: 28px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 800;
}

.state-dot {
  width: 7px;
  height: 7px;
  background: var(--color-text-faint);
}

.state-dot.active {
  background: var(--color-primary);
}

.visualizer-canvas {
  position: relative;
  flex: 1 1 0%;
  min-height: 0;
  overflow: hidden;
  background:
      linear-gradient(rgba(15, 23, 42, 0.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(15, 23, 42, 0.035) 1px, transparent 1px),
      #f8fbfb;
  background-size: 28px 28px;
}

.canvas-loading {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  place-content: center;
  gap: 14px;
  background: rgba(255, 255, 255, 0.94);
}

.canvas-loading p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.loading-spinner {
  width: 34px;
  height: 34px;
  margin: 0 auto;
  border: 3px solid rgba(70, 184, 180, 0.16);
  border-top-color: var(--color-primary);
  border-radius: 50% !important;
  animation: spin 0.9s linear infinite;
}

.visualizer-empty-state {
  height: 100%;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 20px;
  padding: 24px;
  background: transparent;
  text-align: center;
}

.empty-preview {
  width: min(560px, 92%);
  height: 180px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  border: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.68);
}

.preview-bars {
  height: 150px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 22px;
}

.preview-bar-item {
  width: 46px;
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: 6px;
}

.preview-bar-value,
.preview-bar-index {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.preview-bar {
  width: 34px;
  background: linear-gradient(180deg, rgba(70, 184, 180, 0.36), rgba(70, 184, 180, 0.16));
  border: 1px solid rgba(70, 184, 180, 0.28);
}

.empty-copy {
  max-width: 560px;
}

.empty-kicker {
  height: 22px;
  display: inline-flex;
  align-items: center;
  padding: 0 8px;
  border: 1px solid #bfdbfe;
  border-radius: 0;
  background: #eff6ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 800;
}

.empty-copy h2 {
  margin: 12px 0 6px;
  color: #0f172a;
  font-size: 18px;
  line-height: 1.3;
  font-weight: 800;
}

.empty-copy p {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.7;
}

.empty-tips {
  width: min(600px, 100%);
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.empty-tips li {
  padding: 8px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 0;
  background: #ffffff;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
}

/* 简化控制栏 */
.visualizer-control-bar {
  height: 48px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
  box-shadow: none;
}

.control-btn {
  height: 30px;
  min-width: 96px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: 0 !important;
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  transition: var(--btn-transition);
}

.control-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  background: var(--color-surface-hover);
}

.control-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.control-btn.primary {
  border-color: rgba(32, 95, 103, 0.12);
  background: var(--color-primary);
  color: #ffffff;
}

.control-btn.primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.run-state {
  min-width: 0;
  height: 30px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border-left: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-size: 12px;
  white-space: nowrap;
}

.run-state-label {
  color: var(--color-text-secondary);
  font-weight: 800;
}

.run-state-value {
  color: var(--color-text-muted);
  font-weight: 700;
}

.progress-bar {
  height: 32px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.progress-info {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
}

.step-count {
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.step-message {
  max-width: 360px;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.progress-track {
  flex: 1;
  height: 3px;
  overflow: hidden;
  border-radius: 0;
  background: var(--color-border-light);
}

.progress-fill {
  height: 100%;
  border-radius: 0;
  background: var(--color-primary);
  transition: width 0.3s ease;
}

/* 右侧编辑器 */
.code-input-panel {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 0;
}

.code-input-panel.theme-dark {
  background: #171717;
  color: #e5e7eb;
}

.code-input-panel.theme-light {
  background: #ffffff;
  color: #111827;
}

.editor-header {
  height: 44px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 12px;
  border-radius: 0;
}

.theme-dark .editor-header {
  border-bottom: 1px solid #1f2937;
  background: #0f172a;
}

.theme-light .editor-header {
  border-bottom: 1px solid #e5e7eb;
  background: #ffffff;
}

.editor-left,
.editor-right {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.editor-tab {
  height: 44px;
  display: inline-flex;
  align-items: center;
  padding: 0 12px;
  border-bottom: 2px solid currentColor;
  font-size: 13px;
  font-weight: 800;
}

.theme-dark .editor-tab {
  color: #ffffff;
}

.theme-light .editor-tab {
  color: #111827;
}

.editor-language-trigger {
  width: 128px;
  height: 30px;
  border-radius: 0 !important;
  font-size: 12px;
  font-weight: 800;
}

.theme-dark .editor-language-trigger {
  border: 1px solid #334155;
  background: #111827;
  color: #e5e7eb;
}

.theme-light .editor-language-trigger {
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #111827;
}

.editor-language-content {
  border-radius: 0 !important;
}

.theme-label {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 700;
}

.theme-light .theme-label {
  color: #64748b;
}

.theme-switch {
  height: 28px;
  display: inline-flex;
  border-radius: 0;
}

.theme-dark .theme-switch {
  border: 1px solid #334155;
}

.theme-light .theme-switch {
  border: 1px solid #d1d5db;
}

.theme-btn {
  height: 28px;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  border: 0;
  border-radius: 0;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.theme-dark .theme-btn {
  background: #111827;
  color: #94a3b8;
}

.theme-dark .theme-btn.active {
  background: #ffffff;
  color: #111827;
}

.theme-light .theme-btn {
  background: #ffffff;
  color: #64748b;
}

.theme-light .theme-btn.active {
  background: #111827;
  color: #ffffff;
}

.editor-main {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  border-radius: 0;
}

.monaco-container {
  width: 100%;
  height: 100%;
  border-radius: 0;
}

.editor-statusbar {
  height: 30px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 12px;
  border-radius: 0;
  font-size: 12px;
  font-weight: 700;
}

.theme-dark .editor-statusbar {
  border-top: 1px solid #1f2937;
  background: #0f172a;
  color: #94a3b8;
}

.theme-light .editor-statusbar {
  border-top: 1px solid #e5e7eb;
  background: #f8fafc;
  color: #64748b;
}

.status-left,
.status-right {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 14px;
}

.status-right {
  justify-content: flex-end;
}

.active-line-text {
  color: #16a34a;
}

:deep(.active-line-dark) {
  background: rgba(34, 197, 94, 0.14) !important;
  border-left: 3px solid #22c55e;
}

:deep(.active-line-light) {
  background: rgba(37, 99, 235, 0.1) !important;
  border-left: 3px solid #2563eb;
}

:deep(.active-line-gutter-dark) {
  background: rgba(34, 197, 94, 0.2) !important;
}

:deep(.active-line-gutter-light) {
  background: rgba(37, 99, 235, 0.15) !important;
}

:deep(.monaco-editor),
:deep(.monaco-editor-background),
:deep(.monaco-scrollable-element),
:deep(button),
:deep([role='combobox']),
:deep([role='option']) {
  border-radius: 0 !important;
}

/* 删除页面内可能出现的无关悬浮编辑按钮 */
.algorithm-visualizer-page :deep(.floating-action-button),
.algorithm-visualizer-page :deep(.floating-edit-button),
.algorithm-visualizer-page :deep(.fab) {
  display: none !important;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1180px) {
  .workspace-toolbar {
    height: auto;
    min-height: 54px;
    align-items: stretch;
    flex-direction: column;
    padding: 8px 12px;
  }

  .toolbar-left {
    width: 100%;
    flex-wrap: wrap;
    gap: 10px;
  }

  .toolbar-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .template-summary {
    display: none;
  }

  .template-panel {
    left: 0;
  }
}

@media (max-width: 960px) {
  .algorithm-visualizer-page {
    height: auto;
    min-height: 100vh;
    overflow: visible;
  }

  .algorithm-visualizer-main {
    grid-template-columns: 1fr;
  }

  .visualizer-left {
    min-height: 560px;
    border-right: 0;
  }

  .visualizer-right {
    min-height: 520px;
  }
}

@media (max-width: 768px) {
  .template-trigger {
    width: 210px;
  }

  .template-panel {
    width: calc(100vw - 24px);
    height: min(620px, calc(100vh - 120px));
  }

  .visualizer-header {
    height: auto;
    align-items: flex-start;
    flex-direction: column;
  }

  .visualizer-control-bar {
    height: auto;
    align-items: stretch;
    flex-wrap: wrap;
    padding: 8px 12px;
  }

  .run-state {
    width: 100%;
    border-left: 0;
    padding: 0;
  }

  .progress-bar {
    padding: 0 12px;
  }

  .step-message {
    max-width: 150px;
  }

  .empty-tips {
    grid-template-columns: 1fr;
  }

  .empty-copy h2 {
    font-size: 16px;
  }

  .empty-preview {
    display: none;
  }

  .editor-header {
    height: auto;
    min-height: 44px;
    align-items: stretch;
    flex-direction: column;
    padding: 8px 10px;
  }

  .editor-left,
  .editor-right {
    width: 100%;
    flex-wrap: wrap;
  }

  .editor-statusbar {
    height: auto;
    min-height: 30px;
    align-items: flex-start;
    flex-direction: column;
    padding: 7px 10px;
  }
}
</style>