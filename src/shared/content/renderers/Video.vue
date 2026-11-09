<template>
  <section class="video-view">
    <div v-if="artifact" class="player-frame">
      <video
        class="player"
        :src="artifact.publicUrl"
        controls
        playsinline
        preload="metadata"
      >
        <track
          v-if="artifact.captionsUrl"
          kind="subtitles"
          :src="artifact.captionsUrl"
          srclang="zh"
          label="中文字幕"
          default
        />
      </video>
    </div>

    <div v-if="artifact" class="video-meta">
      <div>
        <p class="eyebrow">教学动画视频</p>
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
// 视频渲染器：展示教学动画视频（MP4），含播放器、字幕、规格元数据与下载

import { computed } from 'vue'
import { Download, LoaderCircle } from 'lucide-vue-next'

const props = defineProps<{ resultData?: unknown }>()

type VideoArtifactView = {
  title: string
  publicUrl: string
  captionsUrl: string
  durationSeconds: number
  width: number
  height: number
  sceneCount: number
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

// 从 resultData 中解析视频产物元数据
function parseArtifact(value: unknown): VideoArtifactView | null {
  if (!value) return null
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
  const meta = asRecord(record.metadata) ?? record

  const publicUrl = String(meta.video_url ?? meta.public_url ?? '')
  if (!publicUrl || !publicUrl.endsWith('.mp4')) return null

  const durationSec = Number(meta.duration_seconds ?? (Number(meta.duration_ms ?? 0) / 1000))

  return {
    title: String(record.title ?? meta.title ?? '讲解视频'),
    publicUrl,
    captionsUrl: String(meta.captions_url ?? ''),
    durationSeconds: durationSec > 0 ? durationSec : 0,
    width: Number(meta.width ?? 1920),
    height: Number(meta.height ?? 1080),
    sceneCount: Number(meta.scene_count ?? 1),
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
