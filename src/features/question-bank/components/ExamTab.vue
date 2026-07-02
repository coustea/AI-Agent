<template>
  <div class="exam-shell">
    <div class="workspace-grid">
      <section class="workspace-pane config-workspace">
        <div class="section-head">
          <div>
            <span class="section-kicker">组卷配置</span>
            <h3>考试参数配置区</h3>
          </div>
          <button class="text-btn" type="button" @click="$emit('reset-form')">重置</button>
        </div>

        <form class="config-form" @submit.prevent>
          <div class="field-block">
            <div class="block-title">
              <h4>基础信息</h4>
              <p>设置考试标题、学科、难度和作答时长，用于生成本次试卷。</p>
            </div>

            <div class="field-row">
              <div class="field-group span-two">
                <label>标题</label>
                <input v-model="form.title" type="text" class="field" placeholder="例如：数据结构期末模拟" />
              </div>
              <div class="field-group">
                <label>学科</label>
                <select v-model="form.subject" class="field">
                  <option value="">全部学科</option>
                  <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
                </select>
              </div>
              <div class="field-group">
                <label>难度</label>
                <select v-model="form.difficulty" class="field">
                  <option value="混合">混合</option>
                  <option v-for="item in difficulties" :key="item" :value="item">{{ item }}</option>
                </select>
              </div>
              <div class="field-group">
                <label>时长（分钟）</label>
                <input v-model="form.duration" type="number" min="5" max="180" class="field" />
              </div>
            </div>
          </div>

          <div class="field-block counts-section">
            <div class="block-title">
              <h4>题型分布</h4>
              <p>配置每种题型的出题数量，系统会按当前参数生成试卷预览。</p>
            </div>

            <div class="count-table">
              <div class="count-table-head">
                <span>题型</span>
                <span>数量</span>
              </div>
              <div v-for="item in typeCounts" :key="item.type" class="count-row">
                <span>{{ item.label }}</span>
                <input v-model="item.count" type="number" min="0" max="30" class="count-input" />
              </div>
            </div>
          </div>

          <div class="action-row">
            <button class="secondary-btn" type="button" :disabled="loading" @click="$emit('generate-preview')">
              {{ loading ? '生成中...' : '生成预览' }}
            </button>
            <button class="primary-btn" type="button" :disabled="preview.length === 0" @click="$emit('start-exam')">
              开始考试
            </button>
          </div>
        </form>
      </section>

      <section class="workspace-pane preview-workspace">
        <div class="section-head">
          <div>
            <span class="section-kicker">试卷预览</span>
            <h3>试卷预览区</h3>
          </div>
          <span class="preview-count">{{ preview.length }} 题</span>
        </div>

        <div v-if="preview.length" class="preview-list">
          <article v-for="(question, index) in preview" :key="question.id" class="preview-item">
            <div class="preview-side">
              <span class="preview-no">第 {{ index + 1 }} 题</span>
              <div class="preview-tags">
                <span>{{ question.subject }}</span>
                <span>{{ question.type }}</span>
                <span :class="difficultyClass(question.difficulty)">{{ question.difficulty || '未评级' }}</span>
              </div>
            </div>

            <div class="preview-main">
              <MarkdownRenderer class="preview-text" :content="String(question.content || '')" />
            </div>
          </article>
        </div>

        <div v-else class="preview-empty">
          <strong>暂无试卷预览</strong>
          <p>请先在左侧完成考试参数和题型数量配置。</p>
          <p>点击“生成预览”后，这里会展示即将进入考试的题目列表。</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import MarkdownRenderer from '@/shared/ui/MarkdownRenderer.vue'

defineProps<{
  form: { title: string; subject: string; difficulty: string; duration: number }
  typeCounts: { type: string; label: string; count: number }[]
  preview: any[]
  loading: boolean
  subjects: string[]
  difficulties: string[]
}>()

defineEmits<{
  (e: 'reset-form'): void
  (e: 'generate-preview'): void
  (e: 'start-exam'): void
}>()

function difficultyClass(diff: string) {
  if (diff === '简单') return 'text-success'
  if (diff === '中等') return 'text-warning'
  if (!diff) return 'text-neutral'
  return 'text-danger'
}

</script>

<style scoped>
.exam-shell {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 18px;
  align-items: start;
}

.workspace-pane {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.config-workspace {
  padding-right: 0;
  padding-bottom: 16px;
  border-right: none;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.preview-workspace {
  padding-left: 0;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.section-kicker {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.section-head h3 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 1.08rem;
  font-weight: 700;
  line-height: 1.35;
}

.text-btn {
  border: none;
  background: transparent;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.block-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.block-title h4 {
  margin: 0;
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
}

.block-title p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.55;
}

.field-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 12px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-group.span-two {
  grid-column: span 2;
}

.field-group label {
  color: #475569;
  font-size: 12px;
  font-weight: 600;
}

.field,
.count-input {
  width: 100%;
  min-height: 34px;
  padding: 0 10px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  border-radius: 10px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  box-sizing: border-box;
  outline: none;
}

.field:focus,
.count-input:focus {
  border-color: rgba(148, 163, 184, 0.96);
}

.counts-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.count-table {
  display: flex;
  flex-direction: column;
  border-top: 1px solid rgba(226, 232, 240, 0.92);
}

.count-table-head,
.count-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 96px;
  gap: 12px;
  align-items: center;
}

.count-table-head {
  padding: 0 0 6px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.count-table-head span {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.count-row {
  padding: 7px 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.count-row span {
  color: #334155;
  font-size: 14px;
}

.count-input {
  text-align: center;
}

.action-row {
  display: flex;
  gap: 10px;
  padding-top: 2px;
}

.primary-btn,
.secondary-btn {
  min-height: 34px;
  padding: 0 14px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.primary-btn {
  border: 1px solid #0f172a;
  background: #0f172a;
  color: #fff;
}

.secondary-btn {
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #334155;
}

.preview-count {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.preview-list {
  display: flex;
  flex-direction: column;
  border-top: 1px solid rgba(226, 232, 240, 0.92);
  max-height: 280px;
  overflow: auto;
}

.preview-item {
  display: grid;
  grid-template-columns: 132px minmax(0, 1fr);
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.preview-side {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.preview-no {
  color: #334155;
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.preview-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.preview-tags span {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  background: rgba(248, 250, 252, 0.92);
  color: #475569;
  font-size: 11px;
}

.preview-main {
  min-width: 0;
}

.preview-text {
  color: #1e293b;
  font-size: 13px;
  line-height: 1.5;
}

.preview-empty {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px 0;
  border-top: 1px solid rgba(226, 232, 240, 0.92);
}

.preview-empty strong {
  color: #0f172a;
  font-size: 16px;
  font-weight: 700;
}

.preview-empty p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.text-success {
  color: #047857;
}

.text-warning {
  color: #b45309;
}

.text-danger {
  color: #b91c1c;
}

.text-neutral {
  color: #475569;
}

@media (max-width: 980px) {
  .config-workspace {
    padding-bottom: 14px;
  }

  .preview-workspace {
    padding-left: 0;
  }
}

@media (max-width: 720px) {
  .field-row {
    grid-template-columns: 1fr;
  }

  .field-group.span-two {
    grid-column: auto;
  }

  .action-row {
    flex-direction: column;
  }

  .preview-item {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}
</style>
