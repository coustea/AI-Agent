<template>
  <div v-if="video.status === 'completed' && video.video_url" class="video-player-shell">
    <video :src="video.video_url" controls playsinline preload="metadata" />
  </div>

  <div v-else-if="video.status === 'failed'" class="video-task-failed" role="status">
    视频生成失败，请重新发起请求。
  </div>

  <div v-else class="video-task-waiting" role="status" aria-live="polite">
    <span class="video-task-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none"><rect x="3" y="6" width="12" height="12" rx="2"/><path d="m15 10 5-3v10l-5-3z"/></svg>
    </span>
    <span class="video-task-copy">
      <strong>正在生成动画讲解视频</strong>
      <small>合成动态画面</small>
    </span>
    <span class="video-task-motion" aria-hidden="true">
      <i></i><i></i><i></i><b></b>
    </span>
  </div>
</template>

<script setup lang="ts">
import type { ChatVideoArtifact } from '@/features/chat/types/chat'

defineProps<{ video: ChatVideoArtifact }>()
</script>

<style scoped>
.video-task-waiting {
  width: min(100%, 380px);
  min-height: 42px;
  margin-top: 10px;
  padding: 7px 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid color-mix(in srgb, var(--color-primary) 20%, var(--color-border));
  border-radius: 12px;
  background: color-mix(in srgb, var(--color-primary) 5%, var(--color-surface));
}

.video-task-icon {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  color: var(--color-primary);
  border-radius: 8px;
  background: color-mix(in srgb, var(--color-primary) 11%, transparent);
}

.video-task-icon svg { width: 15px; height: 15px; stroke: currentColor; stroke-width: 1.8; stroke-linejoin: round; }
.video-task-copy { min-width: 0; display: grid; gap: 1px; flex: 1; }
.video-task-copy strong { color: var(--color-text); font-size: 0.77rem; line-height: 1.1; font-weight: 650; }
.video-task-copy small { color: var(--color-text-muted); font-size: 0.67rem; line-height: 1.1; }

.video-task-motion { width: 50px; height: 22px; position: relative; display: flex; align-items: center; justify-content: flex-end; gap: 3px; overflow: hidden; }
.video-task-motion i { width: 8px; height: 12px; border: 1px solid color-mix(in srgb, var(--color-primary) 48%, transparent); border-radius: 2px; opacity: .45; animation: frameBlink 1.35s ease-in-out infinite; }
.video-task-motion i:nth-child(2) { animation-delay: .16s; }.video-task-motion i:nth-child(3) { animation-delay: .32s; }
.video-task-motion b { position: absolute; left: 0; width: 4px; height: 4px; border-radius: 50%; background: var(--color-primary); box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-primary) 14%, transparent); animation: travel 1.5s ease-in-out infinite; }

.video-player-shell { width: min(100%, 700px); margin-top: 10px; overflow: hidden; border-radius: 12px; background: #111827; box-shadow: 0 8px 26px rgb(15 23 42 / 14%); }
.video-player-shell video { display: block; width: 100%; max-height: 430px; background: #111827; }
.video-task-failed { width: fit-content; margin-top: 10px; padding: 8px 10px; border-radius: 10px; color: var(--color-danger); background: color-mix(in srgb, var(--color-danger) 8%, var(--color-surface)); font-size: .78rem; }

@keyframes frameBlink { 0%, 100% { opacity: .3; transform: translateY(1px); } 50% { opacity: 1; transform: translateY(-1px); } }
@keyframes travel { 0% { transform: translateX(0); opacity: 0; } 18% { opacity: 1; } 82% { opacity: 1; } 100% { transform: translateX(45px); opacity: 0; } }
</style>
