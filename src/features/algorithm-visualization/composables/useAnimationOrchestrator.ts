import { computed, onBeforeUnmount, ref, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

export interface OrchestratorOptions {
  events: () => TraceEvent[]
  onStepChange: (event: TraceEvent | null) => void
  defaultSpeed?: number
}

export interface AnimationOrchestrator {
  currentStepIndex: Ref<number>
  currentEvent: ComputedRef<TraceEvent | null>
  playing: Ref<boolean>
  finished: ComputedRef<boolean>
  speed: Ref<number>

  play(): void
  pause(): void
  reset(): void
  stepForward(): void
  stepBackward(): void
  notifyStepComplete(): void
}

const INTER_STEP_DELAY_MS = 300
const SAFETY_TIMEOUT_MS = 2000

export function useAnimationOrchestrator(
  options: OrchestratorOptions,
): AnimationOrchestrator {
  const { events: getEvents, onStepChange, defaultSpeed = 1 } = options

  const currentStepIndex = ref(0)
  const playing = ref(false)
  const speed = ref(defaultSpeed)

  const currentEvent = computed(() => {
    const events = getEvents()
    return events[currentStepIndex.value] || null
  })

  const finished = computed(() => {
    const events = getEvents()
    return events.length > 0 && currentStepIndex.value >= events.length - 1
  })

  let stepCompleteTimerId: ReturnType<typeof setTimeout> | null = null
  let safetyTimerId: ReturnType<typeof setTimeout> | null = null
  let waitingForCompletion = false

  function clearTimers() {
    if (stepCompleteTimerId !== null) {
      clearTimeout(stepCompleteTimerId)
      stepCompleteTimerId = null
    }
    if (safetyTimerId !== null) {
      clearTimeout(safetyTimerId)
      safetyTimerId = null
    }
  }

  // 新运行会替换整个事件数组；即使步数相同，也必须回到首帧。
  watch(
    () => getEvents(),
    () => {
      clearTimers()
      waitingForCompletion = false
      currentStepIndex.value = 0
      playing.value = false
    },
    { flush: 'sync' },
  )

  function stepForward() {
    const events = getEvents()
    if (!events.length) return

    if (currentStepIndex.value >= events.length - 1) {
      playing.value = false
      return
    }

    currentStepIndex.value += 1
    onStepChange(currentEvent.value)
    waitingForCompletion = true

    // Safety timeout: auto-advance if visualizer never calls notifyStepComplete
    safetyTimerId = setTimeout(() => {
      if (waitingForCompletion && playing.value) {
        notifyStepComplete()
      }
    }, SAFETY_TIMEOUT_MS)
  }

  function stepBackward() {
    const events = getEvents()
    if (!events.length || currentStepIndex.value <= 0) return

    clearTimers()
    waitingForCompletion = false
    currentStepIndex.value -= 1
    onStepChange(currentEvent.value)
  }

  function play() {
    const events = getEvents()
    if (!events.length) return

    if (currentStepIndex.value >= events.length - 1) {
      currentStepIndex.value = 0
      onStepChange(currentEvent.value)
    }

    playing.value = true
    // Immediately advance to first step if at the beginning
    if (currentStepIndex.value === 0) {
      onStepChange(currentEvent.value)
      waitingForCompletion = true
      safetyTimerId = setTimeout(() => {
        if (waitingForCompletion && playing.value) {
          notifyStepComplete()
        }
      }, SAFETY_TIMEOUT_MS)
    } else {
      // Resume from paused position: advance next step
      scheduleNextStep()
    }
  }

  function pause() {
    playing.value = false
    clearTimers()
    waitingForCompletion = false
  }

  function reset() {
    playing.value = false
    clearTimers()
    waitingForCompletion = false
    currentStepIndex.value = 0
  }

  function notifyStepComplete() {
    if (!waitingForCompletion) return

    clearTimers()
    waitingForCompletion = false

    if (!playing.value) return

    scheduleNextStep()
  }

  function scheduleNextStep() {
    if (!playing.value) return

    const delay = INTER_STEP_DELAY_MS / speed.value
    stepCompleteTimerId = setTimeout(() => {
      if (!playing.value) return
      stepForward()
    }, delay)
  }

  onBeforeUnmount(() => {
    clearTimers()
  })

  return {
    currentStepIndex,
    currentEvent,
    playing,
    finished,
    speed,
    play,
    pause,
    reset,
    stepForward,
    stepBackward,
    notifyStepComplete,
  }
}
