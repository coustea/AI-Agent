<template>
  <div :class="['analysis-page', scoreClass]">
    <header class="analysis-page-topbar">
      <button class="back-button" type="button" @click="$emit('close')">
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M15 18 9 12l6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        {{ returnLabel }}
      </button>

      <div class="topbar-title">
        <span>{{ sourceLabel }}</span>
        <strong>分析题评阅详情</strong>
      </div>

      <div v-if="showQuestionNavigation" class="question-switcher">
        <button type="button" :disabled="previousDisabled" @click="$emit('previous')">上一道分析题</button>
        <span>{{ analysisIndex + 1 }} / {{ analysisTotal }}</span>
        <button type="button" :disabled="nextDisabled" @click="$emit('next')">下一道分析题</button>
      </div>
    </header>

    <main class="analysis-page-container">
      <section class="analysis-hero">
        <div class="hero-copy">
          <div class="hero-tags">
            <span class="question-index">第 {{ questionNumber }} 题</span>
            <span>{{ question.subject }}</span>
            <span>{{ question.type }}</span>
            <span v-if="question.difficulty">{{ question.difficulty }}</span>
          </div>
          <p class="hero-kicker">AI INTELLIGENT REVIEW</p>
          <h1>分析题作答评阅报告</h1>
          <div class="hero-question" v-html="renderInline(question.content)"></div>
        </div>

        <div class="score-summary">
          <div class="score-ring" :style="{ '--score-angle': `${score * 3.6}deg` }">
            <div class="score-ring-inner">
              <strong>{{ score }}</strong>
              <span>分</span>
            </div>
          </div>
          <div class="score-summary-copy">
            <span>本题评阅结果</span>
            <strong>{{ scoreText }}</strong>
            <p>{{ scoreDescription }}</p>
          </div>
        </div>
      </section>

      <div class="analysis-content-layout">
        <div class="analysis-main-column">
          <section class="report-section feedback-section">
            <div class="section-heading">
              <span class="section-icon">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M8 10h8M8 14h5M6.5 19.5 3 21l1.5-3.5A8.5 8.5 0 1 1 6.5 19.5Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </span>
              <div>
                <span>综合评价</span>
                <h2>AI 评语</h2>
              </div>
            </div>
            <div class="feedback-quote">
              <span aria-hidden="true">“</span>
              <p>{{ review?.feedback || defaultFeedback }}</p>
            </div>
          </section>

          <section class="report-section answer-section">
            <div class="section-heading">
              <span class="section-icon">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M7 4h10a2 2 0 0 1 2 2v14H5V6a2 2 0 0 1 2-2Z" stroke="currentColor" stroke-width="1.8" />
                  <path d="M8.5 8.5h7M8.5 12h7M8.5 15.5h4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                </svg>
              </span>
              <div>
                <span>答案对照</span>
                <h2>作答内容与参考答案</h2>
              </div>
            </div>

            <div class="answer-comparison">
              <article class="answer-card user-answer-card">
                <div class="answer-card-header">
                  <div>
                    <span class="answer-card-number">01</span>
                    <strong>你的作答</strong>
                  </div>
                  <span :class="['answer-status', hasAnswer ? 'answered' : 'unanswered']">
                    {{ hasAnswer ? '已作答' : '未作答' }}
                  </span>
                </div>
                <div :class="['answer-content', { empty: !hasAnswer }]">{{ formattedUserAnswer }}</div>
              </article>

              <article class="answer-card reference-answer-card">
                <div class="answer-card-header">
                  <div>
                    <span class="answer-card-number">02</span>
                    <strong>参考答案</strong>
                  </div>
                  <span class="answer-status reference">对照要点</span>
                </div>
                <div class="answer-content reference">{{ formattedReferenceAnswer || '暂无参考答案。' }}</div>
              </article>
            </div>
          </section>

          <section class="report-section improvement-section">
            <div class="section-heading">
              <span class="section-icon">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="m12 3 2.2 4.8L19 10l-4.8 2.2L12 17l-2.2-4.8L5 10l4.8-2.2L12 3Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
                  <path d="m18.5 16 .8 1.7L21 18.5l-1.7.8-.8 1.7-.8-1.7-1.7-.8 1.7-.8.8-1.7Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" />
                </svg>
              </span>
              <div>
                <span>能力提升</span>
                <h2>改进建议</h2>
              </div>
            </div>

            <ol class="improvement-list">
              <li v-for="(hint, index) in improvementHints" :key="`${index}-${hint}`">
                <span>{{ String(index + 1).padStart(2, '0') }}</span>
                <div>
                  <strong>{{ hintTitle(index) }}</strong>
                  <p>{{ hint }}</p>
                </div>
              </li>
            </ol>
          </section>

          <section class="report-section detail-section">
            <div class="section-heading">
              <span class="section-icon">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M5 4.5h11.5A2.5 2.5 0 0 1 19 7v12.5H7.5A2.5 2.5 0 0 1 5 17V4.5Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
                  <path d="M5 17a2.5 2.5 0 0 1 2.5-2.5H19M9 8h6M9 11h4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                </svg>
              </span>
              <div>
                <span>解题复盘</span>
                <h2>题目解析</h2>
              </div>
            </div>
            <div class="detail-content" v-html="renderInline(question.analysis || '暂无解析。')"></div>
          </section>
        </div>

        <aside class="analysis-side-column">
          <section class="side-card score-card">
            <div class="side-card-title">
              <span>评阅概览</span>
              <strong>{{ scoreText }}</strong>
            </div>
            <div class="score-bar-label">
              <span>得分完成度</span>
              <strong>{{ score }}%</strong>
            </div>
            <div class="score-bar"><span :style="{ width: `${score}%` }"></span></div>
            <dl class="overview-list">
              <div>
                <dt>作答状态</dt>
                <dd>{{ hasAnswer ? '已提交答案' : '本题未作答' }}</dd>
              </div>
              <div>
                <dt>评阅方式</dt>
                <dd>AI 智能评阅</dd>
              </div>
              <div>
                <dt>改进建议</dt>
                <dd>{{ improvementHints.length }} 项</dd>
              </div>
            </dl>
          </section>

          <section class="side-card knowledge-card">
            <div class="side-card-title">
              <span>本题考查</span>
              <strong>知识点</strong>
            </div>
            <div v-if="question.knowledge_points?.length" class="knowledge-tags">
              <span v-for="point in question.knowledge_points" :key="point">{{ point }}</span>
            </div>
            <p v-else class="empty-knowledge">本题暂未标注知识点。</p>
          </section>

          <section class="side-card review-tip-card">
            <div class="tip-icon">!</div>
            <div>
              <strong>复盘建议</strong>
              <p>先对照参考答案补齐遗漏要点，再根据题目解析重新组织一次完整作答。</p>
            </div>
          </section>
        </aside>
      </div>

      <footer :class="['analysis-page-footer', { 'single-action': !showQuestionNavigation }]">
        <button v-if="showQuestionNavigation" type="button" :disabled="previousDisabled" @click="$emit('previous')">
          <span>上一道</span>
          <strong>{{ previousDisabled ? '已经是第一道分析题' : '查看上一题解析' }}</strong>
        </button>
        <button type="button" class="return-report" @click="$emit('close')">{{ returnLabel }}</button>
        <button v-if="showQuestionNavigation" type="button" :disabled="nextDisabled" @click="$emit('next')">
          <span>下一道</span>
          <strong>{{ nextDisabled ? '已经是最后一道分析题' : '查看下一题解析' }}</strong>
        </button>
      </footer>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderQuestionMarkdown } from '@/features/question-bank/model/questionText'

