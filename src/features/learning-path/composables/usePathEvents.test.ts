// @vitest-environment jsdom

import { beforeEach, describe, expect, it, vi } from 'vitest'

import { usePathEvents } from './usePathEvents'

class FakeEventSource {
  static lastUrl = ''
  static lastInstance: FakeEventSource | null = null
  static CLOSED = 2

  readyState = 1
  onerror: (() => void) | null = null
  private listeners = new Map<string, (event: MessageEvent) => void>()

  constructor(url: string | URL) {
    FakeEventSource.lastUrl = String(url)
    FakeEventSource.lastInstance = this
  }

  addEventListener(
    name: string,
    listener: EventListenerOrEventListenerObject,
  ) {
    this.listeners.set(
      name,
      listener as (event: MessageEvent) => void,
    )
  }

  emit(name: string, data: object) {
    this.listeners.get(name)?.(
      new MessageEvent(name, {
        data: JSON.stringify(data),
      }),
    )
  }

  close() {}
}

describe('usePathEvents', () => {
  beforeEach(() => {
    localStorage.clear()
    FakeEventSource.lastUrl = ''
    FakeEventSource.lastInstance = null
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  it('adds the encoded auth token to the path event URL', () => {
    localStorage.setItem('token', 'signed token/+')

    usePathEvents().connect(42, 'run-7')

    expect(FakeEventSource.lastUrl).toBe(
      '/api/v1/ai/path-plan/42/runs/run-7/events?token=signed+token%2F%2B',
    )
  })

  it('dispatches a planning completion event once', () => {
    const onCompleted = vi.fn()
    const pathEvents = usePathEvents()
    pathEvents.connect(42, 'run-7', { onCompleted })

    const completedEvent = {
      sequence: 1,
      run_id: 'run-7',
      path_id: 42,
      event: 'planning.completed',
      stage: 'save',
      message: '路径规划完成',
      progress: 100,
      data: {},
      timestamp: Date.now(),
    }

    FakeEventSource.lastInstance?.emit(
      'path.event',
      completedEvent,
    )
    FakeEventSource.lastInstance?.emit(
      'path.event',
      completedEvent,
    )

    expect(onCompleted).toHaveBeenCalledTimes(1)
    expect(pathEvents.connectionStatus.value).toBe('completed')
  })
})
