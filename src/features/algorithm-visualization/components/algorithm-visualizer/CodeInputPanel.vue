<template>
  <section class="code-input-panel">
    <div class="panel-header">
      <div class="flex items-center gap-2">
        <h2>代码编辑</h2>
        <span v-if="activeLine" class="line-indicator">执行到第 {{ activeLine }} 行</span>
      </div>

      <div class="flex items-center gap-2">
        <!-- 算法选择 -->
        <Select v-model="localAlgorithm">
          <SelectTrigger class="h-8 text-xs min-w-[120px] bg-white">
            <SelectValue placeholder="选择算法" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="alg in algorithms" :key="alg.key" :value="alg.key">
              {{ alg.name }}
            </SelectItem>
          </SelectContent>
        </Select>

        <!-- 语言选择 -->
        <Select v-model="localLanguage">
          <SelectTrigger class="h-8 text-xs min-w-[100px] bg-white">
            <SelectValue placeholder="选择语言" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem v-for="lang in languages" :key="lang.key" :value="lang.key">
              {{ lang.label }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>

    <div class="code-editor-shell">
      <div ref="editorContainer" class="code-editor-monaco" />
    </div>

    <div class="panel-actions">
      <Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs bg-white cursor-pointer" @click="$emit('reset-template')">
        <RotateCcw class="w-3.5 h-3.5" />
        重置模板
      </Button>

      <Button
        variant="default"
        size="sm"
        class="h-8 gap-1.5 text-xs ml-auto bg-blue-600 hover:bg-blue-700 text-white cursor-pointer"
        :disabled="loading || !code.trim()"
        @click="$emit('run')"
      >
        <Play class="w-3.5 h-3.5 fill-current" />
        {{ loading ? '运行中...' : '运行可视化' }}
      </Button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Play, RotateCcw } from 'lucide-vue-next'
import type { CodeLanguage, LanguageInfo, AlgorithmInfo } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  code: string
  language: CodeLanguage
  algorithm: string
  languages: LanguageInfo[]
  algorithms: AlgorithmInfo[]
  loading: boolean
  activeLine?: number
}>()

const emit = defineEmits<{
  'update:code': [value: string]
  'update:language': [value: CodeLanguage]
  'update:algorithm': [value: string]
  'reset-template': []
  'run': []
  dirty: []
}>()

const localLanguage = computed({
  get: () => props.language,
  set: (value: CodeLanguage) => {
    emit('update:language', value)
  },
})

const localAlgorithm = computed({
  get: () => props.algorithm,
  set: (value: string) => {
    emit('update:algorithm', value)
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
  border-radius: 4px;
  padding: 12px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 10px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  box-shadow: none;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f1f5f9;
}

.panel-header h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.panel-header p {
  margin: 2px 0 0;
  font-size: 11px;
  color: #64748b;
}

.language-select {
  height: 28px;
  padding: 0 6px;
  border-radius: 4px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #0f172a;
  outline: none;
  font-size: 12px;
}

.language-select:focus {
  border-color: #3b82f6;
}

.code-editor-shell {
  height: 100%;
  min-height: 0;
}

.line-indicator {
  color: #2563eb;
  font-weight: 600;
}

.code-editor-monaco {
  width: 100%;
  height: 100%;
  min-height: 0;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}

.panel-actions {
  display: flex;
  gap: 8px;
  padding-top: 4px;
}

.secondary-action {
  height: 28px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  background: #ffffff;
  color: #334155;
}

.secondary-action:hover {
  background: #f8fafc;
}

@media (max-width: 1100px) {
  .code-input-panel {
    min-height: 400px;
  }
}

:deep(.monaco-active-line-highlight) {
  background-color: rgba(37, 99, 235, 0.08) !important;
  border-left: 3px solid #2563eb !important;
}
</style>
