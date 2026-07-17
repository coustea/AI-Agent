<template>
  <div class="agent-config-page">
    <div class="config-container">
      <header class="config-topbar">
        <button
          type="button"
          class="back-button"
          @click="emit('back')"
        >
          <ArrowLeft />
          <span>返回需求</span>
        </button>

        <div class="page-heading">
          <div class="heading-icon">
            <SlidersIcon />
          </div>

          <div class="heading-copy">
            <h1>多智能体参数配置</h1>
            <p>选择参与生成的智能体，并调整各类资源的核心参数</p>
          </div>
        </div>

        <div class="topbar-status">
          <span class="step-label">步骤 2 / 3</span>

          <span class="enabled-label">
            <CheckCircle />
            已启用 {{ enabledAgentIds.length }} 个
          </span>
        </div>
      </header>

      <section class="request-bar">
        <div class="request-copy">
          <span>当前学习需求</span>

          <p :title="naturalInput || '暂无原始学习需求。'">
            {{ naturalInput || '暂无原始学习需求。' }}
          </p>
        </div>

        <div
          class="scenario-switcher"
          aria-label="学习场景"
        >
          <span class="scenario-label">学习场景</span>

          <div class="scenario-options">
            <button
              v-for="scenario in scenarioOptions"
              :key="scenario.value"
              type="button"
              :class="{
                active: learningScenario === scenario.value,
              }"
              @click="selectScenario(scenario.value)"
            >
              {{ scenario.name }}
            </button>
          </div>
        </div>
      </section>

      <section
        class="agent-navigation"
        aria-label="协作智能体"
      >
        <div class="agent-navigation-title">
          <div>
            <strong>协作智能体</strong>
            <span>
              至少启用 {{ MIN_ENABLED_AGENTS }} 个，点击智能体切换参数
            </span>
          </div>

          <em>
            {{ enabledAgentIds.length }} / {{ agents.length }}
          </em>
        </div>

        <div class="agent-tabs">
          <button
            v-for="agent in agents"
            :key="agent.id"
            type="button"
            class="agent-tab"
            :class="{
              active: activeAgentId === agent.id,
              disabled: !isAgentEnabled(agent.id),
            }"
            :style="agentThemeStyle(agent.id)"
            @click="selectAgent(agent.id)"
          >
            <span class="agent-tab-icon">
              <component :is="agent.icon" />
            </span>

            <span class="agent-tab-copy">
              <strong>{{ agent.name }}</strong>

              <small>
                {{
                  isAgentEnabled(agent.id)
                    ? getAgentOutput(agent.id)
                    : '未参与生成'
                }}
              </small>
            </span>

            <span
              class="agent-tab-switch"
              @click.stop
            >
              <label
                class="compact-switch"
                :aria-label="`${agent.name}启用状态`"
              >
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

      <main
        class="config-workspace"
      >
        <div
          v-if="!activeAgentEnabled"
          class="disabled-banner"
        >
          <div>
            <strong>该智能体不会参与本次资源生成</strong>
            <span>参数配置会继续保留，重新启用后即可使用。</span>
          </div>

          <button
            type="button"
            @click="toggleAgent(activeAgentId)"
          >
            启用智能体
          </button>
        </div>

        <section
          class="settings-grid"
          :class="{ muted: !activeAgentEnabled }"
        >
          <article
            v-for="(field, index) in activeSettingFields"
            :key="`${activeAgentId}-${field.key}`"
            class="setting-item"
            :class="{
              'switch-setting': field.type === 'switch',
            }"
          >
            <div class="setting-copy">
              <span class="setting-index">
                {{ String(index + 1).padStart(2, '0') }}
              </span>

              <div>
                <strong>{{ field.title }}</strong>
                <p>{{ field.description }}</p>
              </div>

              <em
                v-if="field.type === 'range'"
                class="value-badge"
              >
                {{ getFieldValue(field.key) }}{{ field.unit }}
              </em>
            </div>

            <div
              v-if="
                field.type === 'choice' ||
                field.type === 'multi'
              "
              class="option-grid"
              :class="{
                'two-columns': field.layout !== 'language',
                'language-grid': field.layout === 'language',
              }"
            >
              <button
                v-for="option in field.options"
                :key="option.value"
                type="button"
                class="option-button"
                :class="{
                  active:
                    field.type === 'multi'
                      ? isMultiSelected(field.key, option.value)
                      : getFieldValue(field.key) === option.value,
                }"
                @click="
                  field.type === 'multi'
                    ? toggleMultiValue(field.key, option.value)
                    : setFieldValue(field.key, option.value)
                "
              >
                {{ option.label }}
              </button>
            </div>

            <div
              v-else-if="field.type === 'segment'"
              class="segmented-control"
            >
              <button
                v-for="option in field.options"
                :key="option.value"
                type="button"
                :class="{
                  active: getFieldValue(field.key) === option.value,
                }"
                @click="setFieldValue(field.key, option.value)"
              >
                {{ option.label }}
              </button>
            </div>

            <select
              v-else-if="field.type === 'select'"
              class="clean-select"
              :value="getFieldValue(field.key)"
              @change="setSelectField(field.key, $event)"
            >
              <option
                v-for="option in field.options"
                :key="option.value"
                :value="option.value"
              >
                {{ option.label }}
              </option>
            </select>

            <div
              v-else-if="field.type === 'range'"
              class="range-wrap"
            >
              <input
                class="clean-range"
                type="range"
                :value="getFieldValue(field.key)"
                :min="field.min"
                :max="field.max"
                :step="field.step"
                @input="setRangeField(field.key, $event)"
              />

              <div class="range-scale">
                <span
                  v-for="scale in field.scales"
                  :key="scale"
                >
                  {{ scale }}
                </span>
              </div>
            </div>

            <label
              v-else-if="field.type === 'switch'"
              class="compact-switch large-switch"
            >
              <input
                type="checkbox"
                :checked="Boolean(getFieldValue(field.key))"
                @change="setBooleanField(field.key, $event)"
              />
              <span></span>
            </label>
          </article>
        </section>
      </main>

      <footer class="action-footer">
        <div class="footer-copy">
          <strong>
            {{ enabledAgentIds.length }} 个智能体将并行生成资源
          </strong>

          <span
            v-if="enabledAgentIds.length === MIN_ENABLED_AGENTS"
          >
            当前已达到最低协作数量，无法继续关闭智能体。
          </span>

          <span v-else>
            所有参数会在开始生成时统一提交。
          </span>
        </div>

        <button
          type="button"
          class="primary-button"
          :disabled="!canLaunch"
          @click="launchGeneration"
        >
          开始生成资源
          <Position />
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  ref,
  watch,
} from 'vue'

