<template>
  <section
    class="code-input-panel"
    :class="editorThemeClass"
  >
    <header class="editor-header">
      <div class="editor-left">
        <span class="editor-tab">{{ title ?? '代码' }}</span>

        <Select
          v-model="editorLanguageModel"
          :disabled="disabled"
        >
          <SelectTrigger class="editor-language-trigger">
            <SelectValue placeholder="语言" />
          </SelectTrigger>

          <SelectContent
            class="editor-language-content"
            align="start"
          >
            <SelectItem
              v-for="item in languages"
              :key="item.key"
              :value="item.key"
            >
              {{ item.label }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div class="editor-right">
        <span class="editor-file-pill">{{ editorExtension }}</span>
        <button
          type="button"
          class="theme-toggle"
          :title="themeToggleTitle"
          @click="toggleEditorTheme"
        >
          <Sun
            v-if="editorTheme === 'dark'"
            class="theme-icon"
          />
          <Moon
            v-else
            class="theme-icon"
          />
        </button>
      </div>
    </header>

    <div class="editor-main">
      <div
        ref="editorContainer"
        class="monaco-container"
      />
    </div>

    <div
      v-if="traceReadoutText"
      class="trace-readout"
    >
      <span class="trace-readout-label">运行过程</span>
      <span class="trace-readout-text">{{ traceReadoutText }}</span>
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
          v-if="activeLine"
          class="active-line-text"
        >
          执行行：{{ activeLine }}
        </span>
      </div>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'
import { Moon, Sun } from 'lucide-vue-next'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type {
  CodeLanguage,
  LanguageInfo,
} from '@/features/algorithm-visualization/types'

type EditorTheme = 'dark' | 'light'

const props = defineProps<{
  modelValue: string
  language: CodeLanguage
  languages: LanguageInfo[]
  disabled?: boolean
  readonly?: boolean
  title?: string
  activeLine?: number
  currentStepMessage?: string
  currentStepIndex?: number
  eventCount?: number
  generating?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [code: string]
  'update:language': [language: CodeLanguage]
}>()

// Monaco 编辑器实例引用与状态
const editorContainer = ref<HTMLDivElement | null>(null)
const editorTheme = ref<EditorTheme>('dark')
const editorCursorLine = ref(1)
const editorCursorColumn = ref(1)

let editor: monaco.editor.IStandaloneCodeEditor | null = null
let decorationsCollection: monaco.editor.IEditorDecorationsCollection | null = null
// 内部变更标志，防止外部 modelValue 同步时的循环触发
let internalChange = false

// 编辑器语言双向绑定
const editorLanguageModel = computed({
  get: () => props.language,
  set: (value: CodeLanguage) => emit('update:language', value),
})

// 语言显示标签、文件扩展名、编辑器主题 CSS 类名
const editorLanguageLabel = computed(() => {
  return getLanguageLabel(props.language)
})

const editorExtension = computed(() => {
  return props.languages.find((item) => item.key === props.language)?.extension ?? mapCodeLanguage(props.language)
})

// 编辑器 CSS 类、Monaco 主题名
const editorThemeClass = computed(() => {
  return editorTheme.value === 'dark' ? 'theme-dark' : 'theme-light'
})
const monacoThemeName = computed(() => {
  return editorTheme.value === 'dark' ? 'algorithm-midnight' : 'algorithm-sunlit'
})

// 主题切换按钮标题
const themeToggleTitle = computed(() => {
  return editorTheme.value === 'dark' ? '切换到亮色编辑器' : '切换到暗色编辑器'
})

// 行数和字符数统计
const editorLineCount = computed(() => {
  return props.modelValue ? props.modelValue.split('\n').length : 0
})
const editorCharCount = computed(() => props.modelValue.length)

// 底部运行过程提示文本
const traceReadoutText = computed(() => {
  if (props.generating) return '正在生成可视化轨迹'
  if (!props.eventCount || props.currentStepIndex === undefined) return ''

  const stepText = `步骤 ${props.currentStepIndex + 1} / ${props.eventCount}`
  const message = props.currentStepMessage?.trim()
  return message ? `${stepText} · ${message}` : stepText
})

// 挂载后创建 Monaco 编辑器实例
onMounted(async () => {
  await nextTick()
  createEditor()
})

// 销毁前清理编辑器实例和装饰
onBeforeUnmount(() => {
  decorationsCollection?.clear()
  decorationsCollection = null
  editor?.dispose()
  editor = null
})

// 外部代码变更同步到编辑器（跳过内部变更）
watch(
  () => props.modelValue,
  (newCode) => {
    if (!editor || internalChange) return
    const currentValue = editor.getValue()
    if (currentValue !== newCode) {
      const position = editor.getPosition()
      editor.setValue(newCode)
      if (position) editor.setPosition(position)
    }
  },
)

// 编辑器语言切换
watch(
  () => props.language,
  (newLanguage) => {
    const model = editor?.getModel()
    if (!model) return
    monaco.editor.setModelLanguage(model, mapCodeLanguage(newLanguage))
  },
)

// 运行中禁用编辑
watch(
  () => props.disabled,
  (loading) => {
    editor?.updateOptions({ readOnly: Boolean(loading) || Boolean(props.readonly) })
  },
)

// 高亮当前执行行
watch(
  () => props.activeLine,
  (line) => {
    updateActiveLine(line)
  },
)

// 编辑器主题切换
watch(
  () => editorTheme.value,
  () => {
    monaco.editor.setTheme(monacoThemeName.value)
    updateActiveLine(props.activeLine)
  },
)

// 创建 Monaco 编辑器并绑定事件
function createEditor() {
  if (!editorContainer.value) return

  defineMonacoThemes()

  editor = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: mapCodeLanguage(props.language),
    theme: monacoThemeName.value,
    readOnly: Boolean(props.disabled) || Boolean(props.readonly),
    automaticLayout: true,

    fontSize: 14,
    lineHeight: 24,
    fontFamily: 'JetBrains Mono, Fira Code, Menlo, Monaco, Consolas, "Courier New", monospace',
    fontLigatures: true,

    minimap: { enabled: false },
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
    parameterHints: { enabled: true },
    hover: { enabled: true },

    formatOnType: false,
    formatOnPaste: false,
    wordBasedSuggestions: 'off',

    matchBrackets: 'always',
    bracketPairColorization: { enabled: true },
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
    emit('update:modelValue', editor.getValue())

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

  updateActiveLine(props.activeLine)
}

// 注册自定义 Monaco 暗色/亮色主题
function defineMonacoThemes() {
  monaco.editor.defineTheme('algorithm-midnight', {
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

  monaco.editor.defineTheme('algorithm-sunlit', {
    base: 'vs',
    inherit: true,
    rules: [
      { token: '', foreground: '173b42', background: 'fcffff' },
      { token: 'comment', foreground: '6b858a' },
      { token: 'keyword', foreground: '287b86' },
      { token: 'number', foreground: '329a82' },
      { token: 'string', foreground: 'c7922a' },
      { token: 'type', foreground: '205f67' },
      { token: 'function', foreground: '315e97' },
      { token: 'variable', foreground: '173b42' },
    ],
    colors: {
      'editor.background': '#fcffff',
      'editor.foreground': '#173b42',
      'editorGutter.background': '#fcffff',
      'editorLineNumber.foreground': '#8da4a8',
      'editorLineNumber.activeForeground': '#173b42',
      'editorCursor.foreground': '#173b42',
      'editor.lineHighlightBackground': '#eaf5f4',
      'editor.selectionBackground': '#b9dedc',
      'editor.inactiveSelectionBackground': '#ddecec',
      'editorIndentGuide.background1': '#DDEDEC',
      'editorIndentGuide.activeBackground1': '#9fd2d0',
      'scrollbarSlider.background': '#9fd2d066',
      'scrollbarSlider.hoverBackground': '#6b858a66',
      'scrollbarSlider.activeBackground': '#58747a99',
    },
  })
}

// 切换编辑器暗色/亮色主题
function toggleEditorTheme() {
  editorTheme.value = editorTheme.value === 'dark' ? 'light' : 'dark'
}

// 将后端语言标识映射到 Monaco 编辑器语言 ID
function mapCodeLanguage(value: CodeLanguage): string {
  const map: Partial<Record<CodeLanguage, string>> = {
    python: 'python',
  }

  return map[value] ?? 'plaintext'
}

// 获取语言显示标签（带降级映射）
function getLanguageLabel(value: CodeLanguage | string) {
  const matched = props.languages.find((item) => item.key === value)

  if (matched?.label) return matched.label

  const fallbackMap: Record<string, string> = {
    python: 'Python',
  }

  return fallbackMap[String(value)] ?? String(value)
}

// 更新编辑器中的代码行高亮（当前执行的步骤行）
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
          color: editorTheme.value === 'dark' ? '#46B8B4' : '#205F67',
          position: monaco.editor.OverviewRulerLane.Full,
        },
      },
    },
  ])

  editor.revealLineInCenterIfOutsideViewport(line)
}
</script>

