<template>
  <div class="algorithm-workspace">
    <main class="algorithm-main">
      <section class="visual-area">
        <div class="visual-panel">
          <AlgorithmVisualizer
            v-if="visualTrace"
            :trace="visualTrace"
            :show-code-panel="false"
            :show-playback-controls="false"
            :auto-play="true"
          />

          <div v-else-if="!runError" class="visual-empty">
            <strong>等待运行</strong>
            <p>在右侧输入代码，点击“生成可视化”后查看执行过程。</p>
          </div>

          <div v-else class="visual-error">
            <strong>运行失败</strong>
            <p>{{ runError }}</p>
          </div>
        </div>
      </section>

      <aside class="code-side">
        <section class="code-panel-box">
          <div class="code-panel-head">
            <div class="code-panel-head-main">
              <div>
                <span class="panel-kicker">Code Editor</span>
                <h3>代码输入</h3>
              </div>
            </div>

            <div class="code-actions">
              <select v-model="selectedLanguage" class="language-select">
                <option value="javascript">JavaScript</option>
                <option value="python">Python</option>
                <option value="cpp">C++</option>
              </select>

              <button
                class="run-visual-btn"
                type="button"
                :disabled="running || !userCode.trim()"
                @click="runVisualization"
              >
                {{ running ? '生成中...' : visualTrace ? '重新生成' : '生成可视化' }}
              </button>
            </div>
          </div>

          <textarea
            v-model="userCode"
            class="code-editor"
            spellcheck="false"
            placeholder="请输入你的算法代码"
          ></textarea>
        </section>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import AlgorithmVisualizer from '@/features/algorithm-visualization/components/AlgorithmVisualizer.vue'

type TraceTone = 'default' | 'active' | 'swap' | 'sorted' | 'visited' | 'left' | 'right'

interface AlgorithmTrace {
  title: string
  description: string
  codeLines: string[]
  steps: Array<{
    caption: string
    message: string
    activeLine?: number
    state: {
      kind: 'array'
      items: Array<{ id: string; value: number; tone?: TraceTone }>
      pointers?: Array<{ index: number; label: string; tone?: 'accent' | 'success' | 'warning' }>
    }
  }>
}

const selectedLanguage = ref('javascript')
const userCode = ref('')
const running = ref(false)
const runError = ref('')
const visualTrace = ref<AlgorithmTrace | null>(null)

watch(
  () => selectedLanguage.value,
  () => {
    userCode.value = buildDefaultCodeTemplate()
    runError.value = ''
    visualTrace.value = null
  },
  { immediate: true },
)

async function runVisualization() {
  if (!userCode.value.trim()) return

  running.value = true
  runError.value = ''

  try {
    visualTrace.value = buildPreviewTrace(userCode.value)
  } catch (error) {
    runError.value = error instanceof Error ? error.message : '生成预览失败'
  } finally {
    running.value = false
  }
}

function buildDefaultCodeTemplate() {
  if (selectedLanguage.value === 'python') {
    return `def solve(nums):
    # 后续可接入你的代码执行服务，返回可视化 trace
    return nums

solve([5, 3, 8, 2, 6])`
  }

  if (selectedLanguage.value === 'cpp') {
    return `#include <vector>
using namespace std;

vector<int> solve(vector<int> nums) {
  // 后续可接入你的代码执行服务，返回可视化 trace
  return nums;
}`
  }

  return `function solve(nums) {
  // 后续可接入你的代码执行服务，返回可视化 trace
  return nums
}

solve([5, 3, 8, 2, 6])`
}

