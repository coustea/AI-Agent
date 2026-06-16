<template>
  <div class="exam-tab">
    <div class="header-section">
      <h2>模拟组卷</h2>
      <p class="subtitle">配置参数，生成专属模拟试卷。</p>
    </div>

    <div class="builder-grid">
      <!-- Left: Form -->
      <div class="config-panel">
        <div class="panel-header">
          <h3>试卷配置</h3>
          <button class="btn-text" @click="$emit('reset-form')">重置</button>
        </div>

        <form class="config-form" @submit.prevent>
          <div class="form-row">
            <div class="form-group">
              <label>试卷标题</label>
              <input type="text" v-model="form.title" class="text-input" placeholder="如：数据结构期末模拟" />
            </div>
            <div class="form-group">
              <label>学科</label>
              <select v-model="form.subject" class="select-input">
                <option value="">全部学科</option>
                <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>难度</label>
              <select v-model="form.difficulty" class="select-input">
                <option value="混合">混合（随机）</option>
                <option v-for="item in difficulties" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>时长（分钟）</label>
              <input type="number" v-model="form.duration" min="5" max="180" class="text-input" />
            </div>
          </div>

          <div class="type-counts">
            <label class="section-label">题型分布</label>
            <div class="count-grid">
              <div v-for="item in typeCounts" :key="item.type" class="count-box">
                <span class="type-label">{{ item.label }}</span>
                <input type="number" v-model="item.count" min="0" max="30" class="count-input" />
              </div>
            </div>
          </div>

          <div class="form-actions">
            <button
              class="btn-secondary"
              :disabled="loading"
              @click="$emit('generate-preview')"
            >
              {{ loading ? '生成中...' : '生成预览' }}
            </button>
            <button
              class="btn-primary"
              :disabled="preview.length === 0"
              @click="$emit('start-exam')"
            >
              开始考试
            </button>
          </div>
        </form>
      </div>

      <!-- Right: Preview -->
      <div class="preview-panel">
        <div class="panel-header">
          <h3>试卷预览</h3>
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

        <div v-else class="empty-preview">
          配置试卷参数后，点击「生成预览」查看题目。
        </div>
      </div>
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

const emit = defineEmits<{
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
  gap: 24px;
}

.header-section h2 {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 4px 0;
}

.subtitle {
  color: #6B7280;
  font-size: 14px;
  margin: 0;
}

.builder-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 24px;
}

.config-panel, .preview-panel {
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #E5E7EB;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.btn-text {
  background: none;
  border: none;
  color: #6B7280;
  font-size: 13px;
  cursor: pointer;
}

.btn-text:hover {
  color: #111827;
}

.badge {
  background: #F3F4F6;
  color: #374151;
  padding: 4px 10px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 500;
}

.config-form {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.select-input, .text-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #D1D5DB;
  border-radius: 6px;
  font-size: 14px;
  background: #FFFFFF;
  outline: none;
  transition: border-color 0.15s ease;
  box-sizing: border-box;
}

.select-input:focus, .text-input:focus {
  border-color: #111827;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 12px;
  display: block;
}

.count-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.count-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  padding: 8px 12px;
  border-radius: 6px;
}

.type-label {
  font-size: 13px;
  color: #4B5563;
}

.count-input {
  width: 48px;
  padding: 4px;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  text-align: center;
  font-size: 13px;
  outline: none;
}

.count-input:focus {
  border-color: #111827;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}

.btn-secondary {
  background: #FFFFFF;
  color: #111827;
  border: 1px solid #D1D5DB;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-secondary:hover:not(:disabled) {
  background: #F9FAFB;
  border-color: #9CA3AF;
}

.btn-primary {
  background: #111827;
  color: #FFFFFF;
  border: none;
  padding: 8px 24px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #374151;
}

.btn-primary:disabled, .btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.preview-list {
  padding: 0;
  max-height: 600px;
  overflow-y: auto;
}

.preview-item {
  display: flex;
  gap: 16px;
  padding: 16px 24px;
  border-bottom: 1px solid #F3F4F6;
}

.preview-item:last-child {
  border-bottom: none;
}

.item-number {
  width: 24px;
  height: 24px;
  background: #F3F4F6;
  color: #4B5563;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.item-content {
  flex: 1;
}

.item-meta {
  font-size: 12px;
  color: #6B7280;
  margin-bottom: 6px;
}

.meta-dot {
  margin: 0 6px;
}

.text-success { color: #059669; }
.text-warning { color: #D97706; }
.text-danger { color: #DC2626; }
.text-neutral { color: #6B7280; }

.item-text {
  font-size: 14px;
  color: #111827;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.empty-preview {
  padding: 48px 24px;
  text-align: center;
  color: #6B7280;
  font-size: 14px;
  line-height: 1.6;
}
</style>
