import type {
  ArrayVisualizerState,
  VisualizerGenerationParams,
  VisualizerPayload,
  VisualStep,
} from '@/features/algorithm-visualization/types'

function parseArrayInput(input: string): number[] {
  try {
    const value = JSON.parse(input)

    if (!Array.isArray(value)) {
      return [5, 2, 8, 1, 3]
    }

    const nums = value.map(Number).filter((item) => Number.isFinite(item))
    return nums.length > 0 ? nums : [5, 2, 8, 1, 3]
  } catch {
    return [5, 2, 8, 1, 3]
  }
}

export function createBubbleSortPayload(
  params: VisualizerGenerationParams,
): VisualizerPayload<ArrayVisualizerState> {
  const nums = parseArrayInput(params.input)
  const working = [...nums]
  const steps: VisualStep[] = []

  steps.push({
    id: 'init',
    type: 'init',
    targets: [],
    description: `初始化数组：[${working.join(', ')}]。`,
    codeLine: 1,
    variables: {
      nums: [...working],
    },
    payload: {
      array: [...working],
    },
  })

  for (let i = 0; i < working.length; i += 1) {
    for (let j = 0; j < working.length - i - 1; j += 1) {
      const leftValue = working[j]
      const rightValue = working[j + 1]

      if (leftValue === undefined || rightValue === undefined) {
        continue
      }

      steps.push({
        id: `compare-${i}-${j}`,
        type: 'compare',
        targets: [`bar-${j}`, `bar-${j + 1}`],
        description: `比较 nums[${j}] = ${leftValue} 和 nums[${j + 1}] = ${rightValue}。`,
        codeLine: 4,
        duration: 500,
        variables: {
          i,
          j,
          left: leftValue,
          right: rightValue,
        },
        payload: {
          array: [...working],
          indices: [j, j + 1],
        },
      })

      if (leftValue > rightValue) {
        const left = leftValue
        const right = rightValue

        working[j] = right
        working[j + 1] = left

        steps.push({
          id: `swap-${i}-${j}`,
          type: 'swap',
          targets: [`bar-${j}`, `bar-${j + 1}`],
          description: `${left} 大于 ${right}，交换两个元素的位置。`,
          codeLine: 5,
          duration: 700,
          variables: {
            i,
            j,
            swapped: true,
            nums: [...working],
          },
          payload: {
            from: j,
            to: j + 1,
            array: [...working],
            indices: [j, j + 1],
          },
        })
      }
    }

    steps.push({
      id: `round-${i}-done`,
      type: 'mark-answer',
      targets: [`bar-${working.length - i - 1}`],
      description: `第 ${i + 1} 轮结束，当前未排序区间中的最大值已经归位。`,
      codeLine: 2,
      duration: 400,
      variables: {
        i,
        sortedIndex: working.length - i - 1,
        nums: [...working],
      },
      payload: {
        array: [...working],
        sortedIndex: working.length - i - 1,
      },
    })
  }

  return {
    title: '冒泡排序可视化',
    visualizerType: 'array',
    language: params.language,
    code: params.code,
    input: params.input,
    initialState: {
      array: nums,
    },
    steps,
    finalState: {
      array: working,
    },
    summary: '冒泡排序通过多轮相邻比较，把较大的元素逐步移动到数组末尾。',
  }
}
