<template>
  <section class="algorithm-toolbar">
    <div class="toolbar-left">
      <h1 class="toolbar-title">算法可视化实验室</h1>
    </div>

    <div class="toolbar-center">
      <select v-model="localLanguage" class="toolbar-select">
        <option v-for="lang in languages" :key="lang.key" :value="lang.key">
          {{ lang.label }}
        </option>
      </select>

      <select v-model="localAlgorithm" class="toolbar-select">
        <option v-for="alg in algorithms" :key="alg.key" :value="alg.key">
          {{ alg.name }}
        </option>
      </select>
    </div>

    <div class="toolbar-right">
      <button class="toolbar-btn secondary" @click="$emit('reset-template')">
        重置模板
      </button>
      <button
        class="toolbar-btn primary"
        :disabled="generating || !code.trim()"
        @click="$emit('run')"
      >
        {{ generating ? '运行中...' : '运行可视化' }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AlgorithmInfo, CodeLanguage, LanguageInfo } from '@/features/algorithm-visualization/types'

const props = defineProps<{
  language: CodeLanguage
  algorithm: string
  languages: LanguageInfo[]
  algorithms: AlgorithmInfo[]
  code: string
  generating: boolean
}>()

const emit = defineEmits<{
  'update:language': [value: CodeLanguage]
  'update:algorithm': [value: string]
  'run': []
  'reset-template': []
}>()

const localLanguage = computed({
  get: () => props.language,
  set: (value: CodeLanguage) => emit('update:language', value),
})

const localAlgorithm = computed({
  get: () => props.algorithm,
  set: (value: string) => emit('update:algorithm', value),
})
</script>

<style scoped>
.algorithm-toolbar {
  height: 56px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 22px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
}

.toolbar-title {
  margin: 0;
  font-size: 18px;
  font-weight: 720;
  color: #0f172a;
}

.toolbar-center {
  display: flex;
  gap: 10px;
}

.toolbar-select {
  height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid #dbe3ef;
  background: #f8fafc;
  color: #0f172a;
  font-size: 13px;
  font-weight: 600;
  outline: none;
  cursor: pointer;
}

.toolbar-select:focus {
  border-color: rgba(37, 99, 235, 0.7);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.toolbar-btn {
  height: 36px;
  border: none;
  border-radius: 10px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
}

.toolbar-btn.primary {
  background: #2563eb;
  color: #ffffff;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.22);
}

.toolbar-btn.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}

.toolbar-btn.secondary {
  background: #eff6ff;
  color: #1d4ed8;
}

@media (max-width: 768px) {
  .algorithm-toolbar {
    flex-wrap: wrap;
    height: auto;
    padding: 12px;
    gap: 10px;
  }

  .toolbar-center,
  .toolbar-right {
    width: 100%;
  }

  .toolbar-center {
    justify-content: center;
  }

  .toolbar-right {
    justify-content: flex-end;
  }
}
</style>
