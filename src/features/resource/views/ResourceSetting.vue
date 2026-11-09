<template>
  <div class="resource-setting-container">
    <div class="setting-card">
      <!-- 顶部导航 -->
      <div class="setting-header">
        <button type="button" class="back-btn" @click="emit('back')">
          <ArrowLeft class="icon" />
          <span>返回输入</span>
        </button>
        <div class="header-titles">
          <h2>智能资源定制</h2>
          <p>选择期望生成的交付物清单与学习目标，主智能体将自主编排任务拓扑</p>
        </div>
      </div>

      <!-- 学习主题与目标 -->
      <div class="section-block">
        <label class="section-label">学习主题与意图</label>
        <div class="topic-display">
          <span class="topic-tag">主题</span>
          <span class="topic-text">{{ naturalInput || '未指定主题' }}</span>
        </div>

        <div class="goal-input-box">
          <label class="sub-label">核心学习目标 (可选补充)</label>
          <input
            v-model="learningGoal"
            type="text"
            class="goal-input"
            placeholder="例如：深入理解底层执行机理，掌握典型应用模式与避坑指南..."
          />
        </div>
      </div>

      <!-- 学习难度阶梯 -->
      <div class="section-block">
        <label class="section-label">难度阶梯</label>
        <div class="difficulty-capsules">
          <button
            v-for="item in difficultyOptions"
            :key="item.value"
            type="button"
            class="capsule-btn"
            :class="{ active: difficulty === item.value }"
            @click="difficulty = item.value"
          >
            <span class="capsule-title">{{ item.label }}</span>
            <span class="capsule-desc">{{ item.desc }}</span>
          </button>
        </div>
      </div>

      <!-- 交付物清单多选卡片 -->
      <div class="section-block">
        <div class="section-header-row">
          <label class="section-label">期望交付资源清单</label>
          <span class="badge">已选 {{ selectedResources.length }} 项</span>
        </div>

        <div class="resource-grid">
          <div
            v-for="res in availableResources"
            :key="res.id"
            class="resource-card"
            :class="{ selected: selectedResources.includes(res.id) }"
            @click="toggleResource(res.id)"
          >
            <div class="card-check">
              <CheckCircle v-if="selectedResources.includes(res.id)" class="check-icon checked" />
              <div v-else class="check-circle" />
            </div>
            <div class="card-icon" :style="{ backgroundColor: res.bg }">
              <component :is="res.icon" class="type-icon" :style="{ color: res.color }" />
            </div>
            <div class="card-info">
              <span class="card-name">{{ res.name }}</span>
              <span class="card-desc">{{ res.description }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 可选高级偏好（自适应折叠） -->
      <div v-if="hasAdvancedOptions" class="section-block advanced-block">
        <label class="section-label">偏好设置</label>
        <div class="preference-row">
          <div v-if="selectedResources.includes('code')" class="pref-item">
            <span class="pref-label">示例代码语言</span>
            <select v-model="programmingLanguage" class="pref-select">
              <option value="python">Python</option>
              <option value="typescript">TypeScript</option>
              <option value="javascript">JavaScript</option>
              <option value="go">Go</option>
              <option value="java">Java</option>
              <option value="cpp">C++</option>
            </select>
          </div>

          <div v-if="selectedResources.includes('cartoon')" class="pref-item">
            <span class="pref-label">动画旁白音色</span>
            <select v-model="cartoonVoice" class="pref-select">
              <option value="teacher">专业学术讲师 (沉稳严谨)</option>
              <option value="coach">实战教练 (生动富有感染力)</option>
            </select>
          </div>
        </div>
      </div>

      <!-- 底部操作栏 -->
      <div class="setting-footer">
        <div class="footer-tip">
          主 PlanAgent 将根据选择自动构建依赖 DAG 并分发 SubAgent 协同生成
        </div>
        <button
          type="button"
          class="launch-btn"
          :disabled="selectedResources.length === 0"
          @click="handleLaunch"
        >
          <Sparkle class="icon" />
          <span>开始智能规划与生成 ({{ selectedResources.length }})</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  PhArrowLeft as ArrowLeft,
  PhCheckCircle as CheckCircle,
  PhSparkle as Sparkle,
  PhFileText as DocumentIcon,
  PhTreeStructure as MindmapIcon,
  PhCheckSquare as QuizIcon,
  PhCode as CodeIcon,
  PhBookOpen as BookIcon,
  PhPresentation as PresentationIcon,
  PhFilmStrip as VideoIcon,
} from '@phosphor-icons/vue'
import type { ResourceAgentId, DifficultyLevel } from '../model/resource'

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
    preferences: Record<string, unknown>
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

const programmingLanguage = ref('python')
const cartoonVoice = ref('teacher')

const difficultyOptions = [
  { value: 'beginner' as const, label: '初学入门', desc: '注重直观比喻与基础概念' },
  { value: 'intermediate' as const, label: '进阶实战', desc: '强调工程实践与核心机理' },
  { value: 'advanced' as const, label: '深度探究', desc: '剖析底层源码与架构设计' },
]

