<template>
  <article
    class="resource-result-card"
    :class="{ 'is-readonly': isReadonly }"
    tabindex="0"
    role="button"
    :aria-label="`打开${title}`"
    @click="handleClick"
    @keydown.enter.prevent="handleClick"
    @keydown.space.prevent="handleClick"
  >
    <div class="resource-card-cover">
      <img :src="coverImage" alt="" loading="lazy" />
      <span class="resource-type-label">
        {{ icon }} {{ label }}
      </span>
      <span class="resource-format-label">{{ normalizedFormat }}</span>
    </div>

    <div class="resource-card-content">
      <div class="resource-card-status" :class="statusClass">
        <i></i> {{ statusText }}
      </div>
      <h2>{{ title }}</h2>
      <p>{{ summary || defaultSummary }}</p>

      <div class="resource-card-meta">
        <span v-if="estimatedLabel">{{ estimatedLabel }}</span>
        <span v-for="tag in highlights" :key="tag">{{ tag }}</span>
      </div>
    </div>

    <footer class="resource-card-footer">
      <span>{{ actionText }}</span>
      <button type="button" :aria-label="`打开${title}`" @click.stop="handleClick">
        <ArrowRight class='w-4 h-4 inline-block align-middle' />
      </button>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { PhArrowRight as ArrowRight } from '@phosphor-icons/vue'

import contentCover from '@/features/resource/assets/result-covers/online-learning.svg'
import mindmapCover from '@/features/resource/assets/result-covers/visual-explanation.svg'
import quizCover from '@/features/resource/assets/result-covers/exam-prep.svg'
import codeCover from '@/features/resource/assets/result-covers/web-developer.svg'
import readingCover from '@/features/resource/assets/result-covers/open-book.svg'
import pptCover from '@/features/resource/assets/result-covers/presentation.svg'
import cartoonCover from '@/features/resource/assets/result-covers/video-tutorial.svg'

import { getArtifactLabel } from '@/shared/content/kind'

const props = withDefaults(defineProps<{
  type: string
  title: string
  summary?: string
  format?: string
  status?: 'completed' | 'pending' | 'draft' | string
  estimatedLabel?: string
  highlights?: string[]
  cardData?: any
}>(), {
  summary: '',
  format: '',
  status: 'completed',
  estimatedLabel: '',
  highlights: () => [],
  cardData: null,
})

const emit = defineEmits<{
  click: [card: any]
}>()

const isReadonly = computed(() => props.status !== 'completed')

const coverImage = computed(() => {
  const covers: Record<string, string> = {
    content: contentCover,
    mindmap: mindmapCover,
    quiz: quizCover,
    code: codeCover,
    reading: readingCover,
    ppt: pptCover,
    cartoon: cartoonCover,
  }
  return covers[props.type] || contentCover
})

const icon = computed(() => {
  const icons: Record<string, string> = {
    content: '📘',
    mindmap: '🧠',
    quiz: '✅',
    code: '💻',
    reading: '📚',
    ppt: '📊',
    cartoon: '🎬',
  }
  return icons[props.type] || '✨'
})

const label = computed(() => getArtifactLabel(props.type))

const normalizedFormat = computed(() => {
  if (props.format) return props.format.toUpperCase()
  const fallback: Record<string, string> = {
    content: 'MARKDOWN',
    mindmap: 'MARKMAP',
    quiz: 'JSON',
    code: 'CODE',
    reading: 'LINKS',
    ppt: 'SLIDES',
    cartoon: 'MP4',
  }
  return fallback[props.type] || 'RESOURCE'
})

const defaultSummary = computed(() => {
  const map: Record<string, string> = {
    content: '围绕本次学习目标组织的系统讲解，帮助建立完整知识框架。',
    mindmap: '将核心概念、关系和层级整理为可视化知识结构。',
    quiz: '通过不同题型检查理解程度，并用于学习后的即时巩固。',
    code: '提供可阅读、可实践的代码案例，帮助将概念转化为操作能力。',
    reading: '补充可靠的课程资料与延伸阅读，便于继续深入学习。',
    ppt: '整合基础资源形成结构化教学课件，适合快速复习和演示。',
    cartoon: '通过知识图形、同步动画、配音和字幕讲清概念与执行过程。',
  }
  return map[props.type] || '根据本次学习需求生成的个性化学习资源。'
})

