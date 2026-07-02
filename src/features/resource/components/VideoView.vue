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
        <p>{{ durationLabel }} · {{ artifact.width }} × {{ artifact.height }}</p>
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
import { computed } from 'vue'
import { Download, LoaderCircle } from 'lucide-vue-next'

const props = defineProps<{ resultData?: unknown }>()

type VideoArtifactView = {
  title: string
  publicUrl: string
  durationMs: number
  width: number
  height: number
  style: string
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

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
  const source = nested?.public_url ? nested : record
  const publicUrl = source.public_url
  if (typeof publicUrl !== 'string' || !publicUrl.endsWith('.mp4')) return null

  return {
    title: String(record.title ?? source.title ?? '讲解视频'),
    publicUrl,
    durationMs: Number(record.duration_ms ?? source.duration_ms ?? 0),
    width: Number(record.width ?? source.width ?? 1920),
    height: Number(record.height ?? source.height ?? 1080),
    style: String(record.style ?? source.style ?? '')
  }
}

const artifact = computed(() => parseArtifact(props.resultData))

const durationLabel = computed(() => {
  const seconds = Math.max(0, Math.round((artifact.value?.durationMs ?? 0) / 1000))
  const minutes = Math.floor(seconds / 60)
  const remaining = String(seconds % 60).padStart(2, '0')
  return `${minutes}:${remaining}`
})

const styleLabel = computed(() => {
  const labels: Record<string, string> = {
    precision_light: '精密图解',
    systems_dark: '系统实验室',
    editorial_classroom: '编辑课堂'
  }
  return labels[artifact.value?.style ?? ''] ?? '讲解视频'
})
</script>

<style scoped>
.video-view {
  width: 100%;
  color: #172033;
}

.player-frame {
  overflow: hidden;
  border: 1px solid #dbe3e8;
  border-radius: 8px;
  background: #08111b;
  box-shadow: 0 18px 48px rgb(23 32 51 / 12%);
}

.player {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #08111b;
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
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

h3 {
  margin: 0;
  font-size: 18px;
  line-height: 1.35;
}

.video-meta p:last-child {
  margin: 5px 0 0;
  color: #667085;
  font-size: 13px;
}

.download-button {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  gap: 8px;
  padding: 0 14px;
  border-radius: 6px;
  background: #172033;
  color: white;
  font-size: 13px;
  font-weight: 650;
  text-decoration: none;
}

.empty-state {
  display: flex;
  min-height: 280px;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #667085;
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
