import { computed, ref, watch } from 'vue'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

/** 基于 TraceEvent[] 的播放控制器，替代旧 useVisualizerPlayback。
 * AlgorithmVisualization.vue 直接使用。 */
export function useTracePlayer(eventsRef: () => TraceEvent[]) {
  const playing = ref(false)
  const currentStepIndex = ref(0)
  const speed = ref(1)

  const currentEvent = computed(() => {
    const events = eventsRef()
    return events[currentStepIndex.value] || null
  })

  const finished = computed(() => {
    const events = eventsRef()
    return events.length > 0 && currentStepIndex.value >= events.length - 1
  })

  watch(
    () => eventsRef().length,
    (length) => {
      if (length <= 0) {
        currentStepIndex.value = 0
        playing.value = false
        return
      }

      if (currentStepIndex.value > length - 1) {
        currentStepIndex.value = Math.max(0, length - 1)
        playing.value = false
      }
    },
    { flush: 'sync' },
  )

  function play() {
    const events = eventsRef()
    if (!events.length) return

    if (currentStepIndex.value >= events.length - 1) {
      currentStepIndex.value = 0
    }

    playing.value = true
  }

  function pause() {
    playing.value = false
  }

  function next() {
    const events = eventsRef()
    if (!events.length) return

    if (currentStepIndex.value < events.length - 1) {
      currentStepIndex.value += 1
    } else {
      playing.value = false
    }
  }

  function prev() {
    if (currentStepIndex.value > 0) {
      currentStepIndex.value -= 1
    }
  }

  function reset() {
    playing.value = false
    currentStepIndex.value = 0
  }

  function setSpeed(value: number) {
    speed.value = value
  }

  function seek(index: number) {
    const events = eventsRef()
    if (!events.length) {
      currentStepIndex.value = 0
      return
    }

    currentStepIndex.value = Math.min(Math.max(index, 0), events.length - 1)
  }

  return {
    playing,
    currentStepIndex,
    currentEvent,
    speed,
    finished,
    play,
    pause,
    next,
    prev,
    reset,
    setSpeed,
    seek,
  }
}
