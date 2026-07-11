import { createApp, nextTick } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import TeachingDiagramImage from './TeachingDiagramImage.vue'

const mountedApps: Array<{ unmount: () => void }> = []

const mount = (props: { title: string; image_url: string }) => {
  const target = document.createElement('div')
  document.body.append(target)
  const app = createApp(TeachingDiagramImage, props)
  app.mount(target)
  mountedApps.push(app)
  return target
}

afterEach(() => mountedApps.splice(0).forEach(app => app.unmount()))

describe('TeachingDiagramImage', () => {
  it('renders a PNG image and offers it for download', () => {
    const target = mount({ title: 'TCP 图解', image_url: '/diagram.png' })
    const image = target.querySelector('img')
    const download = target.querySelector('a[download]')

    expect(image?.getAttribute('src')).toBe('/diagram.png')
    expect(download?.getAttribute('href')).toBe('/diagram.png')
  })

  it('does not render an img for fallback payloads', async () => {
    const target = mount({ title: 'fallback', image_url: '' })
    await nextTick()

    expect(target.querySelector('img')).toBeNull()
  })
})
