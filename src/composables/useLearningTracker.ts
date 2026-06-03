import { recordLearningEvent, recordPathLearningEvent, type LearningEventCreate } from '@/api/ai'

type LearningTrackerOptions = {
  context: string
  sessionId?: string | null
  pathId?: number | null
  pathNodeId?: number | null
  nodeId?: string | null
  resourceId?: number | null
  getMetadata?: () => Record<string, unknown>
}

const HEARTBEAT_INTERVAL_MS = 60_000

export function useLearningTracker(options: LearningTrackerOptions) {
  let startedAt = 0
  let timer: ReturnType<typeof window.setInterval> | null = null

  const buildPayload = (durationSeconds: number): LearningEventCreate => ({
    event_type: 'learning_heartbeat',
    session_id: options.sessionId ?? null,
    resource_id: options.resourceId ?? null,
    path_id: options.pathId ?? null,
    path_node_id: options.pathNodeId ?? null,
    node_id: options.nodeId ?? null,
    duration_seconds: durationSeconds,
    metadata: {
      context: options.context,
      ...(options.getMetadata?.() ?? {}),
    },
  })

  const flush = async () => {
    if (!startedAt) return
    const now = Date.now()
    const durationSeconds = Math.max(1, Math.round((now - startedAt) / 1000))
    startedAt = now

    try {
      const payload = buildPayload(durationSeconds)
      if (options.pathId) {
        await recordPathLearningEvent(options.pathId, payload)
        return
      }
      await recordLearningEvent(payload)
    } catch (err) {
      console.warn('[useLearningTracker] record learning heartbeat failed:', err)
    }
  }

  const start = () => {
    if (timer) return
    startedAt = Date.now()
    timer = window.setInterval(() => {
      void flush()
    }, HEARTBEAT_INTERVAL_MS)
  }

  const stop = async () => {
    if (timer) {
      window.clearInterval(timer)
      timer = null
    }
    await flush()
    startedAt = 0
  }

  return {
    start,
    stop,
    flush,
  }
}
