import { createApp, nextTick } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import type { TeachingDiagramImage as TeachingDiagramImagePayload } from '@/features/chat/types/chat'
import TeachingDiagramImage from './TeachingDiagramImage.vue'

const mountedApps: Array<{ unmount: () => void }> = []

const createDiagram = (overrides: Partial<TeachingDiagramImagePayload> = {}): TeachingDiagramImagePayload => ({
  kind: 'image',
  title: 'TCP 图解',
  image_url: '/diagram.png',
  ...overrides,
})

const mount = (
  props: {
    diagram: TeachingDiagramImagePayload
    compact?: boolean
    showDownload?: boolean
  },
  onExpand?: (diagram: TeachingDiagramImagePayload) => void,
) => {
  const target = document.createElement('div')
  document.body.append(target)
  const app = createApp(TeachingDiagramImage, { ...props, onExpand })
  app.mount(target)
  mountedApps.push(app)
  return target
}

afterEach(() => mountedApps.splice(0).forEach(app => app.unmount()))

describe('TeachingDiagramImage', () => {
  it('renders a PNG image and offers it for download when enabled', () => {
    const target = mount({ diagram: createDiagram(), showDownload: true })
    const image = target.querySelector('img')
    const download = target.querySelector('a[download]')

    expect(image?.getAttribute('src')).toBe('/diagram.png')
    expect(download?.getAttribute('href')).toBe('/diagram.png')
  })

  it('does not render an img when image_url is empty', async () => {
    const target = mount({ diagram: createDiagram({ title: 'fallback', image_url: '' }) })
    await nextTick()

    expect(target.querySelector('img')).toBeNull()
  })

  it('emits expand with the diagram when the compact preview is clicked', async () => {
    const diagram = createDiagram()
    let expandedDiagram: TeachingDiagramImagePayload | undefined
    const target = mount(
      { diagram, compact: true },
      payload => { expandedDiagram = payload },
    )

    target.querySelector('img')?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await nextTick()

    expect(expandedDiagram).toBe(diagram)
  })
})
