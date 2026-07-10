<template>
  <div class="daily-tab-shell">
    <section v-if="questions.length" class="daily-list-section">
      <div class="daily-summary">
        <div class="summary-copy">
          <strong>每日 10 题</strong>
          <p>已提交 {{ submittedCount }} / {{ questions.length }}，答对 {{ correctCount }} 题</p>
        </div>
      </div>

      <article v-for="(question, index) in questions" :key="question.id" class="daily-question-block">
        <div class="question-meta">
          <div class="meta-left">
            <span class="meta-title">第 {{ index + 1 }} 题</span>
            <div class="meta-tags">
              <span class="meta-tag subject-tag">{{ question.subject }}</span>
              <span class="meta-tag type-tag">{{ question.type }}</span>
              <span v-if="question.difficulty" class="meta-tag difficulty-tag">{{ question.difficulty }}</span>
            </div>
          </div>
        </div>

        <div class="question-content" v-html="renderInline(question.content)"></div>

        <div v-if="isOptionQuestion(question)" class="option-list">
          <button
            v-for="(text, key) in getOptions(question)"
            :key="key"
            type="button"
            :class="[
              'option-item',
              {
                selected: isSelected(question, String(key)),
                correct: submitted[question.id] && isCorrectOption(question, String(key)),
                wrong: submitted[question.id] && isSelected(question, String(key)) && !isCorrectOption(question, String(key)),
              },
            ]"
            :disabled="submitted[question.id]"
            @click="$emit('select-daily-option', question, String(key))"
          >
            <span class="option-key">{{ key }}</span>
            <span class="option-text" v-html="renderInline(text as string)"></span>
          </button>
        </div>

        <textarea
          v-else
          v-model="answers[question.id]"
          :disabled="submitted[question.id]"
          class="answer-box"
          rows="4"
          placeholder="请输入你的答案"
        ></textarea>

        <div class="question-foot">
          <div class="foot-status">
            <span v-if="submitted[question.id]" :class="['status-pill', subjectiveScoreClass(question)]">
              {{ subjectiveScoreText(question) }}
            </span>
            <span v-if="submitted[question.id] && review[question.id]?.score != null" class="score-badge" :class="subjectiveScoreClass(question)">
              {{ review[question.id].score }}分
            </span>
          </div>

          <div class="foot-actions">
            <button
              class="action-link submit"
              type="button"
              :disabled="submitted[question.id] || !hasAnswer(question)"
              @click="$emit('submit-daily', question)"
            >
              <span v-if="reviewing[question.id]" class="reviewing-spinner"></span>
              {{ reviewing[question.id] ? 'AI 评阅中' : '提交答案' }}
            </button>
            <button
              v-if="submitted[question.id]"
              class="action-link"
              type="button"
              @click="$emit('toggle-daily-analysis', question.id)"
            >
              {{ openedAnalysis.has(question.id) ? '收起解析' : '查看解析' }}
            </button>
          </div>
        </div>

        <div v-if="reviewing[question.id]" class="reviewing-banner">
          <span class="reviewing-spinner-lg"></span>
          <span class="reviewing-text">AI 正在评阅你的答案，请稍候...</span>
        </div>

        <div v-if="submitted[question.id] && openedAnalysis.has(question.id)" class="analysis-box">
          <div class="analysis-head">
            <strong>参考答案：{{ formatAnswer(question.answer) }}</strong>
            <span v-if="review[question.id]?.feedback" class="review-feedback">{{ review[question.id].feedback }}</span>
          </div>
          <div v-if="review[question.id]?.improvement_hints?.length" class="improvement-hints">
            <strong>改进建议</strong>
            <ul>
              <li v-for="hint in review[question.id].improvement_hints" :key="hint">{{ hint }}</li>
            </ul>
          </div>
          <div class="analysis-body" v-html="renderInline(question.analysis || '暂无解析')"></div>
        </div>

      </article>
    </section>

    <section v-else class="daily-empty">
      <div class="empty-copy">
        <strong>今日题目暂未生成</strong>
        <p>当前没有可用题目，可重新获取今日练习。</p>
      </div>
      <button class="action-link" type="button" @click="$emit('refresh-daily')">换一组</button>
    </section>
  </div>
</template>

<script setup lang="ts">

// 每日练习题目类型
interface DailyQuestion {
  id: string
  subject: string
  type: string
  content: string
  difficulty?: string | null
  options?: Record<string, string> | null
  answer: string
  analysis: string
  knowledge_points: string[]
}

// 组件属性：题目列表、答题状态、评阅结果
const props = defineProps<{
  questions: DailyQuestion[]
  answers: Record<string, any>
  submitted: Record<string, boolean>
  correct: Record<string, boolean>
  reviewing: Record<string, boolean>
  review: Record<string, any>
  openedAnalysis: Set<string>
  submittedCount: number
  correctCount: number
}>()

// 事件：换题、选择选项、提交、切换解析
defineEmits<{
  (e: 'refresh-daily'): void
  (e: 'select-daily-option', question: DailyQuestion, key: string): void
  (e: 'submit-daily', question: DailyQuestion): void
  (e: 'toggle-daily-analysis', id: string): void
}>()

// 判断是否选择题/判断题
function isOptionQuestion(question: DailyQuestion) {
  return ['选择题', '单选题', '判断题'].includes(question.type)
}

// 获取选项映射表（判断题特殊处理）
function getOptions(question: DailyQuestion) {
  if (question.type === '判断题') return { A: '正确', B: '错误' }
  return question.options || {}
}

// 检查选项是否被选中
function isSelected(question: DailyQuestion, key: string) {
  const ans = props.answers[question.id]
  if (!ans) return false
  if (Array.isArray(ans)) return ans.includes(key)
  return ans === key
}

