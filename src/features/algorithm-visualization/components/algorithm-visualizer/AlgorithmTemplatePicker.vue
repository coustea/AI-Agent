<template>
  <div class="template-picker">
    <span class="field-label">算法模板</span>

    <button
      type="button"
      class="template-trigger"
      :disabled="disabled"
      @click="openPanel"
    >
      <span class="template-mark">{{ selectedInitial }}</span>
      <span class="template-trigger-main">
        <span class="template-name">{{ selectedAlgorithm?.name || '选择算法模板' }}</span>
        <span class="template-meta">{{ selectedCategoryLabel }} · {{ selectedVisualLabel }}</span>
      </span>
      <span
        v-if="selectedAlgorithm"
        :class="['difficulty-tag', selectedAlgorithm.difficulty]"
      >
        {{ difficultyLabel[selectedAlgorithm.difficulty] }}
      </span>
      <ChevronDown class="template-trigger-icon" />
    </button>

    <div
      v-if="panelOpen"
      class="template-backdrop"
      @click="closePanel"
    />

    <section
      v-if="panelOpen"
      class="template-panel"
      @click.stop
    >
      <header class="template-panel-header">
        <div>
          <span class="panel-kicker">模板浏览器</span>
          <h3>选择算法模板</h3>
        </div>

        <button
          type="button"
          class="template-panel-close"
          @click="closePanel"
        >
          <X class="panel-icon" />
        </button>
      </header>

      <div class="template-search-box">
        <Search class="search-icon" />
        <input
          v-model="searchQuery"
          class="template-search-input"
          type="text"
          placeholder="搜索算法、分类或可视化类型"
          autofocus
        />
      </div>

      <div class="template-browser">
        <aside class="template-category-rail">
          <button
            v-for="tab in categoryTabs"
            :key="tab.key"
            type="button"
            class="category-tab"
            :class="{ active: selectedCategoryKey === tab.key }"
            @click="selectedCategoryKey = tab.key"
          >
            <span>{{ tab.label }}</span>
            <span class="category-count">{{ tab.count }}</span>
          </button>
        </aside>

        <div class="template-results">
          <div class="results-toolbar">
            <span>{{ visibleAlgorithmCount }} 个模板</span>
            <span v-if="metaLoading">正在同步后端目录...</span>
          </div>

          <div
            v-if="filteredCategories.length > 0"
            class="template-grid"
          >
            <template
              v-for="category in filteredCategories"
              :key="category.key"
            >
              <button
                v-for="item in category.algorithms"
                :key="item.key"
                type="button"
                class="template-card"
                :class="{ active: item.key === selectedAlgorithmKey }"
                @click="selectAlgorithm(item.key)"
              >
                <span class="template-card-top">
                  <span>{{ category.label }}</span>
                  <Check
                    v-if="item.key === selectedAlgorithmKey"
                    class="check-icon"
                  />
                </span>

                <span class="template-card-title">{{ item.name }}</span>
                <span class="template-card-desc">
                  {{ getAlgorithmDescription(category.label, item.name) }}
                </span>

                <span class="template-card-meta">
                  <span :class="['level-pill', item.difficulty]">
                    {{ difficultyLabel[item.difficulty] }}
                  </span>
                  <span>{{ getVisualizerLabel(item.visualizerType) }}</span>
                </span>
              </button>
            </template>
          </div>

          <div
            v-else
            class="template-empty-result"
          >
            没有找到匹配的算法模板
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Check, ChevronDown, Search, X } from 'lucide-vue-next'
import type { AlgorithmInfo } from '@/features/algorithm-visualization/types'
import type { AlgorithmCategoryGroup } from '@/features/algorithm-visualization/data/visualizerMetadata'
import {
  getAlgorithmDescription,
  getVisualizerLabel,
} from '@/features/algorithm-visualization/data/visualizerMetadata'

const props = defineProps<{
  categories: AlgorithmCategoryGroup[]
  selectedAlgorithm: AlgorithmInfo | null
  selectedAlgorithmKey: string
  selectedCategoryLabel: string
  selectedVisualLabel: string
  disabled?: boolean
  metaLoading?: boolean
}>()

const emit = defineEmits<{
  select: [algorithmKey: string]
}>()

// 面板打开状态、搜索关键词、选中的分类 filter
const panelOpen = ref(false)
const searchQuery = ref('')
const selectedCategoryKey = ref('all')

// 难度等级中文标签
const difficultyLabel: Record<AlgorithmInfo['difficulty'], string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
}

// 触发器首字母
const selectedInitial = computed(() => {
  return props.selectedAlgorithm?.name.slice(0, 1) || '算'
})

// 分类标签页列表（"全部模板" + 各领域）
const categoryTabs = computed(() => {
  const allCount = props.categories.reduce((sum, category) => sum + category.algorithms.length, 0)

  return [
    { key: 'all', label: '全部模板', count: allCount },
    ...props.categories.map((category) => ({
      key: category.key,
      label: category.label,
      count: category.algorithms.length,
    })),
  ]
})

// 按搜索关键词和分类过滤后的算法列表
const filteredCategories = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  return props.categories
    .filter((category) => {
      return selectedCategoryKey.value === 'all' || category.key === selectedCategoryKey.value
    })
    .map((category) => {
      const algorithms = category.algorithms.filter((item) => {
        if (!query) return true

        return [
          item.name,
          item.key,
          category.label,
          getVisualizerLabel(item.visualizerType),
        ].join(' ').toLowerCase().includes(query)
      })

      return { ...category, algorithms }
    })
    .filter((category) => category.algorithms.length > 0)
})

// 可见模板总数
const visibleAlgorithmCount = computed(() => {
  return filteredCategories.value.reduce((sum, category) => sum + category.algorithms.length, 0)
})

