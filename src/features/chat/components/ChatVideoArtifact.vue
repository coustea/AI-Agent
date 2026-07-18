<template>
  <div v-if="video?.status === 'completed' && video.video_url" class="video-player-shell">
    <video :src="video.video_url" controls playsinline preload="metadata" />
  </div>

  <div v-else-if="video?.status === 'failed'" class="video-task-failed" role="status">
    <span class="failure-mark" aria-hidden="true">!</span>
    <span>{{ video.error || '视频生成失败，请重新发起请求。' }}</span>
  </div>

  <div v-else ref="taskCard" class="video-task-waiting" role="status" aria-live="polite">
    <div class="video-task-head">
      <span class="video-task-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none"><rect x="3" y="6" width="12" height="12" rx="2"/><path d="m15 10 5-3v10l-5-3z"/></svg>
      </span>
      <span class="video-task-copy">
        <strong>{{ statusTitle }}</strong>
        <small>{{ statusDetail }}</small>
      </span>
      <span class="video-task-pulse" aria-hidden="true"><i></i><i></i><i></i></span>
    </div>

    <div class="video-task-timeline" aria-hidden="true">
      <span v-for="stage in stages" :key="stage.id" :class="['video-stage', { active: stage.active, current: stage.current }]">
        <i></i>
        <b>{{ stage.label }}</b>
      </span>
    </div>

    <div class="video-task-storyboard" aria-hidden="true">
      <span></span><span></span><span></span><i></i>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { gsap } from 'gsap'
import type { ChatVideoArtifact } from '@/features/chat/types/chat'

const props = withDefaults(defineProps<{
  video?: ChatVideoArtifact | null
  preparing?: boolean
}>(), {
  video: null,
  preparing: false,
})

const taskCard = ref<HTMLElement | null>(null)
let animationContext: gsap.Context | undefined

const currentStage = computed(() => {
  if (props.preparing || !props.video) return 0
  return props.video.status === 'queued' ? 1 : 2
})

const stages = computed(() => [
  { id: 'brief', label: '提炼讲解', active: currentStage.value >= 0, current: currentStage.value === 0 },
  { id: 'plan', label: '规划分镜', active: currentStage.value >= 1, current: currentStage.value === 1 },
  { id: 'render', label: '合成画面', active: currentStage.value >= 2, current: currentStage.value === 2 },
])

const statusTitle = computed(() => {
  if (currentStage.value === 0) return '正在准备动画讲解'
  if (currentStage.value === 1) return '正在规划动画分镜'
  return '正在合成动画讲解视频'
})

const statusDetail = computed(() => {
  if (currentStage.value === 0) return '提炼知识重点与讲解节奏'
  if (currentStage.value === 1) return '已创建任务，正在组织镜头与旁白'
  return props.video?.title || '动态画面与声音正在同步生成'
})

