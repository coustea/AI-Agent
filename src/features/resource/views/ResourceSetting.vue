<template>
  <div class="agent-config-page">
    <div class="agent-config-shell">
      <aside class="agent-left-rail">
        <section class="rail-section scenario-section">
          <div class="rail-title-row">
            <span class="rail-kicker">SCENARIO</span>
            <strong>学习场景</strong>
          </div>

          <div class="scenario-list">
            <button
                v-for="scenario in scenarioOptions"
                :key="scenario.value"
                type="button"
                class="scenario-row"
                :class="{ active: learningScenario === scenario.value }"
                @click="selectScenario(scenario.value)"
            >
              <span class="scenario-icon">{{ scenario.icon }}</span>
              <span class="scenario-name">{{ scenario.name }}</span>
            </button>
          </div>
        </section>

        <section class="rail-section agent-section">
          <div class="rail-title-row">
            <span class="rail-kicker">AGENTS</span>
            <strong>{{ enabledAgentIds.length }} / {{ agents.length }} 已启用</strong>
          </div>

          <div class="agent-vertical-list">
            <button
                v-for="agent in agents"
                :key="agent.id"
                type="button"
                class="agent-row"
                :class="{
                active: activeAgentId === agent.id,
                disabled: !isAgentEnabled(agent.id)
              }"
                :style="agentThemeStyle(agent.id)"
                @click="selectAgent(agent.id)"
            >
              <span class="agent-color-mark"></span>

              <span class="agent-icon-box">
                <component :is="agent.icon" />
              </span>

              <span class="agent-row-main">
                <strong>{{ agent.name }}</strong>
                <small>{{ isAgentEnabled(agent.id) ? getAgentSummary(agent.id) : '已关闭' }}</small>
              </span>

              <span class="agent-switch-wrap" @click.stop>
                <label class="compact-switch">
                  <input
                      type="checkbox"
                      :checked="isAgentEnabled(agent.id)"
                      @change="toggleAgent(agent.id)"
                  />
                  <span></span>
                </label>
              </span>
            </button>
          </div>
        </section>
      </aside>

      <main class="agent-main-panel" :style="agentThemeStyle(activeAgentId)">
        <header class="config-header">
          <div class="config-heading">
            <span class="config-agent-icon">
              <component :is="activeAgentMeta.icon" />
            </span>

            <div>
              <div class="config-title-line">
                <h2>{{ activeAgentMeta.name }}</h2>
                <span :class="['status-chip', activeAgentEnabled ? 'active' : 'sleep']">
                  {{ activeAgentEnabled ? '已启用' : '已关闭' }}
                </span>
              </div>
              <p>{{ activeAgentOutputLabel }}</p>
            </div>
          </div>

          <label class="compact-switch header-switch">
            <input
                type="checkbox"
                :checked="activeAgentEnabled"
                @change="toggleAgent(activeAgentId)"
            />
            <span></span>
          </label>
        </header>

        <div v-if="!activeAgentEnabled" class="sleep-notice">
          <span>当前智能体未参与本次资源生成，参数可预设但不会提交给协同流程。</span>
          <button type="button" @click="toggleAgent(activeAgentId)">启用该智能体</button>
        </div>

        <section class="config-body" :class="{ muted: !activeAgentEnabled }">
          <div class="config-body-inner">
            <template v-if="activeAgentId === 'content'">
              <div class="setting-block">
                <div class="setting-label">
                  <strong>讲解组织结构</strong>
                  <span>决定文档讲解的展开顺序</span>
                </div>

                <div class="option-grid two">
                  <button
                      v-for="opt in contentStructureOptions"
                      :key="opt.value"
                      type="button"
                      class="option-button"
                      :class="{ active: localConfigs.content.structure === opt.value }"
                      @click="localConfigs.content.structure = opt.value"
                  >
                    {{ opt.label }}
                  </button>
                </div>
              </div>

              <div class="setting-block">
                <div class="setting-label">
                  <strong>讲解深度</strong>
                  <span>控制解释长度与推导强度</span>
                </div>

                <div class="segmented-control">
                  <button
                      v-for="opt in contentDepthOptions"
                      :key="opt.value"
                      type="button"
                      :class="{ active: localConfigs.content.depth_level === opt.value }"
                      @click="localConfigs.content.depth_level = opt.value as any"
                  >
                    {{ opt.label }}
                  </button>
                </div>
              </div>

              <div class="setting-block">
                <div class="setting-label">
                  <strong>聚焦模式</strong>
                  <span>决定讲解更偏向薄弱点、主干概念还是完整覆盖</span>
                </div>

                <select class="clean-select" v-model="localConfigs.content.focus_mode">
                  <option value="weak_points">薄弱点强化</option>
                  <option value="key_concepts">核心概念提炼</option>
                  <option value="full_coverage">完整知识覆盖</option>
                </select>
              </div>

              <div class="setting-line">
                <div>
                  <strong>加入生活化类比</strong>
                  <span>用具象例子解释抽象概念、公式或机制</span>
                </div>

                <label class="compact-switch">
                  <input type="checkbox" v-model="localConfigs.content.include_examples" />
                  <span></span>
                </label>
              </div>
            </template>

            <template v-if="activeAgentId === 'mindmap'">
              <div class="setting-block">
                <div class="setting-label">
                  <strong>思维导图类型</strong>
                  <span>决定知识节点的组织方式</span>
                </div>

                <select class="clean-select" v-model="localConfigs.mindmap.map_type">
                  <option value="knowledge_tree">层级知识树</option>
                  <option value="exam_map">考点重点图</option>
                  <option value="comparison_map">对比复习图</option>
                </select>
              </div>

              <div class="setting-block">
                <div class="setting-label">
                  <strong>最大层级</strong>
                  <span>{{ localConfigs.mindmap.max_depth }} 层</span>
                </div>

                <input
                    class="clean-range"
                    type="range"
                    v-model.number="localConfigs.mindmap.max_depth"
                    :min="2"
                    :max="5"
                    :step="1"
                />
              </div>

              <div class="setting-block">
                <div class="setting-label">
                  <strong>叶子节点密度</strong>
                  <span>控制节点文字长度</span>
                </div>

                <div class="segmented-control">
                  <button
                      v-for="opt in mindmapLeafOptions"
                      :key="opt.value"
                      type="button"
                      :class="{ active: localConfigs.mindmap.leaf_detail === opt.value }"
                      @click="localConfigs.mindmap.leaf_detail = opt.value as any"
                  >
                    {{ opt.label }}
                  </button>
                </div>
              </div>

              <div class="setting-line">
                <div>
                  <strong>显示跨分支关联</strong>
                  <span>适合展示概念之间的非层级关系</span>
                </div>

                <label class="compact-switch">
                  <input type="checkbox" v-model="localConfigs.mindmap.show_relations" />
                  <span></span>
                </label>
              </div>
            </template>

            <template v-if="activeAgentId === 'code'">
              <div class="setting-block">
                <div class="setting-label">
                  <strong>编程语言</strong>
                  <span>生成代码实操案例使用的语言</span>
                </div>

                <div class="option-grid three">
                  <button
                      v-for="lang in programmingLanguageOptions"
                      :key="lang.key"
                      type="button"
                      class="option-button"
                      :class="{ active: localConfigs.code.programming_language === lang.key }"
                      @click="localConfigs.code.programming_language = lang.key"
                  >
                    {{ lang.label }}
                  </button>
                </div>
              </div>

              <div class="setting-block">
                <div class="setting-label">
                  <strong>源码类型</strong>
                  <span>决定代码偏教学、参考实现还是挑战练习</span>
                </div>

                <div class="segmented-control">
                  <button
                      v-for="opt in codeOutputOptions"
                      :key="opt.value"
                      type="button"
                      :class="{ active: localConfigs.code.output_style === opt.value }"
                      @click="localConfigs.code.output_style = opt.value as any"
                  >
                    {{ opt.label }}
                  </button>
                </div>
              </div>

              <div class="setting-block">
                <div class="setting-label">
                  <strong>讲解侧重</strong>
                  <span>决定代码说明重点</span>
                </div>

                <select class="clean-select" v-model="localConfigs.code.focus">
                  <option value="syntax">语法机制与 API 边界</option>
                  <option value="application">工程实践与集成方式</option>
                  <option value="debugging">调试思路与错误排查</option>
                </select>
              </div>
            </template>

            <template v-if="activeAgentId === 'quiz'">
              <div class="setting-block">
                <div class="setting-label">
                  <strong>题目难度策略</strong>
                  <span>决定题目更偏基础、自适应还是考试</span>
                </div>

                <select class="clean-select" v-model="localConfigs.quiz.difficulty_mode">
                  <option value="basic">基础辨析</option>
                  <option value="adaptive">自适应梯度</option>
                  <option value="exam">考试强化</option>
                </select>
              </div>

              <div class="setting-block">
                <div class="setting-label">
                  <strong>题目数量</strong>
                  <span>{{ localConfigs.quiz.question_count }} 题</span>
                </div>

                <input
                    class="clean-range"
                    type="range"
                    v-model.number="localConfigs.quiz.question_count"
                    :min="3"
                    :max="10"
                    :step="1"
                />
              </div>

              <div class="setting-block">
                <div class="setting-label">
                  <strong>题型范围</strong>
                  <span>至少保留一种题型</span>
                </div>

                <div class="option-grid two">
                  <button
                      v-for="opt in questionTypeOptions"
                      :key="opt.value"
                      type="button"
                      class="option-button"
                      :class="{ active: localConfigs.quiz.question_types.includes(opt.value as any) }"
                      @click="toggleQuestionType(opt.value)"
                  >
                    {{ opt.label }}
                  </button>
                </div>
              </div>
            </template>

            <template v-if="activeAgentId === 'reading'">
              <div class="setting-block">
                <div class="setting-label">
                  <strong>资源覆盖范围</strong>
                  <span>控制推荐资料的广度</span>
                </div>

                <div class="segmented-control">
                  <button
                      v-for="opt in readingCoverageOptions"
                      :key="opt.value"
                      type="button"
                      :class="{ active: localConfigs.reading.coverage === opt.value }"
                      @click="localConfigs.reading.coverage = opt.value as any"
                  >
                    {{ opt.label }}
                  </button>
                </div>
              </div>

              <div class="setting-block">
                <div class="setting-label">
                  <strong>资源侧重</strong>
                  <span>决定推荐教材、工程资料还是论文</span>
                </div>

                <select class="clean-select" v-model="localConfigs.reading.focus">
                  <option value="textbook">教材 / 专著</option>
                  <option value="engineering">官方文档 / 工程博客</option>
                  <option value="research">论文 / 白皮书</option>
                </select>
              </div>

              <div class="setting-block">
                <div class="setting-label">
                  <strong>推荐数量</strong>
                  <span>{{ localConfigs.reading.max_items }} 篇</span>
                </div>

                <input
                    class="clean-range"
                    type="range"
                    v-model.number="localConfigs.reading.max_items"
                    :min="3"
                    :max="12"
                    :step="1"
                />
              </div>
            </template>

            <template v-if="activeAgentId === 'ppt'">
              <div class="setting-block">
                <div class="setting-label">
                  <strong>PPT 模板</strong>
                  <span>决定课件视觉风格</span>
                </div>

                <select class="clean-select" v-model="localConfigs.ppt.template">
                  <option value="auto">自动匹配最佳模板</option>
                  <option
                      v-for="template in pptTemplates"
                      :key="template.id"
                      :value="template.id"
                  >
                    {{ template.name }}
                  </option>
                </select>

                <p class="hint-text">{{ selectedPptTemplateDescription }}</p>
              </div>
            </template>

            <template v-if="activeAgentId === 'cartoon'">
              <div class="setting-block">
                <div class="setting-label">
                  <strong>动画风格</strong>
                  <span>决定动画讲解的视觉表达</span>
                </div>

                <select class="clean-select" v-model="localConfigs.cartoon.style">
                  <option value="diagram">动态教学图解</option>
                  <option value="minimal">现代极简版面</option>
                  <option value="dark_tech">高对比科技风</option>
                  <option value="chalkboard">黑板粉笔风</option>
                </select>
              </div>
            </template>
          </div>
        </section>
      </main>

      <aside class="agent-right-panel">
        <section class="summary-block">
          <div class="summary-title">
            <span>INPUT</span>
            <strong>学习输入</strong>
          </div>

          <p class="input-preview">
            {{ naturalInput || '暂无原始学习需求。' }}
          </p>

          <div class="scenario-desc">
            <span>场景策略</span>
            <strong>{{ activeScenarioDesc }}</strong>
          </div>
        </section>

        <section class="summary-block fill">
          <div class="summary-title">
            <span>ACTIVE STACK</span>
            <strong>启用资源链路</strong>
          </div>

          <div class="enabled-list">
            <div
                v-for="agent in enabledAgents"
                :key="agent.id"
                class="enabled-row"
                :style="agentThemeStyle(agent.id)"
            >
              <span class="enabled-dot"></span>
              <div>
                <strong>{{ agent.name }}</strong>
                <small>{{ getAgentSummary(agent.id) }}</small>
              </div>
            </div>
          </div>
        </section>

        <section class="summary-block compact">
          <div class="summary-title">
            <span>CHECK</span>
            <strong>提交前检查</strong>
          </div>

          <div class="check-row">
            <span>最少智能体</span>
            <strong>{{ MIN_AGENTS }} 个</strong>
          </div>
          <div class="check-row">
            <span>当前状态</span>
            <strong :class="{ danger: enabledAgentIds.length <= MIN_AGENTS }">
              {{ enabledAgentIds.length <= MIN_AGENTS ? '核心保护中' : '可继续调整' }}
            </strong>
          </div>
        </section>
      </aside>

      <footer class="bottom-action-bar">
        <button type="button" class="ghost-button" @click="emit('back')">
          返回修改需求
        </button>

        <p v-if="enabledAgentIds.length <= MIN_AGENTS" class="footer-warning">
          至少保留 {{ MIN_AGENTS }} 个智能体，避免资源生成链路过弱。
        </p>

        <button type="button" class="primary-button" @click="emit('launch')">
          确认配置并开始生成
          <Position class="button-icon" />
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { PhPaperPlaneTilt as Position } from '@phosphor-icons/vue'
import { toast } from 'vue-sonner'
import {
  getPptTemplates,
  type PptTemplateOption,
} from '@/features/resource/api/resource'
import type { LearningScenario, ResourceAgentId } from '@/features/resource/model/resource'
import {
  MIN_AGENTS,
  getAgentMeta,
  scenarioOptions,
  getScenarioDesc,
  SCENARIO_DEFAULTS,
  agentMetaList,
  type AnyAgentConfigs,
} from '../model/catalog'

