import { getAuthToken } from '@/shared/auth/token'
import type { AgentEvent } from '@/shared/agent-events/model'

export function subscribeAgentRun(
  runId: string,
  handlers: {
    onEvent: (event: AgentEvent) => void
    onError: (error: Event) => void
  },
): EventSource {
  let lastSequence = 0
  const query = new URLSearchParams()
  const token = getAuthToken()
  if (token) query.set('token', token)
  const suffix = query.size > 0 ? `?${query.toString()}` : ''
  const source = new EventSource(`/api/v1/ai/agent-runs/${encodeURIComponent(runId)}/events${suffix}`)

  source.addEventListener('agent.event', (message) => {
    try {
      const event = JSON.parse((message as MessageEvent).data) as AgentEvent
      if (event.sequence <= lastSequence) return
      lastSequence = event.sequence
      handlers.onEvent(event)
      if (event.type === 'run.completed' || event.type === 'run.failed') source.close()
    } catch (error) {
      console.error('Failed to parse AgentEvent', error)
    }
  })
  source.onerror = handlers.onError
  return source
}
