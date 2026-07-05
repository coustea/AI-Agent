<template>
  <section class="code-input-panel">
    <div class="panel-header">
      <div>
        <h2>代码输入</h2>
        <p>粘贴你想观察的算法代码。</p>
      </div>

      <select v-model="localLanguage" class="language-select">
        <option value="python">Python</option>
        <option value="java">Java</option>
        <option value="cpp">C++</option>
        <option value="c">C</option>
      </select>
    </div>

    <div class="code-editor-shell">
      <div class="editor-meta">
        <span>算法代码</span>
        <span class="line-indicator">{{ executionLabel }}</span>
      </div>

      <Editor
        :value="code"
        :language="monacoLanguage"
        theme="vs"
        :options="editorOptions"
        class="code-editor-monaco"
        @change="onEditorChange"
        @mount="handleEditorMount"
      />
    </div>

    <div class="data-input-block">
      <label for="algorithm-visualizer-input">运行数据</label>
      <textarea
        id="algorithm-visualizer-input"
        v-model="localInput"
        class="data-input"
        placeholder="例如：[5, 2, 8, 1, 3]"
      />
    </div>

    <div class="panel-actions">
      <button class="primary-action" :disabled="loading || !code.trim()" @click="$emit('generate')">
        {{ loading ? '生成中...' : '生成可视化' }}
      </button>
      <button class="secondary-action" @click="$emit('use-example')">
        使用示例
      </button>
      <button class="ghost-action" @click="$emit('reset-all')">
        重置
      </button>
      <button class="ghost-action" @click="$emit('clear')">
        清空
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Editor from '@guolao/vue-monaco-editor'
import type { CodeLanguage } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  code: string
  language: CodeLanguage
  input: string
  loading: boolean
  activeLine?: number
  finished: boolean
  executionLabel: string
}>()

const emit = defineEmits<{
  'update:code': [value: string]
  'update:language': [value: CodeLanguage]
  'update:input': [value: string]
  generate: []
  'use-example': []
  'reset-all': []
  clear: []
  dirty: []
}>()

const localLanguage = computed({
  get: () => props.language,
  set: (value: CodeLanguage) => {
    emit('update:language', value)
  },
})

const localInput = computed({
  get: () => props.input,
  set: (value: string) => {
    emit('update:input', value)
  },
})

// Monaco Editor instances
const editorRef = ref<any>(null)
const monacoRef = ref<any>(null)
const decorationsRef = ref<string[]>([])

const monacoLanguage = computed(() => {
  if (props.language === 'cpp') return 'cpp'
  if (props.language === 'c') return 'c'
  if (props.language === 'java') return 'java'
  if (props.language === 'python') return 'python'
  return 'python'
})

const editorOptions = {
  fontSize: 13,
  fontFamily: 'JetBrains Mono, Fira Code, Menlo, Monaco, Consolas, Courier New, monospace',
  automaticLayout: true,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  lineNumbers: 'on',
  roundedSelection: true,
  readOnly: false,
  renderLineHighlight: 'all',
  scrollbar: {
    verticalScrollbarSize: 8,
    horizontalScrollbarSize: 8,
  },
}

function handleEditorMount(editor: any, monaco: any) {
  editorRef.value = editor
  monacoRef.value = monaco
  updateLineHighlight(props.activeLine)
}

function onEditorChange(value: string | undefined) {
  if (value !== undefined && value !== props.code) {
    emit('update:code', value)
    emit('dirty')
  }
}

function updateLineHighlight(line: number | undefined) {
  const editor = editorRef.value
  const monaco = monacoRef.value
  if (!editor || !monaco) return

  if (!line || line <= 0 || props.finished) {
    decorationsRef.value = editor.deltaDecorations(decorationsRef.value, [])
    return
  }

  decorationsRef.value = editor.deltaDecorations(decorationsRef.value, [
    {
      range: new monaco.Range(line, 1, line, 1),
      options: {
        isWholeLine: true,
        className: 'monaco-active-line-highlight',
      },
    },
  ])

  editor.revealLineInCenterIfOutsideViewport(line)
}

watch(
  () => [props.activeLine, props.finished],
  ([line]) => {
    updateLineHighlight(line as number)
  },
)
</script>

<style scoped>
.code-input-panel {
  height: 100%;
  min-height: 0;
  border-radius: 22px;
  padding: 16px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) 130px auto;
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

.language-select:focus,
.data-input:focus {
  border-color: rgba(37, 99, 235, 0.7);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.data-input-block {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.data-input-block label {
  font-size: 12px;
  font-weight: 650;
  color: #334155;
}

.data-input {
  flex: 1;
  min-height: 0;
  resize: none;
  border: 1px solid #dbe3ef;
  border-radius: 14px;
  padding: 10px 12px;
  background: #f8fafc;
  color: #0f172a;
  font-size: 13px;
  outline: none;
}

.panel-actions {
  display: grid;
  grid-template-columns: 1fr auto auto auto;
  gap: 8px;
}

.primary-action,
.secondary-action,
.ghost-action {
  height: 38px;
  border: none;
  border-radius: 12px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
}

.primary-action {
  background: #2563eb;
  color: #ffffff;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.22);
}

.primary-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}

.secondary-action {
  background: #eff6ff;
  color: #1d4ed8;
}

.ghost-action {
  background: #f8fafc;
  color: #475569;
  border: 1px solid #e2e8f0;
}

@media (max-width: 1100px) {
  .code-input-panel {
    min-height: 620px;
  }
}

@media (max-width: 640px) {
  .panel-actions {
    grid-template-columns: 1fr;
  }
}

/* Monaco active line highlight */
:deep(.monaco-active-line-highlight) {
  background-color: rgba(37, 99, 235, 0.12) !important;
  border-left: 3.5px solid #2563eb !important;
}
</style>
