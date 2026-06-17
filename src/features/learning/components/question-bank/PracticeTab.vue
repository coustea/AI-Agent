<template>
  <div class="practice-tab">
    <header class="module-header">
      <div class="header-copy">
        <span class="section-label">Practice</span>
        <h2>智能练习</h2>
        <p class="subtitle">把综合练习能力集中在一个页面里，按推荐、错题、组卷和自定义四种方式组织训练。</p>
      </div>
      <div class="metrics-grid">
        <div class="metric-card">
          <span class="metric-label">已练题数</span>
          <strong class="metric-value">{{ stats.totalAttempted }}</strong>
        </div>
        <div class="metric-card">
          <span class="metric-label">正确率</span>
          <strong class="metric-value">{{ accuracyText }}</strong>
        </div>
        <div class="metric-card warning">
          <span class="metric-label">待复习</span>
          <strong class="metric-value">{{ wrongTotal }}</strong>
        </div>
      </div>
    </header>

    <div class="main-grid">
      <section class="tasks-column">
        <div class="section-title-row">
          <span class="section-label">Today</span>
          <h3>今日任务</h3>
        </div>

        <div class="section-card emphasized">
          <div class="task-info">
            <h4>推荐练习</h4>
            <p>根据你当前课程和错题情况，优先安排更适合今天完成的训练任务。</p>
            <div class="tags">
              <span class="tag">{{ recommendedSubject }}</span>
              <span class="tag">{{ recommendedCount }} 题</span>
            </div>
          </div>
          <button class="btn-primary" :disabled="practiceLoading" @click="$emit('start-recommended')">
            {{ practiceLoading ? '加载中...' : '开始练习' }}
          </button>
        </div>

        <div class="section-card warning-card">
          <div class="task-info">
            <h4>错题复习</h4>
            <p>你目前有 {{ wrongTotal }} 道题需要重点回看，优先巩固薄弱点会更快提升整体正确率。</p>
          </div>
          <button class="btn-ghost danger" @click="$emit('switch-tab', 'wrong')">立即复习</button>
        </div>

        <div class="section-card">
          <div class="task-info">
            <h4>模拟组卷</h4>
            <p>按学科、难度和题型组合试卷，用更接近真实考试的节奏检验当前掌握情况。</p>
          </div>
          <button class="btn-secondary" @click="$emit('switch-tab', 'paper')">开始组卷</button>
        </div>
      </section>

      <aside class="sidebar-column">
        <div class="section-card custom-card">
          <div class="panel-head stacked">
            <div>
              <span class="section-label">Custom</span>
              <h4>自定义练习</h4>
            </div>
            <p>按你的节奏设定学科、难度、题型和题量，生成一组更贴近当前目标的训练。</p>
          </div>

          <form class="custom-form" @submit.prevent="handleCustomStart">
            <div class="form-group">
              <label>学科</label>
              <select v-model="form.subject" class="field">
                <option value="">全部学科</option>
                <option v-for="item in subjects" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>

            <div class="form-grid">
              <div class="form-group">
                <label>难度</label>
                <select v-model="form.difficulty" class="field">
                  <option value="">不限难度</option>
                  <option v-for="item in difficulties" :key="item" :value="item">{{ item }}</option>
                </select>
              </div>

              <div class="form-group">
                <label>题型</label>
                <select v-model="form.type" class="field">
                  <option value="">全部题型</option>
                  <option v-for="item in types" :key="item" :value="item">{{ item }}</option>
                </select>
              </div>
            </div>

            <div class="form-group">
              <label>题数</label>
              <input v-model="form.count" type="number" min="1" max="30" class="field" />
            </div>

            <button type="submit" class="btn-primary full-width" :disabled="practiceLoading">
              {{ practiceLoading ? '加载中...' : '生成练习' }}
            </button>
          </form>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'

const props = defineProps<{
  stats: { totalAttempted: number; totalCorrect: number }
  wrongTotal: number
  recommendedSubject: string
  recommendedCount: number
  practiceLoading: boolean
  subjects: string[]
  difficulties: string[]
  types: string[]
}>()

const emit = defineEmits<{
  (e: 'switch-tab', tab: string): void
  (e: 'start-recommended'): void
  (e: 'start-custom', config: { subject: string; difficulty: string; type: string; count: number }): void
}>()

