<script setup lang="ts">
import { computed } from 'vue'
import { isRunActive, type RunState } from '@/features/chat/types/chatEvent'
const props = defineProps<{ run: RunState }>()
const labels: Record<string, string> = { queued: '等待处理', running: '进行中', completed: '已完成', failed: '失败', cancelled: '已停止', interrupted: '运行中断' }
const active = computed(() => isRunActive(props.run))
</script>

<template>
  <section class="run-panel" aria-live="polite">
    <p v-if="active" class="run-status">{{ labels[run.status] }}</p>
    <details v-if="run.activities.length" :open="active">
      <summary>执行记录 · {{ run.activities.length }}</summary>
      <div v-for="activity in run.activities" :key="activity.activity_id" class="activity">
        <strong>{{ activity.title }}</strong><span>{{ labels[activity.status] }}</span>
        <p v-if="activity.detail.error">{{ activity.detail.error }}</p>
        <details v-else-if="activity.detail.input || activity.detail.output">
          <summary>详情</summary>
          <pre v-if="activity.detail.input">{{ activity.detail.input }}</pre>
          <pre v-if="activity.detail.output">{{ activity.detail.output }}</pre>
        </details>
      </div>
    </details>
    <article v-for="artifact in run.artifacts" :key="artifact.id" class="artifact">
      <strong>{{ artifact.title }}</strong>
      <video v-if="artifact.kind === 'video'" :src="artifact.url" controls preload="metadata" />
      <div>
        <a :href="artifact.url" target="_blank" rel="noopener noreferrer">{{ artifact.kind === 'ppt' ? '下载 PPTX' : '下载视频' }}</a>
        <a v-if="artifact.preview_url" :href="artifact.preview_url" target="_blank" rel="noopener noreferrer">预览</a>
      </div>
    </article>
    <p v-if="run.status === 'cancelled'" class="run-status">已停止生成</p>
  </section>
</template>

<style scoped>
.run-panel { margin: 12px 0; font-size: 13px; color: var(--color-text-secondary); }
.run-status { margin: 8px 0; }
summary { cursor: pointer; }
.activity { border-left: 2px solid var(--color-border); padding: 8px 12px; margin-top: 8px; }
.activity > span { float: right; margin-left: 16px; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 240px; overflow: auto; }
.artifact { border: 1px solid var(--color-border); padding: 16px; border-radius: 12px; margin-top: 12px; }
.artifact video { width: 100%; display: block; margin: 12px 0; border-radius: 8px; }
.artifact a { display: inline-block; margin: 12px 16px 0 0; color: var(--color-primary); }
</style>