const props = defineProps<{
  learningScenario: LearningScenario
  enabledAgentIds: ResourceAgentId[]
  agentConfigs: AnyAgentConfigs
  naturalInput?: string
}>()

const emit = defineEmits<{
  'update:learningScenario': [value: LearningScenario]
  'update:enabledAgentIds': [value: ResourceAgentId[]]
  'update:agentConfigs': [value: AnyAgentConfigs]
  back: []
  launch: []
}>()

const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value))

const activeAgentId = ref<ResourceAgentId>('content')
const localConfigs = ref<AnyAgentConfigs>(clone(props.agentConfigs))
const pptTemplates = ref<PptTemplateOption[]>([])

const learningScenario = computed({
  get: () => props.learningScenario,
  set: (value) => emit('update:learningScenario', value),
})

const enabledAgentIds = computed({
  get: () => props.enabledAgentIds,
  set: (value) => emit('update:enabledAgentIds', value),
})

const agents = computed(() => agentMetaList)
const enabledAgents = computed(() =>
    agents.value.filter((agent) => enabledAgentIds.value.includes(agent.id as ResourceAgentId))
)

const activeAgentMeta = computed(() => getAgentMeta(activeAgentId.value))
const activeAgentEnabled = computed(() => isAgentEnabled(activeAgentId.value))
const naturalInput = computed(() => props.naturalInput?.trim() || '')
const activeScenarioDesc = computed(() => getScenarioDesc(learningScenario.value))