import {
  PhArrowLeft as ArrowLeft,
  PhCheckCircle as CheckCircle,
  PhPaperPlaneTilt as Position,
  PhSlidersHorizontal as SlidersIcon,
} from '@phosphor-icons/vue'

import { toast } from 'vue-sonner'

import type {
  LearningScenario,
  ResourceAgentId,
} from '@/features/resource/model/resource'

import {
  SCENARIO_DEFAULTS,
  agentMetaList,
  scenarioOptions,
  type AnyAgentConfigs,
} from '../model/catalog'

type SettingType =
  | 'choice'
  | 'segment'
  | 'select'
  | 'range'
  | 'switch'
  | 'multi'

interface SettingOption {
  label: string
  value: string
}

interface SettingField {
  key: string
  title: string
  description: string
  type: SettingType
  options?: SettingOption[]
  layout?: 'default' | 'language'
  min?: number
  max?: number
  step?: number
  scales?: Array<string | number>
  unit?: string
}

const props = defineProps<{
  learningScenario: LearningScenario
  enabledAgentIds: ResourceAgentId[]
  agentConfigs: AnyAgentConfigs
  naturalInput?: string
}>()

const emit = defineEmits<{
  'update:learningScenario': [
    value: LearningScenario,
  ]
  'update:enabledAgentIds': [
    value: ResourceAgentId[],
  ]
  'update:agentConfigs': [
    value: AnyAgentConfigs,
  ]
  back: []
  launch: []
}>()

const MIN_ENABLED_AGENTS = 3

const clone = <T,>(value: T): T =>
  JSON.parse(JSON.stringify(value)) as T

const activeAgentId =
  ref<ResourceAgentId>('content')

const localConfigs = ref<AnyAgentConfigs>(
  clone(props.agentConfigs),
)

const learningScenario = computed({
  get: () => props.learningScenario,
  set: (value: LearningScenario) => {
    emit('update:learningScenario', value)
  },
})

const enabledAgentIds = computed({
  get: () => props.enabledAgentIds,
  set: (value: ResourceAgentId[]) => {
    emit('update:enabledAgentIds', value)
  },
})

const agents = computed(() => agentMetaList)

const naturalInput = computed(
  () => props.naturalInput?.trim() || '',
)

const activeAgentEnabled = computed(() =>
  isAgentEnabled(activeAgentId.value),
)

const canLaunch = computed(
  () =>
    enabledAgentIds.value.length >=
    MIN_ENABLED_AGENTS,
)

const agentSettingSchemas: Record<
  ResourceAgentId,
  SettingField[]
