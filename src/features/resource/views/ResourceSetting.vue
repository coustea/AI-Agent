<template>
  <div class="resource-setting-container">
    <div class="setting-card">
      <!-- 顶部导航与工作坊标题 -->
      <div class="setting-header">
        <button type="button" class="back-btn" @click="emit('back')">
          <ArrowLeft class="w-4 h-4" />
          <span>重设意图</span>
        </button>
        <div class="header-titles">
          <div class="flex items-center gap-2 mb-1">
            <h2 class="text-lg font-bold text-[var(--color-text-strong)] tracking-tight">
              多智能体资源协同定制
            </h2>
            <span class="inline-flex items-center px-2 py-0.5 text-[11px] font-mono font-medium rounded bg-[var(--color-primary-soft)] text-[var(--color-primary-text)] border border-[var(--color-primary-border)]">
              MAS STUDIO
            </span>
          </div>
          <p class="text-xs text-[var(--color-text-secondary)]">
            由课程总规划师 (PlanAgent) 解析需求拓扑，分发专研 SubAgent 并行生成多模态教学资料
          </p>
        </div>
      </div>

      <!-- 学习主题与目标解析 -->
      <div class="section-block">
        <label class="section-label">研学意图与核心目标</label>
        <div class="intent-card">
          <div class="intent-badge-row">
            <span class="intent-badge">
              <span class="w-1.5 h-1.5 rounded-full bg-[var(--color-primary)]"></span>
              已识别研学主题
            </span>
            <span class="text-[11px] font-mono text-[var(--color-text-faint)]">
              自然语言意图已锁定
            </span>
          </div>
          <div class="intent-text">
            {{ naturalInput || '未指定研学主题' }}
          </div>
        </div>

        <div class="goal-input-box mt-3">
          <label class="sub-label">核心攻坚目标（可选精准补充）</label>
          <input
            v-model="learningGoal"
            type="text"
            class="goal-input"
            placeholder="例如：深入理解底层执行机理，掌握典型应用模式与避坑指南..."
          />
        </div>
      </div>

      <!-- 认知难度阶梯 -->
      <div class="section-block">
        <div class="section-header-row mb-2.5">
          <label class="section-label mb-0">认知难度阶梯</label>
          <span class="text-[11px] font-mono text-[var(--color-text-secondary)]">
            决定理论推导深度与代码实现复杂度
          </span>
        </div>
        <div class="difficulty-capsules">
          <button
            v-for="item in difficultyOptions"
            :key="item.value"
            type="button"
            class="capsule-btn"
            :class="{ active: difficulty === item.value }"
            @click="difficulty = item.value"
          >
            <div class="flex items-center justify-between mb-1">
              <span class="capsule-title">{{ item.label }}</span>
              <span
                v-if="difficulty === item.value"
                class="w-2 h-2 rounded-full bg-[var(--color-primary)]"
              ></span>
            </div>
            <span class="capsule-desc">{{ item.desc }}</span>
          </button>
        </div>
      </div>

      <!-- 协同智能体与交付物清单 -->
      <div class="section-block">
        <div class="section-header-row mb-3">
          <div>
            <label class="section-label mb-0.5">交付资源与协同智能体清单</label>
            <span class="text-xs text-[var(--color-text-secondary)]">
              自主勾选需要生成的模态，主智能体将依据依赖关系调度对应 SubAgent
            </span>
          </div>
          <span class="selection-counter-badge">
            已选 {{ selectedResources.length }} / {{ availableResources.length }} 项
          </span>
        </div>

        <div class="resource-grid">
          <div
            v-for="res in availableResources"
            :key="res.id"
            class="resource-card"
            :class="{ selected: selectedResources.includes(res.id) }"
            @click="toggleResource(res.id)"
          >
            <div class="card-top-row">
              <div class="card-icon" :style="{ backgroundColor: res.bg, color: res.color }">
                <component :is="res.icon" class="w-4 h-4" />
              </div>
              <span class="agent-role-pill">
                {{ res.agentRole }}
              </span>
              <div class="card-check ml-auto">
                <div v-if="selectedResources.includes(res.id)" class="check-box checked">
                  <Check class="w-3.5 h-3.5 stroke-[3]" />
                </div>
                <div v-else class="check-box" />
              </div>
            </div>

            <div class="card-info mt-2">
              <span class="card-name">{{ res.name }}</span>
              <span class="card-desc">{{ res.description }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 高级偏好设置（自适应展开） -->
      <div v-if="hasAdvancedOptions" class="section-block advanced-block pt-4 border-t border-dashed border-[var(--color-border-light)]">
        <label class="section-label mb-2.5">生成偏好参数</label>
        <div class="preference-row">
          <div v-if="selectedResources.includes('code')" class="pref-item">
            <span class="pref-label">实操代码语言</span>
            <select v-model="programmingLanguage" class="pref-select">
              <option value="python">Python 3.12+</option>
              <option value="cpp">C++ 20</option>
              <option value="typescript">TypeScript</option>
              <option value="go">Go 1.22+</option>
              <option value="java">Java 21</option>
            </select>
          </div>

          <div v-if="selectedResources.includes('cartoon')" class="pref-item">
            <span class="pref-label">动画旁白音色</span>
            <select v-model="cartoonVoice" class="pref-select">
              <option value="teacher">学术讲师 · 严谨沉稳</option>
              <option value="coach">实战教练 · 启发互动</option>
            </select>
          </div>
        </div>
      </div>

      <!-- 底部执行操作栏 -->
      <div class="setting-footer">
        <div class="footer-tip">
          <span class="font-medium text-[var(--color-text-strong)]">并行编排保障：</span>
          主 PlanAgent 将根据选择自动构建依赖 DAG 并分发 SubAgent 协同生成，过程全透明可观测。
        </div>
        <button
          type="button"
          class="launch-btn"
          :disabled="selectedResources.length === 0"
          @click="handleLaunch"
        >
          <Sparkle class="w-4 h-4" />
          <span>开始智能规划与生成 ({{ selectedResources.length }})</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  ArrowLeftIcon as ArrowLeft,
  CheckIcon as Check,
  SparklesIcon as Sparkle,
  FileTextIcon as DocumentIcon,
  GitBranchIcon as MindmapIcon,
  CheckSquareIcon as QuizIcon,
  CodeIcon as CodeIcon,
  BookOpenIcon as BookIcon,
  PresentationIcon as PresentationIcon,
  FilmIcon as VideoIcon,
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

const difficultyOptions = [
  { value: 'beginner' as const, label: '初学入门', desc: '注重直观比喻与基础理论推导' },
  { value: 'intermediate' as const, label: '进阶实战', desc: '强调工程实践规范与核心机理' },
  { value: 'advanced' as const, label: '深度探究', desc: '剖析底层源码机制与性能权衡' },
]

const availableResources = [
  {
    id: 'content' as const,
    name: '课程精讲',
    agentRole: '讲义生成 Agent',
    description: '系统化理论解析、渐进式知识脉络',
    color: '#0d9488',
    bg: '#f0fdfa',
    icon: DocumentIcon,
  },
  {
    id: 'mindmap' as const,
    name: '思维导图',
    agentRole: '知识拓扑 Agent',
    description: '结构化知识树、层次逻辑一目了然',
    color: '#059669',
    bg: '#ecfdf5',
    icon: MindmapIcon,
  },
  {
    id: 'quiz' as const,
    name: '巩固练习',
    agentRole: '随堂出题 Agent',
    description: '精选针对性习题、强化理解记忆',
    color: '#d97706',
    bg: '#fffbeb',
    icon: QuizIcon,
  },
  {
    id: 'code' as const,
    name: '代码实操',
    agentRole: '工程实训 Agent',
    description: '精炼工程范例、动手实践可运行代码',
    color: '#2563eb',
    bg: '#eff6ff',
    icon: CodeIcon,
  },
  {
    id: 'reading' as const,
    name: '拓展阅读',
    agentRole: '文献推荐 Agent',
    description: '经典文献推荐、RFC 与权威工程白皮书',
    color: '#0284c7',
    bg: '#f0f9ff',
    icon: BookIcon,
  },
  {
    id: 'ppt' as const,
    name: '演示课件',
    agentRole: '幻灯课件 Agent',
    description: '多模态 PPT 课件、支持在线逐页预览',
    color: '#7c3aed',
    bg: '#f5f3ff',
    icon: PresentationIcon,
  },
  {
    id: 'cartoon' as const,
    name: '概念动画',
    agentRole: '动态渲染 Agent',
    description: '1080p 概念教学视频、同步语音解说',
    color: '#e11d48',
    bg: '#fff1f2',
    icon: VideoIcon,
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
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 20px;
}

.setting-card {
  background: var(--color-surface, #fcffff);
  border: 1px solid var(--color-border-light, #ddedec);
  border-radius: var(--radius-lg, 12px);
  padding: 32px;
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.05));
}

.setting-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--color-border-light, #ddedec);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: var(--radius-sm, 6px);
  border: 1px solid var(--color-border, #c8e4e3);
  background: var(--color-bg, #f2f8f7);
  color: var(--color-text-strong, #173b42);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-fast, 180ms) ease;
  shrink: 0;
}

.back-btn:hover {
  background: var(--color-primary-soft, #d8f1f0);
  border-color: var(--color-primary, #46b8b4);
  color: var(--color-primary-text, #205f67);
}

.header-titles {
  flex: 1;
}

.section-block {
  margin-bottom: 28px;
}

.section-label {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-strong, #173b42);
  font-family: var(--font-sans);
  margin-bottom: 8px;
}

.sub-label {
  display: block;
  font-size: 11px;
  color: var(--color-text-secondary, #58747a);
  margin-bottom: 6px;
}

.intent-card {
  padding: 14px 16px;
  background: var(--color-bg, #f2f8f7);
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-border-light, #ddedec);
}

.intent-badge-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.intent-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-primary-text, #205f67);
  background: var(--color-primary-soft, #d8f1f0);
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid var(--color-primary-border, #b9dedc);
}

.intent-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-strong, #173b42);
  line-height: 1.5;
}

.goal-input {
  width: 100%;
  padding: 10px 14px;
  border-radius: var(--radius-sm, 6px);
  border: 1px solid var(--color-border, #c8e4e3);
  background: var(--color-surface, #fcffff);
  font-size: 13px;
  color: var(--color-text-strong, #173b42);
  outline: none;
  box-sizing: border-box;
  transition: border-color var(--duration-fast, 180ms) ease, box-shadow var(--duration-fast, 180ms) ease;
}

.goal-input:focus {
  border-color: var(--color-primary, #46b8b4);
  box-shadow: 0 0 0 3px rgba(70, 184, 180, 0.15);
}

.difficulty-capsules {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.capsule-btn {
  display: flex;
  flex-direction: column;
  padding: 12px 14px;
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-border-light, #ddedec);
  background: var(--color-bg, #f2f8f7);
  cursor: pointer;
  text-align: left;
  transition: all var(--duration-fast, 180ms) ease;
}

.capsule-btn:hover {
  border-color: var(--color-primary-border, #b9dedc);
  background: var(--color-surface, #fcffff);
}

.capsule-btn.active {
  border-color: var(--color-primary, #46b8b4);
  background: var(--color-primary-soft, #d8f1f0);
  box-shadow: 0 2px 6px rgba(70, 184, 180, 0.12);
}

.capsule-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-strong, #173b42);
}

.capsule-btn.active .capsule-title {
  color: var(--color-primary-text, #205f67);
}

.capsule-desc {
  font-size: 11px;
  color: var(--color-text-secondary, #58747a);
  margin-top: 2px;
}

.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.selection-counter-badge {
  font-size: 11px;
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--color-primary-text, #205f67);
  background: var(--color-primary-soft, #d8f1f0);
  padding: 3px 10px;
  border-radius: 99px;
  border: 1px solid var(--color-primary-border, #b9dedc);
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}

.resource-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 14px;
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-border-light, #ddedec);
  background: var(--color-surface, #fcffff);
  cursor: pointer;
  transition: all var(--duration-fast, 180ms) ease;
  user-select: none;
}

.resource-card:hover {
  transform: translateY(-1px);
  border-color: var(--color-border, #c8e4e3);
  box-shadow: 0 4px 12px rgba(23, 59, 66, 0.05);
}

.resource-card.selected {
  border-color: var(--color-primary, #46b8b4);
  background: #ffffff;
  box-shadow: 0 0 0 1px var(--color-primary, #46b8b4), 0 4px 12px rgba(70, 184, 180, 0.1);
}

.card-top-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm, 6px);
  flex-shrink: 0;
}

.agent-role-pill {
  font-size: 10px;
  font-mono: true;
  font-weight: 600;
  color: var(--color-text-secondary, #58747a);
  background: var(--color-bg, #f2f8f7);
  padding: 1.5px 6px;
  border-radius: 4px;
  border: 1px solid var(--color-border-light, #ddedec);
}

.resource-card.selected .agent-role-pill {
  color: var(--color-primary-text, #205f67);
  background: var(--color-primary-soft, #d8f1f0);
  border-color: var(--color-primary-border, #b9dedc);
}

.check-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 1.5px solid var(--color-border, #c8e4e3);
  background: var(--color-surface, #fcffff);
  transition: all var(--duration-fast, 180ms) ease;
}

.check-box.checked {
  background: var(--color-primary, #46b8b4);
  border-color: var(--color-primary, #46b8b4);
  color: #ffffff;
}

.card-name {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-strong, #173b42);
  margin-bottom: 2px;
}

.card-desc {
  display: block;
  font-size: 11px;
  color: var(--color-text-secondary, #58747a);
  line-height: 1.45;
}

.preference-row {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.pref-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pref-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-strong, #173b42);
}

.pref-select {
  padding: 8px 12px;
  border-radius: var(--radius-sm, 6px);
  border: 1px solid var(--color-border, #c8e4e3);
  background: var(--color-surface, #fcffff);
  color: var(--color-text-strong, #173b42);
  font-size: 12px;
  outline: none;
}

.pref-select:focus {
  border-color: var(--color-primary, #46b8b4);
}

.setting-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid var(--color-border-light, #ddedec);
  gap: 16px;
}

.footer-tip {
  font-size: 11px;
  color: var(--color-text-secondary, #58747a);
  max-width: 480px;
  line-height: 1.5;
}

.launch-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: var(--radius-sm, 6px);
  border: none;
  background: var(--color-primary, #46b8b4);
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all var(--duration-fast, 180ms) ease;
  box-shadow: 0 2px 8px rgba(70, 184, 180, 0.3);
  shrink: 0;
}

.launch-btn:hover:not(:disabled) {
  background: var(--color-primary-hover, #35a8a5);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(70, 184, 180, 0.4);
}

.launch-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

@media (max-width: 768px) {
  .resource-setting-container {
    padding: 16px 12px;
  }
  .setting-card {
    padding: 20px;
  }
  .difficulty-capsules {
    grid-template-columns: 1fr;
  }
  .setting-footer {
    flex-direction: column;
    align-items: stretch;
  }
  .launch-btn {
    justify-content: center;
  }
}
</style>
