import { onBeforeUnmount, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

interface UseVisualizerTimelineOptions {
  playing: Ref<boolean>
  currentEvent: ComputedRef<TraceEvent | null>
  speed: Ref<number>
  next: () => void
  pause: () => void
}

/** 自动推进 TraceEvent 步骤的定时器。
 * AlgorithmVisualization.vue 使用。已从 VisualStep 改为 TraceEvent。
 * 基础速度：每步 1200ms，按 speed 比例缩放 */
export function useVisualizerTimeline(options: UseVisualizerTimelineOptions) {
  let timerId: number | null = null

  function clearTimer() {
    if (timerId !== null) {
      window.clearTimeout(timerId)
      timerId = null
    }
  }

  function schedule() {
    clearTimer()

    if (!options.playing.value || !options.currentEvent.value) {
      return
    }

    // 根据倍速比例缩放，限制最小时间为 100ms 避免浏览器卡死
    const duration = Math.max(100, Math.round(1200 / options.speed.value))

    timerId = window.setTimeout(() => {
      if (!options.playing.value) {
        return
      }

      options.next()
      if (!options.playing.value) {
        options.pause()
      }
    }, duration)
  }

  watch(
    [options.playing, options.currentEvent, options.speed],
    () => {
      schedule()
    },
    { immediate: true },
  )

  onBeforeUnmount(() => {
    clearTimer()
  })
}