const availableResources = [
  {
    id: 'content' as const,
    name: '课程精讲',
    description: '系统化理论解析、渐进式知识脉络',
    color: '#3b82f6',
    bg: 'rgba(59, 130, 246, 0.1)',
    icon: DocumentIcon,
  },
  {
    id: 'mindmap' as const,
    name: '思维导图',
    description: '结构化知识树、层次一目了然',
    color: '#10b981',
    bg: 'rgba(16, 185, 129, 0.1)',
    icon: MindmapIcon,
  },
  {
    id: 'quiz' as const,
    name: '巩固练习',
    description: '随堂测验试题、强化理解记忆',
    color: '#f59e0b',
    bg: 'rgba(245, 158, 11, 0.1)',
    icon: QuizIcon,
  },
  {
    id: 'code' as const,
    name: '代码实操',
    description: '精炼工程范例、动手实践运行',
    color: '#8b5cf6',
    bg: 'rgba(139, 92, 246, 0.1)',
    icon: CodeIcon,
  },
  {
    id: 'reading' as const,
    name: '拓展阅读',
    description: '经典文献推荐、权威工程文档',
    color: '#06b6d4',
    bg: 'rgba(6, 182, 212, 0.1)',
    icon: BookIcon,
  },
  {
    id: 'ppt' as const,
    name: '演示课件',
    description: '多模态 PPT 幻灯片、支持课件下载与逐页预览',
    color: '#ec4899',
    bg: 'rgba(236, 72, 153, 0.1)',
    icon: PresentationIcon,
  },
  {
    id: 'cartoon' as const,
    name: '概念动画',
    description: '1080p 教学视频、配音与中文字幕同步',
    color: '#f43f5e',
    bg: 'rgba(244, 63, 94, 0.1)',
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
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 16px;
}

.setting-card {
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-color, #e5e7eb);
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}

.setting-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color, #f3f4f6);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid var(--border-color, #e5e7eb);
  background: transparent;
  color: var(--text-secondary, #4b5563);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.back-btn:hover {
  background: var(--bg-hover, #f9fafb);
  color: var(--text-primary, #111827);
}

.header-titles h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary, #111827);
  margin: 0 0 4px 0;
}

.header-titles p {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  margin: 0;
}

.section-block {
  margin-bottom: 26px;
}

.section-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
  margin-bottom: 10px;
}

.topic-display {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--bg-subtle, #f9fafb);
  border-radius: 8px;
  border: 1px solid var(--border-color, #f3f4f6);
  margin-bottom: 12px;
}

.topic-tag {
  font-size: 12px;
  font-weight: 600;
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.topic-text {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary, #111827);
}

.goal-input-box {
  margin-top: 8px;
}

.sub-label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  margin-bottom: 6px;
}

.goal-input {
  width: 100%;
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid var(--border-color, #d1d5db);
  background: var(--bg-input, #ffffff);
  font-size: 14px;
  color: var(--text-primary, #111827);
  outline: none;
  box-sizing: border-box;
}

.goal-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
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
  border-radius: 10px;
  border: 1px solid var(--border-color, #e5e7eb);
  background: var(--bg-card, #ffffff);
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.capsule-btn:hover {
  border-color: #93c5fd;
}

.capsule-btn.active {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.04);
}

.capsule-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #111827);
  margin-bottom: 2px;
}

.capsule-btn.active .capsule-title {
  color: #2563eb;
}

.capsule-desc {
  font-size: 11px;
  color: var(--text-secondary, #6b7280);
}

.section-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.badge {
  font-size: 12px;
  font-weight: 500;
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.08);
  padding: 2px 10px;
  border-radius: 12px;
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 12px;
}

.resource-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid var(--border-color, #e5e7eb);
  background: var(--bg-card, #ffffff);
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.resource-card:hover {
  transform: translateY(-1px);
  border-color: #cbd5e1;
}

.resource-card.selected {
  border-color: #3b82f6;
  background: rgba(59, 130, 246, 0.02);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.08);
}

.card-check {
  margin-top: 2px;
}

.check-circle {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1.5px solid var(--border-color, #cbd5e1);
}

.check-icon.checked {
  width: 20px;
  height: 20px;
  color: #3b82f6;
}

.card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  flex-shrink: 0;
}

.type-icon {
  width: 20px;
  height: 20px;
}

.card-info {
  display: flex;
  flex-direction: column;
}

.card-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #111827);
  margin-bottom: 2px;
}

.card-desc {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  line-height: 1.4;
}

.advanced-block {
  padding-top: 16px;
  border-top: 1px dashed var(--border-color, #e5e7eb);
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
  font-size: 12px;
  color: var(--text-secondary, #4b5563);
}

.pref-select {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color, #d1d5db);
  background: var(--bg-input, #ffffff);
  color: var(--text-primary, #111827);
  font-size: 13px;
  outline: none;
}

.setting-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color, #f3f4f6);
}

.footer-tip {
  font-size: 12px;
  color: var(--text-secondary, #9ca3af);
  max-width: 400px;
}

.launch-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
}

.launch-btn:hover:not(:disabled) {
  opacity: 0.95;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.35);
}

.launch-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}
</style>