type AnswerValue = string | string[] | undefined

// 分析题评阅结果接口
interface ReviewResult {
  score?: number
  feedback?: string
  improvement_hints?: string[]
}

interface ExamQuestion {
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

// 组件属性：题目信息、评阅结果、翻页状态
const props = defineProps<{
  question: ExamQuestion
  answer: AnswerValue
  review: ReviewResult | null
  scoreValue: number
  resultText: string
  questionNumber: number
  analysisIndex: number
  analysisTotal: number
  previousDisabled: boolean
  nextDisabled: boolean
  showQuestionNavigation: boolean
  sourceLabel: string
  returnLabel: string
}>()

// 事件：关闭/上一道/下一道
defineEmits<{
  (e: 'close'): void
  (e: 'previous'): void
  (e: 'next'): void
}>()

// 计算标准化得分（0-100）
const score = computed(() => {
  return Math.min(100, Math.max(0, Math.round(Number(props.scoreValue) || 0)))
})

// 根据分数确定颜色样式类
const scoreClass = computed(() => {
  if (score.value >= 80) return 'success'
  if (score.value >= 60) return 'warning'
  return 'danger'
})

// 得分文本描述
const scoreText = computed(() => {
  if (props.resultText === '优秀') return '表现优秀'
  if (props.resultText === '部分正确') return '部分正确'
  if (!hasAnswer.value) return '未作答'
  return props.resultText || '仍需加强'
})

// 得分详细评语
const scoreDescription = computed(() => {
  if (score.value >= 80) return '核心观点较完整，作答逻辑清晰。'
  if (score.value >= 60) return '已覆盖部分要点，仍需加强论证。'
  return hasAnswer.value ? '关键要点覆盖不足，建议系统复盘。' : '请先完成作答，再结合解析进行复盘。'
})

// 是否有作答、格式化后的用户答案和参考答案
const hasAnswer = computed(() => normalizeAnswer(props.answer).length > 0)
const formattedUserAnswer = computed(() => formatUserAnswer(props.answer).trim() || '本题未作答。')
const formattedReferenceAnswer = computed(() => String(props.question.answer || '').replace(/,/g, '、'))

// 默认 AI 评语（根据得分动态生成）
const defaultFeedback = computed(() => {
  if (!hasAnswer.value) return '本题未作答。建议先从题干中提取核心任务，再按照“观点—依据—结论”的结构组织答案。'
  if (score.value >= 80) return '整体作答较完整，关键观点覆盖充分，论证结构也比较清晰。'
  if (score.value >= 60) return '已覆盖部分关键内容，但论点之间的衔接和论证深度仍可进一步加强。'
  return '当前回答与参考要点存在较大差距，建议重新梳理题干要求并按要点分层作答。'
})

// 改进建议列表（优先取 API 返回，无则用默认提示）
const improvementHints = computed(() => {
  const hints = props.review?.improvement_hints?.filter(Boolean) || []
  if (hints.length) return hints
  if (!hasAnswer.value) {
    return [
      '先圈出题干中的分析对象、限定条件和作答任务，避免偏离问题核心。',
      '按照"核心观点、分析依据、最终结论"的顺序组织答案。',
    ]
  }
  return [
    '对照参考答案检查遗漏的关键论点，并补充相应分析依据。',
    '使用分点表达和因果连接词，让论证层次更加清晰。',
  ]
})

function hintTitle(index: number) {
  const titles = ['补齐关键要点', '优化论证结构', '增强表达准确性', '强化知识迁移']
  return titles[index] || `改进方向 ${index + 1}`
}

// 标准化用户答案为数组
function normalizeAnswer(answer: AnswerValue): string[] {
  if (Array.isArray(answer)) return answer.map((item) => String(item).trim()).filter(Boolean)
  const text = String(answer || '').trim()
  return text ? [text] : []
}

function formatUserAnswer(answer: AnswerValue) {
  return Array.isArray(answer) ? answer.join('、') : String(answer || '')
}

// 将纯文本中的 markdown 标记渲染为 HTML
function renderInline(text: string) {
  return renderQuestionMarkdown(text)
}
</script>

<style scoped>
.analysis-page {
  --accent: #2563eb;
  --accent-soft: rgba(37, 99, 235, 0.1);
  --accent-border: rgba(37, 99, 235, 0.2);
  min-height: 100%;
  color: #172033;
}

.analysis-page.success {
  --accent: #059669;
  --accent-soft: rgba(5, 150, 105, 0.1);
  --accent-border: rgba(5, 150, 105, 0.22);
}

.analysis-page.warning {
  --accent: #d97706;
  --accent-soft: rgba(217, 119, 6, 0.11);
  --accent-border: rgba(217, 119, 6, 0.23);
}

.analysis-page.danger {
  --accent: #dc2626;
  --accent-soft: rgba(220, 38, 38, 0.09);
  --accent-border: rgba(220, 38, 38, 0.2);
}

.analysis-page-topbar {
  position: static;
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto minmax(280px, 1fr);
  align-items: center;
  gap: 20px;
  width: calc(100% - 56px);
  max-width: 1360px;
  min-height: 72px;
  margin: 28px auto 0;
  padding: 0 28px;
  box-sizing: border-box;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
}

.back-button,
.question-switcher button,
.analysis-page-footer button {
  border: 0;
  font: inherit;
  cursor: pointer;
}

.back-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  justify-self: start;
  padding: 9px 12px;
  border-radius: 10px;
  background: #f1f5f9;
  color: #475569;
  font-size: 13px;
  font-weight: 800;
}

