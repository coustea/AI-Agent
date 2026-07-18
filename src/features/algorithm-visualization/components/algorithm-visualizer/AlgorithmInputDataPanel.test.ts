import { createApp, h, nextTick, ref } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import AlgorithmInputDataPanel from './AlgorithmInputDataPanel.vue'

const mountedApps: Array<{ unmount: () => void }> = []

afterEach(() => mountedApps.splice(0).forEach(app => app.unmount()))

describe('AlgorithmInputDataPanel', () => {
  it('copies reactive default input into an editable plain object when defaultData changes', async () => {
    const defaultData = ref<Record<string, unknown>>({ arr: [6, 1, 8, 3] })
    const updates: Array<Record<string, unknown>> = []
    const target = document.createElement('div')
    document.body.append(target)

    const app = createApp({
      render: () => h(AlgorithmInputDataPanel, {
        modelValue: {},
        defaultData: defaultData.value,
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

    // defaultData watch is not immediate — parent initializes modelValue
    expect(updates).toEqual([])

    // When defaultData reference changes (e.g. algorithm switch), it emits the new defaults
    defaultData.value = { arr: [3, 1, 2] }
    await nextTick()

    expect(updates).toEqual([{ arr: [3, 1, 2] }])
    expect(updates[0]).not.toBe(defaultData.value)
  })

  it('retains intermediate invalid text during typing without immediate reversion', async () => {
    const modelValue = ref<Record<string, unknown>>({ arr: [1, 2] })
    const validityEvents: boolean[] = []
    const updateEvents: Array<Record<string, unknown>> = []
    const target = document.createElement('div')
    document.body.append(target)

    const app = createApp({
      render: () => h(AlgorithmInputDataPanel, {
        modelValue: modelValue.value,
        defaultData: { arr: [1, 2] },
        inputSchema: {
          type: 'object',
          required: ['arr'],
          properties: {
            arr: { type: 'array', items: { type: 'integer' } },
          },
        },
        'onUpdate:modelValue': (value: Record<string, unknown>) => {
          updateEvents.push(value)
          modelValue.value = value
        },
        onValidityChange: (valid: boolean) => validityEvents.push(valid),
      }),
    })
    app.mount(target)
    mountedApps.push(app)

    await nextTick()

    // Find the textarea
    const textarea = target.querySelector('textarea')
    expect(textarea).not.toBeNull()
    if (!textarea) return

    expect(textarea.value).toBe('1, 2')

    // Simulate user typing an intermediate invalid string "1, 2,"
    textarea.value = '1, 2,'
    textarea.dispatchEvent(new Event('input'))
    await nextTick()

    // The validity event should capture invalid status (false)
    expect(validityEvents.at(-1)).toBe(false)
    // The text in textarea should remain "1, 2," rather than reverting
    expect(textarea.value).toBe('1, 2,')
    // No update event should be fired (since it is invalid)
    expect(updateEvents).toEqual([])

    // Simulate user finishing typing "1, 2, 3"
    textarea.value = '1, 2, 3'
    textarea.dispatchEvent(new Event('input'))
    await nextTick()

    // The validity event should capture valid status (true)
    expect(validityEvents.at(-1)).toBe(true)
    // The text should be "1, 2, 3"
    expect(textarea.value).toBe('1, 2, 3')
    // Update event should be fired with the parsed array
    expect(updateEvents).toEqual([{ arr: [1, 2, 3] }])
  })
})
