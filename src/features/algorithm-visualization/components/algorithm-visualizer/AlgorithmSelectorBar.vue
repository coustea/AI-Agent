<template>
  <div class="selector-bar">
    <div class="selectors">
      <!-- 算法选择 -->
      <div class="selector-group">
        <label>算法</label>
        <Select v-model="localAlgorithm">
          <SelectTrigger class="select-trigger algorithm-trigger">
            <SelectValue placeholder="选择算法">
              <template v-if="selectedAlgorithm">
                <span class="selected-alg-name">{{ selectedAlgorithm.name }}</span>
                <span :class="['difficulty-tag', selectedAlgorithm.difficulty]">
                  {{ difficultyLabel[selectedAlgorithm.difficulty] }}
                </span>
              </template>
            </SelectValue>
          </SelectTrigger>
          <SelectContent class="select-content algorithm-content" align="start">
            <!-- 搜索框 -->
            <div class="search-box">
              <Search class="search-icon" />
              <input
                v-model="searchQuery"
                type="text"
                placeholder="搜索算法..."
                class="search-input"
                @click.stop
              />
            </div>
            <!-- 分类列表 -->
            <div class="category-list">
              <div
                v-for="category in filteredCategories"
                :key="category.key"
                class="category-section"
              >
                <div class="category-header">{{ category.label }}</div>
                <SelectItem
                  v-for="alg in category.algorithms"
                  :key="alg.key"
                  :value="alg.key"
                  class="algorithm-item"
                >
                  <span class="alg-name">{{ alg.name }}</span>
                  <span :class="['alg-difficulty', alg.difficulty]">
                    {{ difficultyLabel[alg.difficulty] }}
                  </span>
                </SelectItem>
              </div>
            </div>
          </SelectContent>
        </Select>
      </div>

      <!-- 语言选择 -->
      <div class="selector-group">
        <label>语言</label>
        <Select v-model="localLanguage">
          <SelectTrigger class="select-trigger language-trigger">
            <SelectValue />
          </SelectTrigger>
          <SelectContent class="select-content" align="start">
            <SelectItem
              v-for="lang in languages"
              :key="lang.key"
              :value="lang.key"
            >
              {{ lang.label }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="actions">
      <Button
        variant="outline"
        class="reset-btn"
        :disabled="loading"
        @click="$emit('reset')"
      >
        <RotateCcw class="btn-icon" />
        重置
      </Button>

      <Button
        class="run-btn"
        :disabled="loading || !codeReady"
        @click="$emit('run')"
      >
        <Play v-if="!loading" class="btn-icon" />
        <Loader2 v-else class="btn-icon spin" />
        {{ loading ? '运行中...' : '运行可视化' }}
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Play, RotateCcw, Search, Loader2 } from 'lucide-vue-next'
import { algorithmCategories } from '@/features/algorithm-visualization/data/algorithmCategories'
import type { CodeLanguage, LanguageInfo, AlgorithmInfo } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  algorithm: string
  language: CodeLanguage
  algorithms: AlgorithmInfo[]
  languages: LanguageInfo[]
  loading: boolean
  codeReady: boolean
}>()

const emit = defineEmits<{
  'update:algorithm': [value: string]
  'update:language': [value: CodeLanguage]
  'run': []
  'reset': []
}>()

const searchQuery = ref('')

const localAlgorithm = computed({
  get: () => props.algorithm,
  set: (value: string) => emit('update:algorithm', value),
})

const localLanguage = computed({
  get: () => props.language,
  set: (value: CodeLanguage) => emit('update:language', value),
})

const selectedAlgorithm = computed(() => {
  for (const cat of algorithmCategories) {
    const alg = cat.algorithms.find((a) => a.key === props.algorithm)
    if (alg) return alg
  }
  return null
})

const difficultyLabel = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
} as const

// 过滤分类，只显示支持当前语言的算法
const filteredCategories = computed(() => {
  const query = searchQuery.value.toLowerCase().trim()
  return algorithmCategories
    .map((cat) => ({
      ...cat,
      algorithms: cat.algorithms.filter((alg) => {
        // 过滤支持当前语言的算法
        if (!alg.supportedLanguages.includes(props.language)) return false
        // 搜索过滤
        if (query) {
          return alg.name.toLowerCase().includes(query)
        }
        return true
      }),
    }))
    .filter((cat) => cat.algorithms.length > 0)
})
</script>

<style scoped>
.selector-bar {
  height: 48px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.selectors {
  display: flex;
  align-items: center;
  gap: 16px;
}

.selector-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selector-group label {
  font-size: 13px;
  color: var(--color-text-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.select-trigger {
  height: 32px;
  border-radius: 0;
  border: 1px solid var(--color-border);
  background: #ffffff;
  font-size: 13px;
}

.select-trigger:hover {
  border-color: var(--color-primary);
}

.algorithm-trigger {
  min-width: 180px;
}

.language-trigger {
  min-width: 100px;
}

.select-content {
  border-radius: 0;
  border: 1px solid var(--color-border);
  background: #ffffff;
}

.selected-alg-name {
  font-weight: 500;
}

.difficulty-tag {
  font-size: 11px;
  padding: 1px 6px;
  margin-left: 6px;
}

.difficulty-tag.easy {
  color: var(--color-success);
  background: var(--color-success-soft);
}

.difficulty-tag.medium {
  color: var(--color-warning);
  background: var(--color-warning-soft);
}

.difficulty-tag.hard {
  color: var(--color-danger);
  background: var(--color-danger-soft);
}

/* 搜索框 */
.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border-light);
}

.search-icon {
  width: 14px;
  height: 14px;
  color: var(--color-text-faint);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 13px;
  background: transparent;
  color: var(--color-text);
}

.search-input::placeholder {
  color: var(--color-text-faint);
}

/* 分类列表 */
.category-list {
  max-height: 360px;
  overflow-y: auto;
}

.category-section {
  border-bottom: 1px solid var(--color-border-light);
}

.category-section:last-child {
  border-bottom: none;
}

.category-header {
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  background: var(--color-bg);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.algorithm-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px 8px 16px;
  font-size: 13px;
  cursor: pointer;
}

.algorithm-item:hover {
  background: var(--color-surface-hover);
}

.alg-name {
  color: var(--color-text);
}

.alg-difficulty {
  font-size: 11px;
  padding: 1px 5px;
}

.alg-difficulty.easy {
  color: var(--color-success);
}

.alg-difficulty.medium {
  color: var(--color-warning);
}

.alg-difficulty.hard {
  color: var(--color-danger);
}

/* 操作按钮 */
.actions {
  display: flex;
  gap: 8px;
}

.run-btn {
  height: 32px;
  padding: 0 16px;
  border-radius: 0;
  background: var(--color-primary);
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  border: none;
}

.run-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.reset-btn {
  height: 32px;
  padding: 0 12px;
  border-radius: 0;
  border: 1px solid var(--color-border);
  background: #ffffff;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.reset-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-text);
}

.btn-icon {
  width: 14px;
  height: 14px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .selector-bar {
    height: auto;
    padding: 8px 12px;
    flex-wrap: wrap;
    gap: 8px;
  }

  .selectors {
    flex-wrap: wrap;
    gap: 8px;
  }

  .actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
