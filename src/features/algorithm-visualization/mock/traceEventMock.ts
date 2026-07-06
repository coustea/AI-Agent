import type { TraceEvent, VisualizerType } from '@/features/algorithm-visualization/types'

/** 创建冒泡排序 mock TraceEvent[] — 前端快速预览用。
 * 替代旧 algorithmVisualizerMock.ts。 */
export function createBubbleSortEvents(inputArray: number[] = [5, 3, 8, 1, 2]): TraceEvent[] {
  const nums = [...inputArray]
  const events: TraceEvent[] = []
  let step = 0

  function emit(
    type: string,
    structure: Record<string, unknown>,
    opts: Partial<Pick<TraceEvent, 'targets' | 'message' | 'line'>> = {},
  ): TraceEvent {
    const event: TraceEvent = {
      id: `evt-${step}`,
      step,
      domain: 'data_structure',
      visualizerType: 'array' as VisualizerType,
      type,
      state: { structure },
      targets: opts.targets ?? [],
      message: opts.message,
      line: opts.line,
    }
    events.push(event)
    step++
    return event
  }

  emit('init_array', { array: [...nums] }, { message: `初始化数组：[${nums.join(', ')}]`, line: 2 })

  for (let i = 0; i < nums.length; i++) {
    for (let j = 0; j < nums.length - i - 1; j++) {
      emit('compare', { array: [...nums] }, {
        targets: [j, j + 1],
        message: `比较 nums[${j}]=${nums[j]} 和 nums[${j + 1}]=${nums[j + 1]}`,
        line: 6,
      })

      if (nums[j] > nums[j + 1]) {
        const left = nums[j]
        const right = nums[j + 1]
        nums[j] = right
        nums[j + 1] = left
        emit('swap', { array: [...nums] }, {
          targets: [j, j + 1],
          message: `${left} > ${right}，交换位置`,
          line: 7,
        })
      }
    }

    emit('mark_sorted', { array: [...nums] }, {
      targets: [nums.length - i - 1],
      message: `第 ${i + 1} 轮结束，最大值归位`,
      line: 4,
    })
  }

  emit('finish', { array: [...nums] }, { message: '排序完成' })

  return events
}

/** 创建括号匹配 mock TraceEvent[] — 栈可视化预览用 */
export function createBracketMatchEvents(input: string = '{[()]}'): TraceEvent[] {
  const events: TraceEvent[] = []
  let step = 0
  const stack: Array<{ char: string; index: number }> = []

  function emit(
    type: string,
    structure: Record<string, unknown>,
    opts: Partial<Pick<TraceEvent, 'targets' | 'message'>> = {},
  ): TraceEvent {
    const event: TraceEvent = {
      id: `evt-${step}`,
      step,
      domain: 'data_structure',
      visualizerType: 'stack-queue' as VisualizerType,
      type,
      state: { structure },
      targets: opts.targets ?? [],
      message: opts.message,
    }
    events.push(event)
    step++
    return event
  }

  emit('init_stack', { mode: 'stack', items: [] }, { message: '初始化空栈' })

  for (let i = 0; i < input.length; i++) {
    const char = input[i]
    const isOpening = char === '(' || char === '[' || char === '{'

    if (isOpening) {
      stack.push({ char, index: i })
      emit('push', {
        mode: 'stack',
        items: stack.map((s) => ({ id: `item-${s.index}`, label: s.char, tone: 'default' })),
      }, { targets: [i], message: `入栈：${char}` })
    } else {
      const top = stack[stack.length - 1]
      if (top) {
        const matching = (char === ')' && top.char === '(') || (char === ']' && top.char === '[') || (char === '}' && top.char === '{')
        if (matching) {
          stack.pop()
          emit('pop', {
            mode: 'stack',
            items: stack.map((s) => ({ id: `item-${s.index}`, label: s.char, tone: 'default' })),
          }, { targets: [top.index], message: `出栈：${top.char} 匹配 ${char}` })
        }
      }
    }

    emit('highlight_input', {
      mode: 'stack',
      items: stack.map((s) => ({ id: `item-${s.index}`, label: s.char, tone: 'default' })),
      inputIndex: i,
    }, { targets: [i], message: `当前处理字符：${char}` })
  }

  emit('finish', {
    mode: 'stack',
    items: stack.map((s) => ({ id: `item-${s.index}`, label: s.char, tone: 'visited' })),
  }, { message: stack.length === 0 ? '括号匹配成功！' : '括号不匹配' })

  return events
}