const contentStructureOptions = [
  { label: '渐进式引导', value: 'progressive' },
  { label: '先总后分', value: 'summary_first' },
  { label: '考点驱动', value: 'exam_points' },
  { label: '案例驱动', value: 'case_driven' },
]

const contentDepthOptions = [
  { label: '快速概述', value: 'quick' },
  { label: '标准讲解', value: 'standard' },
  { label: '深度推导', value: 'deep' },
]

const mindmapLeafOptions = [
  { label: '核心词', value: 'keyword' },
  { label: '简要注释', value: 'brief_note' },
  { label: '详细注释', value: 'annotated' },
]

const programmingLanguageOptions = [
  { key: 'python', label: 'Python' },
  { key: 'java', label: 'Java' },
  { key: 'cpp', label: 'C++' },
  { key: 'go', label: 'Go' },
  { key: 'javascript', label: 'JS' },
  { key: 'typescript', label: 'TS' },
]

const codeOutputOptions = [
  { label: '教学案例', value: 'tutorial' },
  { label: '参考实现', value: 'reference' },
  { label: '挑战练习', value: 'challenge' },
]

const questionTypeOptions = [
  { label: '单选题', value: 'single' },
  { label: '多选题', value: 'multiple' },
  { label: '判断题', value: 'judge' },
  { label: '填空题', value: 'fill' },
]