const form = reactive({
  subject: '',
  difficulty: '',
  type: '',
  count: 10,
})

const accuracyText = computed(() => {
  if (!props.stats.totalAttempted) return '0%'
  return `${Math.round((props.stats.totalCorrect / props.stats.totalAttempted) * 100)}%`
})

function handleCustomStart() {
  emit('start-custom', { ...form })
}
</script>

<style scoped>
.practice-tab {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.module-header,
.section-card {
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 22px;
  background: #fff;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.module-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 22px 24px;
}

.header-copy h2,
.section-title-row h3,
.task-info h4,
.panel-head h4 {
  margin: 6px 0 0;
  color: #0f172a;
}

.header-copy h2 {
  font-size: 1.4rem;
  font-weight: 700;
}

.section-label {
  color: #4f46e5;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.subtitle,
.panel-head p,
.task-info p {
  margin: 8px 0 0;
  color: #64748b;
  line-height: 1.65;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(132px, 1fr));
  gap: 12px;
}

.metric-card {
  padding: 16px 18px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 18px;
  background: #f8fafc;
}

.metric-label {
  display: block;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.metric-value {
  display: block;
  margin-top: 8px;
  color: #0f172a;
  font-size: 1.5rem;
  font-weight: 800;
}

.metric-card.warning .metric-value {
  color: #dc2626;
}

.main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(320px, 0.95fr);
  gap: 20px;
}

.tasks-column,
.sidebar-column {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.sidebar-column {
  align-self: start;
}

.section-title-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-card {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 22px;
}

.section-card.emphasized {
  background: linear-gradient(135deg, #ffffff 0%, #eef2ff 100%);
  border-color: rgba(99, 102, 241, 0.22);
}

.section-card.warning-card {
  border-color: rgba(248, 113, 113, 0.24);
  background: rgba(255, 255, 255, 0.96);
}

.task-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-info h4,
.panel-head h4 {
  font-size: 1.05rem;
  font-weight: 700;
}

.tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(238, 242, 255, 0.92);
  color: #4338ca;
  font-size: 12px;
  font-weight: 700;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-head.stacked {
  flex-direction: column;
}

.btn-primary,
.btn-secondary,
.btn-ghost,
.field {
  min-height: 44px;
  border-radius: 14px;
  font-size: 14px;
  font-family: inherit;
}

.btn-primary,
.btn-secondary,
.btn-ghost {
  min-width: 132px;
  padding: 0 18px;
  font-weight: 700;
  cursor: pointer;
  transition: background 150ms ease, border-color 150ms ease, color 150ms ease, opacity 150ms ease;
}

.btn-primary {
  border: 1px solid #4f46e5;
  background: #4f46e5;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: #4338ca;
  border-color: #4338ca;
}

.btn-secondary {
  border: 1px solid rgba(165, 180, 252, 0.4);
  background: rgba(255, 255, 255, 0.9);
  color: #3730a3;
}

.btn-secondary:hover:not(:disabled),
.btn-ghost:hover:not(:disabled) {
  background: #fff;
}

.btn-ghost {
  border: 1px solid rgba(248, 113, 113, 0.26);
  background: rgba(254, 242, 242, 0.8);
  color: #dc2626;
}

.btn-ghost.danger:hover:not(:disabled) {
  background: rgba(254, 226, 226, 0.92);
}

.btn-primary:disabled,
.btn-secondary:disabled,
.btn-ghost:disabled {
  opacity: 0.52;
  cursor: not-allowed;
}

.custom-card .btn-primary {
  width: 100%;
}

.custom-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  color: #475569;
  font-size: 13px;
  font-weight: 700;
}

.field {
  width: 100%;
  padding: 0 14px;
  border: 1px solid rgba(203, 213, 225, 0.96);
  background: #fff;
  color: #0f172a;
  outline: none;
  box-sizing: border-box;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.field:focus {
  border-color: rgba(79, 70, 229, 0.42);
  box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.12);
}

.full-width {
  width: 100%;
}

@media (max-width: 960px) {
  .module-header,
  .main-grid {
    grid-template-columns: 1fr;
  }

  .module-header {
    flex-direction: column;
  }

  .metrics-grid {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .metrics-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .section-card,
  .module-header {
    padding: 18px;
  }

  .btn-primary,
  .btn-secondary,
  .btn-ghost {
    width: 100%;
  }
}
</style>
