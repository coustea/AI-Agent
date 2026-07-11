import { createApp, nextTick } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import TeachingDiagramCard from './TeachingDiagramCard.vue'

const mountedApps: Array<{ unmount: () => void }> = []

afterEach(() => mountedApps.splice(0).forEach(app => app.unmount()))

describe('TeachingDiagramCard fallback', () => {
  it('shows the fallback notice and emits retry', async () => {
    const target = document.createElement('div')
    document.body.append(target)
    let retried = false
    const app = createApp(TeachingDiagramCard, {
      diagram: {
        kind: 'fallback', retryable: true, render_error: '图片生成暂时失败',
        diagram: {
          graph_type: 'framework', title: '软件工程', teaching_goal: '理解', difficulty: 'beginner',
          visual_content: { center: '软件工程', modules: [] },
          teaching_content: { core_explanation: '...', key_points: [], summary: '...' },
        },
      },
      onRetry: () => { retried = true },
    })
    app.mount(target)
    mountedApps.push(app)

    expect(target.textContent).toContain('图片生成失败，已展示图解')
    const button = [...target.querySelectorAll('button')].find(item => item.textContent?.includes('重新生成图片'))
    expect(button).toBeTruthy()
    button?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await nextTick()

    expect(retried).toBe(true)
  })
})