const readingCoverageOptions = [
  { label: '核心精选', value: 'core' },
  { label: '横向延展', value: 'extended' },
  { label: '广泛覆盖', value: 'broad' },
]

const activeAgentOutputLabel = computed(() => {
  const map: Record<ResourceAgentId, string> = {
    content: '生成课程讲解文档，负责知识点主线说明。',
    mindmap: '生成知识结构图，负责概念层级和关联梳理。',
    code: '生成代码实操案例，负责理论到实践的迁移。',
    quiz: '生成练习题，负责检测掌握情况与反馈。',
    reading: '生成拓展阅读，负责补充教材、文档和论文资料。',
    ppt: '生成教学课件，负责结构化演示与课堂展示。',
    cartoon: '生成动画讲解，负责抽象机制的可视化解释。',
  }

  return map[activeAgentId.value] || '配置当前智能体的资源生成策略。'
})

const selectedPptTemplateDescription = computed(() => {
  if (localConfigs.value.ppt.template === 'auto') {
    return '系统会根据知识点类型、内容密度和资源目标自动选择模板。'
  }

  return pptTemplates.value.find(
      (template) => template.id === localConfigs.value.ppt.template
  )?.description || '当前模板已选定。'
})

onMounted(async () => {
  try {
    const response = await getPptTemplates()
    const templates = response.data?.data

    if (Array.isArray(templates) && templates.length > 0) {
      pptTemplates.value = templates
    }
  } catch (error) {
    console.error('PPT 模板加载失败', error)
  }
})

watch(
    () => props.agentConfigs,
    (newVal) => {
      localConfigs.value = clone(newVal)
    },
    { deep: true }
)

watch(
    localConfigs,
    (newVal) => {
      emit('update:agentConfigs', clone(newVal))
    },
    { deep: true }
)

function isAgentEnabled(id: string) {
  return enabledAgentIds.value.includes(id as ResourceAgentId)
}

function selectAgent(id: string) {
  activeAgentId.value = id as ResourceAgentId
}

function toggleAgent(id: string) {
  const agentId = id as ResourceAgentId
  const index = enabledAgentIds.value.indexOf(agentId)

  if (index >= 0) {
    if (enabledAgentIds.value.length <= MIN_AGENTS) {
      toast.warning(`至少需要保留 ${MIN_AGENTS} 个智能体`)
      return
    }

    const next = [...enabledAgentIds.value]
    next.splice(index, 1)
    enabledAgentIds.value = next
    return
  }

  enabledAgentIds.value = [...enabledAgentIds.value, agentId]
}

