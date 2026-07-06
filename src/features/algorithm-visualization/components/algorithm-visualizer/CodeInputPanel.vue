<template>
  <section class="code-input-panel">
    <div class="panel-header">
      <div>
        <h2>代码编辑</h2>
        <p>编辑算法模板代码后点击运行可视化。</p>
      </div>

      <select v-model="localLanguage" class="language-select">
        <option value="python">Python</option>
        <option value="javascript">JavaScript</option>
        <option value="cpp">C++</option>
        <option value="java">Java</option>
        <option value="c">C</option>
      </select>
    </div>

    <div class="code-editor-shell">
      <div class="editor-meta">
        <span>算法代码</span>
        <span v-if="activeLine" class="line-indicator">执行到第 {{ activeLine }} 行</span>
      </div>

      <div ref="editorContainer" class="code-editor-monaco" />
    </div>

    <div class="panel-actions">
      <button class="secondary-action" @click="$emit('reset-template')">
        重置模板
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'
import type { CodeLanguage } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  code: string
  language: CodeLanguage
  loading: boolean
  activeLine?: number
}>()

const emit = defineEmits<{
  'update:code': [value: string]
  'update:language': [value: CodeLanguage]
  'reset-template': []
  dirty: []
}>()

const localLanguage = computed({
  get: () => props.language,
  set: (value: CodeLanguage) => {
    emit('update:language', value)
  },
})

const editorContainer = ref<HTMLDivElement | null>(null)
let editor: monaco.editor.IStandaloneCodeEditor | null = null
let decorationsCollection: monaco.editor.IEditorDecorationsCollection | null = null

function mapLanguage(lang: CodeLanguage): string {
  const map: Record<CodeLanguage, string> = {
    python: 'python',
    javascript: 'javascript',
    cpp: 'cpp',
    java: 'java',
    c: 'c',
  }
  return map[lang] ?? 'plaintext'
}

function configureNoCompletion() {
  const langs = monaco.languages as any
  if (langs.javascriptDefaults) {
    langs.javascriptDefaults.setCompilerOptions({ noLib: true, allowNonTsExtensions: true })
    langs.javascriptDefaults.setDiagnosticsOptions({ noSemanticValidation: true, noSyntaxValidation: true })
  }
  if (langs.typescriptDefaults) {
    langs.typescriptDefaults.setCompilerOptions({ noLib: true, allowNonTsExtensions: true })
    langs.typescriptDefaults.setDiagnosticsOptions({ noSemanticValidation: true, noSyntaxValidation: true })
  }
}

onMounted(() => {
  if (!editorContainer.value) return

  configureNoCompletion()

  editor = monaco.editor.create(editorContainer.value, {
    value: props.code,
    language: mapLanguage(props.language),
    theme: 'vs',
    fontSize: 13,
    fontFamily: 'JetBrains Mono, Fira Code, Menlo, Monaco, Consolas, Courier New, monospace',
    automaticLayout: true,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    lineNumbers: 'on',
    readOnly: false,
    renderLineHighlight: 'none',
    scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
    quickSuggestions: false,
    suggestOnTriggerCharacters: false,
    parameterHints: { enabled: false },
    hover: { enabled: false },
    formatOnType: false,
    formatOnPaste: false,
    autoIndent: 'none',
    folding: false,
    wordBasedSuggestions: 'off',
    matchBrackets: 'always',
  })

  editor.onDidChangeModelContent(() => {
    if (editor) {
      emit('update:code', editor.getValue())
      emit('dirty')
    }
  })

  decorationsCollection = editor.createDecorationsCollection()
  updateLineHighlight(props.activeLine)
})

watch(() => props.code, (newCode) => {
  if (editor && editor.getValue() !== newCode) {
    editor.setValue(newCode)
  }
})

watch(() => props.language, (lang) => {
  if (!editor) return
  const model = editor.getModel()
  if (model) {
    monaco.editor.setModelLanguage(model, mapLanguage(lang))
  }
})

watch(() => props.activeLine, (line) => {
  updateLineHighlight(line)
})

function updateLineHighlight(line: number | undefined) {
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
        className: 'monaco-active-line-highlight',
        overviewRuler: {
          color: '#2563eb',
          position: monaco.editor.OverviewRulerLane.Full,
        },
      },
    },
  ])

  editor.revealLineInCenterIfOutsideViewport(line)
}

onBeforeUnmount(() => {
  if (editor) {
    editor.dispose()
    editor = null
  }
  decorationsCollection = null
})
</script>

<style scoped>
.code-input-panel {
  height: 100%;
  min-height: 0;
  border-radius: 22px;
  padding: 16px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 12px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.panel-header h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 720;
  color: #0f172a;
}

.panel-header p {
  margin: 5px 0 0;
  font-size: 12px;
  color: #64748b;
}

.language-select {
  height: 34px;
  padding: 0 10px;
  border-radius: 10px;
  border: 1px solid #dbe3ef;
  background: #f8fafc;
  color: #0f172a;
  outline: none;
}

.language-select:focus {
  border-color: rgba(37, 99, 235, 0.7);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.code-editor-shell {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 10px;
}

.editor-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: #475569;
  font-size: 12px;
  font-weight: 650;
}

.line-indicator {
  color: #2563eb;
}

.code-editor-monaco {
  width: 100%;
  height: 100%;
  min-height: 0;
  border: 1px solid #dbe3ef;
  border-radius: 16px;
  overflow: hidden;
}

.panel-actions {
  display: flex;
  gap: 8px;
}

.secondary-action {
  height: 36px;
  border: none;
  border-radius: 12px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  background: #eff6ff;
  color: #1d4ed8;
}

@media (max-width: 1100px) {
  .code-input-panel {
    min-height: 480px;
  }
}

@media (max-width: 640px) {
  .panel-actions {
    flex-direction: column;
  }
}

:deep(.monaco-active-line-highlight) {
  background-color: rgba(37, 99, 235, 0.12) !important;
  border-left: 3.5px solid #2563eb !important;
}
</style>