function buildPreviewTrace(code: string): AlgorithmTrace {
  const values = [5, 3, 8, 2, 6]
  const sorted = [...values].sort((a, b) => a - b)

  return {
    title: '算法执行预览',
    description: '当前页面仅保留工作区展示，后续可由外部执行逻辑注入真实 trace。',
    codeLines: code.split('\n'),
    steps: [
      {
        caption: '初始化',
        message: '读取输入数据，准备执行。',
        activeLine: 1,
        state: {
          kind: 'array',
          items: values.map((value, index) => ({ id: `init-${index}`, value })),
        },
      },
      {
        caption: '比较',
        message: '示例高亮当前比较位置。',
        activeLine: 2,
        state: {
          kind: 'array',
          items: values.map((value, index) => ({
            id: `compare-${index}`,
            value,
            tone: index === 0 || index === 1 ? 'active' : 'default',
          })),
          pointers: [
            { index: 0, label: 'i', tone: 'accent' },
            { index: 1, label: 'j', tone: 'warning' },
          ],
        },
      },
      {
        caption: '完成',
        message: '生成完成态，等待后续接入真实运行结果。',
        activeLine: 3,
        state: {
          kind: 'array',
          items: sorted.map((value, index) => ({ id: `sorted-${index}`, value, tone: 'sorted' })),
          pointers: [{ index: sorted.length - 1, label: 'done', tone: 'success' }],
        },
      },
    ],
  }
}

</script>

<style scoped>
.algorithm-workspace {
  position: relative;
  width: min(1480px, 100%);
  height: calc(100vh - 96px);
  min-height: 660px;
  margin: 0 auto;
  overflow: hidden;
}

.algorithm-main {
  height: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 460px);
  gap: 16px;
}

.visual-area {
  position: relative;
  min-width: 0;
  height: 100%;
}

.visual-panel {
  height: 100%;
  padding: 16px;
  border-radius: 20px;
  background: #ffffff;
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

.code-side {
  min-width: 0;
  height: 100%;
  display: flex;
}

.code-panel-box {
  min-width: 0;
  width: 100%;
  border-radius: 20px;
  background: #ffffff;
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05);
  overflow: hidden;
}

.code-panel-box {
  display: flex;
  flex-direction: column;
}

.code-panel-head {
  height: 58px;
  padding: 0 14px 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
}

.code-panel-head-main {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.panel-kicker {
  display: block;
  color: #2563eb;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.code-panel-head h3 {
  margin: 3px 0 0;
  color: #0f172a;
  font-size: 15px;
  font-weight: 900;
}

.code-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.language-select {
  height: 34px;
  padding: 0 10px;
  border-radius: 10px;
  border: 1px solid rgba(203, 213, 225, 0.95);
  background: #ffffff;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
  outline: none;
}

.run-visual-btn {
  height: 34px;
  padding: 0 14px;
  border-radius: 10px;
  border: 1px solid #0f172a;
  background: #0f172a;
  color: #ffffff;
  font-size: 12px;
  font-weight: 900;
  cursor: pointer;
}

.run-visual-btn:hover:not(:disabled) {
  background: #1e293b;
  border-color: #1e293b;
}

.run-visual-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.code-editor {
  flex: 1;
  width: 100%;
  min-height: 0;
  padding: 16px;
  border: none;
  outline: none;
  resize: none;
  background: #0f172a;
  color: #e2e8f0;
  font: 13px/1.7 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  box-sizing: border-box;
}

.visual-empty,
.visual-error {
  height: 100%;
  min-height: 420px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #64748b;
  text-align: center;
}

.visual-empty strong,
.visual-error strong {
  color: #0f172a;
  font-size: 16px;
  font-weight: 900;
}

.visual-empty p,
.visual-error p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
}

.visual-error p {
  color: #dc2626;
}

@media (max-width: 1100px) {
  .algorithm-workspace {
    height: auto;
    min-height: 0;
    overflow: visible;
  }

  .algorithm-main {
    grid-template-columns: 1fr;
  }

  .visual-panel {
    min-height: 520px;
  }

  .code-side {
    min-height: 520px;
  }
}

@media (max-width: 640px) {
  .code-panel-head {
    height: auto;
    padding: 14px 16px;
    align-items: flex-start;
    flex-direction: column;
  }

  .code-panel-head-main,
  .code-actions {
    width: 100%;
  }

  .code-actions {
    justify-content: flex-start;
    margin-left: 0;
    flex-wrap: wrap;
  }
}
</style>
