import { onBeforeUnmount, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

interface UseVisualizerTimelineOptions {
  playing: Ref<boolean>
  speed: Ref<number>
  currentEvent: ComputedRef<TraceEvent | null>
  next: () => void
  pause: () => void
}

/** 自动推进 TraceEvent 步骤的定时器。
 * AlgorithmVisualization.vue 使用。已从 VisualStep 改为 TraceEvent。 */
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

    const duration = 700
    const speed = options.speed.value > 0 ? options.speed.value : 1

    timerId = window.setTimeout(() => {
      if (!options.playing.value) {
        return
      }

      options.next()
      if (!options.playing.value) {
        options.pause()
      }
    }, duration / speed)
  }

  watch(
    [options.playing, options.speed, options.currentEvent],
    () => {
      schedule()
    },
    { immediate: true },
  )

  onBeforeUnmount(() => {
    clearTimer()
  })
}