> = {
  content: [
    {
      key: 'structure',
      title: '讲解组织结构',
      description: '决定知识内容的展开顺序与学习节奏',
      type: 'choice',
      options: [
        {
          label: '渐进式引导',
          value: 'progressive',
        },
        {
          label: '先总后分',
          value: 'summary_first',
        },
        {
          label: '考点驱动',
          value: 'exam_points',
        },
        {
          label: '案例驱动',
          value: 'case_driven',
        },
      ],
    },
    {
      key: 'depth_level',
      title: '讲解深度',
      description: '控制解释长度、概念推导与细节强度',
      type: 'segment',
      options: [
        {
          label: '快速概述',
          value: 'quick',
        },
        {
          label: '标准讲解',
          value: 'standard',
        },
        {
          label: '深度推导',
          value: 'deep',
        },
      ],
    },
    {
      key: 'focus_mode',
      title: '聚焦模式',
      description: '指定文档优先强化的内容范围',
      type: 'select',
      options: [
        {
          label: '薄弱点强化',
          value: 'weak_points',
        },
        {
          label: '核心概念提炼',
          value: 'key_concepts',
        },
        {
          label: '完整知识覆盖',
          value: 'full_coverage',
        },
      ],
    },
    {
      key: 'include_examples',
      title: '加入生活化类比',
      description: '用具象案例解释抽象概念、公式或机制',
      type: 'switch',
    },
  ],

  mindmap: [
    {
      key: 'map_type',
      title: '思维导图类型',
      description: '选择知识节点的主要组织方式',
      type: 'select',
      options: [
        {
          label: '层级知识树',
          value: 'knowledge_tree',
        },
        {
          label: '考点重点图',
          value: 'exam_map',
        },
        {
          label: '对比复习图',
          value: 'comparison_map',
        },
      ],
    },
    {
      key: 'max_depth',
      title: '最大层级',
      description: '控制知识树的纵向展开深度',
      type: 'range',
      min: 2,
      max: 5,
      step: 1,
      scales: [2, 3, 4, 5],
      unit: ' 层',
    },
    {
      key: 'leaf_detail',
      title: '叶子节点密度',
      description: '控制末级节点的文字长度与解释量',
      type: 'segment',
      options: [
        {
          label: '核心词',
          value: 'keyword',
        },
        {
          label: '简要注释',
          value: 'brief_note',
        },
        {
          label: '详细注释',
          value: 'annotated',
        },
      ],
    },
    {
      key: 'show_relations',
      title: '显示跨分支关联',
      description: '补充概念之间非层级的关联关系',
      type: 'switch',
    },
  ],

  code: [
    {
      key: 'programming_language',
      title: '编程语言',
      description: '选择代码实操案例使用的主要语言',
      type: 'choice',
      layout: 'language',
      options: [
        {
          label: 'Python',
          value: 'python',
        },
        {
          label: 'C',
          value: 'c',
        },
        {
          label: 'Java',
          value: 'java',
        },
        {
          label: 'C++',
          value: 'cpp',
        },
        {
          label: 'Go',
          value: 'go',
        },
        {
          label: 'JS',
          value: 'javascript',
        },
        {
          label: 'TS',
          value: 'typescript',
        },
      ],
    },
    {
      key: 'output_style',
      title: '源码类型',
      description: '决定案例偏教学、参考实现或挑战练习',
      type: 'segment',
      options: [
        {
          label: '教学案例',
          value: 'tutorial',
        },
        {
          label: '参考实现',
          value: 'reference',
        },
        {
          label: '挑战练习',
          value: 'challenge',
        },
      ],
    },
    {
      key: 'focus',
      title: '讲解侧重',
      description: '指定代码说明与实践指导的重点',
      type: 'select',
      options: [
        {
          label: '语法机制与 API 边界',
          value: 'syntax',
        },
        {
          label: '工程实践与集成方式',
          value: 'application',
        },
        {
          label: '调试思路与错误排查',
          value: 'debugging',
        },
      ],
    },
    {
      key: 'include_tests',
      title: '包含测试用例',
      description: '为示例代码补充可运行校验或断言',
      type: 'switch',
    },
  ],

  quiz: [
    {
      key: 'difficulty_mode',
      title: '题目难度策略',
      description: '设置练习题的整体难度分布方式',
      type: 'select',
      options: [
        {
          label: '基础辨析',
          value: 'basic',
        },
        {
          label: '自适应梯度',
          value: 'adaptive',
        },
        {
          label: '考试强化',
          value: 'exam',
        },
      ],
    },
    {
      key: 'question_count',
      title: '题目数量',
      description: '设置本次生成的练习题总数',
      type: 'range',
      min: 1,
      max: 20,
      step: 1,
      scales: [1, 5, 10, 15, 20],
      unit: ' 题',
    },
    {
      key: 'emphasis',
      title: '考查侧重',
      description: '控制题目更偏概念、应用还是分析推理',
      type: 'segment',
      options: [
        {
          label: '基础概念',
          value: 'foundations',
        },
        {
          label: '应用迁移',
          value: 'application',
        },
        {
          label: '分析推理',
          value: 'analysis',
        },
      ],
    },
    {
      key: 'question_types',
      title: '题型范围',
      description: '可多选，至少保留一种题型',
      type: 'multi',
      options: [
        {
          label: '单选题',
          value: 'single',
        },
        {
          label: '多选题',
          value: 'multiple',
        },
        {
          label: '判断题',
          value: 'judge',
        },
        {
          label: '填空题',
          value: 'fill',
        },
      ],
    },
  ],

  reading: [
    {
      key: 'coverage',
      title: '资源覆盖范围',
      description: '控制推荐资料的广度与延展范围',
      type: 'segment',
      options: [
        {
          label: '核心精选',
          value: 'core',
        },
        {
          label: '横向延展',
          value: 'extended',
        },
        {
          label: '广泛覆盖',
          value: 'broad',
        },
      ],
    },
    {
      key: 'focus',
      title: '资源侧重',
      description: '选择优先推荐的资料类别',
      type: 'select',
      options: [
        {
          label: '教材 / 专著',
          value: 'textbook',
        },
        {
          label: '官方文档 / 工程博客',
          value: 'engineering',
        },
        {
          label: '论文 / 白皮书',
          value: 'research',
        },
      ],
    },
    {
      key: 'max_items',
      title: '推荐数量',
      description: '限制本次拓展阅读清单的最大数量',
      type: 'range',
      min: 1,
      max: 10,
      step: 1,
      scales: [1, 3, 5, 8, 10],
      unit: ' 篇',
    },
    {
      key: 'language_preference',
      title: '语言偏好',
      description: '限定推荐资料使用的语言范围',
      type: 'segment',
      options: [
        {
          label: '中文',
          value: 'chinese',
        },
        {
          label: '英文',
          value: 'english',
        },
        {
          label: '中英混合',
          value: 'both',
        },
      ],
    },
  ],

  ppt: [
    {
      key: 'narrative_style',
      title: '叙事方式',
      description: '决定教学总监如何组织整套叙事与页面视觉重点',
      type: 'choice',
      options: [
        {
          label: '概念递进',
          value: 'concept',
        },
        {
          label: '案例驱动',
          value: 'case_driven',
        },
        {
          label: '问题引导',
          value: 'problem_led',
        },
        {
          label: '复习巩固',
          value: 'review',
        },
      ],
    },
    {
      key: 'density',
      title: '内容密度',
      description: '调整页面文字与配套讲稿的详略程度',
      type: 'segment',
      options: [
        {
          label: '精炼',
          value: 'concise',
        },
        {
          label: '标准',
          value: 'standard',
        },
        {
          label: '详细',
          value: 'detailed',
        },
      ],
    },
    {
      key: 'emphasis',
      title: '教学重点',
      description: '可多选，至少保留一个教学重点',
      type: 'multi',
      options: [
        {
          label: '核心概念',
          value: 'core_concepts',
        },
        {
          label: '案例应用',
          value: 'cases',
        },
        {
          label: '易错误区',
          value: 'pitfalls',
        },
        {
          label: '推导过程',
          value: 'derivation',
        },
      ],
    },
  ],

  cartoon: [
    {
      key: 'lesson_depth',
      title: '课程深度',
      description: '控制知识讲解的深度和广度',
      type: 'segment',
      options: [
        {
          label: '聚焦',
          value: 'focused',
        },
        {
          label: '标准',
          value: 'standard',
        },
        {
          label: '深入',
          value: 'deep',
        },
      ],
    },
    {
      key: 'visual_density',
      title: '画面信息密度',
      description: '控制每幕知识模型、关系和状态变化的丰富程度',
      type: 'segment',
      options: [
        {
          label: '适中',
          value: 'moderate',
        },
        {
          label: '丰富',
          value: 'rich',
        },
        {
          label: '高密度',
          value: 'intensive',
        },
      ],
    },
    {
      key: 'pace',
      title: '讲解节奏',
      description: '控制旁白语速和动画推进的紧凑程度',
      type: 'segment',
      options: [
        {
          label: '紧凑',
          value: 'fast',
        },
        {
          label: '均衡',
          value: 'balanced',
        },
        {
          label: '从容',
          value: 'calm',
        },
      ],
    },
    {
      key: 'voice',
      title: '配音角色',
      description: '选择动画讲解使用的表达方式',
      type: 'segment',
      options: [
        {
          label: '教师讲解',
          value: 'teacher',
        },
        {
          label: '教练引导',
          value: 'coach',
        },
      ],
    },
  ],
}

