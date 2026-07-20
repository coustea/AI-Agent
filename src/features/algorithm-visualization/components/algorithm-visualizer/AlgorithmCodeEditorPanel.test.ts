import { createApp, defineComponent, h, nextTick, ref } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'

const monacoMocks = vi.hoisted(() => {
  let value = ''
  let contentListener: (() => void) | null = null
  let createOptions: Record<string, unknown> = {}

  const model = {}
  const decorations = {
    clear: vi.fn(),
    set: vi.fn(),
  }
  const editorInstance = {
    createDecorationsCollection: vi.fn(() => decorations),
    dispose: vi.fn(),
    getModel: vi.fn(() => model),
    getPosition: vi.fn(() => ({ lineNumber: 1, column: 1 })),
    getValue: vi.fn(() => value),
    onDidChangeCursorPosition: vi.fn(),
    onDidChangeModelContent: vi.fn((listener: () => void) => {
      contentListener = listener
    }),
    revealLineInCenterIfOutsideViewport: vi.fn(),
    setPosition: vi.fn(),
    setValue: vi.fn((nextValue: string) => {
      value = nextValue
      contentListener?.()
    }),
    updateOptions: vi.fn(),
  }

  return {
    create: vi.fn((_element: HTMLElement, options: Record<string, unknown>) => {
      createOptions = options
      value = String(options.value ?? '')
      return editorInstance
    }),
    defineTheme: vi.fn(),
    editorInstance,
    getCreateOptions: () => createOptions,
    getValue: () => value,
    reset() {
      value = ''
      contentListener = null
      createOptions = {}
      vi.clearAllMocks()
    },
    setModelLanguage: vi.fn(),
    setTheme: vi.fn(),
    simulateInternalEdit(nextValue: string) {
      value = nextValue
      contentListener?.()
    },
  }
})

vi.mock('monaco-editor', () => ({
  Range: class Range {
    constructor(
      _startLineNumber: number,
      _startColumn: number,
      _endLineNumber: number,
      _endColumn: number,
    ) {}
  },
  editor: {
    OverviewRulerLane: { Full: 7 },
    create: monacoMocks.create,
    defineTheme: monacoMocks.defineTheme,
    setModelLanguage: monacoMocks.setModelLanguage,
    setTheme: monacoMocks.setTheme,
  },
}))

import AlgorithmCodeEditorPanel from './AlgorithmCodeEditorPanel.vue'

const mountedApps: Array<{ unmount: () => void }> = []

function mountEditor(modelValue = '') {
  const value = ref(modelValue)
  const target = document.createElement('div')
  document.body.append(target)

  const Host = defineComponent({
    setup() {
      return () => h(AlgorithmCodeEditorPanel, {
        modelValue: value.value,
        title: '官方模板代码',
      })
    },
  })

  const app = createApp(Host)
  app.mount(target)
  mountedApps.push(app)
  return { target, value }
}

async function waitForEditorMount() {
  await nextTick()
  await nextTick()
}

afterEach(() => {
  mountedApps.splice(0).forEach(app => app.unmount())
  monacoMocks.reset()
})

describe('AlgorithmCodeEditorPanel', () => {
  it('uses a single light theme with a fixed Python badge', async () => {
    const { target } = mountEditor('def bubble_sort(arr):\n  return arr')
    await waitForEditorMount()

    expect(monacoMocks.getCreateOptions().theme).toBe('algorithm-sunlit')
    expect(target.querySelector('.theme-toggle')).toBeNull()
    expect(target.querySelector('.editor-language-trigger')).toBeNull()
    expect(target.querySelector('.editor-language-badge')?.textContent).toContain('Python')
  })

  it('does not drop template code when it arrives during an internal Monaco update', async () => {
    const { value } = mountEditor('')
    await waitForEditorMount()

    monacoMocks.simulateInternalEdit('stale editor value')
    value.value = 'def bubble_sort(arr):\n  return sorted(arr)'
    await nextTick()
    await nextTick()

    expect(monacoMocks.getValue()).toBe('def bubble_sort(arr):\n  return sorted(arr)')
  })
})
