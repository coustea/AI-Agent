<template>
  <section class="cartoon-view">
    <div v-if="artifact" class="player-frame">
      <video
        class="player"
        :src="artifact.videoUrl"
        controls
        playsinline
        preload="metadata"
      />
    </div>

    <div v-if="artifact" class="cartoon-meta">
      <div>
        <p class="eyebrow">动画讲解</p>
        <h3>{{ artifact.title }}</h3>
        <p>{{ durationLabel }} · {{ artifact.sceneCount }} 个场景</p>
      </div>
      <a
        class="download-button"
        :href="artifact.videoUrl"
        :download="`${artifact.title}.mp4`"
        title="下载 MP4"
      >
        <Download :size="18" />
        <span>下载</span>
      </a>
    </div>

    <div v-else class="empty-state">
      <LoaderCircle :size="24" class="spinner" />
      <p>动画视频正在生成或产物信息不可用</p>
    </div>
  </section>
</template>

<script setup lang="ts">
// Cartoon 渲染器：展示动画讲解视频（MP4），含播放器、元数据和下载

import { computed } from 'vue'
import { Download, LoaderCircle } from 'lucide-vue-next'

const props = defineProps<{ resultData?: unknown }>()

type CartoonArtifactView = {
  title: string
  videoUrl: string
  durationSeconds: number
  sceneCount: number
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

// 从 resultData 中解析 cartoon 制品（支持字符串 JSON 和嵌套 metadata）
function parseArtifact(value: unknown): CartoonArtifactView | null {
  let candidate = value
  if (typeof candidate === 'string') {
    try {
      candidate = JSON.parse(candidate)
    } catch {
      return null
    }
  }

  const record = asRecord(candidate)
  if (!record) return null
  const nested = asRecord(record.metadata)
  const source = nested?.video_url ? nested : record
  const videoUrl = source.video_url ?? source.public_url
  if (typeof videoUrl !== 'string' || !videoUrl.endsWith('.mp4')) return null

  return {
    title: String(record.title ?? source.title ?? '动画讲解'),
    videoUrl,
    durationSeconds: Number(
      record.duration_seconds ?? source.duration_seconds ?? 0
    ),
    sceneCount: Number(record.scene_count ?? source.scene_count ?? 0),
  }
}

const artifact = computed(() => parseArtifact(props.resultData))

// 时长格式化为 M:SS
const durationLabel = computed(() => {
  const seconds = Math.max(0, Math.round(artifact.value?.durationSeconds ?? 0))
  const minutes = Math.floor(seconds / 60)
  const remaining = String(seconds % 60).padStart(2, '0')
  return `${minutes}:${remaining}`
})
</script>

<style scoped>
.cartoon-view {
  width: 100%;
  color: var(--color-text);
}

.player-frame {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: #ffffff;
  box-shadow: var(--shadow-sm);
}

.player {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000000;
}

.cartoon-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 2px 0;
}

.eyebrow {
  margin: 0 0 4px;
  color: var(--color-primary-text);
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 700;
}

h3 {
  margin: 0;
  font-size: 18px;
  line-height: 1.35;
  color: var(--color-text-strong);
}

.cartoon-meta p:last-child {
  margin: 5px 0 0;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.download-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  gap: 8px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: white;
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  text-decoration: none;
  transition: var(--btn-transition);
}

.download-button:hover {
  background: var(--color-primary-hover);
  transform: translateY(-0.5px);
}

.download-button:active {
  transform: translateY(0.5px);
}

.empty-state {
  display: flex;
  min-height: 280px;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--color-text-faint);
}

.spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