const statusClass = computed(() => {
  if (props.status === 'completed') return 'status-completed'
  if (props.status === 'pending') return 'status-pending'
  return 'status-draft'
})

const statusText = computed(() => {
  if (props.status === 'completed') return '已就绪'
  if (props.status === 'pending') return '生成中'
  return '就绪后生成'
})

const actionText = computed(() => {
  if (props.status === 'completed') return '查看完整内容'
  if (props.status === 'pending') return '智能体加工中'
  return '预览当前配置'
})

function handleClick() {
  if (props.status === 'completed') {
    emit('click', props.cardData || {
      id: props.type,
      type: props.type,
      title: props.title,
      summary: props.summary,
      format: normalizedFormat.value,
      status: props.status,
    })
  }
}
</script>

<style scoped>
.resource-result-card {
  display: flex;
  overflow: hidden;
  flex-direction: column;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 16px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.05);
  transition: all 0.25s cubic-bezier(0.3, 0.7, 0.1, 1);
  box-sizing: border-box;
}

.resource-result-card:not(.is-readonly):hover {
  border-color: rgba(15, 23, 42, 0.15);
  box-shadow: 0 8px 24px rgba(16, 24, 40, 0.08);
  transform: translateY(-2px);
}

.resource-result-card.is-readonly {
  opacity: 0.85;
  cursor: default;
}

.resource-card-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 2 / 1;
  background: #f8fafc;
  overflow: hidden;
}

.resource-card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.resource-result-card:not(.is-readonly):hover .resource-card-cover img {
  transform: scale(1.03);
}

.resource-type-label,
.resource-format-label {
  position: absolute;
  z-index: 1;
  top: 12px;
  display: inline-flex;
  height: 24px;
  align-items: center;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.resource-type-label {
  left: 12px;
  gap: 6px;
  padding: 0 9px;
  color: #344054;
  font-size: 10px;
  font-weight: 700;
}

.resource-format-label {
  right: 12px;
  padding: 0 8px;
  color: #64748b;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.resource-card-content {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  padding: 18px 20px;
}

.resource-card-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  font-weight: 700;
}

.resource-card-status i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-completed {
  color: #10b981;
}
.status-completed i {
  background: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.15);
}

.status-pending {
  color: #3b82f6;
}
.status-pending i {
  background: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
  animation: pulse 1.5s infinite;
}

.status-draft {
  color: #94a3b8;
}
.status-draft i {
  background: #94a3b8;
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: 0.5; }
  100% { transform: scale(1); opacity: 1; }
}

.resource-card-content h2 {
  display: -webkit-box;
  margin: 10px 0 0;
  overflow: hidden;
  color: #0f172a;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: -0.01em;
  line-height: 1.4;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.resource-card-content > p {
  display: -webkit-box;
  margin: 8px 0 0;
  overflow: hidden;
  color: #475569;
  font-size: 12px;
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}

.resource-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: auto;
  padding-top: 14px;
}

.resource-card-meta span {
  padding: 3px 8px;
  border: 1px solid rgba(15, 23, 42, 0.04);
  border-radius: 6px;
  color: #475569;
  background: #f8fafc;
  font-size: 10px;
  font-weight: 600;
}

.resource-card-footer {
  display: flex;
  min-height: 46px;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px 8px 20px;
  border-top: 1px solid rgba(15, 23, 42, 0.04);
  color: #64748b;
  font-size: 11px;
  font-weight: 700;
  background: #fafafb;
  border-bottom-left-radius: 16px;
  border-bottom-right-radius: 16px;
}

.resource-card-footer button {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 1px solid #cdd9e9;
  border-radius: 7px;
  color: #2c5f9f;
  background: #f4f8fe;
  cursor: pointer;
}

.resource-card-footer button:hover {
  border-color: #8eacd3;
  background: #eaf2fd;
}
</style>
