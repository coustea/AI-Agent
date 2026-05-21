import { computed, onBeforeUnmount, ref } from 'vue'

import { recordLearningEvent } from '@/api/ai'

const DEFAULT_HEARTBEAT_INTERVAL_SEC = 30
const DEFAULT_IDLE_TIMEOUT_SEC = 300

type TrackerContext =
  | 'home'
  | 'profile'
  | 'tutor'
  | 'resource_detail'
  | 'path_planner'
  | 'evaluation'

interface LearningTrackerOptions {
  context: TrackerContext
  sessionId?: string | null
  resourceId?: number | null
  heartbeatIntervalSec?: number
  idleTimeoutSec?: number
  getMetadata?: () => Record<string, unknown>
}

export function useLearningTracker(options: LearningTrackerOptions) {
  const elapsedSeconds = ref(0)
  const isActive = ref(false)

  const heartbeatIntervalSec = options.heartbeatIntervalSec ?? DEFAULT_HEARTBEAT_INTERVAL_SEC
  const idleTimeoutSec = options.idleTimeoutSec ?? DEFAULT_IDLE_TIMEOUT_SEC

  let tickTimer: number | null = null
  let heartbeatTimer: number | null = null
  let pendingSeconds = 0
  let lastInteractionAt = Date.now()
  let started = false

  const formattedTime = computed(() => formatDuration(elapsedSeconds.value))

  const buildMetadata = () => ({
    context: options.context,
    route: window.location.pathname + window.location.search,
    resource_id: options.resourceId ?? null,
    session_id: options.sessionId ?? null,
    ...(options.getMetadata?.() ?? {}),
  })

  const isPageTrackable = () => document.visibilityState === 'visible' && Date.now() - lastInteractionAt < idleTimeoutSec * 1000

  const tick = () => {
    if (!isActive.value || !isPageTrackable()) return
    elapsedSeconds.value += 1
    pendingSeconds += 1
  }

  const sendHeartbeat = async (seconds: number) => {
    if (seconds <= 0) return
    await recordLearningEvent({
      event_type: 'learning_heartbeat',
      session_id: options.sessionId ?? null,
      resource_id: options.resourceId ?? null,
      duration_seconds: seconds,
      metadata: buildMetadata(),
    })
  }

  const flushKeepalive = (seconds: number) => {
    if (seconds <= 0) return
    const token = localStorage.getItem('token')
    const payload = JSON.stringify({
      event_type: 'learning_heartbeat',
      session_id: options.sessionId ?? null,
      resource_id: options.resourceId ?? null,
      duration_seconds: seconds,
      metadata: buildMetadata(),
    })

    if (typeof fetch === 'function') {
      void fetch('/api/v1/ai/evaluation/events', {
        method: 'POST',
        keepalive: true,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: payload,
      }).catch(() => {
        flushBeacon(seconds)
      })
      return
    }

    flushBeacon(seconds)
  }

  const flushBeacon = (seconds: number) => {
    if (seconds <= 0 || typeof navigator.sendBeacon !== 'function') return
    const token = localStorage.getItem('token')
    const url = token
      ? `/api/v1/ai/evaluation/events?token=${encodeURIComponent(token)}`
      : '/api/v1/ai/evaluation/events'
    const blob = new Blob([JSON.stringify({
      event_type: 'learning_heartbeat',
      session_id: options.sessionId ?? null,
      resource_id: options.resourceId ?? null,
      duration_seconds: seconds,
      metadata: buildMetadata(),
    })], { type: 'application/json' })
    navigator.sendBeacon(url, blob)
  }

  const flush = async (useKeepalive = false) => {
    const seconds = pendingSeconds
    pendingSeconds = 0
    if (seconds <= 0) return
    if (useKeepalive) {
      flushKeepalive(seconds)
      return
    }
    try {
      await sendHeartbeat(seconds)
    } catch {
      pendingSeconds += seconds
    }
  }

  const pause = async () => {
    if (!started) return
    isActive.value = false
    await flush()
  }

  const start = () => {
    if (started) {
      isActive.value = true
      return
    }

    started = true
    isActive.value = true
    lastInteractionAt = Date.now()

    tickTimer = window.setInterval(tick, 1000)
    heartbeatTimer = window.setInterval(() => {
      void flush()
    }, heartbeatIntervalSec * 1000)

    document.addEventListener('visibilitychange', handleVisibilityChange)
    window.addEventListener('mousemove', handleInteraction, { passive: true })
    window.addEventListener('keydown', handleInteraction, { passive: true })
    window.addEventListener('scroll', handleInteraction, { passive: true })
    window.addEventListener('touchstart', handleInteraction, { passive: true })
    window.addEventListener('beforeunload', handleBeforeUnload)
  }

  const stop = async () => {
    if (!started) return
    started = false
    isActive.value = false

    if (tickTimer !== null) {
      window.clearInterval(tickTimer)
      tickTimer = null
    }
    if (heartbeatTimer !== null) {
      window.clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }

    document.removeEventListener('visibilitychange', handleVisibilityChange)
    window.removeEventListener('mousemove', handleInteraction)
    window.removeEventListener('keydown', handleInteraction)
    window.removeEventListener('scroll', handleInteraction)
    window.removeEventListener('touchstart', handleInteraction)
    window.removeEventListener('beforeunload', handleBeforeUnload)

    await flush()
  }

  const handleVisibilityChange = () => {
    if (document.visibilityState === 'hidden') {
      void pause()
      return
    }
    lastInteractionAt = Date.now()
    isActive.value = true
  }

  const handleInteraction = () => {
    lastInteractionAt = Date.now()
    if (started && document.visibilityState === 'visible') {
      isActive.value = true
    }
  }

  const handleBeforeUnload = () => {
    if (pendingSeconds > 0) {
      void flush(true)
    }
  }

  onBeforeUnmount(() => {
    void stop()
  })

  return {
    elapsedSeconds,
    formattedTime,
    isActive,
    start,
    pause,
    stop,
    flush,
  }
}

function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`
  }
  return `${seconds}s`
}
