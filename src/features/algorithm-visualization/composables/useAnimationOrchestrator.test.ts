import { nextTick, ref } from 'vue'
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import type { TraceEvent } from '@/features/algorithm-visualization/types'
import { useAnimationOrchestrator } from './useAnimationOrchestrator'

function makeEvent(id: string, line?: number): TraceEvent {
  return {
    id,
    step: 0,
    visualizerType: 'array',
    type: 'snapshot',
    state: { structure: { array: [1] } },
    line,
  }
}

describe('useAnimationOrchestrator', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('initializes with step 0 and not playing', () => {
    const events = ref([makeEvent('one'), makeEvent('two')])
    const onStepChange = vi.fn()
    const orchestrator = useAnimationOrchestrator({
      events: () => events.value,
      onStepChange,
    })

    expect(orchestrator.currentStepIndex.value).toBe(0)
    expect(orchestrator.playing.value).toBe(false)
    expect(orchestrator.finished.value).toBe(false)
  })

  it('play() sets playing to true and calls onStepChange', () => {
    const events = ref([makeEvent('one'), makeEvent('two')])
    const onStepChange = vi.fn()
    const orchestrator = useAnimationOrchestrator({
      events: () => events.value,
      onStepChange,
    })

    orchestrator.play()
    expect(orchestrator.playing.value).toBe(true)
    expect(onStepChange).toHaveBeenCalledWith(events.value[0])
  })

  it('pause() stops playback', () => {
    const events = ref([makeEvent('one'), makeEvent('two')])
    const onStepChange = vi.fn()
    const orchestrator = useAnimationOrchestrator({
      events: () => events.value,
      onStepChange,
    })

    orchestrator.play()
    orchestrator.pause()
    expect(orchestrator.playing.value).toBe(false)
  })

  it('notifyStepComplete() advances to next step after inter-step delay', () => {
    const events = ref([makeEvent('one'), makeEvent('two'), makeEvent('three')])
    const onStepChange = vi.fn()
    const orchestrator = useAnimationOrchestrator({
      events: () => events.value,
      onStepChange,
    })

    orchestrator.play()
    onStepChange.mockClear()

    // Simulate visualizer animation complete
    orchestrator.notifyStepComplete()

    // Wait for inter-step delay (300ms at 1x speed)
    vi.advanceTimersByTime(300)

    expect(orchestrator.currentStepIndex.value).toBe(1)
    expect(onStepChange).toHaveBeenCalledWith(events.value[1])
  })

  it('stepForward() advances one step and calls onStepChange', () => {
    const events = ref([makeEvent('one'), makeEvent('two'), makeEvent('three')])
    const onStepChange = vi.fn()
    const orchestrator = useAnimationOrchestrator({
      events: () => events.value,
      onStepChange,
    })

    orchestrator.stepForward()
    expect(orchestrator.currentStepIndex.value).toBe(1)
    expect(onStepChange).toHaveBeenCalledWith(events.value[1])
  })

  it('stepForward() stops at last event', () => {
    const events = ref([makeEvent('one'), makeEvent('two')])
    const onStepChange = vi.fn()
    const orchestrator = useAnimationOrchestrator({
      events: () => events.value,
      onStepChange,
    })

    orchestrator.stepForward()
    expect(orchestrator.currentStepIndex.value).toBe(1)
    expect(orchestrator.finished.value).toBe(true)

    orchestrator.stepForward()
    expect(orchestrator.currentStepIndex.value).toBe(1)
  })

  it('stepBackward() goes to previous step', () => {
    const events = ref([makeEvent('one'), makeEvent('two'), makeEvent('three')])
    const onStepChange = vi.fn()
    const orchestrator = useAnimationOrchestrator({
      events: () => events.value,
      onStepChange,
    })

    orchestrator.stepForward()
    orchestrator.stepForward()
    expect(orchestrator.currentStepIndex.value).toBe(2)

    orchestrator.stepBackward()
    expect(orchestrator.currentStepIndex.value).toBe(1)
    expect(onStepChange).toHaveBeenCalledWith(events.value[1])
  })

  it('reset() goes back to step 0 and stops playing', () => {
    const events = ref([makeEvent('one'), makeEvent('two')])
    const onStepChange = vi.fn()
    const orchestrator = useAnimationOrchestrator({
      events: () => events.value,
      onStepChange,
    })

    orchestrator.play()
    orchestrator.stepForward()
    orchestrator.reset()

    expect(orchestrator.currentStepIndex.value).toBe(0)
    expect(orchestrator.playing.value).toBe(false)
  })

  it('resets when events are replaced', async () => {
    const events = ref([makeEvent('old-1'), makeEvent('old-2')])
    const onStepChange = vi.fn()
    const orchestrator = useAnimationOrchestrator({
      events: () => events.value,
      onStepChange,
    })

    orchestrator.play()
    orchestrator.stepForward()
    expect(orchestrator.currentStepIndex.value).toBe(1)

    events.value = [makeEvent('new-1'), makeEvent('new-2')]
    await nextTick()

    expect(orchestrator.currentStepIndex.value).toBe(0)
    expect(orchestrator.playing.value).toBe(false)
  })

  it('play() from finished state restarts from step 0', () => {
    const events = ref([makeEvent('one'), makeEvent('two')])
    const onStepChange = vi.fn()
    const orchestrator = useAnimationOrchestrator({
      events: () => events.value,
      onStepChange,
    })

    orchestrator.stepForward()
    expect(orchestrator.finished.value).toBe(true)

    orchestrator.play()
    expect(orchestrator.currentStepIndex.value).toBe(0)
    expect(orchestrator.playing.value).toBe(true)
  })

  it('safety timeout auto-advances if notifyStepComplete is never called', () => {
    const events = ref([makeEvent('one'), makeEvent('two'), makeEvent('three')])
    const onStepChange = vi.fn()
    const orchestrator = useAnimationOrchestrator({
      events: () => events.value,
      onStepChange,
    })

    orchestrator.play()
    onStepChange.mockClear()

    // Don't call notifyStepComplete — safety timeout should fire at 2s,
    // then scheduleNextStep waits 300ms before calling stepForward
    vi.advanceTimersByTime(2000 + 300)

    expect(orchestrator.currentStepIndex.value).toBe(1)
    expect(onStepChange).toHaveBeenCalledWith(events.value[1])
  })

  it('speed affects inter-step delay', () => {
    const events = ref([makeEvent('one'), makeEvent('two'), makeEvent('three')])
    const onStepChange = vi.fn()
    const orchestrator = useAnimationOrchestrator({
      events: () => events.value,
      onStepChange,
    })

    orchestrator.speed.value = 2
    orchestrator.play()
    onStepChange.mockClear()

    orchestrator.notifyStepComplete()

    // At 2x speed, delay is 300/2 = 150ms
    vi.advanceTimersByTime(150)

    expect(orchestrator.currentStepIndex.value).toBe(1)
  })

  it('onStepChange receives event with line for Monaco highlighting', () => {
    const events = ref([makeEvent('one', 5), makeEvent('two', 10)])
    const onStepChange = vi.fn()
    const orchestrator = useAnimationOrchestrator({
      events: () => events.value,
      onStepChange,
    })

    orchestrator.stepForward()
    expect(onStepChange).toHaveBeenCalledWith(
      expect.objectContaining({ line: 10 }),
    )
  })
})
