import { getChatVideo } from '@/features/chat/api/chat'
import type { ChatVideoArtifact } from '@/features/chat/types/chat'

const ACTIVE_VIDEO_STATES = new Set<ChatVideoArtifact['status']>(['queued', 'running'])
const POLL_INTERVAL_MS = 2500

/** Poll only explicit video jobs; it is intentionally separate from the chat SSE lifecycle. */
export function useChatVideoTasks() {
  const timers = new Map<number, ReturnType<typeof window.setTimeout>>()

  const stop = (userMessageId: number) => {
    const timer = timers.get(userMessageId)
    if (timer) window.clearTimeout(timer)
    timers.delete(userMessageId)
  }

  const watch = (
    sessionId: string,
    userMessageId: number,
    onUpdate: (video: ChatVideoArtifact) => void,
  ) => {
    stop(userMessageId)

    const poll = async () => {
      try {
        const response = await getChatVideo(sessionId, userMessageId)
        const video = response.data.data.video
        onUpdate(video)
        if (!ACTIVE_VIDEO_STATES.has(video.status)) {
          stop(userMessageId)
          return
        }
      } catch {
        // Keep the local waiting state while the server is publishing the task.
      }
      timers.set(userMessageId, window.setTimeout(poll, POLL_INTERVAL_MS))
    }

    void poll()
  }

  const dispose = () => {
    for (const messageId of timers.keys()) stop(messageId)
  }

  return { watch, stop, dispose }
}
