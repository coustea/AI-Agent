<template>
  <div class="path-start-hub">
    <!-- 背景发光效果 -->
    <div class="ambient-glow bg-blue"></div>
    <div class="ambient-glow bg-indigo"></div>

    <div class="start-card glass-panel hub-dashboard-grid">
      <!-- 左半区：输入及介绍 -->
      <div class="hub-left-column">
        <div class="start-header-left">
          <span class="eyebrow">AI 学习路径规划</span>
          <h1>开启专属学习旅程</h1>
          <p>输入你的长期学习目标，AI 智能体将结合你的学习画像与背景知识，动态生成定制化的依赖大纲与学习资源。</p>
        </div>

        <!-- 输入区域 -->
        <div class="input-section">
          <el-input
            v-model="goalInput"
            placeholder="例如：大语言模型底层原理与部署"
            class="goal-input glossy-input"
            size="large"
            clearable
            @keyup.enter="triggerGenerate"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <div class="quick-tags">
            <span class="quick-tag-label">快捷灵感：</span>
            <el-tag
              v-for="tag in quickTags"
              :key="tag"
              class="quick-tag-item"
              effect="plain"
              round
              @click="goalInput = tag"
            >
              {{ tag }}
            </el-tag>
          </div>

          <el-button
            type="primary"
            size="large"
            class="generate-btn"
            :loading="isGenerating"
            @click="triggerGenerate"
          >
            <span>生成专属学习路径</span>
            <el-icon class="el-icon--right"><MagicStick /></el-icon>
          </el-button>
        </div>

        <!-- 多智能体生成管线步骤图 -->
        <div class="pipeline-section-compact">
          <h3 class="section-title-small">AI 多智能体协同规划阶段</h3>
          <div class="pipeline-flow">
            <div class="pipeline-step">
              <div class="step-icon-box blue-box"><el-icon><User /></el-icon></div>
              <div class="step-info"><strong>画像分析</strong></div>
            </div>
            <div class="pipeline-connector"><div class="connector-line"></div></div>
            <div class="pipeline-step">
              <div class="step-icon-box teal-box"><el-icon><Search /></el-icon></div>
              <div class="step-info"><strong>联网检索</strong></div>
            </div>
            <div class="pipeline-connector"><div class="connector-line"></div></div>
            <div class="pipeline-step">
              <div class="step-icon-box indigo-box"><el-icon><Connection /></el-icon></div>
              <div class="step-info"><strong>拓扑编排</strong></div>
            </div>
            <div class="pipeline-connector"><div class="connector-line"></div></div>
            <div class="pipeline-step">
              <div class="step-icon-box emerald-box"><el-icon><Checked /></el-icon></div>
              <div class="step-info"><strong>生成大纲</strong></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右半区：推荐路线 -->
      <div class="hub-right-column">
        <div class="templates-section-right">
          <h3 class="section-title">推荐热门学习路线 <el-icon><HotWater /></el-icon></h3>
          <div class="templates-grid">
            <div
              v-for="tmpl in templates"
              :key="tmpl.title"
              class="template-card"
              @click="selectTemplate(tmpl.title)"
            >
              <div class="card-header">
                <div class="tmpl-icon-box" :class="tmpl.colorClass">
                  <el-icon><component :is="tmpl.icon" /></el-icon>
                </div>
                <div class="tmpl-title-block">
                  <h4>{{ tmpl.title }}</h4>
                  <div class="tmpl-tags">
                    <span class="tmpl-tag diff-tag">{{ tmpl.difficulty }}</span>
                    <span class="tmpl-tag duration-tag">{{ tmpl.duration }}</span>
                  </div>
                </div>
              </div>
              <p class="tmpl-desc">{{ tmpl.description }}</p>
              <div class="tmpl-meta">
                <span>{{ tmpl.stagesCount }} 学习阶段</span>
                <span class="dot">•</span>
                <span>{{ tmpl.nodesCount }} 核心节点</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Search, User, Connection, Checked, Cpu, Coordinate, Memo, Reading, MagicStick, HotWater } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

defineProps<{
  isGenerating: boolean
}>()

const emit = defineEmits<{
  (e: 'generate-path', goal: string): void
}>()

const goalInput = ref('')

const quickTags = [
  'React 19 渲染机制与实践',
  'Vue 3 源码解析',
  'Node.js 高级异步编程',
  '机器学习核心数学'
]

const templates = [
  {
    title: '大语言模型底层原理与部署',
    description: '深入了解 Transformer 架构，从零预训练、微调（LORA）到量化与 vLLM 高并发推理服务部署。',
    difficulty: '高级',
    duration: '14 天',
    stagesCount: 3,
    nodesCount: 9,
    icon: Cpu,
    colorClass: 'tone-blue'
  },
  {
    title: 'Python 全栈开发入门',
    description: '面向零基础学员，覆盖核心语法，掌握 FastAPI 后端框架与 Vue3 前端开发，完成高可用全栈项目。',
    difficulty: '入门',
    duration: '21 天',
    stagesCount: 4,
    nodesCount: 15,
    icon: Coordinate,
    colorClass: 'tone-emerald'
  },
  {
    title: '机器学习数学基础',
    description: '打通机器学习背后的数学瓶颈，专注于线性代数、微积分、概率论与反向传播求导。',
    difficulty: '进阶',
    duration: '9 天',
    stagesCount: 2,
    nodesCount: 7,
    icon: Memo,
    colorClass: 'tone-indigo'
  },
  {
    title: '前端框架 React 进阶',
    description: '解析 React 19 渲染机制与 Fiber 架构，深入掌握自定义 Hooks、状态管理及性能调优。',
    difficulty: '进阶',
    duration: '12 天',
    stagesCount: 3,
    nodesCount: 8,
    icon: Reading,
    colorClass: 'tone-amber'
  }
]