.back-button svg {
  width: 18px;
  height: 18px;
}

.topbar-title {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}

.topbar-title span {
  color: #94a3b8;
  font-size: 11px;
}

.topbar-title strong {
  font-size: 16px;
  font-weight: 900;
}

.question-switcher {
  display: flex;
  align-items: center;
  justify-self: end;
  gap: 8px;
}

.question-switcher button {
  min-height: 34px;
  padding: 0 11px;
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-radius: 9px;
  background: #fff;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
}

.question-switcher button:disabled,
.analysis-page-footer button:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.question-switcher span {
  min-width: 50px;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
  text-align: center;
}

.analysis-page-container {
  display: flex;
  flex-direction: column;
  gap: 22px;
  width: 100%;
  max-width: 1416px;
  margin: 0 auto;
  padding: 28px;
  box-sizing: border-box;
}

.analysis-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 28px;
  overflow: hidden;
  padding: 34px;
  border: 1px solid var(--accent-border);
  border-radius: 24px;
  background:
    radial-gradient(circle at 92% 10%, var(--accent-soft), transparent 32%),
    linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
}

.analysis-hero::after {
  content: '';
  position: absolute;
  right: -80px;
  bottom: -120px;
  width: 300px;
  height: 300px;
  border: 38px solid var(--accent-soft);
  border-radius: 50%;
}

