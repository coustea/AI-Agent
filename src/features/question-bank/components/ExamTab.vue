<template>
  <div class="exam-tab">

    <div class="builder-grid">
      <section class="config-panel">
        <div class="panel-header">
          <div>
            <span class="section-label">Config</span>
            <h3>试卷配置</h3>
          </div>
          <button class="btn-link" @click="$emit('reset-form')">重置</button>
        </div>

        <form class="config-form" @submit.prevent>
          <div class="form-row">
            <div class="form-group">
              <label>试卷标题</label>
              <input v-model="form.title" type="text" class="field" placeholder="例如：数据结构期末模拟" />
            </div>
            <div class="form-group">
              <label>学科</label>
              <select v-model="form.subject" class="field">
                <option value="">全部学科</option>
                <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>难度</label>
              <select v-model="form.difficulty" class="field">
                <option value="混合">混合（随机）</option>
                <option v-for="item in difficulties" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>时长（分钟）</label>
              <input v-model="form.duration" type="number" min="5" max="180" class="field" />
            </div>
          </div>

          <div class="type-counts">
            <span class="section-label">Question Mix</span>
            <h4>题型分布</h4>
            <div class="count-grid">
              <div v-for="item in typeCounts" :key="item.type" class="count-box">
                <span class="type-label">{{ item.label }}</span>
                <input v-model="item.count" type="number" min="0" max="30" class="count-input" />
              </div>
            </div>
          </div>

          <div class="form-actions">
            <button class="btn-secondary" :disabled="loading" @click="$emit('generate-preview')">
              {{ loading ? '生成中...' : '生成预览' }}
            </button>
            <button class="btn-primary" :disabled="preview.length === 0" @click="$emit('start-exam')">开始考试</button>
          </div>
        </form>
      </section>

      <section class="preview-panel">
        <div class="panel-header">
          <div>
            <span class="section-label">Preview</span>
            <h3>试卷预览</h3>
          </div>
          <span v-if="preview.length > 0" class="badge">{{ preview.length }} 题</span>
        </div>

        <div v-if="preview.length > 0" class="preview-list">
          <div v-for="(question, index) in preview" :key="question.id" class="preview-item">
            <div class="item-number">{{ index + 1 }}</div>
            <div class="item-content">
              <div class="item-meta">
                <strong>{{ question.type }}</strong>
                <span class="meta-dot">·</span>
                <span>{{ question.subject }}</span>
                <span class="meta-dot">·</span>
                <span :class="['diff', difficultyClass(question.difficulty)]">{{ question.difficulty || '未评级' }}</span>
              </div>
              <div class="item-text" v-html="renderInline(question.content)"></div>
            </div>
          </div>
        </div>

        <div v-else class="empty-preview">配置试卷参数后，点击“生成预览”查看题目。</div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
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
.exam-tab {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.module-header,
.config-panel,
.preview-panel,
.empty-preview {
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.module-header {
  padding: 22px 24px;
}

.section-label {
  color: var(--cat-eval, #8b5cf6);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.module-header h2,
.panel-header h3,
.type-counts h4 {
  margin: 6px 0 0;
  color: #0f172a;
}

.module-header h2 {
  font-size: 1.35rem;
  font-weight: 700;
}

.subtitle {
  margin: 8px 0 0;
  color: #64748b;
  line-height: 1.65;
}

.builder-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: 20px;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 22px 24px 0;
}

.btn-link {
  border: none;
  background: transparent;
  color: #6366f1;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.btn-link:hover {
  color: #6d28d9;
}

.badge {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(238, 242, 255, 0.92);
  color: #6d28d9;
  font-size: 12px;
  font-weight: 700;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 20px 24px 24px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label,
.type-label {
  color: #475569;
  font-size: 13px;
  font-weight: 700;
}

.field,
.count-input,
.btn-primary,
.btn-secondary {
  min-height: 44px;
  border-radius: 14px;
  font-size: 14px;
  font-family: inherit;
}

.field,
.count-input {
  width: 100%;
  padding: 0 14px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #0f172a;
  outline: none;
  box-sizing: border-box;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.field:focus,
.count-input:focus {
  border-color: rgba(79, 70, 229, 0.42);
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.12);
}

.type-counts {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.count-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.count-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid rgba(226, 232, 240, 0.92);
}

.count-input {
  width: 64px;
  padding: 0 8px;
  text-align: center;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.preview-list {
  display: flex;
  flex-direction: column;
  max-height: 680px;
  overflow-y: auto;
  padding: 8px 24px 24px;
}

.preview-item {
  display: flex;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.82);
}

.preview-item:last-child {
  border-bottom: none;
}

.item-number {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: rgba(238, 242, 255, 0.92);
  color: #6d28d9;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 800;
  flex-shrink: 0;
}

.item-content {
  min-width: 0;
}

.item-meta {
  color: #64748b;
  font-size: 13px;
}

.meta-dot {
  margin: 0 6px;
}

.item-text {
  margin-top: 8px;
  color: #0f172a;
  line-height: 1.65;
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.text-success {
  color: #059669;
}

.text-warning {
  color: #d97706;
}

.text-danger {
  color: #dc2626;
}

.text-neutral {
  color: #64748b;
}

.empty-preview {
  margin: 0 24px 24px;
  padding: 40px 24px;
  border-radius: 18px;
  background: #f8fafc;
  border: 1px dashed rgba(203, 213, 225, 0.96);
  color: #64748b;
  text-align: center;
}

@media (max-width: 960px) {
  .builder-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .module-header,
  .panel-header,
  .config-form,
  .preview-list {
    padding-left: 18px;
    padding-right: 18px;
  }

  .form-row,
  .count-grid {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-direction: column;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
  }

  .empty-preview {
    margin: 0 18px 18px;
  }
}
</style>