// 判断选项是否为正确答案
function isCorrectOption(question: DailyQuestion, key: string) {
  let ansText = String(question.answer || '').trim()
  if (question.type === '判断题') {
    const upper = ansText.toUpperCase()
    if (upper === 'A' || ['TRUE', 'T', '正确', '对'].some((item) => upper.includes(item))) ansText = 'A'
    else if (upper === 'B' || ['FALSE', 'F', '错误', '错'].some((item) => upper.includes(item))) ansText = 'B'
  }
  const correctKeys = ansText.split(/[、,，\s]+/).map((item) => item.trim().toUpperCase()).filter(Boolean)
  return correctKeys.includes(key)
}

// 判断题目是否已有答案
function hasAnswer(question: DailyQuestion) {
  const ans = props.answers[question.id]
  if (Array.isArray(ans)) return ans.length > 0
  return !!ans && String(ans).trim().length > 0
}

function formatAnswer(ans: string | undefined) {
  return String(ans || '').replace(/,/g, '、')
}

// 主观题得分对应颜色样式
function subjectiveScoreClass(question: DailyQuestion) {
  const score = props.review[question.id]?.score
  if (score == null) return props.correct[question.id] ? 'success' : 'danger'
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

// 主观题得分对应文本描述
function subjectiveScoreText(question: DailyQuestion) {
  const score = props.review[question.id]?.score
  if (score == null) return props.correct[question.id] ? '回答正确' : '回答错误，已加入错题本'
  if (score >= 80) return '回答优秀'
  if (score >= 60) return '基本正确，部分不足'
  return '回答错误，已加入错题本'
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
.daily-tab-shell {
  display: flex;
  flex-direction: column;
}

.daily-list-section {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.daily-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0 18px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.summary-copy strong {
  color: #0f172a;
  font-size: 16px;
  font-weight: 700;
}

.summary-copy p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

.daily-question-block {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.question-meta,
.question-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex-wrap: wrap;
}

.meta-title {
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
  line-height: 1.3;
}

.meta-tags,
.foot-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.subject-tag {
  background: #eef6ff;
  color: #3d78b5;
}

.type-tag {
  background: #eff6f2;
  color: #288a6e;
}

.difficulty-tag {
  background: #dff2ff;
  color: #3487c7;
}

.question-content {
  color: #1e293b;
  font-size: 14px;
  line-height: 1.7;
}

.option-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.option-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 12px;
  background: #fff;
  color: #1e293b;
  text-align: left;
  cursor: pointer;
}

.option-item.selected {
  border-color: rgba(15, 23, 42, 0.35);
}

.option-item.correct {
  border-color: rgba(16, 185, 129, 0.45);
  background: rgba(236, 253, 245, 0.7);
}

.option-item.wrong {
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(254, 242, 242, 0.7);
}

.option-key {
  display: inline-flex;
  align-items: flex-start;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.06);
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.option-text {
  line-height: 1.7;
  flex: 1;
  text-align: left;
}

.answer-box {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 12px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  resize: vertical;
  box-sizing: border-box;
}

.foot-status {
  min-height: 28px;
  display: flex;
  align-items: center;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
}

.status-pill.success {
  background: rgba(220, 252, 231, 0.8);
  color: #047857;
}

.status-pill.warning {
  background: rgba(254, 249, 195, 0.8);
  color: #854d0e;
}

.status-pill.danger {
  background: rgba(254, 226, 226, 0.8);
  color: #b91c1c;
}

.action-link {
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid rgba(226, 232, 240, 0.96);
  border-radius: 10px;
  background: #fff;
  color: #334155;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.action-link.submit {
  border-color: #0f172a;
  background: #0f172a;
  color: #fff;
}

.analysis-box {
  margin-top: 4px;
  padding-top: 14px;
  border-top: 1px dashed rgba(226, 232, 240, 0.92);
}

.analysis-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  color: #475569;
  font-size: 13px;
}

.analysis-body {
  margin-top: 10px;
  color: #475569;
  line-height: 1.7;
}

.review-feedback {
  color: #6366f1;
  font-weight: 500;
}

.improvement-hints {
  margin-top: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #fffbeb;
  border: 1px solid rgba(250, 204, 21, 0.3);
}

.improvement-hints strong {
  display: block;
  margin-bottom: 6px;
  color: #92400e;
  font-size: 12px;
}

.improvement-hints ul {
  margin: 0;
  padding-left: 18px;
  color: #78350f;
  font-size: 13px;
  line-height: 1.8;
}

.improvement-hints li + li {
  margin-top: 4px;
}

.reviewing-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  vertical-align: middle;
  margin-right: 4px;
}

.reviewing-spinner-lg {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2.5px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.reviewing-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  border: 1px solid rgba(99, 102, 241, 0.15);
}

.reviewing-text {
  color: #4338ca;
  font-size: 13px;
  font-weight: 500;
}

.score-badge {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  margin-left: 8px;
}

.score-badge.success {
  background: #dcfce7;
  color: #166534;
}

.score-badge.warning {
  background: #fef9c3;
  color: #854d0e;
}

.score-badge.danger {
  background: #fee2e2;
  color: #991b1b;
}

.daily-empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 88px;
  padding-top: 4px;
}

.empty-copy {
  min-width: 0;
}

.daily-empty strong {
  color: #0f172a;
  font-size: 15px;
  line-height: 1.3;
}

.daily-empty p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.6;
}

@media (max-width: 640px) {
  .question-meta,
  .question-foot,
  .daily-empty {
    flex-direction: column;
    align-items: stretch;
  }

  .foot-actions {
    justify-content: flex-start;
  }
}
</style>