const playEntrance = () => {
  animationContext?.revert()
  if (!taskCard.value || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  animationContext = gsap.context(() => {
    gsap.from(taskCard.value!, {
      opacity: 0,
      y: 10,
      duration: 0.34,
      ease: 'power2.out',
    })
    gsap.from(taskCard.value!.querySelectorAll('.video-task-head, .video-task-timeline, .video-task-storyboard'), {
      opacity: 0,
      y: 6,
      duration: 0.28,
      stagger: 0.06,
      delay: 0.08,
      ease: 'power2.out',
    })
  }, taskCard.value)
}

onMounted(() => void nextTick(playEntrance))
watch(currentStage, () => void nextTick(playEntrance))
onBeforeUnmount(() => animationContext?.revert())
</script>

<style scoped>
.video-task-waiting {
  --video-accent: #32bbb9;
  --video-ink: #17424a;
  width: min(100%, 470px);
  margin-top: 12px;
  padding: 13px 15px 12px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--video-accent) 45%, var(--color-border));
  border-radius: 18px;
  background:
    radial-gradient(circle at 90% 0%, rgb(50 187 185 / 14%), transparent 34%),
    linear-gradient(120deg, rgb(244 253 253 / 96%), color-mix(in srgb, var(--color-surface) 91%, #e7f7f7));
  box-shadow: 0 12px 30px rgb(22 102 111 / 10%);
}

.video-task-head { display: flex; align-items: center; gap: 10px; position: relative; z-index: 1; }
.video-task-icon {
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  display: grid;
  place-items: center;
  color: var(--video-accent);
  border: 1px solid rgb(50 187 185 / 18%);
  border-radius: 12px;
  background: rgb(50 187 185 / 10%);
}

.video-task-icon svg { width: 19px; height: 19px; stroke: currentColor; stroke-width: 1.8; stroke-linejoin: round; }
.video-task-copy { min-width: 0; display: grid; gap: 1px; flex: 1; }
.video-task-copy strong { color: var(--video-ink); font-size: .9rem; line-height: 1.25; font-weight: 720; letter-spacing: -.012em; }
.video-task-copy small { color: color-mix(in srgb, var(--video-ink) 62%, var(--color-text-muted)); font-size: .72rem; line-height: 1.35; }

.video-task-pulse { width: 37px; height: 22px; display: inline-flex; align-items: center; justify-content: flex-end; gap: 3px; }
.video-task-pulse i { width: 4px; border-radius: 999px; background: var(--video-accent); animation: videoPulse 1s ease-in-out infinite; }
.video-task-pulse i:nth-child(1) { height: 8px; animation-delay: -.24s; }.video-task-pulse i:nth-child(2) { height: 16px; animation-delay: -.12s; }.video-task-pulse i:nth-child(3) { height: 11px; }

.video-task-timeline { display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px; margin-top: 13px; position: relative; z-index: 1; }
.video-stage { min-width: 0; display: grid; gap: 5px; color: color-mix(in srgb, var(--video-ink) 38%, var(--color-text-muted)); font-size: .63rem; line-height: 1; white-space: nowrap; }
.video-stage i { display: block; height: 3px; border-radius: 999px; background: rgb(22 91 101 / 12%); overflow: hidden; }
.video-stage.active i { background: color-mix(in srgb, var(--video-accent) 48%, #d9eeee); }
.video-stage.current i { background: linear-gradient(90deg, var(--video-accent) 0 42%, rgb(50 187 185 / 20%) 42% 100%); background-size: 200% 100%; animation: timelineTravel 1.45s linear infinite; }
.video-stage.current b { color: var(--video-ink); font-weight: 700; }
.video-stage b { overflow: hidden; text-overflow: ellipsis; font-weight: 520; }

.video-task-storyboard { height: 23px; margin: 11px -15px -12px; padding: 0 15px; display: flex; align-items: end; gap: 5px; position: relative; background: linear-gradient(90deg, transparent, rgb(50 187 185 / 8%), transparent); }
.video-task-storyboard span { width: 22px; height: 14px; display: block; border: 1px solid rgb(50 187 185 / 28%); border-radius: 4px 4px 2px 2px; background: linear-gradient(145deg, rgb(255 255 255 / 80%), rgb(50 187 185 / 13%)); transform-origin: bottom; animation: storyboardLift 1.8s ease-in-out infinite; }
.video-task-storyboard span:nth-child(2) { height: 18px; animation-delay: -.36s; }.video-task-storyboard span:nth-child(3) { height: 11px; animation-delay: -.72s; }
.video-task-storyboard i { position: absolute; bottom: 7px; left: 9px; width: 6px; height: 6px; border-radius: 50%; background: var(--video-accent); box-shadow: 0 0 0 4px rgb(50 187 185 / 14%); animation: storyboardTraverse 2.35s ease-in-out infinite; }

.video-player-shell { width: min(100%, 700px); margin-top: 10px; overflow: hidden; border-radius: 12px; background: #111827; box-shadow: 0 8px 26px rgb(15 23 42 / 14%); }
.video-player-shell video { display: block; width: 100%; max-height: 430px; background: #111827; }
.video-task-failed { width: fit-content; margin-top: 10px; padding: 8px 10px; display: inline-flex; align-items: center; gap: 7px; border-radius: 10px; color: var(--color-danger); background: color-mix(in srgb, var(--color-danger) 8%, var(--color-surface)); font-size: .78rem; }
.failure-mark { width: 16px; height: 16px; display: inline-grid; place-items: center; border-radius: 50%; color: #fff; background: currentColor; font-size: .7rem; font-weight: 800; }

@keyframes videoPulse { 0%, 100% { opacity: .28; transform: scaleY(.55); } 45% { opacity: 1; transform: scaleY(1); } }
@keyframes timelineTravel { to { background-position: -200% 0; } }
@keyframes storyboardLift { 0%, 100% { opacity: .42; transform: translateY(0) scaleY(.88); } 50% { opacity: 1; transform: translateY(-2px) scaleY(1); } }
@keyframes storyboardTraverse { 0%, 12% { transform: translateX(0); opacity: 0; } 20% { opacity: 1; } 80% { opacity: 1; } 100% { transform: translateX(150px); opacity: 0; } }

@media (prefers-reduced-motion: reduce) {
  .video-task-pulse i,
  .video-stage.current i,
  .video-task-storyboard span,
  .video-task-storyboard i { animation: none; }
}
</style>
