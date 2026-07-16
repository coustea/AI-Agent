<template>
  <section class="code-input-panel">
    <header class="editor-header">
      <div class="editor-left">
        <span class="editor-tab">{{ title ?? '代码' }}</span>

        <span class="editor-language-badge">Python</span>
      </div>

      <div class="editor-right">
        <span class="editor-file-pill">{{ editorExtension }}</span>
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
import type {
  CodeLanguage,
  LanguageInfo,
} from '@/features/algorithm-visualization/types'

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
}>()

// Monaco 编辑器实例引用与状态
const editorContainer = ref<HTMLDivElement | null>(null)
const editorCursorLine = ref(1)
const editorCursorColumn = ref(1)

let editor: monaco.editor.IStandaloneCodeEditor | null = null
let decorationsCollection: monaco.editor.IEditorDecorationsCollection | null = null

// 语言显示标签、文件扩展名
const editorLanguageLabel = computed(() => {
  return getLanguageLabel(props.language)
})

const editorExtension = computed(() => {
  return props.languages.find((item) => item.key === props.language)?.extension ?? mapCodeLanguage(props.language)
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
    if (!editor) return
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

// 创建 Monaco 编辑器并绑定事件
function createEditor() {
  if (!editorContainer.value) return

  defineMonacoThemes()

  editor = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: mapCodeLanguage(props.language),
    theme: 'algorithm-sunlit',
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
    emit('update:modelValue', editor.getValue())
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

// 注册与页面一致的浅色 Monaco 主题
function defineMonacoThemes() {
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
        className: 'active-line-light',
        linesDecorationsClassName: 'active-line-gutter-light',
        overviewRuler: {
          color: '#205F67',
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
  padding: 0 4px;
  color: var(--color-text-strong);
  font-size: 13px;
  font-weight: 800;
}

.editor-language-badge {
  height: 26px;
  display: inline-flex;
  align-items: center;
  padding: 0 9px;
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: 800;
}

.editor-file-pill {
  height: 24px;
  display: inline-flex;
  align-items: center;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 11px;
  border: 1px solid var(--color-border-light);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-weight: 800;
}

.editor-main {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.monaco-container {
  width: 100%;
  height: 100%;
  background: var(--color-surface);
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
  border-top: 1px solid var(--color-border-light);
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 800;
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

.editor-statusbar {
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

:deep(.active-line-light) {
  background: rgba(70, 184, 180, 0.13) !important;
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
    padding: 0 10px;
  }

  .editor-left,
  .editor-right {
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
