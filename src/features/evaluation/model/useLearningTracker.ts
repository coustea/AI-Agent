import { recordLearningSession } from '@/features/evaluation/api/evaluation'
import type { LearningSessionCreate } from '@/features/evaluation/model/evaluation'

export interface TrackingContext {
  sourcePage: string
  resourceId?: number
  pathId?: number
  pathNodeId?: number
  nodeId?: string
  course?: string
  topic?: string
}

const IDLE_TIMEOUT_MS = 30000
const MIN_DURATION_SECONDS = 1
const ACTIVITY_EVENTS: Array<keyof WindowEventMap> = ['pointerdown', 'keydown', 'scroll', 'touchstart', 'wheel']

let activeStartTime: number | null = null
let sessionStartedAt: number | null = null
let activeContext: TrackingContext | null = null
let accumulatedMs = 0
let isPaused = false
let idleTimer: number | null = null
let listenersBound = false

function clearIdleTimer() {
  if (idleTimer !== null) {
    window.clearTimeout(idleTimer)
    idleTimer = null
  }
}

function pauseTracking() {
  if (activeStartTime === null || isPaused) return
  accumulatedMs += Date.now() - activeStartTime
  activeStartTime = null
  isPaused = true
  clearIdleTimer()
}

function scheduleIdleTimeout() {
  clearIdleTimer()
  if (!activeContext || isPaused || document.hidden) return
  idleTimer = window.setTimeout(() => {
    pauseTracking()
  }, IDLE_TIMEOUT_MS)
}

function resumeTracking() {
  if (!activeContext || !isPaused || document.hidden) return
  const now = Date.now()
  if (sessionStartedAt === null) {
    sessionStartedAt = now
  }
  activeStartTime = now
  isPaused = false
  scheduleIdleTimeout()
}

function handleUserActivity() {
  if (!activeContext) return
  if (isPaused) {
    resumeTracking()
    return
  }
  scheduleIdleTimeout()
}

function onVisibilityChange() {
  if (!activeContext) return
  if (document.hidden) {
    pauseTracking()
  } else {
    scheduleIdleTimeout()
  }
}

function onBeforeUnload() {
  stopTracking()
}

function bindGlobalListeners() {
  if (listenersBound) return
  listenersBound = true
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('beforeunload', onBeforeUnload)
  ACTIVITY_EVENTS.forEach((eventName) => {
    window.addEventListener(eventName, handleUserActivity, { passive: true })
  })
}

export function startTracking(context: TrackingContext) {
  bindGlobalListeners()

  if (activeContext) {
    stopTracking()
  }

  const now = Date.now()
  activeContext = context
  sessionStartedAt = now
  accumulatedMs = 0
  isPaused = document.hidden
  activeStartTime = isPaused ? null : now

  if (!isPaused) {
    scheduleIdleTimeout()
  }
}

export function stopTracking() {
  if (!activeContext) return

  pauseTracking()

  const durationSeconds = Math.floor(accumulatedMs / 1000)
  const now = new Date()
  const startedAt = new Date(sessionStartedAt ?? now.getTime())
  const context = activeContext

  activeStartTime = null
  sessionStartedAt = null
  activeContext = null
  accumulatedMs = 0
  isPaused = false
  clearIdleTimer()

  if (durationSeconds < MIN_DURATION_SECONDS) {
    return
  }

  const payload: LearningSessionCreate = {
    source_page: context.sourcePage,
    started_at: startedAt.toISOString(),
    ended_at: now.toISOString(),
    duration_seconds: durationSeconds,
    resource_id: context.resourceId,
    path_id: context.pathId,
    path_node_id: context.pathNodeId,
    node_id: context.nodeId,
    course: context.course,
    topic: context.topic,
  }

  recordLearningSession(payload).catch(() => {
    // Silent failure: tracking should not block the user flow.
  })
}
