import { nextTick, ref } from 'vue'
import { describe, expect, it } from 'vitest'
import type { TraceEvent } from '@/features/algorithm-visualization/types'
import { useTracePlayer } from './useTracePlayer'

function makeEvent(id: string): TraceEvent {
  return {
    id,
    step: 0,
    domain: 'test',
    visualizerType: 'array',
    type: 'snapshot',
    state: { structure: { array: [1] } },
  }
}

describe('useTracePlayer', () => {
  it('plays, pauses, and stops at the final event', () => {
    const events = ref([makeEvent('one'), makeEvent('two')])
    const player = useTracePlayer(() => events.value)

    player.play()
    expect(player.playing.value).toBe(true)

    player.pause()
    expect(player.playing.value).toBe(false)

    player.play()
    player.next()
    expect(player.currentStepIndex.value).toBe(1)
    expect(player.finished.value).toBe(true)

    player.next()
    expect(player.playing.value).toBe(false)
  })

  it('replays from the first event after finishing', () => {
    const events = ref([makeEvent('one'), makeEvent('two')])
    const player = useTracePlayer(() => events.value)

    player.play()
    player.next()
    player.play()

    expect(player.currentStepIndex.value).toBe(0)
    expect(player.currentEvent.value?.id).toBe('one')
    expect(player.playing.value).toBe(true)
  })

  it('resets when a new run replaces events with the same length', async () => {
    const events = ref([makeEvent('old-1'), makeEvent('old-2')])
    const player = useTracePlayer(() => events.value)
    player.play()
    player.next()
    expect(player.currentStepIndex.value).toBe(1)

    events.value = [makeEvent('new-1'), makeEvent('new-2')]
    await nextTick()

    expect(player.currentStepIndex.value).toBe(0)
    expect(player.playing.value).toBe(false)
    expect(player.currentEvent.value?.id).toBe('new-1')
  })
})