function selectScenario(scenario: LearningScenario) {
  learningScenario.value = scenario

  const defaults = SCENARIO_DEFAULTS[scenario]
  if (defaults) {
    localConfigs.value = clone({
      ...localConfigs.value,
      ...defaults,
    })
  }
}

function toggleQuestionType(type: string) {
  const types = [...localConfigs.value.quiz.question_types]
  const index = types.indexOf(type as any)

  if (index >= 0) {
    if (types.length <= 1) {
      toast.warning('至少需要保留一种题型')
      return
    }

    types.splice(index, 1)
  } else {
    types.push(type as any)
  }

  localConfigs.value.quiz.question_types = types
}

function getAgentSummary(id: string) {
  const configs = localConfigs.value

  if (id === 'content') {
    const structureMap: Record<string, string> = {
      progressive: '渐进式',
      summary_first: '先总后分',
      exam_points: '考点驱动',
      case_driven: '案例驱动',
    }

    const depthMap: Record<string, string> = {
      quick: '快速',
      standard: '标准',
      deep: '深度',
    }

    return `${structureMap[configs.content.structure] || '标准'} · ${depthMap[configs.content.depth_level] || '标准'}`
  }

  if (id === 'mindmap') {
    const mapType: Record<string, string> = {
      knowledge_tree: '知识树',
      exam_map: '考点图',
      comparison_map: '对比图',
    }

    return `${mapType[configs.mindmap.map_type] || '知识树'} · ${configs.mindmap.max_depth} 层`
  }

  if (id === 'quiz') {
    return `${configs.quiz.question_count} 题 · ${configs.quiz.question_types.length} 类题型`
  }

  if (id === 'code') {
    const languageMap: Record<string, string> = {
      python: 'Python',
      c: 'C',
      cpp: 'C++',
      java: 'Java',
      go: 'Go',
      javascript: 'JS',
      typescript: 'TS',
    }

    return `${languageMap[configs.code.programming_language] || '代码'} · ${configs.code.output_style}`
  }

  if (id === 'reading') {
    return `${configs.reading.coverage} · ${configs.reading.max_items} 篇`
  }

  if (id === 'ppt') {
    return configs.ppt.template === 'auto' ? '自动模板' : '指定模板'
  }

  if (id === 'cartoon') {
    return `${configs.cartoon.style} 风格`
  }

  return '已配置'
}

function agentThemeStyle(id: string) {
  const themes: Record<string, { accent: string; soft: string; text: string; glow: string }> = {
    content: {
      accent: '#3B82F6',
      soft: '#EFF6FF',
      text: '#1D4ED8',
      glow: 'rgba(59, 130, 246, 0.16)',
    },
    mindmap: {
      accent: '#8B5CF6',
      soft: '#F5F3FF',
      text: '#6D28D9',
      glow: 'rgba(139, 92, 246, 0.14)',
    },
    code: {
      accent: '#22C55E',
      soft: '#F0FDF4',
      text: '#15803D',
      glow: 'rgba(34, 197, 94, 0.14)',
    },
    quiz: {
      accent: '#F59E0B',
      soft: '#FFFBEB',
      text: '#B45309',
      glow: 'rgba(245, 158, 11, 0.14)',
    },
    reading: {
      accent: '#14B8A6',
      soft: '#F0FDFA',
      text: '#0F766E',
      glow: 'rgba(20, 184, 166, 0.14)',
    },
    ppt: {
      accent: '#EF4444',
      soft: '#FEF2F2',
      text: '#B91C1C',
      glow: 'rgba(239, 68, 68, 0.14)',
    },
    cartoon: {
      accent: '#6366F1',
      soft: '#EEF2FF',
      text: '#4338CA',
      glow: 'rgba(99, 102, 241, 0.14)',
    },
  }

  const theme = themes[id] || themes.content

  return {
    '--agent-accent': theme.accent,
    '--agent-soft': theme.soft,
    '--agent-text': theme.text,
    '--agent-glow': theme.glow,
  }
}
</script>

<style scoped>
.agent-config-page {
  width: 100%;
  height: calc(100vh - var(--navbar-height, 72px));
  padding: 14px;
  box-sizing: border-box;
  background:
      radial-gradient(circle at 18% 10%, rgba(59, 130, 246, 0.08), transparent 32%),
      radial-gradient(circle at 86% 16%, rgba(20, 184, 166, 0.08), transparent 28%),
      linear-gradient(135deg, rgba(248, 251, 255, 0.96), rgba(241, 248, 250, 0.94));
}

.agent-config-shell {
  width: min(1580px, 100%);
  height: 100%;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr) 290px;
  grid-template-rows: minmax(0, 1fr) 66px;
  overflow: hidden;
  border-radius: 24px;
  border: 1px solid rgba(226, 232, 240, 0.78);
  background: rgba(255, 255, 255, 0.55);
  box-shadow:
      0 12px 40px rgba(15, 23, 42, 0.06),
      0 2px 8px rgba(15, 23, 42, 0.03);
  backdrop-filter: blur(12px);
}

