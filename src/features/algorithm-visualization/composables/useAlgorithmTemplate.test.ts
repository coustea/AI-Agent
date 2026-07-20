import { describe, expect, it, vi } from 'vitest'

const apiMocks = vi.hoisted(() => ({
  fetchAlgorithms: vi.fn(),
  fetchTemplate: vi.fn(),
}))

vi.mock('@/features/algorithm-visualization/api/algorithmVisualizer', () => ({
  fetchAlgorithms: apiMocks.fetchAlgorithms,
  fetchTemplate: apiMocks.fetchTemplate,
}))

vi.mock('vue-sonner', () => ({
  toast: { error: vi.fn() },
}))

import { useAlgorithmTemplate } from './useAlgorithmTemplate'

describe('useAlgorithmTemplate', () => {
  it('loads and replaces editor code for every selected template', async () => {
    apiMocks.fetchAlgorithms.mockResolvedValue({
      data: {
        data: [
          { key: 'bubble_sort', name: '冒泡排序', domain: 'sorting', visualizerType: 'array', difficulty: 'easy' },
          { key: 'binary_search', name: '二分查找', domain: 'searching', visualizerType: 'array', difficulty: 'easy' },
        ],
      },
    })
    apiMocks.fetchTemplate.mockImplementation((algorithm: string) => Promise.resolve({
      data: {
        data: {
          key: algorithm,
          name: algorithm,
          domain: 'sorting',
          visualizerType: 'array',
          difficulty: 'easy',
          version: 'sha256:test',
          templateCode: `def ${algorithm}():\n  pass`,
          defaultInput: {},
          inputSchema: {},
        },
      },
    }))

    const template = useAlgorithmTemplate()
    await template.loadMeta()
    await template.setAlgorithm('bubble_sort')
    const firstVersion = template.templateVersion.value

    await template.setAlgorithm('binary_search')

    expect(template.code.value).toBe('def binary_search():\n  pass')
    expect(template.templateData.value?.key).toBe('binary_search')
    expect(template.templateVersion.value).toBe(firstVersion + 1)
    expect(apiMocks.fetchTemplate).toHaveBeenLastCalledWith('binary_search')
  })
})
