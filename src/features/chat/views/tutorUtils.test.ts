import { describe, expect, it } from 'vitest'
import { assignPersistedAssistantMessageId, normalizeTeachingDiagram } from './tutorUtils'

describe('normalizeTeachingDiagram', () => {
  it('keeps a structured diagram when the server returns an image fallback', () => {
    const diagram = normalizeTeachingDiagram({
      kind: 'fallback', retryable: true, render_error: '图片生成暂时失败',
      diagram: {
        graph_type: 'framework', title: '软件工程', teaching_goal: '理解', difficulty: 'beginner',
        visual_content: { center: '软件工程', modules: [] },
        teaching_content: { core_explanation: '...', key_points: [], common_mistakes: [], examples: [], summary: '...' },
      },
    })

    expect(diagram?.kind).toBe('fallback')
  })
})

describe('assignPersistedAssistantMessageId', () => {
  it('replaces a synthetic assistant ID with the persisted message ID', () => {
    const message = { id: 100001, role: 'ai' as const, content: '', time: 'now' }

    const messageId = assignPersistedAssistantMessageId(message, 99)

    expect(messageId).toBe(99)
    expect(message.id).toBe(99)
  })
})
