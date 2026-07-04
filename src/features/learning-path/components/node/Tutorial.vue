<template>
  <article class="tutorial-main">
    <header class="tutorial-head">
      <div>
        <span class="section-kicker">AI Tutorial</span>
        <h2>{{ tutorial?.title || nodeTitle }}</h2>
        <p>先完成当前教程，再使用右侧资源智能体生成导图、代码、PPT、拓展阅读和节点测验。</p>
      </div>

      <div v-if="tutorials.length > 1" class="tutorial-tabs">
        <button
          v-for="item in tutorials"
          :key="item.id"
          type="button"
          :class="{ active: item.id === tutorial?.id, current: item.id === currentId }"
          @click="emit('select', item.id)"
        >
          {{ typeLabel(item.tutorial_type) }}
          <em>v{{ item.version_no }}</em>
        </button>
      </div>
    </header>

    <section class="tutorial-reader">
      <div v-if="tutorial" ref="contentEl" class="markdown-shell">
        <Article :result-data="{ content: tutorial.content_markdown }" />
      </div>

      <div v-else class="tutorial-empty">
        <h3>当前节点还没有教程</h3>
        <p>进入节点后系统会自动调用学习推进智能体生成主教程。</p>
      </div>
    </section>
  </article>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Article from '@/shared/content/renderers/Article.vue'
import type { LearningPathTutorial } from '../../model/path'

defineProps<{
  nodeTitle: string
  tutorial: LearningPathTutorial | null
  tutorials: LearningPathTutorial[]
  currentId: number | null
}>()

const emit = defineEmits<{
  select: [id: number]
}>()

const contentEl = ref<HTMLElement | null>(null)

function getContentElement() {
  return contentEl.value
}

function typeLabel(value?: string | null) {
  if (value === 'remediation') return '补救教程'
  if (value === 'reinforced') return '强化教程'
  return '主教程'
}

defineExpose({ getContentElement })
</script>

<style scoped>
.tutorial-main {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #dfe5ec;
  border-radius: 14px;
  background: #fff;
}

.tutorial-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 20px 22px;
  border-bottom: 1px solid #edf0f4;
}

.section-kicker {
  color: #24589d;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.tutorial-head h2 {
  margin: 5px 0 7px;
  color: #263246;
  font-size: 20px;
}

.tutorial-head p {
  max-width: 680px;
  margin: 0;
  color: #667085;
  font-size: 11px;
  line-height: 1.65;
}

.tutorial-tabs {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.tutorial-tabs button {
  padding: 7px 9px;
  border: 1px solid #dfe5ec;
  border-radius: 8px;
  color: #667085;
  background: #fff;
  font-size: 10px;
  cursor: pointer;
}

.tutorial-tabs button.active {
  border-color: #9bb9df;
  color: #24589d;
  background: #edf4fc;
}

.tutorial-tabs em {
  margin-left: 4px;
  color: #98a2b3;
  font-size: 8px;
  font-style: normal;
}

.tutorial-reader {
  min-height: 560px;
  padding: 24px;
}

.markdown-shell {
  max-width: 820px;
  margin: 0 auto;
}

.markdown-shell :deep(.tutorial-anchor-heading) {
  scroll-margin-top: 18px;
}

.tutorial-empty {
  display: grid;
  min-height: 420px;
  place-content: center;
  text-align: center;
}

.tutorial-empty h3,
.tutorial-empty p {
  margin: 0;
}

.tutorial-empty p {
  margin-top: 7px;
  color: #7a8494;
  font-size: 11px;
}
</style>
