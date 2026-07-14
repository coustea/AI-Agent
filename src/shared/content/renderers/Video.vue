<template>
  <section class="video-view">
    <div v-if="artifact" class="player-frame">
      <video
        class="player"
        :src="artifact.publicUrl"
        controls
        playsinline
        preload="metadata"
      />
    </div>

    <div v-if="artifact" class="video-meta">
      <div>
        <p class="eyebrow">{{ styleLabel }}</p>
        <h3>{{ artifact.title }}</h3>
        <p>{{ metadataLabel }}</p>
      </div>
      <a
        class="download-button"
        :href="artifact.publicUrl"
        :download="`${artifact.title}.mp4`"
        title="下载 MP4"
      >
        <Download :size="18" />
        <span>下载</span>
      </a>
    </div>

    <div v-else class="empty-state">
      <LoaderCircle :size="24" class="spinner" />
      <p>视频正在生成或产物信息不可用</p>
    </div>
  </section>
</template>

<script setup lang="ts">
// 视频渲染器：展示讲解视频（MP4），含播放器、元数据和下载

import { computed } from 'vue'
import { Download, LoaderCircle } from 'lucide-vue-next'

const props = defineProps<{ resultData?: unknown }>()

type VideoArtifactView = {
  title: string
  publicUrl: string
  durationMs: number
  width: number
  height: number
  sceneCount: number
  style: string
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

// 从 resultData 中解析视频制品（支持字符串 JSON 和嵌套 metadata）
function parseArtifact(value: unknown): VideoArtifactView | null {
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
  const content = asRecord(record.content)
  const contentMetadata = asRecord(content?.metadata)
  const source = nested?.public_url || nested?.video_url
    ? nested
    : contentMetadata?.public_url || contentMetadata?.video_url
      ? contentMetadata
      : content?.public_url || content?.video_url
        ? content
        : record
  const publicUrl = source.public_url ?? source.video_url
  if (typeof publicUrl !== 'string' || !publicUrl.endsWith('.mp4')) return null

  return {
    title: String(record.title ?? source.title ?? '讲解视频'),
    publicUrl,
    durationMs: Number(
      record.duration_ms ??
      source.duration_ms ??
      Number(record.duration_seconds ?? source.duration_seconds ?? 0) * 1000
    ),
    width: Number(record.width ?? source.width ?? 1920),
    height: Number(record.height ?? source.height ?? 1080),
    sceneCount: Number(record.scene_count ?? source.scene_count ?? 0),
    style: String(record.style ?? source.style ?? '')
  }
}

const artifact = computed(() => parseArtifact(props.resultData))

// 时长格式化为 M:SS
const durationLabel = computed(() => {
  const seconds = Math.max(0, Math.round((artifact.value?.durationMs ?? 0) / 1000))
  const minutes = Math.floor(seconds / 60)
  const remaining = String(seconds % 60).padStart(2, '0')
  return `${minutes}:${remaining}`
})

const metadataLabel = computed(() => {
  const value = artifact.value
  const details = [durationLabel.value]
  const sceneCount = value?.sceneCount ?? 0
  if (sceneCount > 0) {
    details.push(`${sceneCount} 个场景`)
  }
  details.push(`${value?.width ?? 1920} × ${value?.height ?? 1080}`)
  return details.join(' · ')
})

// 视频风格的中文标签映射
const styleLabel = computed(() => {
  const labels: Record<string, string> = {
    precision_light: '精密图解',
    systems_dark: '系统实验室',
    editorial_classroom: '编辑课堂',
    diagram: '清晰图解',
    minimal: '简约教学',
    dark_tech: '暗黑科技'
  }
  return labels[artifact.value?.style ?? ''] ?? '讲解视频'
})
</script>

<style scoped>
.video-view {
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

.video-meta {
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

.video-meta p:last-child {
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
