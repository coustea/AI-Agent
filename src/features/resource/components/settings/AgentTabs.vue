<template>
  <!-- 智能体选择标签页栏：以网格展示各智能体并可切换启用状态 -->
  <div class="workspace-tabs-bar grid grid-cols-2 border-b border-slate-100 bg-slate-50/50 p-4 gap-3 md:grid-cols-8">
    <!-- 遍历智能体，点击选中，按启用/激活状态切换样式 -->
    <button
      v-for="agent in agents"
      :key="agent.id"
      type="button"
      class="agent-tab-item relative flex cursor-pointer select-none flex-col items-center justify-center rounded-2xl border border-slate-200 p-4 transition-all"
      :class="[
        `tab-theme-${agent.id}`,
        {
          active: activeId === agent.id,
          'disabled-tab': !isEnabled(agent.id),
        },
      ]"
      @click="emit('select', agent.id as ResourceAgentId)"
    >
      <!-- 右上角启用/停用开关 -->
      <span class="tab-switch absolute right-2 top-2" @click.stop>
        <input
          class="sr-only peer"
          type="checkbox"
          :checked="isEnabled(agent.id)"
          :aria-label="`${isEnabled(agent.id) ? '停用' : '启用'}${agent.name}`"
          @change="emit('toggle', agent.id as ResourceAgentId)"
        />
        <span class="flex h-4 w-4 items-center justify-center rounded-full border border-slate-200 bg-white text-transparent transition-all peer-checked:border-emerald-500 peer-checked:bg-emerald-500 peer-checked:text-white">
          <svg class="h-2.5 w-2.5" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path>
          </svg>
        </span>
      </span>

      <!-- 智能体图标 -->
      <span
        class="tab-icon-wrap mb-2 flex h-8 w-8 items-center justify-center rounded-xl border transition-all"
        :class="isEnabled(agent.id) ? agent.colorClass : 'border-slate-200 bg-slate-50 text-slate-400'"
      >
        <component :is="agent.icon" class="h-4 w-4" />
      </span>

      <!-- 智能体名称与配置摘要（启用时显示摘要，关闭时显示“已关闭”） -->
      <span class="tab-title text-xs font-bold tracking-wide">{{ agent.name }}</span>
      <span class="tab-desc mt-1 w-full truncate text-center text-[9px] font-bold text-slate-400">
        {{ isEnabled(agent.id) ? getSummary(agent.id) : '已关闭' }}
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
// 引入 Vue 计算属性
import { computed } from 'vue'
// 引入智能体标识类型
import type { ResourceAgentId } from '../../model/resource'
// 引入智能体元信息列表与配置联合类型
import { agentMetaList, type AnyAgentConfigs } from '../../model/catalog'

// 组件入参：当前激活 id、已启用 id 列表、各智能体配置
const props = defineProps<{
  activeId: ResourceAgentId
  enabledIds: ResourceAgentId[]
  configs: AnyAgentConfigs
}>()

// 组件事件：选中与切换启用状态
const emit = defineEmits<{
  select: [id: ResourceAgentId]
  toggle: [id: ResourceAgentId]
}>()

// 直接计算为智能体元信息列表
const agents = computed(() => agentMetaList)

// 判断某智能体是否处于启用状态
function isEnabled(id: string) {
  return props.enabledIds.includes(id as ResourceAgentId)
}

// 根据各智能体的配置生成一行中文摘要，用于标签页副标题
function getSummary(id: string) {
  const configs = props.configs
  // 课程讲解：结构 + 深度
  if (id === 'content') {
    const structure: Record<string, string> = {
      progressive: '渐进式',
      summary_first: '先总后分',
      exam_points: '考点驱动',
      case_driven: '案例驱动',
    }
    const depth: Record<string, string> = { quick: '快速', standard: '标准', deep: '深度' }
    return `${structure[configs.content.structure] || configs.content.structure} · ${depth[configs.content.depth_level] || configs.content.depth_level}`
  }
  // 思维导图：类型 + 层数
  if (id === 'mindmap') {
    const type: Record<string, string> = {
      knowledge_tree: '知识树',
      exam_map: '考点图',
      comparison_map: '对比图',
    }
    return `${type[configs.mindmap.map_type] || configs.mindmap.map_type} · ${configs.mindmap.max_depth}层`
  }
  // 随堂练习：难度 + 题数
  if (id === 'quiz') {
    const difficulty: Record<string, string> = { basic: '基础', adaptive: '自适应', exam: '考研' }
    return `${difficulty[configs.quiz.difficulty_mode] || configs.quiz.difficulty_mode} · ${configs.quiz.question_count}题`
  }
  // 代码实操：语言 + 输出风格
  if (id === 'code') {
    const language: Record<string, string> = {
      python: 'Python',
      c: 'C',
      cpp: 'C++',
      java: 'Java',
      go: 'Go',
      javascript: 'JS',
      typescript: 'TS',
    }
    const outputStyle: Record<string, string> = {
      tutorial: '教学',
      reference: '参考',
      challenge: '挑战',
    }
    return `${language[configs.code.programming_language] || configs.code.programming_language} · ${outputStyle[configs.code.output_style] || configs.code.output_style}`
  }
  // 拓展阅读：覆盖度 + 篇数
  if (id === 'reading') {
    const coverage: Record<string, string> = {
      core: '精选',
      extended: '延伸',
      broad: '广泛',
    }
    return `${coverage[configs.reading.coverage] || configs.reading.coverage} · ${configs.reading.max_items}篇`
  }
  // 演示幻灯：讲解风格 + 密度
  if (id === 'ppt') {
    const style: Record<string, string> = {
      concept: '概念',
      case_driven: '案例',
      problem_led: '问题',
      review: '复习',
    }
    const density: Record<string, string> = { concise: '精炼', standard: '标准', detailed: '深入' }
    return `${style[configs.ppt.explanation_style] || configs.ppt.explanation_style} · ${density[configs.ppt.density] || configs.ppt.density}`
  }
  // 动画讲解：风格 + 深度
  if (id === 'cartoon') {
    const style: Record<string, string> = { diagram: '图解', minimal: '简约', dark_tech: '暗黑', chalkboard: '黑板' }
    const depth: Record<string, string> = { overview: '概览', standard: '标准', deep: '深度' }
    return `${style[configs.cartoon.style] || configs.cartoon.style} · ${depth[configs.cartoon.depth] || configs.cartoon.depth}`
  }
  // 讲解视频：风格 + 焦点
  if (id === 'video') {
    const style: Record<string, string> = { precision_light: '精确明亮', systems_dark: '系统深色', editorial_classroom: '编辑式课堂' }
    const focus: Record<string, string> = { concept: '概念', process: '过程', comparison: '对比', practice: '实战' }
    return `${style[configs.video.style] || configs.video.style} · ${focus[configs.video.focus] || configs.video.focus}`
  }
  return id
}
</script>

<style scoped>
.agent-tab-item {
  border-color: rgb(15 23 42 / 6%);
  background: #fff;
}

.agent-tab-item:hover {
  border-color: rgb(15 23 42 / 15%);
}

.agent-tab-item.active {
  border-color: var(--color-primary);
  box-shadow: 0 4px 16px rgb(99 102 241 / 6%);
}

.agent-tab-item.disabled-tab {
  opacity: 0.55;
  background: rgb(248 250 252 / 80%);
}

.tab-icon-wrap {
  border-color: rgb(15 23 42 / 5%);
}

.tab-title {
  color: var(--color-text-strong);
}
</style>
