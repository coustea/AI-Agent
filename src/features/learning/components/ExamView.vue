<template>
  <div class="exam-container">
    <header class="exam-header">
      <div class="exam-header-left">
        <div class="exam-title-row">
          <h2>{{ title }}</h2>
          <div class="exam-meta-tags">
            <el-tag type="primary" class="meta-tag">试题数量: {{ paper.length }} 题</el-tag>
            <el-tag v-if="isSubmitted" type="success" class="meta-tag">答题正确率: {{ reportScore }}%</el-tag>
          </div>
        </div>
      </div>
      <div class="exam-header-right">
        <div class="exam-timer">
          <el-icon><Timer /></el-icon>
          <span>{{ isSubmitted ? `用时: ${reportTimeSpent}` : formattedTime }}</span>
        </div>
        <el-button v-if="!isSubmitted" type="danger" @click="$emit('quit')">
          <el-icon><Close /></el-icon> 退出答卷
        </el-button>
        <el-button v-else type="primary" class="back-btn" @click="$emit('quit')">返回题库主页</el-button>
      </div>
    </header>

    <div class="exam-layout">
      <main class="exam-papers">
        <div
          v-for="(q, idx) in paper"
          :key="q.id"
          :id="'eq-' + idx"
          :class="['exam-card', { active: currentIdx === idx }]"
          @click="currentIdx = idx"
        >
          <div class="eq-header">
            <div class="eq-left">
              <span class="eq-num">第 {{ idx + 1 }} 题</span>
              <div class="eq-tags">
                <el-tag size="small" type="info">{{ q.subject }}</el-tag>
                <el-tag size="small" type="warning">{{ q.type }}</el-tag>
                <el-tag v-if="q.type === '多选题'" size="small" type="primary">可多选</el-tag>
                <el-tag size="small" :type="getDiffType(q.difficulty)">{{ q.difficulty || '未标注' }}</el-tag>
              </div>
            </div>
            <div v-if="isSubmitted" class="eq-result" :class="isCorrect(q) ? 'ok' : 'fail'">
              <el-icon v-if="isCorrect(q)"><CircleCheck /></el-icon>
              <el-icon v-else><CircleClose /></el-icon>
              <span>{{ isCorrect(q) ? '回答正确！' : '回答错误' }}</span>
            </div>
          </div>

          <div class="eq-text markdown-body" v-html="renderMd(q.content)"></div>

          <!-- Options -->
          <div v-if="isOptionType(q)" class="eq-options">
            <div
              v-for="(val, key) in getOpts(q)"
              :key="key"
              :class="['eq-opt', {
                selected: isSel(q.id, key),
                'is-correct': isSubmitted && isCorrOpt(q, key),
                'is-wrong': isSubmitted && isSel(q.id, key) && !isCorrOpt(q, key),
                disabled: isSubmitted,
              }]"
              @click="!isSubmitted && selectOpt(q, key)"
            >
              <span class="eq-opt-badge">{{ key }}</span>
              <span class="eq-opt-text markdown-body" v-html="renderInline(val)"></span>
              <el-tag v-if="isSubmitted && isCorrOpt(q, key)" size="small" type="success" class="eq-opt-tag">正确答案</el-tag>
              <el-tag v-if="isSubmitted && isSel(q.id, key) && !isCorrOpt(q, key)" size="small" type="danger" class="eq-opt-tag">您的选项</el-tag>
            </div>
          </div>

          <!-- Text input -->
          <div v-else class="eq-textarea">
            <el-input
              v-model="answers[q.id]"
              type="textarea"
              :rows="4"
              :placeholder="q.type === '填空题' ? '请输入填空答案...' : '请详细描述您的解答步骤与答案...'"
              :disabled="isSubmitted"
            />
            <div v-if="isSubmitted" class="eq-text-review">
              <div :class="['eq-review-line', isCorrect(q) ? 'ok' : 'fail']">
                <strong>您的回答：</strong>{{ answers[q.id] || '(未作答)' }}
                <el-icon v-if="isCorrect(q)"><CircleCheck /></el-icon>
                <el-icon v-else><CircleClose /></el-icon>
                {{ isCorrect(q) ? '正确' : '错误' }}
              </div>
              <div class="eq-standard">参考答案：{{ q.answer }}</div>
            </div>
          </div>

          <!-- Analysis toggle -->
          <div v-if="isSubmitted" class="eq-analysis-toggle">
            <el-button type="primary" plain size="small" @click="toggleAnalysis(q.id)">
              {{ analysisVisible[q.id] ? '收起答案解析' : '查看答案解析' }}
            </el-button>
          </div>
          <transition name="collapse">
            <div v-if="isSubmitted && analysisVisible[q.id]" class="eq-analysis">
              <div class="eq-analysis-body markdown-body" v-html="renderMd(q.analysis)"></div>
              <div v-if="q.knowledge_points?.length" class="eq-analysis-kps">
                <span>考查知识点：</span>
                <el-tag v-for="kp in q.knowledge_points" :key="kp" size="small" type="info">{{ kp }}</el-tag>
              </div>
            </div>
          </transition>
        </div>
      </main>

      <aside class="exam-sidebar">
        <div class="sidebar-card">
          <h3>答题卡</h3>
          <div class="legend" v-if="!isSubmitted">
            <span><span class="dot done"></span> 已答</span>
            <span><span class="dot todo"></span> 未答</span>
          </div>
          <div class="legend" v-else>
            <span><span class="dot correct"></span> 正确</span>
            <span><span class="dot wrong"></span> 错误</span>
          </div>
          <div class="nav-grid">
            <button
              v-for="(q, idx) in paper"
              :key="q.id"
              :class="['grid-btn', {
                answered: !isSubmitted && hasAnswer(q),
                active: currentIdx === idx,
                'review-correct': isSubmitted && isCorrect(q),
                'review-wrong': isSubmitted && !isCorrect(q),
              }]"
              @click="scrollTo(idx)"
            >{{ idx + 1 }}</button>
          </div>
          <div v-if="!isSubmitted" class="progress-section">
            <div class="progress-info">
              <span>答题进度</span>
              <span>{{ answeredCount }} / {{ paper.length }}</span>
            </div>
            <el-progress :percentage="Math.round((answeredCount / paper.length) * 100)" :show-text="false" color="#4F46E5" />
          </div>
          <div v-if="!isSubmitted" class="submit-section">
            <el-button type="success" class="full-btn" @click="handleSubmit">确认交卷</el-button>
          </div>
          <div v-else class="report-section">
            <div class="report-score">
              <span class="score-label">答对题数</span>
              <div class="score-num" :style="{ color: scoreColor }">
                {{ correctCount }} <small>/ {{ paper.length }} 题</small>
              </div>
            </div>
            <div class="report-eval">
              <h4>{{ scoreLevel }}</h4>
              <p>{{ scoreMsg }}</p>
            </div>
            <el-button type="primary" class="full-btn" @click="$emit('quit')">返回题库主页</el-button>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Timer, CircleCheck, CircleClose, Close } from '@element-plus/icons-vue'
