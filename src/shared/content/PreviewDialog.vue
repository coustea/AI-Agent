<template>
  <Teleport to="body">
    <transition name="modal-fade">
      <div v-if="activeAgent" class="preview-overlay" @click="close">
        <section
          class="preview-dialog"
          :class="{ 'is-media': normalizedType === 'ppt' || normalizedType === 'video' }"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
          @click.stop
        >
          <header>
            <h3>{{ title }}</h3>
            <button type="button" aria-label="关闭预览" @click="close">×</button>
          </header>

          <div class="preview-body" :class="{ 'is-media': normalizedType === 'ppt' || normalizedType === 'video' }">
            <component
              :is="renderer"
              v-if="renderer && hasRenderableData"
              v-bind="rendererProps"
            />
            <div v-else class="preview-empty">
              <strong>{{ renderer ? '暂无可预览内容' : '暂不支持此内容类型' }}</strong>
              <p>{{ renderer ? '资源内容完成后可在这里查看。' : `未知类型：${activeAgent}` }}</p>
            </div>
          </div>
        </section>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
// PreviewDialog 组件：资源预览模态框，根据资源类型动态选择渲染器

import { computed, type Component } from 'vue'
import Markdown from './renderers/Markdown.vue'
import MindMap from './renderers/MindMap.vue'
import Quiz from './renderers/Quiz.vue'
import Reading from './renderers/Reading.vue'
import Slides from './renderers/Slides.vue'
import Video from './renderers/Video.vue'

const props = defineProps<{
  activeAgent: string | null
  data: any
  resource?: any
}>()

const emit = defineEmits<{
  'update:activeAgent': [value: string | null]
}>()

// 标准化资源类型别名（markdown → content, cartoon → video）
const normalizedType = computed(() => {
  const type = props.activeAgent?.toLowerCase() || ''
  if (type === 'markdown') return 'content'
  if (type === 'cartoon') return 'video'
  return type
})

// 类型到渲染器的映射表
const rendererMap: Record<string, Component> = {
  content: Markdown,
  mindmap: MindMap,
  quiz: Quiz,
  code: Markdown,
  reading: Reading,
  ppt: Slides,
  video: Video,
}

// 类型到中文标题的映射表
const titleMap: Record<string, string> = {
  content: '核心精要',
  mindmap: '思维导图',
  quiz: '测验练习',
  code: '代码实操',
  reading: '拓展阅读',
  ppt: '演示幻灯',
  video: '讲解视频',
  cartoon: '动画讲解',
}

// 当前类型对应的渲染器组件
const renderer = computed(() => rendererMap[normalizedType.value] || null)

// 当前类型对应的中文标题
const title = computed(() => {
  const raw = (props.activeAgent || '').toLowerCase()
  return titleMap[raw] || titleMap[normalizedType.value] || '资源预览'
})

// PPT 需要额外传入 resource，其余只用 data
const hasRenderableData = computed(() => (
  normalizedType.value === 'ppt'
    ? Boolean(props.resource || props.data)
    : Boolean(props.data)
))
const rendererProps = computed(() => (
  normalizedType.value === 'ppt'
    ? { resource: props.resource || props.data }
    : { resultData: props.data }
))

function close() {
  emit('update:activeAgent', null)
}
</script>

<style scoped>
.preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(15 23 42 / 42%);
  backdrop-filter: blur(5px);
}

.preview-dialog {
  display: flex;
  width: min(1120px, 92vw);
  max-height: 88vh;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgb(255 255 255 / 75%);
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 28px 80px rgb(15 23 42 / 24%);
}

.preview-dialog header {
  display: flex;
  min-height: 58px;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid #e8ecf1;
}

.preview-dialog h3 {
  margin: 0;
  color: #263246;
  font-size: 16px;
}

.preview-dialog header button {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 0;
  border-radius: 8px;
  color: #7a8494;
  background: #f3f5f8;
  font-size: 22px;
  cursor: pointer;
}

.preview-body {
  min-height: 240px;
  overflow: auto;
  padding: 24px;
  background: #ffffff;
}

/* PPT uses iframe (white), video uses native player (black poster) */
.preview-body.is-media {
  padding: 0;
  background: #000;
}

.preview-dialog.is-media {
  background: #000;
}

.preview-empty {
  display: grid;
  min-height: 220px;
  place-content: center;
  text-align: center;
}

.preview-empty strong {
  color: #344054;
  font-size: 14px;
}

.preview-empty p {
  margin: 6px 0 0;
  color: #98a2b3;
  font-size: 11px;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.18s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .preview-overlay {
    padding: 10px;
  }

  .preview-dialog {
    width: 100%;
    max-height: 94vh;
    border-radius: 12px;
  }
}
</style>
