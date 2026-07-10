import { computed, ref, watch } from 'vue'
import type { TraceEvent } from '@/features/algorithm-visualization/types'

// 可视化步骤播放器 — 控制播放/暂停/步进/重置
export function useTracePlayer(eventsRef: () => TraceEvent[]) {
  // 播放中状态、当前步骤索引
  const playing = ref(false)
  const currentStepIndex = ref(0)

  // 根据当前索引获取当前 TraceEvent
  const currentEvent = computed(() => {
    const events = eventsRef()
    return events[currentStepIndex.value] || null
  })

  // 是否已播放到最后一个步骤
  const finished = computed(() => {
    const events = eventsRef()
    return events.length > 0 && currentStepIndex.value >= events.length - 1
  })

  // 事件列表变化时，重置索引和播放状态
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

  // 从当前位置或开头开始播放
  function play() {
    const events = eventsRef()
    if (!events.length) return

    if (currentStepIndex.value >= events.length - 1) {
      currentStepIndex.value = 0
    }

    playing.value = true
  }

  // 暂停播放
  function pause() {
    playing.value = false
  }

  // 前进到下一步
  function next() {
    const events = eventsRef()
    if (!events.length) return

    if (currentStepIndex.value < events.length - 1) {
      currentStepIndex.value += 1
    } else {
      playing.value = false
    }
  }

  // 重置到初始状态
  function reset() {
    playing.value = false
    currentStepIndex.value = 0
  }

  return {
    playing,
    currentStepIndex,
    currentEvent,
    finished,
    play,
    pause,
    next,
    reset,
  }
}
