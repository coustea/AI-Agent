import { recordLearningSession } from '@/features/learning/api/evaluation'
import type { LearningSessionCreate } from '@/features/learning/model/evaluation'

export interface TrackingContext {
  sourcePage: string
  resourceId?: number
  pathId?: number
  pathNodeId?: number
  nodeId?: string
  course?: string
  topic?: string
}

const MIN_DURATION_SECONDS = 5

let activeStartTime: number | null = null
let activeContext: TrackingContext | null = null
let accumulatedMs = 0
let isPaused = false

function onVisibilityChange() {
  if (!activeStartTime) return
  if (document.hidden) {
    if (!isPaused) {
      accumulatedMs += Date.now() - activeStartTime
      isPaused = true
    }
  } else {
    if (isPaused) {
      activeStartTime = Date.now()
      isPaused = false
    }
  }
}

function onBeforeUnload() {
  stopTracking()
}

document.addEventListener('visibilitychange', onVisibilityChange)
window.addEventListener('beforeunload', onBeforeUnload)

export function startTracking(context: TrackingContext) {
  if (activeStartTime !== null) {
    stopTracking()
  }
  activeStartTime = Date.now()
  activeContext = context
  accumulatedMs = 0
  isPaused = document.hidden
}

export function stopTracking() {
  if (activeStartTime === null || !activeContext) return

  if (!isPaused) {
    accumulatedMs += Date.now() - activeStartTime
  }

  const durationSeconds = Math.floor(accumulatedMs / 1000)
  const now = new Date()
  const startedAt = new Date(now.getTime() - accumulatedMs)

  activeStartTime = null
  isPaused = false

  if (durationSeconds < MIN_DURATION_SECONDS) {
    activeContext = null
    return
  }

  const payload: LearningSessionCreate = {
    source_page: activeContext.sourcePage,
    started_at: startedAt.toISOString(),
    ended_at: now.toISOString(),
    duration_seconds: durationSeconds,
    resource_id: activeContext.resourceId,
    path_id: activeContext.pathId,
    path_node_id: activeContext.pathNodeId,
    node_id: activeContext.nodeId,
    course: activeContext.course,
    topic: activeContext.topic,
  }

  activeContext = null

  recordLearningSession(payload).catch(() => {
    // 静默失败，学习时长上报不应阻塞用户操作
  })
}
