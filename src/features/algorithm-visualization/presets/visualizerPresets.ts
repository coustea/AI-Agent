import { bubbleSortExamples } from '@/features/algorithm-visualization/presets/exampleCodes'
import type { CodeLanguage } from '@/features/algorithm-visualization/types'

export const DEFAULT_VISUALIZER_LANGUAGE: CodeLanguage = 'python'
export const DEFAULT_VISUALIZER_INPUT = '[5, 2, 8, 1, 3]'

export function getDefaultVisualizerCode(language: CodeLanguage = DEFAULT_VISUALIZER_LANGUAGE) {
  return bubbleSortExamples[language]
}
