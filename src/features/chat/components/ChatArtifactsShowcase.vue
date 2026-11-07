<script setup lang="ts">
import { computed } from 'vue'
import {
  isRunActive,
  type ChatArtifact,
  type RunState,
  type SourceItem,
} from '@/features/chat/types/chatEvent'

const props = defineProps<{
  run: RunState
}>()

const active = computed(() => isRunActive(props.run))
const artifacts = computed<ChatArtifact[]>(() => props.run.artifacts || [])
const sources = computed<SourceItem[]>(() => props.run.sources || [])

const hasContent = computed(() => artifacts.value.length > 0 || (sources.value.length > 0 && !active.value))
</script>

<template>
  <div v-if="hasContent" class="artifacts-showcase-container">
    <!-- 1. 多模态生成产物卡片（教学视频 / PPT 课件） -->
    <div v-if="artifacts.length > 0" class="artifacts-grid">
      <article
        v-for="artifact in artifacts"
        :key="artifact.id"
        class="artifact-card"
      >
        <div class="artifact-card-top">
          <div class="artifact-title-box">
            <span class="artifact-badge" :class="`is-${artifact.kind}`">
              {{ artifact.kind === 'video' ? '教学动画视频' : 'PPT 演示课件' }}
            </span>
            <strong class="artifact-title-text">{{ artifact.title }}</strong>
          </div>
          <div class="artifact-actions">
            <a
              v-if="artifact.preview_url"
              :href="artifact.preview_url"
              target="_blank"
              rel="noopener noreferrer"
              class="artifact-btn is-preview"
            >
              在线预览
            </a>
            <a
              :href="artifact.url"
              target="_blank"
              rel="noopener noreferrer"
              class="artifact-btn is-download"
            >
              {{ artifact.kind === 'ppt' ? '下载课件' : '下载视频' }}
            </a>
          </div>
        </div>

        <video
          v-if="artifact.kind === 'video'"
          :src="artifact.url"
          controls
          preload="metadata"
          class="artifact-video-player"
        />
      </article>
    </div>

    <!-- 2. 知识库参考来源书签条 -->
    <div v-if="sources.length > 0 && !active" class="sources-strip">
      <div class="sources-label">
        <svg viewBox="0 0 14 14" fill="none" class="source-icon" aria-hidden="true">
          <path d="M2.2 3a1.2 1.2 0 0 1 1.2-1.2h7.4v9.2H3.4a1.2 1.2 0 0 0-1.2 1.2V3Z" stroke="currentColor" stroke-width="1.3" />
          <path d="M2.2 11h8.6" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" />
        </svg>
        <span>参考资料</span>
      </div>
      <div class="sources-chips">
        <span
          v-for="(src, idx) in sources"
          :key="`${src.title}-${idx}`"
          class="source-chip"
          :title="src.summary || src.heading || src.title"
        >
          {{ src.title || src.source }}{{ src.heading ? ` · ${src.heading}` : '' }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.artifacts-showcase-container {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.artifacts-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.artifact-card {
  border-radius: 12px;
  background: var(--color-surface, #ffffff);
  border: 1px solid var(--color-border-subtle, rgba(0, 0, 0, 0.08));
  padding: 0.75rem 0.95rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
}

:root.dark .artifact-card {
  background: rgba(255, 255, 255, 0.02);
  border-color: rgba(255, 255, 255, 0.08);
}

.artifact-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.artifact-title-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.artifact-badge {
  font-size: 0.6875rem;
  font-weight: 600;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  white-space: nowrap;
}

.artifact-badge.is-video {
  background: rgba(245, 158, 11, 0.12);
  color: #d97706;
}

.artifact-badge.is-ppt {
  background: rgba(70, 184, 180, 0.12);
  color: var(--color-primary, #46b8b4);
}

.artifact-title-text {
  font-size: 0.84375rem;
  color: var(--color-text-primary, #1e293b);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:root.dark .artifact-title-text {
  color: #f1f5f9;
}

.artifact-actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-shrink: 0;
}

.artifact-btn {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.15s ease;
}

.artifact-btn.is-preview {
  background: rgba(0, 0, 0, 0.04);
  color: var(--color-text-secondary, #475569);
}

:root.dark .artifact-btn.is-preview {
  background: rgba(255, 255, 255, 0.06);
  color: #cbd5e1;
}

.artifact-btn.is-preview:hover {
  background: rgba(0, 0, 0, 0.08);
}

.artifact-btn.is-download {
  background: var(--color-primary, #46b8b4);
  color: #ffffff;
}

.artifact-btn.is-download:hover {
  filter: brightness(1.08);
}

.artifact-video-player {
  margin-top: 0.65rem;
  width: 100%;
  max-height: 360px;
  border-radius: 8px;
  background: #000000;
}

.sources-strip {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  padding: 0.45rem 0.75rem;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.02);
  border: 1px solid rgba(0, 0, 0, 0.04);
}

:root.dark .sources-strip {
  background: rgba(255, 255, 255, 0.02);
  border-color: rgba(255, 255, 255, 0.04);
}

.sources-label {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-secondary, #64748b);
  white-space: nowrap;
  margin-top: 0.1rem;
}

.source-icon {
  width: 13px;
  height: 13px;
}

.sources-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  flex: 1;
}

.source-chip {
  font-size: 0.6875rem;
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
  background: var(--color-surface, #ffffff);
  border: 1px solid rgba(0, 0, 0, 0.06);
  color: var(--color-text-secondary, #475569);
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

:root.dark .source-chip {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.08);
  color: #94a3b8;
}
</style>