.hero-copy,
.score-summary {
  position: relative;
  z-index: 1;
}

.hero-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.hero-tags span {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 11px;
  font-weight: 800;
}

.hero-tags .question-index {
  background: var(--accent-soft);
  color: var(--accent);
}

.hero-kicker {
  margin: 22px 0 6px;
  color: var(--accent);
  font-size: 11px;
  font-weight: 950;
  letter-spacing: 0.14em;
}

.hero-copy h1 {
  margin: 0;
  color: #0f172a;
  font-size: clamp(25px, 3vw, 36px);
  font-weight: 950;
  letter-spacing: -0.04em;
}

.hero-question {
  max-width: 850px;
  margin-top: 20px;
  color: #334155;
  font-size: 16px;
  line-height: 1.9;
}

.score-summary {
  display: flex;
  align-items: center;
  gap: 18px;
  align-self: center;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.88);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 15px 34px rgba(15, 23, 42, 0.09);
  backdrop-filter: blur(12px);
}

.score-ring {
  display: grid;
  place-items: center;
  flex: 0 0 112px;
  width: 112px;
  height: 112px;
  border-radius: 50%;
  background: conic-gradient(var(--accent) var(--score-angle), #e2e8f0 0);
}

.score-ring-inner {
  display: flex;
  align-items: baseline;
  justify-content: center;
  width: 88px;
  height: 88px;
  border-radius: 50%;
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.9);
}

.score-ring-inner strong {
  align-self: center;
  color: var(--accent);
  font-size: 32px;
  font-weight: 950;
}

.score-ring-inner span {
  align-self: center;
  margin-top: 12px;
  color: #94a3b8;
  font-size: 12px;
  font-weight: 800;
}

.score-summary-copy {
  min-width: 0;
}

