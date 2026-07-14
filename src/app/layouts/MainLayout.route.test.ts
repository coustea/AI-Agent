import { createApp, defineComponent, h, nextTick } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import MainLayout from './MainLayout.vue'

vi.mock('primevue/useconfirm', () => ({
  useConfirm: () => ({ require: vi.fn() }),
}))

vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: vi.fn() }),
}))

vi.mock('@/features/auth/model/useAuthPolling', () => ({
  useAuthPolling: vi.fn(),
}))

const mountedApps: Array<{ unmount: () => void }> = []

function createRoutePage(testId: string, label: string) {
  return defineComponent({
    name: `${label}Page`,
    setup() {
      return () => h('section', { 'data-route-page': testId }, label)
    },
  })
}

afterEach(() => mountedApps.splice(0).forEach((app) => app.unmount()))

describe('MainLayout route outlet', () => {
  it('replaces the algorithm page when a top-level destination changes', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/',
          component: MainLayout,
          children: [
            { path: 'algorithm-visualizer', component: createRoutePage('algorithm', '算法可视化') },
            { path: 'path-planner', component: createRoutePage('path-planner', '路径规划') },
          ],
        },
      ],
    })
    const target = document.createElement('div')
    document.body.append(target)
    const app = createApp({ render: () => h(RouterView) })
    app.use(router)
    mountedApps.push(app)

    await router.push('/algorithm-visualizer')
    await router.isReady()
    app.mount(target)
    await nextTick()
    expect(target.querySelector('[data-route-page="algorithm"]')).not.toBeNull()

    await router.push('/path-planner')
    await nextTick()

    expect(target.querySelector('[data-route-page="algorithm"]')).toBeNull()
    expect(target.querySelector('[data-route-page="path-planner"]')).not.toBeNull()
  })
})
