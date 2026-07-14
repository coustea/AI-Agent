import { describe, expect, it, vi } from 'vitest'

const apiMocks = vi.hoisted(() => ({
  fetchAlgorithms: vi.fn(),
  fetchLanguages: vi.fn(),
  fetchTemplate: vi.fn(),
}))

vi.mock('@/features/algorithm-visualization/api/algorithmVisualizer', () => ({
  fetchAlgorithms: apiMocks.fetchAlgorithms,
  fetchLanguages: apiMocks.fetchLanguages,
  fetchTemplate: apiMocks.fetchTemplate,
}))

vi.mock('vue-sonner', () => ({
  toast: { error: vi.fn() },
}))

import { useAlgorithmTemplate } from './useAlgorithmTemplate'

describe('useAlgorithmTemplate', () => {
  it('loads and replaces editor code for every selected template', async () => {
    apiMocks.fetchLanguages.mockResolvedValue({ data: { data: [{ key: 'python', label: 'Python', extension: 'py' }] } })
    apiMocks.fetchAlgorithms.mockResolvedValue({
      data: {
        data: [
          { key: 'bubble_sort', name: '冒泡排序', domain: 'sorting', visualizerType: 'array', difficulty: 'easy', supportedLanguages: ['python'] },
          { key: 'binary_search', name: '二分查找', domain: 'searching', visualizerType: 'array', difficulty: 'easy', supportedLanguages: ['python'] },
        ],
      },
    })
    apiMocks.fetchTemplate.mockImplementation((algorithm: string) => Promise.resolve({
      data: {
        data: {
          algorithm,
          domain: 'sorting',
          visualizerType: 'array',
          language: 'python',
          templateCode: `def ${algorithm}():\n  pass`,
          requiredEvents: [],
          supportedLanguages: ['python'],
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
    expect(template.templateData.value?.algorithm).toBe('binary_search')
    expect(template.templateVersion.value).toBe(firstVersion + 1)
    expect(apiMocks.fetchTemplate).toHaveBeenLastCalledWith('binary_search', 'python')
  })
})