<style scoped>
.code-input-panel {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: var(--radius-sm);
}

.code-input-panel.theme-dark {
  background: #171717;
  color: #e5e7eb;
}

.code-input-panel.theme-light {
  background: var(--color-surface);
  color: var(--color-text-strong);
}

.editor-header {
  min-height: 46px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 12px;
}

.theme-dark .editor-header {
  border-bottom: 1px solid #1f2937;
  background: #0f172a;
}

.theme-light .editor-header {
  border-bottom: 1px solid var(--color-border-light);
  background: var(--color-surface);
}

.editor-left,
.editor-right {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.editor-tab {
  height: 46px;
  display: inline-flex;
  align-items: center;
  padding: 0 12px;
  border-bottom: 2px solid currentColor;
  font-size: 13px;
  font-weight: 900;
}

.theme-dark .editor-tab {
  color: #ffffff;
}

.theme-light .editor-tab {
  color: var(--color-text-strong);
}

.editor-language-trigger {
  width: 132px;
  height: 32px;
  border-radius: var(--radius-sm) !important;
  font-size: 12px;
  font-weight: 900;
}

.theme-dark .editor-language-trigger {
  border: 1px solid #334155;
  background: #111827;
  color: #e5e7eb;
}

.theme-light .editor-language-trigger {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-strong);
}

