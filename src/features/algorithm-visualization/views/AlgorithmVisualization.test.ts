import { createApp, defineComponent, h, nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AlgorithmVisualization from './AlgorithmVisualization.vue'

const apiMocks = vi.hoisted(() => ({
  fetchAlgorithms: vi.fn(),
  fetchTemplate: vi.fn(),
  runVisualization: vi.fn(),
}))

vi.mock('@/features/algorithm-visualization/api/algorithmVisualizer', () => apiMocks)

vi.mock('@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmTemplatePicker.vue', () => ({
  default: defineComponent({
    name: 'AlgorithmTemplatePickerStub',
    emits: ['select'],
    setup(_, { emit }) {
      return () => h('button', {
        type: 'button',
        'data-testid': 'select-binary-search',
        onClick: () => emit('select', 'binary_search'),
      }, '选择二分查找')
    },
  }),
}))

vi.mock('@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmCodeEditorPanel.vue', () => ({
  default: defineComponent({
    name: 'AlgorithmCodeEditorPanelStub',
    props: { modelValue: { type: String, default: '' } },
    setup(props, { expose }) {
      expose({ highlightLine: vi.fn() })
      return () => h('textarea', {
        'data-testid': 'code-editor',
        value: props.modelValue,
      })
    },
  }),
}))

vi.mock('@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmInputDataPanel.vue', () => ({
  default: defineComponent({
    name: 'AlgorithmInputDataPanelStub',
    setup: () => () => h('div', { 'data-testid': 'input-panel' }),
  }),
}))

vi.mock('@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmVisualizerStage.vue', () => ({
  default: defineComponent({
    name: 'AlgorithmVisualizerStageStub',
    setup: () => () => h('div', { 'data-testid': 'visualizer-stage' }),
  }),
}))

vi.mock('@/features/algorithm-visualization/components/algorithm-visualizer/AlgorithmRunErrorDialog.vue', () => ({
  default: defineComponent({
    name: 'AlgorithmRunErrorDialogStub',
    setup: () => () => h('div', { 'data-testid': 'run-error' }),
  }),
}))

const mountedApps: Array<{ unmount: () => void }> = []

function successResponse<T>(data: T) {
  return { data: { code: 200, message: 'success', data } }
}

function createTraceResult(algorithm: string) {
  return successResponse({
    domain: 'searching',
    templateKey: algorithm,
    templateVersion: 'sha256:test',
    visualizerType: 'array',
    events: [
      {
        id: 'evt-0',
        step: 0,
        visualizerType: 'array',
        type: 'init_array',
        state: { structure: { array: [3, 1, 2] } },
      },
      {
        id: 'evt-1',
        step: 1,
        visualizerType: 'array',
        type: 'finish',
        state: { structure: { array: [1, 2, 3] } },
      },
    ],
    result: [1, 2, 3],
    summary: '完成',
  })
}

async function mountPage() {
  const target = document.createElement('div')
  document.body.append(target)
  const app = createApp(AlgorithmVisualization)
  app.mount(target)
  mountedApps.push(app)
  await vi.waitFor(() => {
    expect(apiMocks.fetchTemplate).toHaveBeenCalledWith('bubble_sort')
  })
  await nextTick()
  return target
}

beforeEach(() => {
  apiMocks.fetchAlgorithms.mockResolvedValue(successResponse([
    {
      key: 'bubble_sort',
      name: '冒泡排序',
      domain: 'sorting',
      visualizerType: 'array',
      difficulty: 'easy',
    },
    {
      key: 'binary_search',
      name: '二分查找',
      domain: 'searching',
      visualizerType: 'array',
      difficulty: 'easy',
    },
  ]))
  apiMocks.fetchTemplate.mockImplementation(async (algorithm: string) => {
    const binarySearch = algorithm === 'binary_search'
    return successResponse({
      domain: binarySearch ? 'searching' : 'sorting',
      key: algorithm,
      name: algorithm,
      visualizerType: 'array',
      difficulty: 'easy',
      version: 'sha256:test',
      templateCode: binarySearch
        ? 'def binary_search(arr, target):\n  return arr.index(target)'
        : 'def bubble_sort(arr):\n  return sorted(arr)',
      defaultInput: binarySearch
        ? { arr: [1, 2, 3, 5], target: 5 }
        : { arr: [3, 1, 2] },
      inputSchema: {
        type: 'object',
        required: binarySearch ? ['arr', 'target'] : ['arr'],
        properties: {
          arr: { type: 'array', items: { type: 'integer' } },
          ...(binarySearch ? { target: { type: 'integer' } } : {}),
        },
      },
    })
  })
  apiMocks.runVisualization.mockImplementation(async (payload: { algorithm?: string }) => (
    createTraceResult(payload.algorithm ?? 'bubble_sort')
  ))
})

afterEach(() => {
  mountedApps.splice(0).forEach(app => app.unmount())
  document.body.innerHTML = ''
  vi.clearAllMocks()
})

describe('AlgorithmVisualization run flows', () => {
  it('exposes only official template controls', async () => {
    const target = await mountPage()

    expect(target.querySelector('.execution-mode-switch')).toBeNull()
    expect(target.querySelector('.custom-visualizer-picker')).toBeNull()
  })

  it('runs a selected official template with its default input', async () => {
    const target = await mountPage()

    target.querySelector<HTMLButtonElement>('[data-testid="select-binary-search"]')!.click()
    await vi.waitFor(() => {
      expect(apiMocks.fetchTemplate).toHaveBeenCalledWith('binary_search')
    })
    await nextTick()

    target.querySelector<HTMLButtonElement>('.control-btn.primary')!.click()

    await vi.waitFor(() => {
      expect(apiMocks.runVisualization).toHaveBeenCalledWith('binary_search', {
        inputData: { arr: [1, 2, 3, 5], target: 5 },
      })
    })
  })
})