.score-summary-copy > span {
  color: #94a3b8;
  font-size: 11px;
  font-weight: 800;
}

.score-summary-copy > strong {
  display: block;
  margin-top: 4px;
  color: var(--accent);
  font-size: 20px;
  font-weight: 950;
}

.score-summary-copy p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.analysis-content-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 22px;
  align-items: start;
}

.analysis-main-column {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

.report-section,
.side-card {
  border: 1px solid rgba(226, 232, 240, 0.92);
  background: #fff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.055);
}

.report-section {
  padding: 24px;
  border-radius: 20px;
}

.section-heading {
  display: flex;
  align-items: center;
  gap: 13px;
  margin-bottom: 20px;
}

.section-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 42px;
  width: 42px;
  height: 42px;
  border-radius: 13px;
  background: var(--accent-soft);
  color: var(--accent);
}

.section-icon svg {
  width: 22px;
  height: 22px;
}

.section-heading span:not(.section-icon) {
  color: var(--accent);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.1em;
}

.section-heading h2 {
  margin: 2px 0 0;
  color: #0f172a;
  font-size: 18px;
  font-weight: 900;
}

.feedback-section {
  overflow: hidden;
  border-color: var(--accent-border);
  background: linear-gradient(135deg, #fff, var(--accent-soft));
}

.feedback-quote {
  position: relative;
  padding: 18px 22px 18px 54px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.8);
}

.feedback-quote > span {
  position: absolute;
  left: 18px;
  top: 10px;
  color: var(--accent);
  font-family: Georgia, serif;
  font-size: 52px;
  line-height: 1;
}

.feedback-quote p {
  margin: 0;
  color: #334155;
  font-size: 15px;
  font-weight: 650;
  line-height: 1.9;
}

.answer-comparison {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.answer-card {
  min-width: 0;
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 16px;
  background: #f8fafc;
}

.user-answer-card {
  border-top: 3px solid #64748b;
}

.reference-answer-card {
  border-top: 3px solid var(--accent);
}

.answer-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 17px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  background: #fff;
}

.answer-card-header > div {
  display: flex;
  align-items: center;
  gap: 10px;
}

.answer-card-number {
  color: var(--accent);
  font-size: 11px;
  font-weight: 950;
}

.answer-card-header strong {
  font-size: 14px;
  font-weight: 900;
}

.answer-status {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 850;
}

.answer-status.answered {
  background: #ecfdf5;
  color: #059669;
}

.answer-status.unanswered {
  background: #fef2f2;
  color: #dc2626;
}

.answer-status.reference {
  background: var(--accent-soft);
  color: var(--accent);
}

.answer-content {
  min-height: 160px;
  padding: 18px;
  color: #334155;
  font-size: 14px;
  line-height: 1.9;
  white-space: pre-wrap;
  word-break: break-word;
}

.answer-content.reference {
  background: linear-gradient(180deg, var(--accent-soft), rgba(255, 255, 255, 0.45));
}

.answer-content.empty {
  color: #94a3b8;
  font-style: italic;
}

.improvement-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.improvement-list li {
  display: flex;
  gap: 13px;
  padding: 16px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 14px;
  background: #f8fafc;
}

.improvement-list li > span {
  flex: 0 0 auto;
  color: var(--accent);
  font-size: 12px;
  font-weight: 950;
}

.improvement-list strong {
  display: block;
  color: #1e293b;
  font-size: 13px;
  font-weight: 900;
}

.improvement-list p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.7;
}

.detail-content {
  padding: 20px;
  border-radius: 16px;
  background: #f8fafc;
  color: #334155;
  font-size: 14px;
  line-height: 2;
}

.detail-content :deep(code) {
  padding: 2px 6px;
  border-radius: 6px;
  background: #e0e7ff;
  color: #4338ca;
}

