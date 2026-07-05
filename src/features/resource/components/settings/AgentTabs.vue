<template>
  <div class="workspace-tabs-bar grid grid-cols-2 border-b border-slate-100 bg-slate-50/50 p-4 gap-3 md:grid-cols-7">
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

      <span
        class="tab-icon-wrap mb-2 flex h-8 w-8 items-center justify-center rounded-xl border transition-all"
        :class="isEnabled(agent.id) ? agent.colorClass : 'border-slate-200 bg-slate-50 text-slate-400'"
      >
        <component :is="agent.icon" class="h-4 w-4" />
      </span>

      <span class="tab-title text-xs font-bold tracking-wide">{{ agent.name }}</span>
      <span class="tab-desc mt-1 w-full truncate text-center text-[9px] font-bold text-slate-400">
        {{ isEnabled(agent.id) ? getSummary(agent.id) : '已关闭' }}
      </span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ResourceAgentId } from '../../model/resource'
import { agentMetaList, type AnyAgentConfigs } from '../../model/catalog'

const props = defineProps<{
  activeId: ResourceAgentId
  enabledIds: ResourceAgentId[]
  configs: AnyAgentConfigs
}>()

const emit = defineEmits<{
  select: [id: ResourceAgentId]
  toggle: [id: ResourceAgentId]
}>()

const agents = computed(() => agentMetaList.filter(agent => (
  !['master', 'assembler'].includes(agent.id)
)))

function isEnabled(id: string) {
  return props.enabledIds.includes(id as ResourceAgentId)
}

function getSummary(id: string) {
  const configs = props.configs
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
  if (id === 'mindmap') {
    const type: Record<string, string> = {
      knowledge_tree: '知识树',
      exam_map: '考点图',
      comparison_map: '对比图',
    }
    return `${type[configs.mindmap.map_type] || configs.mindmap.map_type} · ${configs.mindmap.max_depth}层`
  }
  if (id === 'quiz') {
    const difficulty: Record<string, string> = { basic: '基础', adaptive: '自适应', exam: '考研' }
    return `${difficulty[configs.quiz.difficulty_mode] || configs.quiz.difficulty_mode} · ${configs.quiz.question_count}题`
  }
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
    const difficulty: Record<string, string> = {
      beginner: '入门',
      intermediate: '进阶',
      advanced: '挑战',
    }
    return `${language[configs.code.programming_language] || configs.code.programming_language} · ${difficulty[configs.code.difficulty] || configs.code.difficulty}`
  }
  if (id === 'reading') {
    const depth: Record<string, string> = {
      course_extended: '课内',
      tag_reading: '学术',
      engineering: '工程',
      frontier: '前沿',
    }
    return `${depth[configs.reading.reading_depth] || configs.reading.reading_depth} · ${configs.reading.max_items}篇`
  }
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
  const style: Record<string, string> = { diagram: '图解', minimal: '简约', dark_tech: '暗黑', chalkboard: '黑板' }
  const depth: Record<string, string> = { overview: '概览', standard: '标准', deep: '深度' }; return `${style[configs.cartoon.style] || configs.cartoon.style} · ${depth[configs.cartoon.depth] || configs.cartoon.depth}`
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