const activeSettingFields = computed(
  () =>
    agentSettingSchemas[
      activeAgentId.value
    ] ?? [],
)

watch(
  () => props.enabledAgentIds,
  (ids) => {
    if (
      ids.length >=
      MIN_ENABLED_AGENTS
    ) {
      return
    }

    const normalized = [...ids]

    for (const agent of agentMetaList) {
      if (!normalized.includes(agent.id)) {
        normalized.push(agent.id)
      }

      if (
        normalized.length >=
        MIN_ENABLED_AGENTS
      ) {
        break
      }
    }

    emit(
      'update:enabledAgentIds',
      normalized,
    )
  },
  {
    immediate: true,
  },
)

watch(
  () => props.agentConfigs,
  (value) => {
    localConfigs.value = clone(value)
  },
  {
    deep: true,
  },
)

watch(
  localConfigs,
  (value) => {
    emit(
      'update:agentConfigs',
      clone(value),
    )
  },
  {
    deep: true,
  },
)

function isAgentEnabled(
  id: ResourceAgentId | string,
): boolean {
  return enabledAgentIds.value.includes(
    id as ResourceAgentId,
  )
}

function selectAgent(
  id: ResourceAgentId | string,
): void {
  activeAgentId.value =
    id as ResourceAgentId
}

function toggleAgent(
  id: ResourceAgentId | string,
): void {
  const agentId = id as ResourceAgentId
  const index =
    enabledAgentIds.value.indexOf(agentId)

  if (index >= 0) {
    if (
      enabledAgentIds.value.length <=
      MIN_ENABLED_AGENTS
    ) {
      toast.warning(
        `至少需要保留 ${MIN_ENABLED_AGENTS} 个智能体`,
      )
      return
    }

    const next = [
      ...enabledAgentIds.value,
    ]

    next.splice(index, 1)
    enabledAgentIds.value = next
    return
  }

  enabledAgentIds.value = [
    ...enabledAgentIds.value,
    agentId,
  ]
}

function selectScenario(
  scenario: LearningScenario,
): void {
  learningScenario.value = scenario

  const defaults =
    SCENARIO_DEFAULTS[scenario]

  if (!defaults) {
    return
  }

  localConfigs.value = clone({
    ...localConfigs.value,
    ...defaults,
  })
}

function getActiveAgentConfig(): Record<
  string,
  unknown
