import { createApp, defineComponent, h, nextTick } from 'vue'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import MainLayout from './MainLayout.vue'
import AlgorithmVisualization from '@/features/algorithm-visualization/views/AlgorithmVisualization.vue'

vi.mock('primevue/useconfirm', () => ({
  useConfirm: () => ({ require: vi.fn() }),
}))

vi.mock('primevue/usetoast', () => ({
  useToast: () => ({ add: vi.fn() }),
}))

vi.mock('@/features/auth/model/useAuthPolling', () => ({
  useAuthPolling: vi.fn(),
}))

vi.mock('@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmCodeEditorPanel.vue', () => ({
  default: defineComponent({
    name: 'AlgorithmCodeEditorPanelStub',
    setup: () => () => h('div', { 'data-testid': 'algorithm-code-editor' }),
  }),
}))

vi.mock('@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmInputDataPanel.vue', () => ({
  default: defineComponent({
    name: 'AlgorithmInputDataPanelStub',
    setup: () => () => h('div', { 'data-testid': 'algorithm-input-data' }),
  }),
}))

vi.mock('@/features/algorithm-visualization/api/algorithmVisualizer', () => ({
  fetchLanguages: vi.fn(async () => ({ data: { data: [] } })),
  fetchAlgorithms: vi.fn(async () => ({ data: { data: [] } })),
  fetchTemplate: vi.fn(async () => ({
    data: {
      data: {
        templateCode: 'def demo():\n  pass',
        defaultInput: {},
      },
    },
  })),
  fetchCustomCodeContract: vi.fn(),
  runVisualization: vi.fn(),
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
            { path: 'algorithm-visualizer', component: AlgorithmVisualization },
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
    await vi.waitFor(() => {
      expect(target.querySelector('.algorithm-visualizer-page')).not.toBeNull()
    })

    const pathPlannerNav = target.querySelector<HTMLElement>('.nav-item[title="路径规划"]')
    expect(pathPlannerNav).not.toBeNull()
    pathPlannerNav!.click()
    await nextTick()

    await vi.waitFor(() => {
      expect(router.currentRoute.value.path).toBe('/path-planner')
      expect(target.querySelector('.algorithm-visualizer-page')).toBeNull()
      expect(target.querySelector('[data-route-page="path-planner"]')).not.toBeNull()
    })
  })
})
