<template>
  <div class="algorithm-workspace">
    <header class="workspace-topbar">
      <div class="topbar-left">
        <button class="topbar-btn" type="button" @click="$emit('back')">返回题库</button>
        <div>
          <span class="topbar-kicker">Algorithm Lab</span>
          <h1>{{ question.subject }} · 算法可视化工作台</h1>
        </div>
      </div>
      <div class="topbar-status">
        <span :class="['status-chip', running ? 'running' : 'idle']">{{ running ? '运行中' : '待运行' }}</span>
      </div>
    </header>

    <main class="workspace-main">
      <section class="workspace-left">
        <article class="work-card">
          <div class="card-head">
            <span class="card-kicker">题目</span>
            <div class="question-tags">
              <span>{{ question.type }}</span>
              <span>{{ question.subject }}</span>
              <span v-if="question.difficulty">{{ question.difficulty }}</span>
            </div>
          </div>
          <div class="question-stem" v-html="renderInline(question.content)"></div>
          <div v-if="question.knowledge_points?.length" class="knowledge-points">
            <span v-for="point in question.knowledge_points" :key="point">{{ point }}</span>
          </div>
        </article>

        <article class="work-card">
          <div class="card-head">
            <span class="card-kicker">代码编辑器</span>
            <select v-model="selectedLanguage" class="language-select">
              <option value="javascript">JavaScript</option>
              <option value="python">Python</option>
              <option value="cpp">C++</option>
            </select>
          </div>
          <textarea v-model="userCode" class="code-editor" spellcheck="false"></textarea>
        </article>

        <article class="work-card compact">
          <div class="field-group">
            <label>测试输入</label>
            <textarea v-model="customInput" class="field-area" rows="4" placeholder="输入测试数据"></textarea>
          </div>

          <div class="workspace-actions">
            <button class="run-btn" type="button" :disabled="running" @click="runVisualization">
              {{ running ? '运行中...' : '运行并可视化' }}
            </button>
          </div>

          <div class="field-group">
            <label>运行结果</label>
            <div class="result-panel">
              <p v-if="runError" class="result-error">{{ runError }}</p>
              <pre v-else>{{ runOutput || '运行后将在这里显示结果摘要。' }}</pre>
            </div>
          </div>
        </article>
      </section>

      <section class="workspace-right">
        <div class="visual-panel">
          <AlgorithmVisualizer :question="question" :trace="visualTrace" />
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import AlgorithmVisualizer from '@/features/question-bank/components/AlgorithmVisualizer.vue'
import { buildTraceForQuestion, detectAlgorithmCategory } from '@/features/question-bank/utils/algorithmAdapters'
import { buildDefaultCodeTemplate } from '@/features/question-bank/utils/algorithmTemplates'
import type { AlgorithmTrace } from '@/features/question-bank/utils/algorithmTrace'

interface Question {
  id: string
  subject: string
  type: string
  content: string
  difficulty?: string | null
  answer: string
  analysis: string
  knowledge_points: string[]
  tags?: string[]
}

const props = defineProps<{
  question: Question
}>()

defineEmits<{
  (e: 'back'): void
}>()

const selectedLanguage = ref('javascript')
const userCode = ref('')
const customInput = ref('')
const running = ref(false)
const runError = ref('')
const runOutput = ref('')
const visualTrace = ref<AlgorithmTrace | null>(null)

watch(
  () => props.question,
  (question) => {
    const category = detectAlgorithmCategory(question)
    userCode.value = buildDefaultCodeTemplate(category)
    customInput.value = ''
    runError.value = ''
    runOutput.value = ''
    visualTrace.value = null
  },
  { immediate: true },
)

async function runVisualization() {
  running.value = true
  runError.value = ''

  try {
    const trace = buildTraceForQuestion(props.question, customInput.value, userCode.value)
    visualTrace.value = trace
    runOutput.value = `已生成 ${trace.steps.length} 个可视化步骤，正在右侧播放。`
  } catch (error) {
    runError.value = error instanceof Error ? error.message : '生成可视化失败'
  } finally {
    running.value = false
  }
}

function renderInline(text: string) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.algorithm-workspace {
  width: min(1480px, 100%);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.workspace-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 12px 0 14px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.topbar-btn {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(203, 213, 225, 0.92);
  background: #fff;
  color: #334155;
  font-weight: 700;
  cursor: pointer;
}

.topbar-kicker {
  display: block;
  color: #2563eb;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.workspace-topbar h1 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 20px;
  font-weight: 900;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.status-chip.idle {
  background: rgba(226, 232, 240, 0.92);
  color: #475569;
}

.status-chip.running {
  background: rgba(219, 234, 254, 0.92);
  color: #2563eb;
}

.workspace-main {
  display: grid;
  grid-template-columns: 420px minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.workspace-left,
.workspace-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.work-card,
.visual-panel {
  padding: 18px;
  border-radius: 18px;
  background: #fff;
  border: 1px solid rgba(226, 232, 240, 0.92);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.card-kicker {
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.question-tags,
.knowledge-points {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.question-tags span,
.knowledge-points span {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(239, 246, 255, 0.92);
  color: #2563eb;
  font-size: 11px;
  font-weight: 700;
}

.question-stem {
  color: #1e293b;
  font-size: 14px;
  line-height: 1.8;
}

.language-select,
.field-area,
.run-btn {
  min-height: 40px;
  border-radius: 12px;
  font: inherit;
}

.language-select,
.field-area {
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #0f172a;
  outline: none;
}

.language-select {
  padding: 0 10px;
}

.code-editor {
  width: 100%;
  min-height: 280px;
  padding: 16px;
  border: 1px solid rgba(15, 23, 42, 0.9);
  border-radius: 16px;
  background: #0f172a;
  color: #e2e8f0;
  font: 13px/1.7 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  box-sizing: border-box;
  resize: vertical;
}

.work-card.compact {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-group label {
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.field-area {
  width: 100%;
  padding: 12px 14px;
  box-sizing: border-box;
  resize: vertical;
}

.workspace-actions {
  display: flex;
}

.run-btn {
  padding: 0 16px;
  border: 1px solid #0f172a;
  background: #0f172a;
  color: #fff;
  font-weight: 800;
  cursor: pointer;
}

.run-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.result-panel {
  min-height: 92px;
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid rgba(226, 232, 240, 0.92);
}

.result-panel pre {
  margin: 0;
  white-space: pre-wrap;
  color: #334155;
  font: inherit;
  line-height: 1.7;
}

.result-error {
  margin: 0;
  color: #dc2626;
  line-height: 1.7;
}

.visual-panel {
  min-height: 620px;
}

@media (max-width: 1100px) {
  .workspace-main {
    grid-template-columns: 1fr;
  }
}
</style>