> {
  const configs =
    localConfigs.value as unknown as Record<
      ResourceAgentId,
      Record<string, unknown>
    >

  return configs[activeAgentId.value]
}

function getFieldValue(
  key: string,
): unknown {
  return getActiveAgentConfig()[key]
}

function setFieldValue(
  key: string,
  value: unknown,
): void {
  getActiveAgentConfig()[key] = value
}

function setSelectField(
  key: string,
  event: Event,
): void {
  const target =
    event.target as HTMLSelectElement

  setFieldValue(key, target.value)
}

function setRangeField(
  key: string,
  event: Event,
): void {
  const target =
    event.target as HTMLInputElement

  setFieldValue(
    key,
    Number(target.value),
  )
}

function setBooleanField(
  key: string,
  event: Event,
): void {
  const target =
    event.target as HTMLInputElement

  setFieldValue(
    key,
    target.checked,
  )
}

function isMultiSelected(
  key: string,
  value: string,
): boolean {
  const current = getFieldValue(key)

  return (
    Array.isArray(current) &&
    current.includes(value)
  )
}

function toggleMultiValue(
  key: string,
  value: string,
): void {
  const currentValue = getFieldValue(key)

  const current = Array.isArray(currentValue)
    ? [...currentValue]
    : []

  const index = current.indexOf(value)

  if (index >= 0) {
    if (current.length <= 1) {
      toast.warning(
        key === 'question_types'
          ? '至少需要保留一种题型'
          : '至少需要保留一个教学重点',
      )
      return
    }

    current.splice(index, 1)
  } else {
    current.push(value)
  }

  setFieldValue(key, current)
}

function launchGeneration(): void {
  if (!canLaunch.value) {
    toast.warning(
      `请至少启用 ${MIN_ENABLED_AGENTS} 个智能体`,
    )
    return
  }

  emit('launch')
}

function getAgentOutput(
  id: ResourceAgentId | string,
): string {
  const outputMap: Record<
    ResourceAgentId,
    string
  > = {
    content: '讲解文档',
    mindmap: '思维导图',
    code: '代码示例',
    quiz: '练习题',
    reading: '阅读清单',
    ppt: 'PPT 文件',
    cartoon: '动画视频',
  }

  return (
    outputMap[id as ResourceAgentId] ??
    '学习资源'
  )
}

function agentThemeStyle(
  id: ResourceAgentId | string,
): Record<string, string> {
  const themes: Record<
    ResourceAgentId,
    {
      accent: string
      soft: string
      text: string
      glow: string
    }
  > = {
    content: {
      accent: '#3b82f6',
      soft: 'rgba(59, 130, 246, 0.10)',
      text: '#1d4ed8',
      glow: 'rgba(59, 130, 246, 0.20)',
    },

    mindmap: {
      accent: '#8b5cf6',
      soft: 'rgba(139, 92, 246, 0.10)',
      text: '#6d28d9',
      glow: 'rgba(139, 92, 246, 0.20)',
    },

    code: {
      accent: '#10b981',
      soft: 'rgba(16, 185, 129, 0.10)',
      text: '#047857',
      glow: 'rgba(16, 185, 129, 0.20)',
    },

    quiz: {
      accent: '#f43f5e',
      soft: 'rgba(244, 63, 94, 0.10)',
      text: '#be123c',
      glow: 'rgba(244, 63, 94, 0.20)',
    },

    reading: {
      accent: '#f59e0b',
      soft: 'rgba(245, 158, 11, 0.11)',
      text: '#b45309',
      glow: 'rgba(245, 158, 11, 0.20)',
    },

    ppt: {
      accent: '#6366f1',
      soft: 'rgba(99, 102, 241, 0.10)',
      text: '#4338ca',
      glow: 'rgba(99, 102, 241, 0.20)',
    },

    cartoon: {
      accent: '#ec4899',
      soft: 'rgba(236, 72, 153, 0.10)',
      text: '#be185d',
      glow: 'rgba(236, 72, 153, 0.20)',
    },
  }

  const theme =
    themes[id as ResourceAgentId] ??
    themes.content

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
  --page-blue: var(
    --cat-resource,
    #3b82f6
  );

  --page-blue-soft: var(
    --cat-resource-soft,
    #eff6ff
  );

  width: 100%;
  min-height: calc(
    100vh - var(--navbar-height, 72px)
  );
  padding:
    20px
    clamp(18px, 3vw, 42px)
    30px;
  box-sizing: border-box;
  background: #fafafa;
  color: var(
    --color-text,
    #334155
  );
  color-scheme: light;
}

.config-container {
  width: min(1320px, 100%);
  margin: 0 auto;
}

.config-topbar {
  position: relative;
  min-height: 56px;
  display: grid;
  grid-template-columns:
    136px
    minmax(0, 1fr)
    auto;
  align-items: center;
  gap: 18px;
  padding: 0 2px 14px;
  border-bottom: 1px solid #dfe7f0;
}

.back-button,
.primary-button,
.agent-tab,
.option-button,
.segmented-control button,
.scenario-options button,
.disabled-banner button {
  font: inherit;
}

.back-button {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 0;
  padding: 7px 0;
  background: transparent;
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: color 0.18s ease;
}

.back-button:hover {
  color: var(--page-blue);
}

.back-button svg {
  width: 17px;
  height: 17px;
}

.page-heading {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 11px;
}