.agent-left-rail {
  grid-row: 1 / 2;
  min-height: 0;
  background: rgba(255, 255, 255, 0.66);
  backdrop-filter: blur(18px);
  border-right: 1px solid rgba(226, 232, 240, 0.72);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.rail-section {
  padding: 18px 16px;
}

.scenario-section {
  border-bottom: 1px solid rgba(226, 232, 240, 0.72);
}

.agent-section {
  min-height: 0;
  display: flex;
  flex: 1;
  flex-direction: column;
}

.rail-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.rail-title-row strong {
  font-size: 13px;
  font-weight: 800;
  color: #102f36;
}

.rail-kicker {
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.08em;
  color: #3b82f6;
  background: rgba(239, 246, 255, 0.92);
  border: 1px solid rgba(191, 219, 254, 0.9);
  border-radius: 999px;
  padding: 3px 8px;
}

.scenario-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.scenario-row {
  min-height: 38px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.72);
  border-radius: 12px;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
      transform 0.18s ease,
      box-shadow 0.18s ease,
      border-color 0.18s ease,
      background 0.18s ease,
      color 0.18s ease;
}

.scenario-row:hover {
  border-color: rgba(59, 130, 246, 0.35);
  color: #2563eb;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 8px 18px rgba(148, 163, 184, 0.08);
  transform: translateY(-1px);
}

.scenario-row.active {
  background: #eff6ff;
  border-color: rgba(59, 130, 246, 0.45);
  color: #1d4ed8;
  box-shadow:
      0 8px 18px rgba(59, 130, 246, 0.08),
      inset 0 0 0 1px rgba(59, 130, 246, 0.08);
}

.scenario-icon {
  font-size: 13px;
}

.scenario-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-vertical-list {
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 9px;
  padding-right: 2px;
}

.agent-vertical-list::-webkit-scrollbar,
.config-body::-webkit-scrollbar,
.enabled-list::-webkit-scrollbar,
.input-preview::-webkit-scrollbar {
  width: 6px;
}

.agent-vertical-list::-webkit-scrollbar-thumb,
.config-body::-webkit-scrollbar-thumb,
.enabled-list::-webkit-scrollbar-thumb,
.input-preview::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.34);
  border-radius: 999px;
}

.agent-row {
  width: 100%;
  min-height: 60px;
  border: 1px solid rgba(226, 232, 240, 0.88);
  background: rgba(255, 255, 255, 0.68);
  border-radius: 16px;
  display: grid;
  grid-template-columns: 4px 36px minmax(0, 1fr) 42px;
  align-items: center;
  gap: 10px;
  padding: 10px 10px 10px 0;
  text-align: left;
  cursor: pointer;
  transition:
      transform 0.18s ease,
      box-shadow 0.18s ease,
      border-color 0.18s ease,
      background 0.18s ease,
      opacity 0.18s ease;
}

.agent-row:hover {
  border-color: color-mix(in srgb, var(--agent-accent) 42%, white);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 10px 20px rgba(148, 163, 184, 0.09);
  transform: translateY(-1px);
}

.agent-row.active {
  border-color: color-mix(in srgb, var(--agent-accent) 52%, white);
  background: var(--agent-soft);
  box-shadow:
      0 10px 24px var(--agent-glow),
      inset 0 0 0 1px rgba(255, 255, 255, 0.58);
}

.agent-row.disabled {
  opacity: 0.56;
  filter: saturate(0.82);
}

.agent-row.disabled.active {
  opacity: 0.84;
}

.agent-color-mark {
  width: 4px;
  align-self: stretch;
  border-radius: 0 999px 999px 0;
  background: transparent;
}

.agent-row.active .agent-color-mark {
  background: var(--agent-accent);
}

.agent-icon-box {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.9);
  color: #64748b;
  display: grid;
  place-items: center;
  transition:
      background 0.18s ease,
      color 0.18s ease,
      box-shadow 0.18s ease;
}

.agent-row.active .agent-icon-box {
  background: rgba(255, 255, 255, 0.82);
  color: var(--agent-accent);
  box-shadow: 0 6px 14px rgba(148, 163, 184, 0.12);
}

.agent-icon-box :deep(svg) {
  width: 17px;
  height: 17px;
}

.agent-row-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.agent-row-main strong {
  font-size: 13px;
  font-weight: 800;
  color: #102f36;
}

.agent-row-main small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  line-height: 1.2;
  color: #71828a;
  font-weight: 500;
}

.agent-row.active .agent-row-main small {
  color: var(--agent-text);
}

.agent-switch-wrap {
  display: flex;
  justify-content: flex-end;
}

.agent-main-panel {
  grid-row: 1 / 2;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: rgba(248, 251, 255, 0.52);
}