// 分类列表变化时，确保当前选中分类仍然有效
watch(
  () => props.categories.map((category) => category.key).join('|'),
  () => {
    if (selectedCategoryKey.value === 'all') return
    const exists = props.categories.some((category) => category.key === selectedCategoryKey.value)
    if (!exists) selectedCategoryKey.value = 'all'
  },
)

// 打开模板选择面板
function openPanel() {
  if (props.disabled) return
  panelOpen.value = true
}

// 关闭模板选择面板
function closePanel() {
  panelOpen.value = false
}

// 选择算法并关闭面板
function selectAlgorithm(algorithmKey: string) {
  emit('select', algorithmKey)
  closePanel()
}
</script>

<style scoped>
.template-picker {
  position: relative;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.field-label {
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
}

.template-trigger {
  width: min(420px, 48vw);
  height: 40px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  border: 1px solid var(--color-primary-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
}

.template-trigger:hover:not(:disabled) {
  border-color: var(--color-primary);
  background: var(--color-surface-hover);
}

.template-trigger:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

.template-mark {
  width: 24px;
  height: 24px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  border-radius: var(--radius-sm);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: 900;
}

.template-trigger-main {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  line-height: 1.1;
}

.template-name,
.template-meta {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-name {
  color: var(--color-text-strong);
  font-size: 13px;
  font-weight: 900;
}

.template-meta {
  margin-top: 3px;
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 700;
}

.template-trigger-icon {
  width: 15px;
  height: 15px;
  flex: 0 0 auto;
  color: var(--color-text-muted);
}

.difficulty-tag,
.level-pill {
  flex: 0 0 auto;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 900;
}

.difficulty-tag {
  padding: 2px 7px;
}

.level-pill {
  padding: 2px 6px;
}

.difficulty-tag.easy,
.level-pill.easy {
  color: var(--color-success);
  background: var(--color-success-soft);
}

.difficulty-tag.medium,
.level-pill.medium {
  color: var(--color-warning);
  background: var(--color-warning-soft);
}

.difficulty-tag.hard,
.level-pill.hard {
  color: var(--color-danger);
  background: var(--color-danger-soft);
}

.template-backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: rgba(15, 23, 42, 0.22);
  backdrop-filter: blur(2px);
}

.template-panel {
  position: fixed;
  top: 50%;
  left: 50%;
  z-index: 60;
  width: min(1040px, calc(100vw - 48px));
  height: min(680px, calc(100vh - 48px));
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  box-shadow: 0 24px 60px rgba(23, 59, 66, 0.18);
  transform: translate(-50%, -50%);
  overflow: hidden;
}

.template-panel-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.panel-kicker {
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 900;
}

.template-panel-header h3 {
  margin: 4px 0 0;
  color: var(--color-text-strong);
  font-size: 16px;
  font-weight: 900;
}

.template-panel-close {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-muted);
  cursor: pointer;
}

.template-panel-close:hover {
  border-color: var(--color-primary);
  color: var(--color-text-strong);
}

.panel-icon,
.search-icon,
.check-icon {
  width: 15px;
  height: 15px;
}

.template-search-box {
  height: 48px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid var(--color-border-light);
  color: var(--color-text-faint);
}

.template-search-input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 700;
}

.template-search-input::placeholder {
  color: var(--color-text-faint);
}

.template-browser {
  min-height: 0;
  display: grid;
  grid-template-columns: 176px minmax(0, 1fr);
}

.template-category-rail {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border-right: 1px solid var(--color-border-light);
  overflow-y: auto;
}

.category-tab {
  width: 100%;
  min-height: 34px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 12px;
  font-weight: 800;
  text-align: left;
  cursor: pointer;
}

.category-tab:hover {
  background: var(--color-surface-hover);
  color: var(--color-text-strong);
}

.category-tab.active {
  border-color: var(--color-primary-border);
  background: var(--color-primary-soft);
  color: var(--color-primary-text);
}

.category-count {
  color: inherit;
  opacity: 0.7;
}

.template-results {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  background: color-mix(in srgb, var(--color-bg) 50%, var(--color-surface));
}

.results-toolbar {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 14px;
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 800;
}

.template-grid {
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
  padding: 0 14px 14px;
  overflow-y: auto;
}

.template-card {
  min-height: 142px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text);
  text-align: left;
  cursor: pointer;
}

.template-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-1px);
}

.template-card.active {
  border-color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary-soft) 72%, var(--color-surface));
}

.template-card-top,
.template-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 800;
}

.template-card-top {
  justify-content: space-between;
}

.template-card-title {
  color: var(--color-text-strong);
  font-size: 15px;
  font-weight: 900;
}

.template-card-desc {
  flex: 1;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.template-card-meta {
  flex-wrap: wrap;
}

.check-icon {
  color: var(--color-primary);
}

.template-empty-result {
  display: grid;
  place-items: center;
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: 800;
}

@media (max-width: 960px) {
  .template-trigger {
    width: min(420px, 72vw);
  }

  .template-panel {
    width: calc(100vw - 24px);
    height: min(680px, calc(100vh - 24px));
  }

  .template-browser {
    grid-template-columns: 1fr;
    grid-template-rows: auto minmax(0, 1fr);
  }

  .template-category-rail {
    flex-direction: row;
    border-right: 0;
    border-bottom: 1px solid var(--color-border-light);
    overflow-x: auto;
  }

  .category-tab {
    width: auto;
    white-space: nowrap;
  }
}

@media (max-width: 640px) {
  .template-picker {
    width: 100%;
    align-items: stretch;
    flex-direction: column;
    gap: 6px;
  }

  .template-trigger {
    width: 100%;
  }

  .difficulty-tag,
  .template-meta {
    display: none;
  }
}
</style>
