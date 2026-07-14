import { createApp, h, reactive } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import AlgorithmInputDataPanel from './AlgorithmInputDataPanel.vue'

const mountedApps: Array<{ unmount: () => void }> = []

afterEach(() => mountedApps.splice(0).forEach(app => app.unmount()))

describe('AlgorithmInputDataPanel', () => {
  it('copies reactive default input into an editable plain object', () => {
    const defaultData = reactive({ arr: [6, 1, 8, 3] })
    const updates: Array<Record<string, unknown>> = []
    const target = document.createElement('div')
    document.body.append(target)

    const app = createApp({
      render: () => h(AlgorithmInputDataPanel, {
        modelValue: {},
        defaultData,
        inputSchema: {
          type: 'object',
          required: ['arr'],
          properties: {
            arr: { type: 'array', items: { type: 'integer' } },
          },
        },
        'onUpdate:modelValue': (value: Record<string, unknown>) => updates.push(value),
      }),
    })
    app.mount(target)
    mountedApps.push(app)

    expect(updates).toEqual([{ arr: [6, 1, 8, 3] }])
    expect(updates[0]).not.toBe(defaultData)
  })
})
