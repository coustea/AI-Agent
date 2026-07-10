import { onBeforeUnmount, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

interface UseVisualizerTimelineOptions {
  playing: Ref<boolean>
  currentEvent: ComputedRef<TraceEvent | null>
  next: () => void
  pause: () => void
}

// 每步停留时长（毫秒）
const STEP_DURATION_MS = 1200

// 自动播放时间线调度器 — 用 setTimeout 驱动步骤播放
export function useVisualizerTimeline(options: UseVisualizerTimelineOptions) {
  let timerId: number | null = null

  // 清除当前播放定时器
  function clearTimer() {
    if (timerId !== null) {
      window.clearTimeout(timerId)
      timerId = null
    }
  }

  // 调度下一步播放（仅在播放中和有事件时执行）
  function schedule() {
    clearTimer()

    if (!options.playing.value || !options.currentEvent.value) {
      return
    }

    timerId = window.setTimeout(() => {
      if (!options.playing.value) {
        return
      }

      options.next()
      if (!options.playing.value) {
        options.pause()
      }
    }, STEP_DURATION_MS)
  }

  // 播放状态或事件变化时重新调度
  watch(
    [options.playing, options.currentEvent],
    () => {
      schedule()
    },
    { immediate: true },
  )

  // 组件卸载时清除定时器
  onBeforeUnmount(() => {
    clearTimer()
  })
}