.analysis-side-column {
  position: sticky;
  top: 94px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.side-card {
  padding: 20px;
  border-radius: 18px;
}

.side-card-title {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.side-card-title span {
  color: #94a3b8;
  font-size: 11px;
  font-weight: 800;
}

.side-card-title strong {
  color: var(--accent);
  font-size: 14px;
  font-weight: 950;
}

.score-bar-label {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: #64748b;
  font-size: 12px;
}

.score-bar-label strong {
  color: var(--accent);
}

.score-bar {
  height: 8px;
  margin-top: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: #e2e8f0;
}

.score-bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--accent);
}

.overview-list {
  margin: 18px 0 0;
}

.overview-list > div {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 0;
  border-top: 1px dashed rgba(203, 213, 225, 0.8);
}

.overview-list dt,
.overview-list dd {
  margin: 0;
  font-size: 12px;
}

.overview-list dt {
  color: #94a3b8;
}

.overview-list dd {
  color: #334155;
  font-weight: 800;
  text-align: right;
}

.knowledge-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.knowledge-tags span {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 11px;
  font-weight: 800;
}

.empty-knowledge {
  margin: 0;
  color: #94a3b8;
  font-size: 12px;
}

.review-tip-card {
  display: flex;
  gap: 12px;
  border-color: rgba(59, 130, 246, 0.18);
  background: #eff6ff;
}

.tip-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 30px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #2563eb;
  color: #fff;
  font-weight: 950;
}

.review-tip-card strong {
  color: #1e40af;
  font-size: 13px;
}

.review-tip-card p {
  margin: 6px 0 0;
  color: #475569;
  font-size: 12px;
  line-height: 1.65;
}

.analysis-page-footer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 14px;
  align-items: stretch;
  padding-bottom: 24px;
}

.analysis-page-footer button {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  min-height: 68px;
  padding: 12px 16px;
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-radius: 14px;
  background: #fff;
  color: #475569;
  text-align: left;
}

.analysis-page-footer button:not(.return-report):last-child {
  align-items: flex-end;
  text-align: right;
}

.analysis-page-footer.single-action {
  grid-template-columns: minmax(0, 1fr);
}

.analysis-page-footer.single-action .return-report {
  justify-self: center;
  width: min(100%, 320px);
}

.analysis-page-footer button span {
  color: #94a3b8;
  font-size: 10px;
  font-weight: 800;
}

.analysis-page-footer button strong {
  margin-top: 4px;
  font-size: 13px;
  font-weight: 900;
}

.analysis-page-footer .return-report {
  align-items: center;
  min-width: 156px;
  border-color: #0f172a;
  background: #0f172a;
  color: #fff;
  text-align: center;
}

@media (max-width: 1080px) {
  .analysis-page-topbar {
    grid-template-columns: 1fr auto;
  }

  .topbar-title {
    display: none;
  }

  .analysis-hero,
  .analysis-content-layout {
    grid-template-columns: 1fr;
  }

  .score-summary {
    justify-self: start;
    width: min(100%, 420px);
    box-sizing: border-box;
  }

  .analysis-side-column {
    position: static;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .review-tip-card {
    grid-column: 1 / -1;
  }
}

@media (max-width: 720px) {
  .analysis-page-topbar {
    grid-template-columns: 1fr;
    gap: 10px;
    width: calc(100% - 32px);
    margin-top: 16px;
    padding: 12px 16px;
  }

  .question-switcher {
    justify-self: stretch;
    justify-content: space-between;
  }

  .analysis-page-container {
    padding: 16px;
  }

  .analysis-hero {
    padding: 22px 18px;
  }

  .score-summary {
    align-items: flex-start;
  }

  .score-ring {
    flex-basis: 92px;
    width: 92px;
    height: 92px;
  }

  .score-ring-inner {
    width: 72px;
    height: 72px;
  }

  .score-ring-inner strong {
    font-size: 25px;
  }

  .answer-comparison,
  .improvement-list,
  .analysis-side-column,
  .analysis-page-footer {
    grid-template-columns: 1fr;
  }

  .report-section {
    padding: 18px;
  }

  .feedback-quote {
    padding-left: 46px;
  }

  .analysis-page-footer .return-report {
    order: -1;
  }

  .analysis-page-footer button,
  .analysis-page-footer button:not(.return-report):last-child {
    align-items: center;
    text-align: center;
  }
}
</style>
