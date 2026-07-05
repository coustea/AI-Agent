import { computed, ref, watch } from 'vue'
import type { VisualStep } from '@/features/algorithm-visualization/types'

export function useVisualizerPlayback(stepsRef: () => VisualStep[]) {
  const playing = ref(false)
  const currentStepIndex = ref(0)
  const speed = ref(1)

  const currentStep = computed(() => {
    const steps = stepsRef()
    return steps[currentStepIndex.value] || null
  })

  const finished = computed(() => {
    const steps = stepsRef()
    return steps.length > 0 && currentStepIndex.value >= steps.length - 1
  })

  watch(
    () => stepsRef().length,
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
    const steps = stepsRef()
    if (!steps.length) return

    if (currentStepIndex.value >= steps.length - 1) {
      currentStepIndex.value = 0
    }

    playing.value = true
  }

  function pause() {
    playing.value = false
  }

  function next() {
    const steps = stepsRef()
    if (!steps.length) return

    if (currentStepIndex.value < steps.length - 1) {
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
    const steps = stepsRef()
    if (!steps.length) {
      currentStepIndex.value = 0
      return
    }

    currentStepIndex.value = Math.min(Math.max(index, 0), steps.length - 1)
  }

  return {
    playing,
    currentStepIndex,
    currentStep,
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
