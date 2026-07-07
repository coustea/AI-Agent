<template>
  <section class="code-input-panel">
    <div class="panel-header">
      <div class="header-left">
        <h2>代码编辑</h2>
        <span v-if="activeLine" class="line-indicator">
          执行到第 {{ activeLine }} 行
        </span>
      </div>
    </div>

    <div class="code-editor-shell">
      <div ref="editorContainer" class="code-editor-monaco" />
    </div>

    <div class="panel-footer">
      <span class="language-hint">{{ languageLabel }}</span>
      <div class="footer-actions">
        <Button
          variant="outline"
          size="sm"
          class="reset-btn"
          @click="$emit('reset-template')"
        >
          <RotateCcw class="btn-icon" />
          重置模板
        </Button>
        <Button
          class="run-btn"
          :disabled="loading || !code.trim()"
          @click="$emit('run')"
        >
          <Play v-if="!loading" class="btn-icon" />
          <Loader2 v-else class="btn-icon spin" />
          {{ loading ? '运行中...' : '运行可视化' }}
        </Button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'
import { Button } from '@/components/ui/button'
import { Play, RotateCcw, Loader2 } from 'lucide-vue-next'
import type { CodeLanguage } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  code: string
  language: CodeLanguage
  loading: boolean
  activeLine?: number
}>()

const emit = defineEmits<{
  'update:code': [value: string]
  'run': []
  'reset-template': []
  dirty: []
}>()

const editorContainer = ref<HTMLDivElement | null>(null)
let editor: monaco.editor.IStandaloneCodeEditor | null = null
let decorationsCollection: monaco.editor.IEditorDecorationsCollection | null = null

const languageLabel = computed(() => {
  const map: Record<CodeLanguage, string> = {
    python: 'Python',
    javascript: 'JavaScript',
    cpp: 'C++',
    java: 'Java',
    c: 'C',
  }
  return map[props.language] ?? props.language
})

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
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.panel-header h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-strong);
}

.line-indicator {
  font-size: 12px;
  color: var(--color-primary);
  font-weight: 500;
}

.code-editor-shell {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.code-editor-monaco {
  width: 100%;
  height: 100%;
  border: none;
}

.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-top: 1px solid var(--color-border);
  flex-shrink: 0;
}

.language-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
}

.footer-actions {
  display: flex;
  gap: 8px;
}

.run-btn {
  height: 32px;
  padding: 0 16px;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  border: none;
}

.run-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.reset-btn {
  height: 32px;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: #ffffff;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.reset-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-text);
}

.btn-icon {
  width: 14px;
  height: 14px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

:deep(.monaco-active-line-highlight) {
  background-color: rgba(70, 184, 180, 0.08) !important;
  border-left: 3px solid var(--color-primary) !important;
}

@media (max-width: 1100px) {
  .code-input-panel {
    min-height: 400px;
  }
}
</style>