.heading-icon {
  flex: 0 0 auto;
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border: 1px solid #cfe0f5;
  border-radius: 10px;
  background: #ffffff;
  color: var(--page-blue);
  box-shadow:
    0 4px 12px
    rgba(45, 83, 126, 0.07);
}

.heading-icon svg {
  width: 19px;
  height: 19px;
}

.heading-copy {
  min-width: 0;
}

.page-heading h1 {
  margin: 0;
  color: var(
    --color-text-strong,
    #0f172a
  );
  font-size: clamp(
    20px,
    1.7vw,
    24px
  );
  font-weight: 800;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.page-heading p {
  margin: 4px 0 0;
  color: var(
    --color-text-muted,
    #64748b
  );
  font-size: 12px;
  line-height: 1.4;
}

.topbar-status {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  white-space: nowrap;
}

.step-label {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 700;
}

.enabled-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #0f766e;
  font-size: 13px;
  font-weight: 750;
}

.enabled-label svg {
  width: 16px;
  height: 16px;
}

.request-bar {
  min-height: 72px;
  display: grid;
  grid-template-columns:
    minmax(0, 1fr)
    auto;
  align-items: center;
  gap: 28px;
  padding: 14px 2px;
  border-bottom: 1px solid #dfe7f0;
}

.request-copy {
  min-width: 0;
  display: grid;
  grid-template-columns:
    auto
    minmax(0, 1fr);
  align-items: center;
  gap: 14px;
}

.request-copy > span,
.scenario-label {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 750;
  white-space: nowrap;
}

.request-copy p {
  min-width: 0;
  margin: 0;
  overflow: hidden;
  color: #334155;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scenario-switcher {
  display: flex;
  align-items: center;
  gap: 12px;
}

.scenario-options {
  display: inline-flex;
  align-items: center;
  padding: 3px;
  border: 1px solid #dce5ef;
  border-radius: 10px;
  background: #ffffff;
}