.config-header {
  height: 76px;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(226, 232, 240, 0.76);
  background: rgba(255, 255, 255, 0.68);
  backdrop-filter: blur(16px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.config-heading {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.config-agent-icon {
  width: 42px;
  height: 42px;
  border-radius: 15px;
  background: var(--agent-soft);
  color: var(--agent-accent);
  display: grid;
  place-items: center;
  flex-shrink: 0;
  box-shadow: 0 8px 18px var(--agent-glow);
}

.config-agent-icon :deep(svg) {
  width: 22px;
  height: 22px;
}

.config-title-line {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.config-title-line h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 850;
  letter-spacing: -0.02em;
  color: #102f36;
}

.config-heading p {
  margin: 4px 0 0;
  color: #71828a;
  font-size: 12px;
  line-height: 1.45;
  font-weight: 500;
}

.status-chip {
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  font-weight: 800;
  white-space: nowrap;
}

.status-chip.active {
  color: var(--agent-text);
  background: var(--agent-soft);
  border: 1px solid color-mix(in srgb, var(--agent-accent) 24%, white);
}

.status-chip.sleep {
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.header-switch {
  transform: scale(1.08);
}

.sleep-notice {
  margin: 18px 24px 0;
  padding: 10px 12px;
  border: 1px dashed rgba(245, 158, 11, 0.55);
  background: rgba(255, 251, 235, 0.86);
  color: #92400e;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  font-size: 12px;
  font-weight: 650;
}

.sleep-notice button {
  height: 28px;
  border: 1px solid rgba(245, 158, 11, 0.5);
  background: rgba(255, 255, 255, 0.86);
  color: #92400e;
  border-radius: 999px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
}

.config-body {
  min-height: 0;
  overflow-y: auto;
  padding: 20px 24px 28px;
}

.config-body.muted {
  opacity: 0.68;
}

.config-body-inner {
  width: 100%;
  max-width: 980px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.setting-block,
.setting-line {
  border: 1px solid rgba(226, 232, 240, 0.88);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.035);
}

.setting-label {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.setting-label strong {
  font-size: 14px;
  font-weight: 850;
  color: #102f36;
}

.setting-label span {
  color: #71828a;
  font-size: 12px;
  font-weight: 500;
}

.option-grid {
  display: grid;
  gap: 8px;
}

.option-grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.option-grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.option-button {
  min-height: 38px;
  border: 1px solid rgba(226, 232, 240, 0.96);
  background: rgba(255, 255, 255, 0.82);
  border-radius: 12px;
  color: #64748b;
  font-size: 12px;
  font-weight: 750;
  cursor: pointer;
  transition:
      transform 0.16s ease,
      box-shadow 0.16s ease,
      border-color 0.16s ease,
      background 0.16s ease,
      color 0.16s ease;
}

.option-button:hover {
  border-color: color-mix(in srgb, var(--agent-accent) 40%, white);
  color: var(--agent-text);
  background: rgba(255, 255, 255, 0.96);
  transform: translateY(-1px);
}

.option-button.active {
  background: var(--agent-soft);
  border-color: color-mix(in srgb, var(--agent-accent) 56%, white);
  color: var(--agent-text);
  box-shadow: 0 8px 16px var(--agent-glow);
}

.segmented-control {
  min-height: 44px;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 13px;
  background: rgba(248, 250, 252, 0.82);
  padding: 4px;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  gap: 4px;
}

.segmented-control button {
  border: 0;
  background: transparent;
  border-radius: 10px;
  color: #64748b;
  font-size: 12px;
  font-weight: 750;
  cursor: pointer;
  transition:
      color 0.16s ease,
      background 0.16s ease,
      box-shadow 0.16s ease;
}

.segmented-control button.active {
  background: #ffffff;
  color: var(--agent-text);
  box-shadow: 0 6px 14px rgba(148, 163, 184, 0.13);
}

.clean-select {
  width: 100%;
  height: 42px;
  border: 1px solid rgba(226, 232, 240, 0.96);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.88);
  color: #102f36;
  outline: none;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 650;
  transition:
      border-color 0.16s ease,
      box-shadow 0.16s ease,
      background 0.16s ease;
}

.clean-select:focus {
  background: #ffffff;
  border-color: color-mix(in srgb, var(--agent-accent) 52%, white);
  box-shadow: 0 0 0 4px var(--agent-glow);
}

.clean-range {
  width: 100%;
  accent-color: var(--agent-accent);
}

.setting-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.setting-line strong {
  display: block;
  margin-bottom: 4px;
  color: #102f36;
  font-size: 14px;
  font-weight: 850;
}

.setting-line span {
  display: block;
  color: #71828a;
  font-size: 12px;
  font-weight: 500;
}

.hint-text {
  margin: 10px 0 0;
  color: #71828a;
  font-size: 12px;
  line-height: 1.6;
  font-weight: 500;
}

.agent-right-panel {
  grid-row: 1 / 2;
  min-height: 0;
  background: rgba(255, 255, 255, 0.64);
  backdrop-filter: blur(18px);
  border-left: 1px solid rgba(226, 232, 240, 0.72);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.summary-block {
  padding: 16px 16px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.72);
}

.summary-block.fill {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.summary-block.compact {
  flex-shrink: 0;
}

.summary-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.summary-title span {
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.08em;
  color: #3b82f6;
}

.summary-title strong {
  font-size: 13px;
  font-weight: 850;
  color: #102f36;
}

.input-preview {
  margin: 0;
  max-height: 90px;
  overflow-y: auto;
  color: #475569;
  font-size: 13px;
  line-height: 1.65;
  font-weight: 550;
}

.scenario-desc {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed rgba(203, 213, 225, 0.86);
}

.scenario-desc span {
  display: block;
  margin-bottom: 5px;
  color: #94a3b8;
  font-size: 11px;
  font-weight: 800;
}

.scenario-desc strong {
  color: #2563eb;
  font-size: 12px;
  line-height: 1.5;
}

.enabled-list {
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.enabled-row {
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  padding: 10px;
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.025);
}

.enabled-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--agent-accent);
  box-shadow: 0 0 0 4px var(--agent-glow);
}

.enabled-row strong {
  display: block;
  color: #102f36;
  font-size: 12px;
  font-weight: 850;
}

.enabled-row small {
  display: block;
  margin-top: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #71828a;
  font-size: 11px;
  font-weight: 500;
}

.check-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 32px;
  color: #64748b;
  font-size: 12px;
  font-weight: 650;
}

.check-row strong {
  color: #102f36;
  font-weight: 850;
}

.check-row strong.danger {
  color: #b45309;
}

.bottom-action-bar {
  grid-column: 1 / -1;
  grid-row: 2 / 3;
  height: 66px;
  border-top: 1px solid rgba(226, 232, 240, 0.76);
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(18px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 0 20px;
  box-sizing: border-box;
}

.ghost-button,
.primary-button {
  height: 40px;
  border-radius: 999px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 850;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition:
      transform 0.18s ease,
      box-shadow 0.18s ease,
      border-color 0.18s ease,
      background 0.18s ease,
      color 0.18s ease;
}

.ghost-button {
  border: 1px solid rgba(226, 232, 240, 0.95);
  background: rgba(255, 255, 255, 0.76);
  color: #64748b;
}

.ghost-button:hover {
  border-color: rgba(59, 130, 246, 0.42);
  color: #2563eb;
  background: #ffffff;
  transform: translateY(-1px);
}

.primary-button {
  border: 0;
  background: var(--cat-resource, #3b82f6);
  color: #ffffff;
  box-shadow: 0 10px 24px rgba(59, 130, 246, 0.22);
}

.primary-button:hover {
  background: var(--color-info, #2563eb);
  transform: translateY(-1px);
  box-shadow: 0 14px 30px rgba(59, 130, 246, 0.28);
}

.button-icon {
  width: 15px;
  height: 15px;
}

.footer-warning {
  margin: 0;
  color: #b45309;
  font-size: 12px;
  font-weight: 750;
  text-align: center;
}

.compact-switch {
  position: relative;
  width: 38px;
  height: 22px;
  display: inline-block;
  flex-shrink: 0;
}

.compact-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.compact-switch span {
  position: absolute;
  inset: 0;
  cursor: pointer;
  background: #d7e0e4;
  border-radius: 999px;
  transition:
      background 0.18s ease,
      box-shadow 0.18s ease;
}

.compact-switch span::before {
  content: "";
  position: absolute;
  width: 16px;
  height: 16px;
  left: 3px;
  top: 3px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.16);
  transition: transform 0.18s ease;
}

.compact-switch input:checked + span {
  background: var(--agent-accent, #3b82f6);
  box-shadow: 0 0 0 4px var(--agent-glow, rgba(59, 130, 246, 0.14));
}

.compact-switch input:checked + span::before {
  transform: translateX(16px);
}

button,
select {
  font-family: inherit;
}

@media (max-width: 1440px) {
  .agent-config-shell {
    grid-template-columns: 252px minmax(0, 1fr) 268px;
  }
}

@media (max-width: 1280px) {
  .agent-config-shell {
    grid-template-columns: 240px minmax(0, 1fr) 250px;
  }

  .option-grid.three {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1080px) {
  .agent-config-page {
    padding: 10px;
  }

  .agent-config-shell {
    grid-template-columns: 250px minmax(0, 1fr);
  }

  .agent-right-panel {
    display: none;
  }

  .config-body-inner {
    max-width: 100%;
  }
}

@media (max-width: 860px) {
  .agent-config-page {
    height: auto;
    min-height: calc(100vh - var(--navbar-height, 72px));
  }

  .agent-config-shell {
    height: auto;
    min-height: calc(100vh - var(--navbar-height, 72px) - 20px);
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto auto;
  }

  .agent-left-rail {
    border-right: 0;
    border-bottom: 1px solid rgba(226, 232, 240, 0.72);
  }

  .agent-right-panel {
    display: flex;
    border-left: 0;
    border-top: 1px solid rgba(226, 232, 240, 0.72);
  }

  .bottom-action-bar {
    position: static;
    height: auto;
    min-height: 66px;
    flex-wrap: wrap;
    justify-content: center;
    padding: 12px 16px;
  }
}
</style>