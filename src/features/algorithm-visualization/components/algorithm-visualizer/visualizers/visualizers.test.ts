import { createApp, nextTick, type Component } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import type { TraceEvent, VisualizerType } from '@/features/algorithm-visualization/types'
import ArrayBarsVisualizer from './sorting/ArrayBarsVisualizer.vue'
import StackQueueVisualizer from './structures/StackQueueVisualizer.vue'
import LinkedListVisualizer from './structures/LinkedListVisualizer.vue'
import TreeVisualizer from './trees/TreeVisualizer.vue'
import GraphVisualizer from './graphs/GraphVisualizer.vue'
import DpTableVisualizer from './dp/DpTableVisualizer.vue'

const mountedApps: Array<{ unmount: () => void }> = []

function makeEvent(
  visualizerType: VisualizerType,
  structure: Record<string, unknown>,
  targets: TraceEvent['targets'] = [],
): TraceEvent {
  return {
    id: 'event-1',
    step: 1,
    domain: 'test',
    visualizerType,
    type: 'snapshot',
    state: { structure },
    targets,
  }
}

function mount(
  component: Component,
  currentEvent: TraceEvent,
  events: TraceEvent[] = [currentEvent],
  currentStepIndex = 0,
) {
  const target = document.createElement('div')
  document.body.append(target)
  const app = createApp(component, {
    currentEvent,
    currentStepIndex,
    events,
  })
  app.mount(target)
  mountedApps.push(app)
  return target
}

afterEach(() => mountedApps.splice(0).forEach(app => app.unmount()))

describe('algorithm visualizers', () => {
  it('renders array bars and the focused index', async () => {
    const current = makeEvent('array', { array: [3, 1, 2] }, [1])
    const target = mount(ArrayBarsVisualizer, current)
    await nextTick()

    expect(target.querySelectorAll('.bar-group')).toHaveLength(3)
    expect(target.querySelector('[data-bar-id="bar-1"]')?.getAttribute('data-tone')).toBe('focus')
  })

  it('renders an explicit horizontal exchange for swap events', async () => {
    const previous = makeEvent('array', { array: [3, 1, 2] }, [0, 1])
    const current = makeEvent('array', { array: [1, 3, 2] }, [0, 1])
    current.id = 'event-2'
    current.step = 2
    current.type = 'swap'
    const target = mount(ArrayBarsVisualizer, current, [previous, current], 1)
    await nextTick()

    expect(target.querySelector('.operation-indicator')?.textContent).toContain('交换位置 0 与 1')
    expect(target.querySelector('[data-bar-id="bar-0"]')?.getAttribute('data-swap-from')).toBe('1')
    expect(target.querySelector('[data-bar-id="bar-1"]')?.getAttribute('data-swap-from')).toBe('0')
  })

  it('renders the current token and stack top pointer', () => {
    const current = makeEvent('stack-queue', {
      mode: 'stack',
      items: [
        { id: 'item-0', label: '(' },
        { id: 'item-1', label: '[' },
      ],
      pointers: [{ label: 'top', itemIndex: 1, tone: 'accent' }],
      currentValue: ']',
    })
    const target = mount(StackQueueVisualizer, current)

    expect(target.querySelector('.current-token')?.textContent).toContain(']')
    expect(target.querySelector('.pointer-pill')?.textContent).toContain('top')
  })

  it('renders stable linked-list relations and named pointers', () => {
    const current = makeEvent('linked-list', {
      nodes: [
        { id: 'node-0', label: '1', next: null },
        { id: 'node-1', label: '2', next: 'node-0', tone: 'visited' },
      ],
      pointers: [{ label: 'prev', nodeId: 'node-1', nodeIndex: 1, tone: 'accent' }],
    })
    const target = mount(LinkedListVisualizer, current)

    expect(target.querySelector('[data-node-id="node-1"] .node-next')?.textContent).toContain('1')
    expect(target.querySelector('[data-node-id="node-1"] .pointer-pill')?.textContent).toContain('prev')
  })

  it('renders tree nodes and parent-child links', () => {
    const current = makeEvent('tree', {
      nodes: [
        { id: 'node-0', label: '1', left: 'node-1' },
        { id: 'node-1', label: '2', tone: 'visited' },
      ],
    }, ['node-1'])
    const target = mount(TreeVisualizer, current)

    expect(target.querySelectorAll('.tree-node')).toHaveLength(2)
    expect(target.querySelectorAll('.tree-link')).toHaveLength(1)
    expect(target.querySelector('.tree-node.active')?.textContent).toContain('2')
    expect(target.querySelector('.current-status')?.textContent).toContain('当前节点 2')
    expect((target.querySelector('.tree-node') as HTMLElement)?.style.left).toContain('%')
  })

  it('renders graph edges, weights, and Dijkstra distances', () => {
    const current = makeEvent('graph', {
      nodes: [
        {
          id: '0',
          label: '0',
          distance: 0,
          tone: 'visited',
          edges: [{ to: '1', weight: 5 }],
        },
        { id: '1', label: '1', distance: 5, edges: [] },
      ],
    }, ['1'])
    const target = mount(GraphVisualizer, current)

    expect(target.querySelectorAll('.graph-edge')).toHaveLength(1)
    expect(target.querySelector('.graph-edge-weight')?.textContent).toContain('5')
    expect(target.textContent).toContain('距离 5')
    expect(target.querySelector('.graph-node.active')?.textContent).toContain('1')
    expect(target.querySelector('.current-status')?.textContent).toContain('当前节点 1')
    expect((target.querySelector('.graph-node') as HTMLElement)?.style.left).toContain('%')
  })

  it('renders active and dependency DP cells', () => {
    const current = makeEvent('dp-table', {
      headers: ['0', '1'],
      values: [[0, 0], [0, 2]],
      highlighted: [
        { row: 1, col: 1, tone: 'active' },
        { row: 0, col: 1, tone: 'dependency' },
      ],
    })
    const target = mount(DpTableVisualizer, current)

    expect(target.querySelectorAll('.dp-cell.active')).toHaveLength(1)
    expect(target.querySelectorAll('.dp-cell.dependency')).toHaveLength(1)
    expect(target.querySelector('.legend')?.textContent).toContain('依赖')
  })
})
