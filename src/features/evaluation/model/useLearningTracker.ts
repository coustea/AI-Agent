import { recordLearningSession } from '@/features/evaluation/api/evaluation'
import type { LearningSessionCreate } from '@/features/evaluation/model/evaluation'

// 追踪上下文：当前页面/资源/路径信息
export interface TrackingContext {
  sourcePage: string
  resourceId?: number
  pathId?: number
  pathNodeId?: number
  nodeId?: string
  course?: string
  topic?: string
}

// 空闲超时 30s、最小有效时长 1s、用户活动事件列表
const IDLE_TIMEOUT_MS = 30000
const MIN_DURATION_SECONDS = 1
const ACTIVITY_EVENTS: Array<keyof WindowEventMap> = ['pointerdown', 'keydown', 'scroll', 'touchstart', 'wheel']

// 模块级状态：活跃时段起始、会话起始、当前上下文、累计毫秒、暂停标志、闲置定时器、是否已绑定监听
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

// 暂停追踪：累计当前段时长，清空起始时间
function pauseTracking() {
  if (activeStartTime === null || isPaused) return
  accumulatedMs += Date.now() - activeStartTime
  activeStartTime = null
  isPaused = true
  clearIdleTimer()
}

// 设置空闲超时：无操作 30s 后自动暂停
function scheduleIdleTimeout() {
  clearIdleTimer()
  if (!activeContext || isPaused || document.hidden) return
  idleTimer = window.setTimeout(() => {
    pauseTracking()
  }, IDLE_TIMEOUT_MS)
}

// 恢复追踪：重新记录起始时间并重置空闲定时器
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

// 用户活动回调：暂停时恢复，否则刷新空闲超时
function handleUserActivity() {
  if (!activeContext) return
  if (isPaused) {
    resumeTracking()
    return
  }
  scheduleIdleTimeout()
}

// 页面可见性变化：切后台暂停，回到前台恢复定时
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

// 绑定全局事件：可见性变化、页面关闭、用户交互（仅一次）
function bindGlobalListeners() {
  if (listenersBound) return
  listenersBound = true
  document.addEventListener('visibilitychange', onVisibilityChange)
  window.addEventListener('beforeunload', onBeforeUnload)
  ACTIVITY_EVENTS.forEach((eventName) => {
    window.addEventListener(eventName, handleUserActivity, { passive: true })
  })
}

// 开始追踪：绑定全局事件，初始化状态（如果页面隐藏则不立即开始）
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

// 停止追踪：计算时长并上报，不足最小阈值则丢弃
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
    course: context.course,
    topic: context.topic,
    client_session_id: typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : 'sess-' + Math.random().toString(36).slice(2, 11) + '-' + Date.now(),
    event_metadata: {
      resource_id: context.resourceId,
      path_id: context.pathId,
      path_node_id: context.pathNodeId,
      node_id: context.nodeId,
    },
  }

  // 静默上报，不阻塞用户流程
  recordLearningSession(payload).catch(() => {})
}