.scenario-options button {
  min-height: 32px;
  border: 0;
  border-radius: 7px;
  padding: 0 13px;
  background: transparent;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
    background 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.scenario-options button:hover {
  color: #334155;
}

.scenario-options button.active {
  background:
    var(--page-blue-soft);
  color: var(--page-blue);
  box-shadow:
    0 1px 3px
    rgba(59, 130, 246, 0.12);
}

.agent-navigation {
  padding-top: 18px;
}

.agent-navigation-title {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  padding: 0 2px 11px;
}

.agent-navigation-title > div {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.agent-navigation-title strong {
  color: #1e293b;
  font-size: 15px;
  font-weight: 800;
}

.agent-navigation-title span {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 600;
}

.agent-navigation-title em {
  color: #64748b;
  font-size: 12px;
  font-style: normal;
  font-weight: 750;
}

.agent-tabs {
  display: grid;
  grid-template-columns:
    repeat(
      7,
      minmax(142px, 1fr)
    );
  overflow-x: auto;
  border: none;
  background: transparent;
  scrollbar-width: thin;
}

.agent-tab {
  position: relative;
  min-width: 142px;
  min-height: 74px;
  display: grid;
  grid-template-columns:
    36px
    minmax(0, 1fr)
    auto;
  align-items: center;
  gap: 9px;
  border: 0;
  padding: 11px 10px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition:
    background 0.18s ease,
    opacity 0.18s ease;
}

.agent-tab:last-child {
  border-right: 0;
}

.agent-tab::after {
  content: '';
  position: absolute;
  right: 12px;
  bottom: -1px;
  left: 12px;
  height: 3px;
  border-radius:
    999px 999px 0 0;
  background: transparent;
}

.agent-tab:hover {
  background:
    color-mix(
      in srgb,
      var(--agent-soft) 45%,
      #ffffff
    );
}

.agent-tab.active {
  background:
    color-mix(
      in srgb,
      var(--agent-soft) 64%,
      #ffffff
    );
}

.agent-tab.active::after {
  background:
    var(--agent-accent);
}

.agent-tab.disabled {
  opacity: 0.52;
}

.agent-tab.disabled.active {
  opacity: 0.72;
}

.agent-tab-icon {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border:
    1px solid
    color-mix(
      in srgb,
      var(--agent-accent) 25%,
      #dce5ef
    );
  border-radius: 10px;
  background: #ffffff;
  color: var(--agent-accent);
}

.agent-tab-icon :deep(svg) {
  width: 19px;
  height: 19px;
}

.agent-tab-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.agent-tab-copy strong {
  overflow: hidden;
  color: #243244;
  font-size: 13px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-tab-copy small {
  overflow: hidden;
  color: #94a3b8;
  font-size: 10px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-tab.active
  .agent-tab-copy
  strong,
.agent-tab.active
  .agent-tab-copy
  small {
  color: var(--agent-text);
}

.agent-tab-switch {
  display: grid;
  place-items: center;
}

.config-workspace {
  /* 参数区使用系统冰川绿；多色主题仅用于上方 Agent 选择。 */
  --agent-accent: var(--color-primary, #46b8b4);
  --agent-soft: var(--color-primary-soft, #d8f1f0);
  --agent-text: var(--color-primary-text, #205f67);

  position: relative;
  margin-top: 14px;
  overflow: hidden;
  border: none;
  border-radius: 20px;
  background: transparent;
  box-shadow: none;
}

.disabled-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 18px 20px 0;
  border: 1px solid #fde68a;
  border-radius: 10px;
  padding: 12px 14px;
  background: #fffbeb;
}

.disabled-banner > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.disabled-banner strong {
  color: #92400e;
  font-size: 13px;
  font-weight: 800;
}

.disabled-banner span {
  color: #a16207;
  font-size: 12px;
}

.disabled-banner button {
  flex: 0 0 auto;
  border: 1px solid #f59e0b;
  border-radius: 8px;
  padding: 7px 12px;
  background: #ffffff;
  color: #b45309;
  font-size: 12px;
  font-weight: 750;
  cursor: pointer;
}

.settings-grid {
  display: grid;
  grid-template-columns:
    repeat(2, minmax(0, 1fr));
  gap: 32px 48px;
  padding: 12px 4px;
  transition:
    opacity 0.18s ease,
    filter 0.18s ease;
}

.settings-grid.muted {
  opacity: 0.58;
  filter: saturate(0.72);
}

.setting-item {
  min-width: 0;
  min-height: 184px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 22px;
  padding: 23px;
  border: none;
}

.setting-item:nth-child(2n) {
  border: none;
}

.setting-item:nth-last-child(-n + 2) {
  border: none;
}

.setting-copy {
  min-width: 0;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.setting-copy > div {
  min-width: 0;
  flex: 1;
}

.setting-index {
  flex: 0 0 auto;
  margin-top: 1px;
  color:
    color-mix(
      in srgb,
      var(--agent-accent) 70%,
      #64748b
    );
  font-size: 11px;
  font-weight: 850;
  letter-spacing: 0.04em;
}

.setting-copy strong {
  display: block;
  color: #1e293b;
  font-size: 15px;
  font-weight: 800;
  line-height: 1.35;
}

.setting-copy p {
  margin: 5px 0 0;
  color: #8492a6;
  font-size: 12px;
  line-height: 1.5;
}

.value-badge {
  flex: 0 0 auto;
  border-radius: 8px;
  padding: 4px 8px;
  background:
    color-mix(
      in srgb,
      var(--agent-soft) 72%,
      #ffffff
    );
  color: var(--agent-text);
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}

.option-grid {
  display: grid;
  gap: 8px;
}

.two-columns {
  grid-template-columns:
    repeat(2, minmax(0, 1fr));
}

.language-grid {
  grid-template-columns:
    repeat(4, minmax(0, 1fr));
}

.option-button {
  min-height: 40px;
  border: none;
  border-radius: 8px;
  padding: 8px 10px;
  background: #f1f5f9;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    background 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.option-button:hover {
  background: #e2e8f0;
  color: #334155;
}

.option-button.active {
  background: var(--agent-soft);
  color: var(--agent-text);
  font-weight: 800;
  box-shadow: none;
}

.segmented-control {
  display: grid;
  grid-template-columns:
    repeat(3, minmax(0, 1fr));
  padding: 4px;
  border: none;
  border-radius: 10px;
  background: #f1f5f9;
}

.segmented-control button {
  min-height: 36px;
  border: 0;
  border-radius: 7px;
  padding: 6px 8px;
  background: transparent;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition:
    background 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.segmented-control button:hover {
  color: #334155;
}

.segmented-control button.active {
  background: #ffffff;
  color: var(--agent-text);
  font-weight: 800;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.clean-select {
  width: 100%;
  min-height: 42px;
  appearance: none;
  -webkit-appearance: none;
  color-scheme: light;
  forced-color-adjust: none;
  border: none;
  border-radius: 8px;
  padding: 0 42px 0 13px;

  background-color: #f1f5f9 !important;
  background-image:
    linear-gradient(
      45deg,
      transparent 50%,
      #7b8a9d 50%
    ),
    linear-gradient(
      135deg,
      #7b8a9d 50%,
      transparent 50%
    );
  background-position:
    calc(100% - 18px) 18px,
    calc(100% - 13px) 18px;
  background-size:
    5px 5px,
    5px 5px;
  background-repeat: no-repeat;

  color: #334155 !important;
  font-size: 13px;
  font-weight: 650;
  outline: none;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.clean-select:hover {
  background-color: #e2e8f0 !important;
  color: #334155 !important;
}

.clean-select:focus,
.clean-select:focus-visible {
  background-color: #ffffff !important;
  color: #334155 !important;
  box-shadow: 0 0 0 2px var(--agent-accent);
}

.clean-select:disabled {
  background-color: #f8fafc !important;
  color: #94a3b8 !important;
  cursor: not-allowed;
}

.clean-select option,
.clean-select optgroup {
  color-scheme: light;
  background-color: #ffffff !important;
  color: #334155 !important;
  font-size: 13px;
  font-weight: 500;
}

.clean-select option:hover,
.clean-select option:focus {
  background-color: #eff6ff !important;
  color: #1d4ed8 !important;
}

.clean-select option:checked {
  background:
    linear-gradient(
      0deg,
      #eff6ff,
      #eff6ff
    ) !important;
  background-color: #eff6ff !important;
  color: #1d4ed8 !important;
  font-weight: 700;
}

.range-wrap {
  width: 100%;
}

.clean-range {
  width: 100%;
  height: 5px;
  appearance: none;
  border-radius: 999px;
  background: #e5ebf2;
  outline: none;
  cursor: pointer;
}

.clean-range::-webkit-slider-thumb {
  width: 18px;
  height: 18px;
  appearance: none;
  border: 4px solid #ffffff;
  border-radius: 50%;
  background: var(--agent-accent);
  box-shadow:
    0 1px 5px
    rgba(30, 41, 59, 0.2);
}

.clean-range::-moz-range-thumb {
  width: 12px;
  height: 12px;
  border: 4px solid #ffffff;
  border-radius: 50%;
  background: var(--agent-accent);
  box-shadow:
    0 1px 5px
    rgba(30, 41, 59, 0.2);
}

.range-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 9px;
  color: #a0aec0;
  font-size: 10px;
  font-weight: 650;
}

.switch-setting {
  flex-direction: row;
  align-items: center;
}

.compact-switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

.compact-switch input {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
}

.compact-switch > span {
  position: relative;
  width: 30px;
  height: 18px;
  border-radius: 999px;
  background: #cbd5e1;
  transition: background 0.18s ease;
}

.compact-switch > span::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #ffffff;
  box-shadow:
    0 1px 3px
    rgba(15, 23, 42, 0.22);
  transition:
    transform 0.18s ease;
}

.compact-switch
  input:checked
  + span {
  background:
    var(
      --agent-accent,
      var(--page-blue)
    );
}

.compact-switch
  input:checked
  + span::after {
  transform: translateX(12px);
}

.large-switch > span {
  width: 42px;
  height: 24px;
}

.large-switch > span::after {
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
}

.large-switch
  input:checked
  + span::after {
  transform: translateX(18px);
}

.action-footer {
  min-height: 78px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-top: 17px;
  border-top: 1px solid #dfe7f0;
  padding: 17px 2px 0;
}

.footer-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.footer-copy strong {
  color: #334155;
  font-size: 13px;
  font-weight: 800;
}

.footer-copy span {
  color: #94a3b8;
  font-size: 12px;
}

.primary-button {
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  border: 1px solid var(--page-blue);
  border-radius: 10px;
  padding: 0 18px;
  background: var(--page-blue);
  color: #ffffff;
  font-size: 13px;
  font-weight: 750;
  cursor: pointer;
  box-shadow:
    0 8px 18px
    rgba(59, 130, 246, 0.22);
  transition:
    transform 0.18s ease,
    background 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.primary-button:hover {
  transform: translateY(-1px);
  box-shadow:
    0 10px 24px
    rgba(59, 130, 246, 0.28);
}

.primary-button:disabled {
  border-color: #cbd5e1;
  background: #cbd5e1;
  box-shadow: none;
  cursor: not-allowed;
}

.primary-button:disabled:hover {
  transform: none;
  box-shadow: none;
}

.primary-button svg {
  width: 17px;
  height: 17px;
}

@media (max-width: 1120px) {
  .config-topbar {
    grid-template-columns:
      44px
      minmax(0, 1fr)
      auto;
  }

  .back-button span {
    display: none;
  }

  .request-bar {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .scenario-switcher {
    justify-content: space-between;
  }

  .language-grid {
    grid-template-columns:
      repeat(
        4,
        minmax(86px, 1fr)
      );
  }
}

@media (max-width: 820px) {
  .agent-config-page {
    padding:
      16px
      14px
      24px;
  }

  .config-topbar {
    grid-template-columns:
      auto
      minmax(0, 1fr);
    gap: 12px;
  }

  .page-heading {
    position: static;
    transform: none;
  }

  .topbar-status {
    display: none;
  }

  .page-heading p,
  .agent-navigation-title span {
    display: none;
  }

  .request-copy {
    grid-template-columns: 1fr;
    gap: 5px;
  }

  .scenario-switcher {
    align-items: flex-start;
    flex-direction: column;
  }

  .scenario-options {
    width: 100%;
    overflow-x: auto;
  }

  .scenario-options button {
    flex: 1 0 auto;
  }

  .settings-grid {
    grid-template-columns: 1fr;
  }

  .setting-item,
  .setting-item:nth-child(2n),
  .setting-item:nth-last-child(-n + 2) {
    min-height: auto;
    border-right: 0;
    border-bottom:
      1px solid #e6edf4;
  }

  .setting-item:last-child {
    border-bottom: 0;
  }

  .language-grid {
    grid-template-columns:
      repeat(
        3,
        minmax(0, 1fr)
      );
  }

  .action-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .primary-button {
    width: 100%;
  }
}

@media (max-width: 540px) {
  .page-heading {
    gap: 9px;
  }

  .heading-icon {
    width: 34px;
    height: 34px;
  }

  .page-heading h1 {
    font-size: 19px;
  }

  .disabled-banner {
    align-items: flex-start;
    flex-direction: column;
    margin: 14px 16px 0;
  }

  .setting-item {
    padding: 20px 16px;
  }

  .two-columns,
  .language-grid {
    grid-template-columns:
      repeat(
        2,
        minmax(0, 1fr)
      );
  }

  .switch-setting {
    align-items: flex-start;
  }
}

@media (
  prefers-reduced-motion: reduce
) {
  *,
  *::before,
  *::after {
    scroll-behavior:
      auto !important;
    transition-duration:
      0.01ms !important;
    animation-duration:
      0.01ms !important;
    animation-iteration-count:
      1 !important;
  }
}
</style>
