import { computed, ref } from 'vue'
import { describe, expect, it } from 'vitest'
import { useVisualizerPlayback } from '@/features/algorithm-visualization/composables/useVisualizerPlayback'
import type { VisualStep } from '@/features/algorithm-visualization/types'

function createSteps(): VisualStep[] {
  return [
    { id: 's1', type: 'init', targets: [], description: 'step 1' },
    { id: 's2', type: 'compare', targets: ['bar-0', 'bar-1'], description: 'step 2' },
    { id: 's3', type: 'swap', targets: ['bar-0', 'bar-1'], description: 'step 3' },
  ]
}

describe('useVisualizerPlayback', () => {
  it('advances and rewinds through steps', () => {
    const steps = ref(createSteps())
    const playback = useVisualizerPlayback(() => steps.value)

    expect(playback.currentStepIndex.value).toBe(0)
    expect(playback.currentStep.value?.id).toBe('s1')

    playback.next()
    expect(playback.currentStepIndex.value).toBe(1)
    expect(playback.currentStep.value?.id).toBe('s2')

    playback.prev()
    expect(playback.currentStepIndex.value).toBe(0)
    expect(playback.currentStep.value?.id).toBe('s1')
  })

  it('tracks finished state and resets correctly', () => {
    const steps = ref(createSteps())
    const playback = useVisualizerPlayback(() => steps.value)

    playback.next()
    playback.next()

    expect(playback.finished.value).toBe(true)

    playback.reset()
    expect(playback.playing.value).toBe(false)
    expect(playback.currentStepIndex.value).toBe(0)
    expect(playback.finished.value).toBe(false)
  })

  it('clamps the current index when the steps array shrinks', () => {
    const steps = ref(createSteps())
    const playback = useVisualizerPlayback(() => steps.value)

    playback.next()
    playback.next()

    steps.value = steps.value.slice(0, 1)

    expect(computed(() => playback.currentStep.value?.id).value).toBe('s1')
    expect(playback.currentStepIndex.value).toBe(0)
  })
})