import { marked } from 'marked'

interface Question {
  id: string
  subject: string
  type: string
  difficulty?: string | null
  content: string
  options?: Record<string, string> | null
  answer: string
  analysis: string
  knowledge_points: string[]
}

const props = defineProps<{ paper: Question[]; title: string }>()
const emit = defineEmits<{
  quit: []
  submit: [result: { score: number; correct: number }]
}>()

const renderMd = (text: string) => marked.parse(text || '', { async: false }) as string
const renderInline = (text: string) => marked.parseInline(text || '', { async: false }) as string

const answers = ref<Record<string, any>>({})
const currentIdx = ref(0)
const isSubmitted = ref(false)
const analysisVisible = ref<Record<string, boolean>>({})
const elapsed = ref(0)
let timer: number | null = null

const reportScore = ref(0)
const correctCount = ref(0)
const reportTimeSpent = ref('')

const formattedTime = computed(() => {
  const m = Math.floor(elapsed.value / 60)
  const s = elapsed.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const answeredCount = computed(() => props.paper.filter(q => hasAnswer(q)).length)

const hasAnswer = (q: Question) => {
  const a = answers.value[q.id]
  if (Array.isArray(a)) return a.length > 0
  return String(a || '').trim().length > 0
}

const isOptionType = (q: Question) => q.type === '选择题' || q.type === '多选题' || q.type === '判断题'

const getOpts = (q: Question) => {
  if (q.type === '判断题') return { A: '正确', B: '错误' }
  return q.options || {}
}

const getOptVal = (q: Question, key: string) => {
  if (q.type === '判断题') return key === 'A' ? '正确' : '错误'
  return key
}

const normAns = (a: any): string[] => {
  const v = Array.isArray(a) ? a : String(a || '').split(',')
  return v.map(x => String(x).trim().toUpperCase()).filter(Boolean).sort()
}

const isSel = (qid: string, key: string) => {
  const selected = normAns(answers.value[qid])
  const val = String(getOptVal({ id: qid } as Question, key)).toUpperCase()
  return selected.includes(val) || selected.includes(key)
}

const isCorrOpt = (q: Question, key: string) => {
  const standard = normAns(q.answer)
  const val = String(getOptVal(q, key)).toUpperCase()
  return standard.includes(val)
}

const isCorrect = (q: Question) => {
  const user = normAns(answers.value[q.id])
  const standard = normAns(q.answer)
  if (isOptionType(q)) return user.length === standard.length && user.every((v, i) => v === standard[i])
  const text = String(answers.value[q.id] || '').trim().toUpperCase()
  if (!text) return false
  return standard.some(kw => text.includes(kw)) || text.length > 2
}

const selectOpt = (q: Question, key: string) => {
  const value = getOptVal(q, key)
  if (q.type === '多选题') {
    const selected = normAns(answers.value[q.id])
    const norm = String(value).toUpperCase()
    answers.value[q.id] = selected.includes(norm)
      ? selected.filter(v => v !== norm)
      : [...selected, norm]
  } else {
    answers.value[q.id] = value
  }
}

const toggleAnalysis = (id: string) => {
  analysisVisible.value = { ...analysisVisible.value, [id]: !analysisVisible.value[id] }
}

const scrollTo = (idx: number) => {
  currentIdx.value = idx
  document.getElementById(`eq-${idx}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

const handleSubmit = async () => {
  const unanswered = props.paper.length - answeredCount.value
  let msg = '提交后将结束本次作答，并立即生成答题报告。'
  if (unanswered > 0) msg = `您还有 ${unanswered} 道题未作答，提交后将直接计入本次答题报告。`

  try {
    await ElMessageBox.confirm(msg, '确认提交', { type: 'warning', confirmButtonText: '确认交卷', cancelButtonText: '继续检查' })
    doSubmit()
  } catch { /* cancelled */ }
}

const doSubmit = () => {
  if (timer) clearInterval(timer)
  const spentSec = elapsed.value
  const m = Math.floor(spentSec / 60)
  const s = spentSec % 60
  reportTimeSpent.value = m > 0 ? `${m}分${s}秒` : `${s}秒`

  let correct = 0
  props.paper.forEach(q => { if (isCorrect(q)) correct++ })
  correctCount.value = correct
  reportScore.value = Math.round((correct / props.paper.length) * 100)
  isSubmitted.value = true
  emit('submit', { score: reportScore.value, correct })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const getDiffType = (d?: string | null) => {
  if (d === '简单') return 'success'
  if (d === '中等') return 'warning'
  return 'danger'
}

const scoreColor = computed(() => {
  if (reportScore.value >= 90) return '#10B981'
  if (reportScore.value >= 60) return '#4F46E5'
  return '#EF4444'
})

const scoreLevel = computed(() => {
  if (reportScore.value >= 90) return '优秀'
  if (reportScore.value >= 75) return '良好'
  if (reportScore.value >= 60) return '合格'
  return '不合格'
})

const scoreMsg = computed(() => {
  if (reportScore.value >= 90) return '太棒了！继续保持！'
  if (reportScore.value >= 75) return '成绩良好，部分细节仍有巩固空间。'
  if (reportScore.value >= 60) return '考核通过，建议对照错题多看看解析。'
  return '建议在题库主页中多进行单题速练。'
})

onMounted(() => {
  props.paper.forEach(q => { answers.value[q.id] = q.type === '多选题' ? [] : '' })
  timer = window.setInterval(() => { if (!isSubmitted.value) elapsed.value++ }, 1000)
})

onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.exam-container { display: flex; flex-direction: column; min-height: calc(100vh - 112px); }

.exam-header {
  background: var(--color-surface); border: 1px solid var(--color-border-light);
  border-radius: 16px; padding: 16px 24px; display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.02);
}
.exam-header-left { display: flex; align-items: center; gap: 16px; }
.exam-title-row { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.exam-title-row h2 { margin: 0; font-size: 1.3rem; font-weight: 800; color: var(--color-text); }
.exam-meta-tags { display: flex; gap: 8px; }
.meta-tag { font-size: 0.88rem !important; font-weight: 600 !important; height: 28px !important; border-radius: 6px !important; }
.exam-header-right { display: flex; align-items: center; gap: 16px; }
.exam-timer {
  display: flex; align-items: center; gap: 8px; background: rgba(79, 70, 229, 0.08);
  border: 1px solid rgba(79, 70, 229, 0.2); padding: 8px 16px; border-radius: 10px;
  color: var(--color-primary); font-weight: bold;
}
.back-btn { border-radius: 10px; font-weight: 600; }

.exam-layout { display: grid; grid-template-columns: 1fr 260px; gap: 20px; flex: 1; overflow: hidden; }

.exam-papers { overflow-y: auto; display: flex; flex-direction: column; gap: 16px; padding-right: 8px; }

.exam-card {
  background: var(--color-surface); border: 1px solid var(--color-border-light);
  border-radius: 14px; padding: 22px; transition: all 0.2s ease; cursor: pointer;
}
.exam-card.active { border-color: var(--color-primary); box-shadow: 0 4px 20px rgba(79, 70, 229, 0.06); }

.eq-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.eq-left { display: flex; align-items: center; gap: 12px; }
.eq-num { font-size: 1.05rem; font-weight: 850; color: var(--color-primary); }
.eq-tags { display: flex; gap: 6px; }
.eq-result { display: flex; align-items: center; gap: 6px; font-weight: 700; }
.eq-result.ok { color: var(--color-success); }
.eq-result.fail { color: var(--color-danger); }

.eq-text { font-size: 1.02rem; font-weight: 600; line-height: 1.6; color: var(--color-text); margin-bottom: 18px; white-space: pre-wrap; }

.eq-options { display: grid; gap: 10px; }
.eq-opt {
  display: flex; align-items: flex-start; gap: 12px; padding: 13px 16px;
  background: var(--color-bg); border: 1px solid var(--color-border-light);
  border-radius: 10px; cursor: pointer; transition: all 0.15s ease;
}
.eq-opt:hover { background: rgba(79, 70, 229, 0.04); }
.eq-opt.selected { background: rgba(79, 70, 229, 0.08); border-color: var(--color-primary); font-weight: 600; }
.eq-opt.is-correct { border-color: var(--color-success); background: rgba(16, 185, 129, 0.06); color: #065F46; }
.eq-opt.is-wrong { border-color: var(--color-danger); background: rgba(239, 68, 68, 0.06); color: #991B1B; }
.eq-opt.disabled { cursor: not-allowed; }
.eq-opt.disabled:hover { background: inherit; }
.eq-opt.disabled.is-correct:hover { background: rgba(16, 185, 129, 0.06); }
.eq-opt.disabled.is-wrong:hover { background: rgba(239, 68, 68, 0.06); }

.eq-opt-badge {
  width: 26px; height: 26px; border-radius: 50%; background: rgba(15, 23, 42, 0.05);
  display: flex; align-items: center; justify-content: center; font-weight: bold;
  font-size: 0.85rem; flex-shrink: 0; color: var(--color-text-secondary);
}
.eq-opt.selected .eq-opt-badge { background: var(--color-primary); color: #fff; }
.eq-opt.is-correct .eq-opt-badge { background: var(--color-success); color: #fff; }
.eq-opt.is-wrong .eq-opt-badge { background: var(--color-danger); color: #fff; }
.eq-opt-text { font-size: 0.95rem; min-width: 0; flex: 1; }
.eq-opt-tag { margin-left: auto; font-weight: 700; flex-shrink: 0; }

.eq-textarea { margin-top: 4px; }
.eq-text-review {
  margin-top: 14px; padding: 14px 16px; background: var(--color-bg);
  border-left: 4px solid var(--color-primary); border-radius: 4px 10px 10px 4px;
  display: flex; flex-direction: column; gap: 8px;
}
.eq-review-line { font-size: 0.92rem; font-weight: 500; display: flex; align-items: center; gap: 6px; }
.eq-review-line.ok { color: var(--color-success); }
.eq-review-line.fail { color: var(--color-danger); }
.eq-standard { font-size: 0.92rem; color: var(--color-text); background: var(--color-surface-hover); padding: 10px 14px; border-radius: 8px; }

.eq-analysis-toggle { margin-top: 14px; display: flex; justify-content: flex-end; }
.eq-analysis {
  margin-top: 14px; padding: 14px; border-top: 1px dashed #FCD34D;
  border-left: 4px solid var(--color-warning); background: #FFFDF5; border-radius: 8px;
  font-size: 0.9rem; color: #78350F; line-height: 1.6;
}
.eq-analysis-body { margin-bottom: 10px; }
.eq-analysis-kps { display: flex; align-items: center; gap: 6px; font-size: 0.82rem; color: var(--text-muted); border-top: 1px dashed var(--color-border); padding-top: 10px; margin-top: 10px; flex-wrap: wrap; }

/* Sidebar */
.exam-sidebar { overflow-y: hidden; }
.sidebar-card {
  background: var(--color-surface); border: 1px solid var(--color-border-light);
  border-radius: 16px; padding: 20px; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.02);
  display: flex; flex-direction: column; gap: 14px; position: sticky; top: 24px;
}
.sidebar-card h3 { margin: 0; font-size: 1.05rem; font-weight: bold; }
.legend { display: flex; gap: 14px; font-size: 0.8rem; color: var(--color-text-muted); }
.legend span { display: flex; align-items: center; gap: 4px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot.done { background: var(--color-primary); }
.dot.todo { background: var(--color-border-hover); }
.dot.correct { background: var(--color-success); }
.dot.wrong { background: var(--color-danger); }

.nav-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.grid-btn {
  display: flex; align-items: center; justify-content: center; padding: 0; margin: 0;
  aspect-ratio: 1; border-radius: 8px; border: 1px solid var(--color-border);
  background: var(--color-surface); color: var(--color-text-muted); font-weight: bold;
  font-size: 0.95rem; cursor: pointer; transition: all 0.2s ease;
}
.grid-btn:hover { border-color: var(--color-primary); color: var(--color-primary); }
.grid-btn.answered { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.grid-btn.active { box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.25); }
.grid-btn.review-correct { background: var(--color-success) !important; color: #fff !important; border-color: var(--color-success) !important; }
.grid-btn.review-wrong { background: var(--color-danger) !important; color: #fff !important; border-color: var(--color-danger) !important; }

.progress-section { margin-top: 8px; }
.progress-info { display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 6px; font-weight: bold; }
.submit-section { margin-top: 6px; }
.full-btn { width: 100%; border-radius: 10px !important; }

.report-section { margin-top: 16px; padding: 16px; background: var(--color-bg); border-radius: 12px; border: 1px solid var(--color-border-light); }
.report-score { display: flex; flex-direction: column; align-items: center; margin-bottom: 12px; }
.score-label { font-size: 0.85rem; color: var(--color-text-muted); font-weight: 600; margin-bottom: 4px; }
.score-num { font-size: 1.8rem; font-weight: 800; display: flex; align-items: baseline; }
.score-num small { font-size: 0.9rem; color: var(--color-text-muted); font-weight: 500; margin-left: 2px; }
.report-eval { text-align: center; padding: 8px 12px; background: var(--color-surface); border-radius: 8px; border: 1px solid rgba(226, 232, 240, 0.6); margin-bottom: 14px; }
.report-eval h4 { margin: 0 0 4px; font-size: 0.95rem; font-weight: bold; color: var(--color-text); }
.report-eval p { margin: 0; font-size: 0.8rem; color: var(--color-text-muted); line-height: 1.4; }

.collapse-enter-active, .collapse-leave-active { transition: all 0.25s ease; overflow: hidden; }
.collapse-enter-from, .collapse-leave-to { opacity: 0; max-height: 0; }
.collapse-enter-to, .collapse-leave-from { max-height: 600px; }

@media (max-width: 820px) {
  .exam-layout { grid-template-columns: 1fr; }
  .exam-sidebar { display: none; }
}
</style>
