<template>
  <div class="resource-setting-container">
    <div class="setting-card">
      <!-- 顶部工作台导航与信息栏 -->
      <header class="setting-header">
        <button
          type="button"
          class="back-btn"
          aria-label="返回重设研学意图"
          @click="emit('back')"
        >
          <ArrowLeftIcon class="w-4 h-4" />
          <span>重设意图</span>
        </button>

        <div class="header-titles">
          <div class="flex items-center gap-2 mb-1">
            <h1 class="text-xl font-bold text-[var(--color-text-strong)] tracking-tight">
              多智能体协同配置工作台
            </h1>
            <span class="studio-badge">
              <span class="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)] animate-pulse"></span>
              MAS STUDIO
            </span>
          </div>
          <p class="text-xs text-[var(--color-text-secondary)]">
            由课程总规划师 (PlanAgent) 解析需求拓扑，分发专研 SubAgent 并行生成多模态教学资料
          </p>
        </div>

        <!-- 常用预设快捷切换 -->
        <div class="preset-switcher" aria-label="快捷方案预设">
          <span class="preset-label">快速预设:</span>
          <div class="preset-buttons">
            <button
              v-for="preset in presetTemplates"
              :key="preset.id"
              type="button"
              class="preset-btn"
              :class="{ active: isPresetActive(preset.agents) }"
              @click="applyPreset(preset.agents)"
            >
              {{ preset.name }}
            </button>
          </div>
        </div>
      </header>

      <!-- 模块一：研学主题与攻坚目标 -->
      <section class="section-block">
        <div class="section-header-row mb-2">
          <label class="section-label">研学意图与攻坚目标</label>
          <span class="section-hint">自然语言意图已锁定，可精准补充攻坚重心</span>
        </div>

        <div class="intent-card">
          <div class="intent-top">
            <div class="intent-badge">
              <SparklesIcon class="w-3.5 h-3.5 text-[var(--color-primary-text)]" />
              <span>已识别研学主题</span>
            </div>
            <span class="intent-status">语义拓扑准备就绪</span>
          </div>
          <div class="intent-content">
            {{ naturalInput || '未指定研学主题' }}
          </div>
        </div>

        <!-- 补充攻坚目标输入框 -->
        <div class="goal-input-wrapper mt-3">
          <div class="flex items-center justify-between mb-1.5">
            <label class="sub-label">核心攻坚目标（可选补充）</label>
            <div class="quick-tags">
              <span class="quick-tag-hint">快速插入:</span>
              <button
                v-for="tag in quickGoalTags"
                :key="tag"
                type="button"
                class="quick-tag-btn"
                @click="appendGoalTag(tag)"
              >
                + {{ tag }}
              </button>
            </div>
          </div>
          <input
            v-model="learningGoal"
            type="text"
            class="goal-input"
            placeholder="例如：深入理解底层执行机理，掌握典型应用模式与避坑指南..."
            @keydown.enter.prevent="handleEnterKey"
          />
        </div>
      </section>

      <!-- 模块二：认知难度梯度 -->
      <section class="section-block">
        <div class="section-header-row mb-3">
          <label class="section-label mb-0">认知难度阶梯</label>
          <span class="section-hint">决定理论推导深度、技术解析细度与工程代码复杂度</span>
        </div>

        <div class="difficulty-grid">
          <div
            v-for="item in difficultyOptions"
            :key="item.value"
            role="button"
            tabindex="0"
            class="difficulty-card"
            :class="{ active: difficulty === item.value }"
            @click="difficulty = item.value"
            @keydown.enter="difficulty = item.value"
            @keydown.space.prevent="difficulty = item.value"
          >
            <div class="diff-card-header">
              <span class="diff-badge" :style="{ backgroundColor: item.badgeBg, color: item.badgeColor }">
                {{ item.tag }}
              </span>
              <span class="diff-title">{{ item.label }}</span>
              <div class="diff-radio ml-auto">
                <span v-if="difficulty === item.value" class="radio-dot"></span>
              </div>
            </div>
            <p class="diff-desc">{{ item.desc }}</p>
            <div class="diff-ratio-bar">
              <span class="ratio-text">{{ item.ratio }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 模块三：协同智能体与交付物矩阵 -->
      <section class="section-block">
        <div class="section-header-row mb-3">
          <div>
            <label class="section-label mb-0.5">交付资源与协同智能体清单</label>
            <span class="section-hint">
              自主勾选需要生成的模态，主智能体将依据依赖关系调度对应 SubAgent
            </span>
          </div>
          <div class="flex items-center gap-2">
            <span class="selection-counter-badge">
              已选 {{ selectedResources.length }} / {{ availableResources.length }} 项
            </span>
            <button
              type="button"
              class="quick-toggle-btn"
              @click="toggleAllResources"
            >
              {{ selectedResources.length === availableResources.length ? '清除非必需' : '全选所有' }}
            </button>
          </div>
        </div>

        <div class="resource-grid">
          <div
            v-for="res in availableResources"
            :key="res.id"
            role="button"
            tabindex="0"
            class="resource-card"
            :class="{ selected: selectedResources.includes(res.id) }"
            @click="toggleResource(res.id)"
            @keydown.enter="toggleResource(res.id)"
            @keydown.space.prevent="toggleResource(res.id)"
          >
            <div class="card-top-row">
              <div class="card-icon" :style="{ backgroundColor: res.bg, color: res.color }">
                <component :is="res.icon" class="w-4 h-4" />
              </div>
              <div class="card-role-group">
                <span class="agent-role-pill">
                  {{ res.agentRole }}
                </span>
                <span class="artifact-format-tag">
                  {{ res.formatTag }}
                </span>
              </div>
              <div class="card-check ml-auto">
                <div v-if="selectedResources.includes(res.id)" class="check-box checked">
                  <CheckIcon class="w-3.5 h-3.5 stroke-[3]" />
                </div>
                <div v-else class="check-box" />
              </div>
            </div>

            <div class="card-info mt-3">
              <div class="flex items-center justify-between mb-1">
                <span class="card-name">{{ res.name }}</span>
                <span class="card-engine-tag">{{ res.engine }}</span>
              </div>
              <p class="card-desc">{{ res.description }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- 模块四：智能体专属偏好配置（自适应平滑展开） -->
      <transition name="expand-fade">
        <section v-if="hasAdvancedOptions" class="section-block advanced-block pt-4 border-t border-dashed border-[var(--color-border-light)]">
          <div class="section-header-row mb-3">
            <label class="section-label mb-0">智能体专属定制参数</label>
            <span class="section-hint">已自动联动当前选中的专业智能体</span>
          </div>

          <div class="preference-grid">
            <!-- 实操代码语言选择器 -->
            <div v-if="selectedResources.includes('code')" class="pref-panel">
              <div class="pref-header">
                <CodeIcon class="w-4 h-4 text-blue-600" />
                <span class="pref-title">实操代码编程语言</span>
                <span class="pref-sub">为工程实训 Agent 指定语言栈</span>
              </div>
              <div class="lang-pills">
                <button
                  v-for="lang in languageOptions"
                  :key="lang.value"
                  type="button"
                  class="lang-pill-btn"
                  :class="{ active: programmingLanguage === lang.value }"
                  @click="programmingLanguage = lang.value"
                >
                  <span class="lang-badge">{{ lang.badge }}</span>
                  <span class="lang-label">{{ lang.label }}</span>
                </button>
              </div>
            </div>

            <!-- 动画视频旁白音色选择器 -->
            <div v-if="selectedResources.includes('cartoon')" class="pref-panel">
              <div class="pref-header">
                <FilmIcon class="w-4 h-4 text-rose-600" />
                <span class="pref-title">动画解说旁白音色</span>
                <span class="pref-sub">为动态渲染 Agent 设定教学语音基调</span>
              </div>
              <div class="voice-cards">
                <button
                  v-for="v in voiceOptions"
                  :key="v.value"
                  type="button"
                  class="voice-card-btn"
                  :class="{ active: cartoonVoice === v.value }"
                  @click="cartoonVoice = v.value"
                >
                  <div class="voice-info">
                    <span class="voice-title">{{ v.title }}</span>
                    <span class="voice-desc">{{ v.desc }}</span>
                  </div>
                  <div class="voice-radio">
                    <span v-if="cartoonVoice === v.value" class="radio-dot"></span>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </section>
      </transition>

      <!-- 模块五：调度编排预览与操作底栏 -->
      <footer class="setting-footer">
        <div class="pipeline-preview">
          <span class="pipeline-title">调度编排流:</span>
          <div class="pipeline-steps">
            <span class="step-pill">1. 主规划解析</span>
            <span class="step-arrow">→</span>
            <span class="step-pill active">
              2. 并行协同 ({{ selectedResources.length }} 项)
            </span>
            <span class="step-arrow">→</span>
            <span class="step-pill">3. 汇编归档</span>
          </div>
        </div>

        <div class="action-cluster">
          <span class="shortcut-tip">可按回车快速启动</span>
          <button
            type="button"
            class="launch-btn"
            :disabled="selectedResources.length === 0"
            @click="handleLaunch"
          >
            <SparklesIcon class="w-4 h-4" />
            <span>启动多智能体协同生成 ({{ selectedResources.length }})</span>
          </button>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  ArrowLeftIcon,
  CheckIcon,
  SparklesIcon,
  FileTextIcon,
  GitBranchIcon,
  CheckSquareIcon,
  CodeIcon,
  BookOpenIcon,
  PresentationIcon,
  FilmIcon,
} from '@lucide/vue'
import type {
  ResourceAgentId,
  DifficultyLevel,
  ProgrammingLanguage,
  CartoonVoice,
  ResourcePreferences,
} from '../model/resource'

const props = defineProps<{
  naturalInput: string
}>()

const emit = defineEmits<{
  (e: 'back'): void
  (e: 'launch', payload: {
    topic: string
    learningGoal: string
    targetResources: ResourceAgentId[]
    difficulty: DifficultyLevel
    preferences: ResourcePreferences
  }): void
}>()

// 表单状态
const learningGoal = ref('')
const difficulty = ref<DifficultyLevel>('intermediate')
const selectedResources = ref<ResourceAgentId[]>([
  'content',
  'mindmap',
  'quiz',
  'code',
  'ppt',
])

const programmingLanguage = ref<ProgrammingLanguage>('python')
const cartoonVoice = ref<CartoonVoice>('teacher')

// 攻坚目标快捷标签
const quickGoalTags = [
  '底层执行机制',
  '经典高频陷阱',
  '工程最佳实践',
  '架构与设计模式',
  '核心考点精要',
]

function appendGoalTag(tag: string) {
  if (!learningGoal.value.trim()) {
    learningGoal.value = `深入理解${tag}`
  } else if (!learningGoal.value.includes(tag)) {
    learningGoal.value = `${learningGoal.value.trim()}，重点剖析${tag}`
  }
}

function handleEnterKey() {
  if (selectedResources.value.length > 0) {
    handleLaunch()
  }
}

// 认知难度配置阶梯
const difficultyOptions = [
  {
    value: 'beginner' as const,
    label: '初学入门',
    tag: '基础推导',
    desc: '注重直观比喻与基础理论推演，适合快速建立知识全貌',
    ratio: '理论推导 70% · 实践示例 30%',
    badgeBg: '#ecfdf5',
    badgeColor: '#059669',
  },
  {
    value: 'intermediate' as const,
    label: '进阶实战',
    tag: '工程规范',
    desc: '强调工程实战标准与核心运行机理，理论与实践紧密融合',
    ratio: '核心机理 50% · 工程实战 50%',
    badgeBg: '#eff6ff',
    badgeColor: '#2563eb',
  },
  {
    value: 'advanced' as const,
    label: '深度探究',
    tag: '源码权衡',
    desc: '深度剖析底层执行模型、极端边界异常与系统性能权衡',
    ratio: '底层剖析 40% · 极限场景 60%',
    badgeBg: '#f5f3ff',
    badgeColor: '#7c3aed',
  },
]

// 7 大专研教学智能体定义
const availableResources = [
  {
    id: 'content' as const,
    name: '课程精讲',
    agentRole: '讲师 SubAgent',
    engine: 'Deep Lecture',
    formatTag: 'Markdown 讲义',
    description: '系统化理论讲解、渐进式知识脉络与核心机理剖析',
    color: '#0d9488',
    bg: '#f0fdfa',
    icon: FileTextIcon,
  },
  {
    id: 'mindmap' as const,
    name: '思维导图',
    agentRole: '拓扑 SubAgent',
    engine: 'Mermaid Engine',
    formatTag: '结构化脑图',
    description: '层级化知识树图谱，多维知识依赖关系一目了然',
    color: '#059669',
    bg: '#ecfdf5',
    icon: GitBranchIcon,
  },
  {
    id: 'quiz' as const,
    name: '巩固练习',
    agentRole: '测验 SubAgent',
    engine: 'Assessment Gen',
    formatTag: '自测试题库',
    description: '单选、多选与判断题目，附带深度解析与考核点标注',
    color: '#d97706',
    bg: '#fffbeb',
    icon: CheckSquareIcon,
  },
  {
    id: 'code' as const,
    name: '代码实操',
    agentRole: '工程 SubAgent',
    engine: 'CodeCraft LLM',
    formatTag: '可运行工程',
    description: '规范代码范例、详细行级注释与自动化自测用例',
    color: '#2563eb',
    bg: '#eff6ff',
    icon: CodeIcon,
  },
  {
    id: 'reading' as const,
    name: '拓展阅读',
    agentRole: '策展 SubAgent',
    engine: 'Curator Spec',
    formatTag: '权威白皮书',
    description: '精选国际权威规范、经典论文与高含金量工程博客',
    color: '#0284c7',
    bg: '#f0f9ff',
    icon: BookOpenIcon,
  },
  {
    id: 'ppt' as const,
    name: '演示课件',
    agentRole: '幻灯 SubAgent',
    engine: 'Slides Renderer',
    formatTag: 'PPTX 课件包',
    description: '多模态 16:9 演示文稿，支持逐页在线高清预览与导出',
    color: '#7c3aed',
    bg: '#f5f3ff',
    icon: PresentationIcon,
  },
  {
    id: 'cartoon' as const,
    name: '概念动画',
    agentRole: '渲染 SubAgent',
    engine: 'Video Studio',
    formatTag: '1080P 视频',
    description: '动态生动呈现抽象机制变化过程，配套专业语音解说',
    color: '#e11d48',
    bg: '#fff1f2',
    icon: FilmIcon,
  },
]

// 快捷预设方案
const presetTemplates: Array<{ id: string; name: string; agents: ResourceAgentId[] }> = [
  {
    id: 'standard',
    name: '推荐标准组 (5项)',
    agents: ['content', 'mindmap', 'quiz', 'code', 'ppt'],
  },
  {
    id: 'core',
    name: '极简理论 (3项)',
    agents: ['content', 'mindmap', 'quiz'],
  },
  {
    id: 'all',
    name: '全模态全家桶 (7项)',
    agents: ['content', 'mindmap', 'quiz', 'code', 'reading', 'ppt', 'cartoon'],
  },
]

function isPresetActive(agents: ResourceAgentId[]): boolean {
  if (agents.length !== selectedResources.value.length) return false
  return agents.every(a => selectedResources.value.includes(a))
}

function applyPreset(agents: ResourceAgentId[]) {
  selectedResources.value = [...agents]
}

function toggleAllResources() {
  if (selectedResources.value.length === availableResources.length) {
    selectedResources.value = ['content', 'mindmap', 'quiz']
  } else {
    selectedResources.value = availableResources.map(r => r.id)
  }
}

// 编程语言选项
const languageOptions: Array<{ value: ProgrammingLanguage; label: string; badge: string }> = [
  { value: 'python', label: 'Python 3.12+', badge: 'PY' },
  { value: 'typescript', label: 'TypeScript', badge: 'TS' },
  { value: 'cpp', label: 'C++ 20', badge: 'C++' },
  { value: 'go', label: 'Go 1.22+', badge: 'GO' },
  { value: 'java', label: 'Java 21 LTS', badge: 'JV' },
]

// 旁白音色选项
const voiceOptions: Array<{ value: CartoonVoice; title: string; desc: string }> = [
  {
    value: 'teacher',
    title: '学术讲师 · 严谨沉稳',
    desc: '语调清晰自然、条理分明，适于深度原理剖析',
  },
  {
    value: 'coach',
    title: '实战教练 · 启发互动',
    desc: '语调生动亲切、强调动手实践与即时反馈',
  },
]

const hasAdvancedOptions = computed(() => {
  return selectedResources.value.includes('code') || selectedResources.value.includes('cartoon')
})

function toggleResource(id: ResourceAgentId) {
  const idx = selectedResources.value.indexOf(id)
  if (idx > -1) {
    if (selectedResources.value.length > 1) {
      selectedResources.value.splice(idx, 1)
    }
  } else {
    selectedResources.value.push(id)
  }
}

function handleLaunch() {
  emit('launch', {
    topic: props.naturalInput,
    learningGoal: learningGoal.value,
    targetResources: [...selectedResources.value],
    difficulty: difficulty.value,
    preferences: {
      programming_language: programmingLanguage.value,
      voice: cartoonVoice.value,
    },
  })
}
</script>

<style scoped>
.resource-setting-container {
  width: 100%;
  max-width: 1560px;
  margin: 0 auto;
  padding: 24px 32px 56px;
  box-sizing: border-box;
}

.setting-card {
  background: var(--color-surface, #fcffff);
  border: 1px solid var(--color-border-light, #ddedec);
  border-radius: 20px;
  padding: 32px 36px;
  box-shadow: 0 4px 24px rgba(23, 59, 66, 0.04), 0 1px 3px rgba(23, 59, 66, 0.02);
  transition: all 0.2s ease;
}

/* 顶部工作台头部 */
.setting-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 28px;
  padding-bottom: 22px;
  border-bottom: 1px solid var(--color-border-light, #ddedec);
  flex-wrap: wrap;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid var(--color-border, #c8e4e3);
  background: var(--color-bg, #f2f8f7);
  color: var(--color-text-strong, #173b42);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s ease;
  flex-shrink: 0;
}

.back-btn:hover {
  background: var(--color-primary-soft, #d8f1f0);
  border-color: var(--color-primary, #46b8b4);
  color: var(--color-primary-text, #205f67);
  transform: translateX(-2px);
}

.header-titles {
  flex: 1;
  min-width: 280px;
}

.studio-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  font-size: 11px;
  font-family: var(--font-mono, monospace);
  font-weight: 600;
  border-radius: 6px;
  background: var(--color-primary-soft, #d8f1f0);
  color: var(--color-primary-text, #205f67);
  border: 1px solid var(--color-primary-border, #b9dedc);
}

.preset-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px;
  background: var(--color-bg, #f2f8f7);
  border-radius: 10px;
  border: 1px solid var(--color-border-light, #ddedec);
  flex-shrink: 0;
}

.preset-label {
  font-size: 11px;
  color: var(--color-text-secondary, #58747a);
  padding-left: 8px;
  font-weight: 500;
}

.preset-buttons {
  display: flex;
  gap: 4px;
}

.preset-btn {
  padding: 6px 12px;
  border-radius: 7px;
  border: 1px solid transparent;
  background: transparent;
  font-size: 12px;
  color: var(--color-text-strong, #173b42);
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.preset-btn:hover {
  background: rgba(255, 255, 255, 0.7);
}

.preset-btn.active {
  background: #ffffff;
  color: var(--color-primary-text, #205f67);
  font-weight: 600;
  border-color: var(--color-primary-border, #b9dedc);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

/* 模块分块样式 */
.section-block {
  margin-bottom: 32px;
}

.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.section-label {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--color-text-strong, #173b42);
  display: inline-block;
}

.section-hint {
  font-size: 12px;
  color: var(--color-text-secondary, #58747a);
}

/* 模块一：主题与攻坚目标 */
.intent-card {
  padding: 18px 22px;
  background: linear-gradient(135deg, rgba(216, 241, 240, 0.4) 0%, rgba(242, 248, 247, 0.85) 100%);
  border-radius: 14px;
  border: 1px solid var(--color-primary-border, #b9dedc);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.intent-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.intent-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-primary-text, #205f67);
  background: var(--color-primary-soft, #d8f1f0);
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid var(--color-primary-border, #b9dedc);
}

.intent-status {
  font-size: 11px;
  font-family: var(--font-mono, monospace);
  color: var(--color-text-faint, #8da4a8);
}

.intent-content {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-strong, #173b42);
  line-height: 1.6;
}

.sub-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--color-text-strong, #173b42);
}

.quick-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.quick-tag-hint {
  font-size: 11px;
  color: var(--color-text-secondary, #58747a);
}

.quick-tag-btn {
  font-size: 11px;
  color: var(--color-primary-text, #205f67);
  background: var(--color-bg, #f2f8f7);
  border: 1px dashed var(--color-primary-border, #b9dedc);
  padding: 3px 9px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-tag-btn:hover {
  background: var(--color-primary-soft, #d8f1f0);
  border-style: solid;
}

.goal-input {
  width: 100%;
  padding: 12px 18px;
  border-radius: 10px;
  border: 1px solid var(--color-border, #c8e4e3);
  background: #ffffff;
  font-size: 13.5px;
  color: var(--color-text-strong, #173b42);
  outline: none;
  box-sizing: border-box;
  transition: all 0.18s ease;
}

.goal-input:focus {
  border-color: var(--color-primary, #46b8b4);
  box-shadow: 0 0 0 3px rgba(70, 184, 180, 0.18);
}

/* 模块二：难度阶梯卡片 */
.difficulty-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.difficulty-card {
  display: flex;
  flex-direction: column;
  padding: 18px 20px;
  border-radius: 14px;
  border: 1.5px solid var(--color-border-light, #ddedec);
  background: var(--color-bg, #f2f8f7);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  box-sizing: border-box;
  outline: none;
  user-select: none;
}

.difficulty-card:hover {
  border-color: var(--color-primary-border, #b9dedc);
  background: #ffffff;
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(23, 59, 66, 0.05);
}

.difficulty-card:focus-visible {
  outline: 2px solid var(--color-primary, #46b8b4);
  outline-offset: 2px;
}

.difficulty-card.active {
  border-color: var(--color-primary, #46b8b4);
  background: #ffffff;
  box-shadow: 0 0 0 1px var(--color-primary, #46b8b4), 0 8px 20px rgba(70, 184, 180, 0.15);
}

.diff-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.diff-badge {
  font-size: 10.5px;
  font-weight: 700;
  padding: 2.5px 7px;
  border-radius: 5px;
  flex-shrink: 0;
}

.diff-title {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--color-text-strong, #173b42);
}

.diff-radio {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1.5px solid var(--color-border, #c8e4e3);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.18s ease;
  flex-shrink: 0;
}

.difficulty-card.active .diff-radio {
  border-color: var(--color-primary, #46b8b4);
  background: var(--color-primary, #46b8b4);
}

.radio-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #ffffff;
}

.diff-desc {
  font-size: 13px;
  color: var(--color-text-secondary, #58747a);
  line-height: 1.6;
  margin-bottom: 14px;
  min-height: 42px;
  flex: 1;
}

.diff-ratio-bar {
  padding-top: 10px;
  border-top: 1px dashed var(--color-border-light, #ddedec);
}

.ratio-text {
  font-size: 11.5px;
  font-family: var(--font-mono, monospace);
  color: var(--color-text-faint, #8da4a8);
}

/* 模块三：智能体矩阵卡片 */
.selection-counter-badge {
  font-size: 11.5px;
  font-family: var(--font-mono, monospace);
  font-weight: 600;
  color: var(--color-primary-text, #205f67);
  background: var(--color-primary-soft, #d8f1f0);
  padding: 4px 10px;
  border-radius: 99px;
  border: 1px solid var(--color-primary-border, #b9dedc);
}

.quick-toggle-btn {
  font-size: 11.5px;
  color: var(--color-text-secondary, #58747a);
  background: var(--color-bg, #f2f8f7);
  border: 1px solid var(--color-border, #c8e4e3);
  padding: 3.5px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-toggle-btn:hover {
  background: var(--color-primary-soft, #d8f1f0);
  color: var(--color-primary-text, #205f67);
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.resource-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 18px 20px;
  border-radius: 14px;
  border: 1.5px solid var(--color-border-light, #ddedec);
  background: var(--color-surface, #fcffff);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  user-select: none;
  outline: none;
  box-sizing: border-box;
}

.resource-card:hover {
  transform: translateY(-2px);
  border-color: var(--color-border, #c8e4e3);
  box-shadow: 0 6px 18px rgba(23, 59, 66, 0.06);
}

.resource-card:focus-visible {
  outline: 2px solid var(--color-primary, #46b8b4);
  outline-offset: 2px;
}

.resource-card.selected {
  border-color: var(--color-primary, #46b8b4);
  background: #ffffff;
  box-shadow: 0 0 0 1px var(--color-primary, #46b8b4), 0 8px 20px rgba(70, 184, 180, 0.12);
}

.card-top-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.resource-card:hover .card-icon {
  transform: scale(1.06);
}

.card-role-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.agent-role-pill {
  font-size: 11.5px;
  font-weight: 700;
  color: var(--color-text-strong, #173b42);
}

.artifact-format-tag {
  font-size: 10.5px;
  font-family: var(--font-mono, monospace);
  color: var(--color-text-secondary, #58747a);
  background: var(--color-bg, #f2f8f7);
  padding: 1.5px 6px;
  border-radius: 4px;
  display: inline-block;
  width: fit-content;
}

.resource-card.selected .artifact-format-tag {
  background: var(--color-primary-soft, #d8f1f0);
  color: var(--color-primary-text, #205f67);
}

.card-check {
  margin-left: auto;
}

.check-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  border: 1.5px solid var(--color-border, #c8e4e3);
  background: var(--color-surface, #fcffff);
  transition: all 0.18s ease;
}

.check-box.checked {
  background: var(--color-primary, #46b8b4);
  border-color: var(--color-primary, #46b8b4);
  color: #ffffff;
}

.card-info {
  display: flex;
  flex-direction: column;
}

.card-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text-strong, #173b42);
}

.card-engine-tag {
  font-size: 10.5px;
  font-family: var(--font-mono, monospace);
  color: var(--color-text-faint, #8da4a8);
}

.card-desc {
  font-size: 12.5px;
  color: var(--color-text-secondary, #58747a);
  line-height: 1.55;
  margin-top: 4px;
}

/* 模块四：偏好定制面板 */
.preference-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 18px;
}

.pref-panel {
  padding: 18px 20px;
  background: var(--color-bg, #f2f8f7);
  border-radius: 14px;
  border: 1px solid var(--color-border-light, #ddedec);
}

.pref-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.pref-title {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--color-text-strong, #173b42);
}

.pref-sub {
  font-size: 11.5px;
  color: var(--color-text-faint, #8da4a8);
  margin-left: auto;
}

.lang-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.lang-pill-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 8px;
  border: 1px solid var(--color-border, #c8e4e3);
  background: #ffffff;
  font-size: 12.5px;
  color: var(--color-text-strong, #173b42);
  cursor: pointer;
  transition: all 0.15s ease;
}

.lang-pill-btn:hover {
  border-color: var(--color-primary, #46b8b4);
  background: var(--color-primary-soft, #d8f1f0);
}

.lang-pill-btn.active {
  background: var(--color-primary-soft, #d8f1f0);
  border-color: var(--color-primary, #46b8b4);
  color: var(--color-primary-text, #205f67);
  font-weight: 600;
}

.lang-badge {
  font-size: 9.5px;
  font-family: var(--font-mono, monospace);
  font-weight: 700;
  background: rgba(0, 0, 0, 0.06);
  padding: 1.5px 5px;
  border-radius: 4px;
}

.voice-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.voice-card-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 16px;
  border-radius: 10px;
  border: 1px solid var(--color-border-light, #ddedec);
  background: #ffffff;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s ease;
}

.voice-card-btn:hover {
  border-color: var(--color-primary-border, #b9dedc);
}

.voice-card-btn.active {
  border-color: var(--color-primary, #46b8b4);
  background: var(--color-primary-soft, #d8f1f0);
}

.voice-title {
  display: block;
  font-size: 12.5px;
  font-weight: 700;
  color: var(--color-text-strong, #173b42);
}

.voice-card-btn.active .voice-title {
  color: var(--color-primary-text, #205f67);
}

.voice-desc {
  display: block;
  font-size: 11.5px;
  color: var(--color-text-secondary, #58747a);
  margin-top: 2px;
}

.voice-radio {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1.5px solid var(--color-border, #c8e4e3);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.voice-card-btn.active .voice-radio {
  border-color: var(--color-primary, #46b8b4);
  background: var(--color-primary, #46b8b4);
}

/* 模块五：操作底栏 */
.setting-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 40px;
  padding-top: 24px;
  border-top: 1px solid var(--color-border-light, #ddedec);
  gap: 20px;
  flex-wrap: wrap;
}

.pipeline-preview {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pipeline-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--color-text-strong, #173b42);
}

.pipeline-steps {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
}

.step-pill {
  padding: 4px 10px;
  border-radius: 6px;
  background: var(--color-bg, #f2f8f7);
  color: var(--color-text-secondary, #58747a);
  border: 1px solid var(--color-border-light, #ddedec);
}

.step-pill.active {
  background: var(--color-primary-soft, #d8f1f0);
  color: var(--color-primary-text, #205f67);
  font-weight: 600;
  border-color: var(--color-primary-border, #b9dedc);
}

.step-arrow {
  color: var(--color-text-faint, #8da4a8);
  font-size: 11px;
}

.action-cluster {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-left: auto;
}

.shortcut-tip {
  font-size: 11.5px;
  font-family: var(--font-mono, monospace);
  color: var(--color-text-faint, #8da4a8);
}

.launch-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 13px 30px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, var(--color-primary, #46b8b4) 0%, var(--color-primary-hover, #35a8a5) 100%);
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 4px 14px rgba(70, 184, 180, 0.35);
  flex-shrink: 0;
}

.launch-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(70, 184, 180, 0.45);
}

.launch-btn:active:not(:disabled) {
  transform: translateY(0);
}

.launch-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

/* 过渡动效 */
.expand-fade-enter-active,
.expand-fade-leave-active {
  transition: all 0.25s ease;
}

.expand-fade-enter-from,
.expand-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 1200px) {
  .resource-grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  }
}

@media (max-width: 1024px) {
  .resource-setting-container {
    padding: 20px 20px 48px;
  }
  .setting-card {
    padding: 24px 20px;
  }
  .difficulty-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .resource-setting-container {
    padding: 16px 12px 36px;
  }
  .setting-card {
    padding: 20px 16px;
  }
  .preference-grid {
    grid-template-columns: 1fr;
  }
  .setting-footer {
    flex-direction: column;
    align-items: stretch;
  }
  .action-cluster {
    margin-left: 0;
    flex-direction: column;
    width: 100%;
  }
  .launch-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