function selectTemplate(title: string) {
  goalInput.value = title
  triggerGenerate()
}

function triggerGenerate() {
  if (!goalInput.value.trim()) {
    ElMessage.warning('请输入您的学习目标或选择上方推荐模板')
    return
  }
  emit('generate-path', goalInput.value.trim())
}
</script>

<style scoped>
.path-start-hub {
  position: relative;
  max-width: 1120px;
  margin: 48px auto 0;
  padding: 0 16px 48px;
}

/* 霓虹背景发光 */
.ambient-glow {
  position: absolute;
  width: 380px;
  height: 380px;
  border-radius: 50%;
  filter: blur(140px);
  opacity: 0.15;
  pointer-events: none;
  z-index: 0;
}
.ambient-glow.bg-blue {
  top: -60px;
  left: 10%;
  background: var(--tone-blue);
}
.ambient-glow.bg-indigo {
  bottom: 40px;
  right: 15%;
  background: var(--color-primary);
}

.glass-panel {
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-2xl);
  padding: 48px;
  box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.hub-dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 48px;
  align-items: start;
}

.start-header-left {
  text-align: left;
  margin-bottom: 32px;
}

.start-header-left h1 {
  font-size: var(--text-2xl);
  font-weight: var(--weight-extrabold);
  color: var(--color-text);
  margin: 0 0 16px;
  letter-spacing: -0.02em;
}

.start-header-left p {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: var(--leading-relaxed);
}

/* 搜索/输入模块 */
.input-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 40px;
}

.quick-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.quick-tag-label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: var(--weight-bold);
}

.quick-tag-item {
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-tag-item:hover {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  border-color: var(--color-primary-border);
}

.generate-btn {
  height: 54px;
  width: 100%;
  border-radius: var(--radius-lg) !important;
  font-size: var(--text-base);
  box-shadow: 0 4px 14px rgba(79, 70, 229, 0.25) !important;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 规划管线图 */
.pipeline-section-compact {
  padding: 24px;
  background: rgba(15, 23, 42, 0.02);
  border-radius: var(--radius-xl);
  border: 1px dashed var(--color-border);
  margin-top: 16px;
}

.section-title-small {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0 0 16px;
  text-align: center;
}

.section-title {
  font-size: var(--text-md);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.pipeline-flow {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.pipeline-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  text-align: center;
}

.step-icon-box {
  width: 42px;
  height: 42px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
}
.step-icon-box.blue-box { background: rgba(37, 99, 235, 0.08); color: var(--tone-blue); }
.step-icon-box.teal-box { background: rgba(13, 148, 136, 0.08); color: #0d9488; }
.step-icon-box.indigo-box { background: rgba(79, 70, 229, 0.08); color: var(--color-primary); }
.step-icon-box.emerald-box { background: rgba(16, 185, 129, 0.08); color: var(--color-success); }

.step-info {
  display: flex;
}

.step-info strong {
  font-size: 0.72rem;
  color: var(--color-text-strong);
}

.pipeline-connector {
  flex: 1;
  padding: 0 8px;
  margin-top: -16px; /* align with icons */
}

.connector-line {
  height: 2px;
  background: repeating-linear-gradient(90deg, var(--color-border), var(--color-border) 4px, transparent 4px, transparent 8px);
}

/* 推荐路线模板卡片 */
.templates-section-right {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.templates-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}

.template-card {
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: var(--radius-xl);
  padding: 24px;
  cursor: pointer;
  text-align: left;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 4px 12px -4px rgba(0, 0, 0, 0.03);
}

.template-card:hover {
  background: rgba(255, 255, 255, 0.85);
  transform: translateY(-4px);
  border-color: rgba(255, 255, 255, 0.8);
  box-shadow: 0 20px 32px -8px rgba(0, 0, 0, 0.08);
}

.template-card .card-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.tmpl-icon-box {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  background: rgba(15, 23, 42, 0.03);
}
.tmpl-icon-box.tone-blue { color: var(--tone-blue); background: rgba(37, 99, 235, 0.08); }
.tmpl-icon-box.tone-emerald { color: var(--color-success); background: rgba(16, 185, 129, 0.08); }
.tmpl-icon-box.tone-indigo { color: var(--color-primary); background: rgba(79, 70, 229, 0.08); }
.tmpl-icon-box.tone-amber { color: #d97706; background: rgba(217, 119, 6, 0.08); }

.tmpl-title-block {
  display: grid;
  gap: 4px;
}

.tmpl-title-block h4 {
  font-size: var(--text-md);
  font-weight: var(--weight-bold);
  color: var(--color-text-strong);
  margin: 0;
}

.tmpl-tags {
  display: flex;
  gap: 6px;
}

.tmpl-tag {
  font-size: 0.72rem;
  font-weight: var(--weight-semibold);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
}

.diff-tag {
  background: rgba(15, 23, 42, 0.05);
  color: var(--color-text-secondary);
}

.duration-tag {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.tmpl-desc {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin: 0 0 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tmpl-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.tmpl-meta .dot {
  font-size: 10px;
}

@media (max-width: 960px) {
  .hub-dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
