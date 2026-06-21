<template>
  <div class="practice-tab">

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
import { reactive } from 'vue'

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

/* ================== Layout & Shells ================== */
.main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(320px, 0.95fr);
  gap: 24px;
}

@media (max-width: 960px) {
  .main-grid {
    grid-template-columns: 1fr;
  }
}

.module-header,
.section-card {
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(16px) saturate(120%);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.module-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 32px;
}

@media (max-width: 900px) {
  .module-header {
    flex-direction: column;
    align-items: stretch;
    padding: 24px;
  }
}

.section-card {
  padding: 28px;
}

.section-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 36px rgba(15, 23, 42, 0.06);
}

.tasks-column,
.sidebar-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sidebar-column {
  align-self: start;
}

/* ================== Typography & Headers ================== */
.section-label {
  color: #8b5cf6;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.header-copy h2 {
  margin: 4px 0 0;
  color: #0f172a;
  font-size: 1.45rem;
  font-weight: 800;
  letter-spacing: -0.01em;
}

.subtitle {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 14px;
  line-height: 1.65;
}

.section-title-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.section-title-row h3 {
  margin: 0;
  color: #0f172a;
  font-size: 1.35rem;
  font-weight: 800;
}

/* ================== Metric Stats Cards ================== */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(110px, 1fr));
  gap: 12px;
}

.metric-card {
  padding: 14px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(226, 232, 240, 0.8);
}

.metric-label {
  display: block;
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.metric-value {
  display: block;
  margin-top: 6px;
  color: #0f172a;
  font-size: 1.4rem;
  font-weight: 800;
}

.metric-card.warning .metric-value {
  color: #dc2626;
}

/* ================== Emphasized Task Cards ================== */
.section-card.emphasized {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.85) 0%, rgba(245, 243, 255, 0.85) 100%);
  border-color: rgba(139, 92, 246, 0.25);
  box-shadow: 0 10px 25px rgba(139, 92, 246, 0.06);
}

.section-card.emphasized:hover {
  border-color: rgba(139, 92, 246, 0.35);
  box-shadow: 0 14px 32px rgba(139, 92, 246, 0.1);
}

.section-card.warning-card {
  border-color: rgba(239, 68, 68, 0.2);
  background: rgba(255, 255, 255, 0.8);
}

.section-card.warning-card:hover {
  border-color: rgba(239, 68, 68, 0.3);
  box-shadow: 0 14px 32px rgba(239, 68, 68, 0.05);
}

.task-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-info h4,
.panel-head h4 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  color: #0f172a;
}

.task-info p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13.5px;
  line-height: 1.6;
}

.tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.tag {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 99px;
  background: rgba(139, 92, 246, 0.06);
  color: #7c3aed;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid rgba(139, 92, 246, 0.12);
}

/* ================== Floating Custom Form Card ================== */
.section-card.custom-card {
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(24px) saturate(130%);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
}

.section-card.custom-card:hover {
  box-shadow: 0 20px 48px rgba(139, 92, 246, 0.12), 0 4px 12px rgba(0, 0, 0, 0.01);
  border-color: rgba(139, 92, 246, 0.25);
}

.panel-head.stacked {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 18px;
}

.panel-head.stacked p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.5;
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
  gap: 6px;
}

.form-group label {
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.field {
  height: 40px;
  border-radius: 12px;
  font-size: 13.5px;
  font-family: inherit;
  width: 100%;
  padding: 0 12px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.7);
  color: #0f172a;
  outline: none;
  box-sizing: border-box;
  transition: all 0.2s ease;
}

.field:focus {
  border-color: rgba(139, 92, 246, 0.4);
  background: #fff;
  box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.08);
}

/* ================== Actions & Buttons ================== */
.btn-primary,
.btn-secondary,
.btn-ghost {
  height: 42px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  padding: 0 20px;
}

.btn-primary {
  background: #8b5cf6;
  color: #fff;
  box-shadow: 0 4px 10px rgba(139, 92, 246, 0.15);
}

.btn-primary:hover:not(:disabled) {
  background: #7c3aed;
  box-shadow: 0 6px 14px rgba(139, 92, 246, 0.25);
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(226, 232, 240, 0.9);
  color: #475569;
}

.btn-secondary:hover {
  background: #f8fafc;
  color: #1e293b;
  transform: translateY(-1px);
}

.btn-ghost {
  border: 1px solid rgba(239, 68, 68, 0.2);
  background: rgba(239, 68, 68, 0.04);
  color: #ef4444;
}

.btn-ghost:hover {
  background: #ef4444;
  color: #fff;
  border-color: #ef4444;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.15);
}

.full-width {
  width: 100%;
}

/* ================== Responsive Styles ================== */
@media (max-width: 640px) {
  .metrics-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }

  .section-card,
  .module-header {
    padding: 20px;
  }

  .btn-primary,
  .btn-secondary,
  .btn-ghost {
    width: 100%;
    justify-content: center;
  }
}
</style>
