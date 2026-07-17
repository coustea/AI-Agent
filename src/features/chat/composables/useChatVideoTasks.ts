import { getChatVideo } from '@/features/chat/api/chat'
import type { ChatVideoArtifact } from '@/features/chat/types/chat'

const ACTIVE_VIDEO_STATES = new Set<ChatVideoArtifact['status']>(['queued', 'running'])
const POLL_INTERVAL_MS = 2500

/** Poll only explicit video jobs; it is intentionally separate from the chat SSE lifecycle. */
export function useChatVideoTasks() {
  const timers = new Map<number, ReturnType<typeof window.setTimeout>>()

  const stop = (assistantMessageId: number) => {
    const timer = timers.get(assistantMessageId)
    if (timer) window.clearTimeout(timer)
    timers.delete(assistantMessageId)
  }

  const watch = (
    sessionId: string,
    assistantMessageId: number,
    onUpdate: (video: ChatVideoArtifact) => void,
  ) => {
    stop(assistantMessageId)

    const poll = async () => {
      try {
        const response = await getChatVideo(sessionId, assistantMessageId)
        const video = response.data.data.video
        onUpdate(video)
        if (!ACTIVE_VIDEO_STATES.has(video.status)) {
          stop(assistantMessageId)
          return
        }
      } catch {
        // Keep the local waiting state while the server is publishing the task.
      }
      timers.set(assistantMessageId, window.setTimeout(poll, POLL_INTERVAL_MS))
    }

    void poll()
  }

  const dispose = () => {
    for (const messageId of timers.keys()) stop(messageId)
  }

  return { watch, stop, dispose }
}
