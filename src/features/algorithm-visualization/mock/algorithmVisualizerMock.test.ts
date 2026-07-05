import { describe, expect, it } from 'vitest'
import { createBubbleSortPayload } from '@/features/algorithm-visualization/mock/algorithmVisualizerMock'

describe('createBubbleSortPayload', () => {
  it('builds bubble sort steps from the provided input array', () => {
    const payload = createBubbleSortPayload({
      language: 'javascript',
      code: 'function bubbleSort(arr) { return arr }',
      input: '[5,2,8,1,3]',
    })

    expect(payload.visualizerType).toBe('array')
    expect(payload.initialState).toEqual({ array: [5, 2, 8, 1, 3] })
    expect(payload.finalState).toEqual({ array: [1, 2, 3, 5, 8] })
    expect(payload.steps[0]?.type).toBe('init')
    expect(payload.steps.some((step) => step.type === 'compare')).toBe(true)
    expect(payload.steps.some((step) => step.type === 'swap')).toBe(true)
    expect(payload.steps[payload.steps.length - 1]?.type).toBe('mark-answer')
  })

  it('falls back to the default array when the input is invalid', () => {
    const payload = createBubbleSortPayload({
      language: 'python',
      code: 'def bubble_sort(arr): return arr',
      input: '{bad json}',
    })

    expect(payload.initialState).toEqual({ array: [5, 2, 8, 1, 3] })
  })
})