.editor-language-content {
  border-radius: var(--radius-sm) !important;
}

.editor-file-pill {
  height: 24px;
  display: inline-flex;
  align-items: center;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 800;
}

.theme-dark .editor-file-pill {
  background: #111827;
  color: #94a3b8;
}

.theme-light .editor-file-pill {
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
}

.theme-toggle {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.theme-dark .theme-toggle {
  border: 1px solid #334155;
  background: #111827;
  color: #facc15;
}

.theme-light .theme-toggle {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-strong);
}

.theme-toggle:hover {
  transform: translateY(-1px);
}

.theme-icon {
  width: 16px;
  height: 16px;
}

.editor-main {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.monaco-container {
  width: 100%;
  height: 100%;
  border-radius: 0;
}

.editor-statusbar {
  min-height: 32px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 800;
}

.trace-readout {
  min-height: 34px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  border-top: 1px solid;
  font-size: 12px;
  font-weight: 800;
}

.theme-dark .trace-readout {
  border-top-color: #1f2937;
  background: #101827;
  color: #cbd5e1;
}

.theme-light .trace-readout {
  border-top-color: var(--color-border-light);
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
}

.trace-readout-label {
  flex: 0 0 auto;
  color: var(--color-primary);
  font-weight: 900;
}

.trace-readout-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.theme-dark .editor-statusbar {
  border-top: 1px solid #1f2937;
  background: #0f172a;
  color: #94a3b8;
}

.theme-light .editor-statusbar {
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg);
  color: var(--color-text-muted);
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
  color: var(--color-primary);
}

:deep(.active-line-dark) {
  background: rgba(70, 184, 180, 0.14) !important;
  border-left: 3px solid var(--color-primary);
}

:deep(.active-line-light) {
  background: rgba(70, 184, 180, 0.13) !important;
  border-left: 3px solid var(--color-primary);
}

:deep(.active-line-gutter-dark) {
  background: rgba(70, 184, 180, 0.2) !important;
}

:deep(.active-line-gutter-light) {
  background: rgba(70, 184, 180, 0.16) !important;
}

:deep(.monaco-editor),
:deep(.monaco-editor-background),
:deep(.monaco-scrollable-element) {
  border-radius: 0 !important;
}

@media (max-width: 768px) {
  .editor-header {
    min-height: 46px;
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
    min-height: 32px;
    align-items: flex-start;
    flex-direction: column;
    padding: 7px 10px;
  }

  .trace-readout {
    align-items: flex-start;
    flex-direction: column;
    gap: 4px;
    padding: 7px 10px;
  }
}
</style>
