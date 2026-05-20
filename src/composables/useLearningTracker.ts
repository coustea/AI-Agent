import { recordLearningEvent, type LearningEventCreate } from '@/api/ai'

type LearningTrackerOptions = {
  context: string
  sessionId?: string | null
  getMetadata?: () => Record<string, unknown>
}

const HEARTBEAT_INTERVAL_MS = 60_000

export function useLearningTracker(options: LearningTrackerOptions) {
  let startedAt = 0
  let timer: ReturnType<typeof window.setInterval> | null = null

  const buildPayload = (durationSeconds: number): LearningEventCreate => ({
    event_type: 'learning_heartbeat',
    session_id: options.sessionId ?? null,
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
      await recordLearningEvent(buildPayload(durationSeconds))
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
