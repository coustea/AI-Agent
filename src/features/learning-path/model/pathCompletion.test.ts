import { describe, expect, it, vi } from 'vitest'

import {
  runPathCompletionTransition,
  waitForPathTerminalEvent,
} from './pathCompletion'

describe('path completion', () => {
  it('renders 100 percent before waiting 300ms and navigating', async () => {
    const calls: string[] = []
    const wait = vi.fn(async (ms: number) => {
      calls.push(`wait:${ms}`)
    })

    await runPathCompletionTransition({
      markComplete: () => {
        calls.push('complete')
      },
      waitForRender: async () => {
        calls.push('render')
      },
      wait,
      navigate: async () => {
        calls.push('navigate')
      },
    })

    expect(calls).toEqual([
      'complete',
      'render',
      'wait:300',
      'navigate',
    ])
    expect(wait).toHaveBeenCalledWith(300)
  })

  it('waits for the SSE terminal event without starting a polling interval', async () => {
    vi.useFakeTimers()
    const setIntervalSpy = vi.spyOn(globalThis, 'setInterval')
    let complete: (() => void) | undefined

    try {
      const waiting = waitForPathTerminalEvent({
        timeoutMs: 180_000,
        start: (handlers) => {
          complete = handlers.onCompleted
        },
        onCompleted: async () => {},
        onFailed: () => {},
        onTimeout: () => {},
      })

      await vi.advanceTimersByTimeAsync(10_000)

      expect(setIntervalSpy).not.toHaveBeenCalled()
      expect(complete).toBeTypeOf('function')

      complete?.()
      await waiting
    } finally {
      setIntervalSpy.mockRestore()
      vi.useRealTimers()
    }
  })
})
