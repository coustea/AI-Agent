import { onBeforeUnmount, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import type { VisualStep } from '@/features/algorithm-visualization/types'

interface UseVisualizerTimelineOptions {
  playing: Ref<boolean>
  speed: Ref<number>
  currentStep: ComputedRef<VisualStep | null>
  next: () => void
  pause: () => void
}

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

    if (!options.playing.value || !options.currentStep.value) {
      return
    }

    const duration = options.currentStep.value.duration ?? 700
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
    [options.playing, options.speed, options.currentStep],
    () => {
      schedule()
    },
    { immediate: true },
  )

  onBeforeUnmount(() => {
    clearTimer()
  })
}
