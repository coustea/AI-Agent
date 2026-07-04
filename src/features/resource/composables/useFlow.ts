import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
  type ComputedRef,
} from 'vue'
import type { DagNodeState } from '../model/catalog'

type LinkGeometry = {
  id: string
  x: number
  y: number
  d: string
}

export function useFlow(nodes: ComputedRef<DagNodeState[]>) {
  const canvasRef = ref<HTMLElement | null>(null)
  const sourceRef = ref<HTMLElement | null>(null)
  const cardRefs = new Map<string, HTMLElement>()
  const canvasSize = ref({ width: 1000, height: 700 })
  const measuredLinks = ref<LinkGeometry[]>([])
  let measureFrame = 0
  let resizeObserver: ResizeObserver | null = null

  const links = computed(() => {
    const measured = new Map(measuredLinks.value.map(link => [link.id, link]))
    return nodes.value.flatMap((node) => {
      const link = measured.get(node.id)
      return link ? [{ ...link, status: node.status }] : []
    })
  })

  function setCardRef(id: string, element: unknown) {
    if (element instanceof HTMLElement) {
      cardRefs.set(id, element)
    } else {
      cardRefs.delete(id)
    }
    scheduleMeasure()
  }

  function scheduleMeasure() {
    if (typeof window === 'undefined') return
    if (measureFrame) window.cancelAnimationFrame(measureFrame)
    measureFrame = window.requestAnimationFrame(() => {
      measureFrame = 0
      measure()
    })
  }

  function measure() {
    const canvas = canvasRef.value
    const source = sourceRef.value
    if (!canvas || !source) return

    const canvasRect = canvas.getBoundingClientRect()
    const width = Math.max(1, Math.round(canvasRect.width))
    const height = Math.max(1, Math.round(canvasRect.height))
    if (canvasSize.value.width !== width || canvasSize.value.height !== height) {
      canvasSize.value = { width, height }
    }

    const sourceRect = source.getBoundingClientRect()
    const startX = Math.round(sourceRect.left - canvasRect.left + sourceRect.width / 2)
    const startY = Math.round(sourceRect.bottom - canvasRect.top + 8)

    const nextLinks = nodes.value
      .map((node) => {
        const card = cardRefs.get(node.id)
        if (!card) return null

        const cardRect = card.getBoundingClientRect()
        const endX = Math.round(cardRect.left - canvasRect.left + cardRect.width / 2)
        const endY = Math.round(cardRect.top - canvasRect.top - 8)
        const distanceY = Math.max(42, endY - startY)
        const distanceX = endX - startX
        const sidePull = Math.min(120, Math.max(28, Math.abs(distanceX) * 0.18))
        const c1X = Math.round(startX + (distanceX > 0 ? sidePull : -sidePull))
        const c2X = Math.round(endX - (distanceX > 0 ? sidePull : -sidePull))
        const c1Y = Math.round(startY + distanceY * 0.36)
        const c2Y = Math.round(endY - distanceY * 0.28)

        return {
          id: node.id,
          x: endX,
          y: endY,
          d: `M ${startX} ${startY} C ${c1X} ${c1Y}, ${c2X} ${c2Y}, ${endX} ${endY}`,
        }
      })
      .filter((link): link is LinkGeometry => Boolean(link))

    if (!sameGeometry(measuredLinks.value, nextLinks)) {
      measuredLinks.value = nextLinks
    }
  }

  onMounted(async () => {
    await nextTick()
    scheduleMeasure()
    window.addEventListener('resize', scheduleMeasure)

    if (typeof ResizeObserver !== 'undefined' && canvasRef.value) {
      resizeObserver = new ResizeObserver(scheduleMeasure)
      resizeObserver.observe(canvasRef.value)
    }
  })

  onBeforeUnmount(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('resize', scheduleMeasure)
      if (measureFrame) window.cancelAnimationFrame(measureFrame)
    }
    resizeObserver?.disconnect()
  })

  watch(
    () => nodes.value.map(node => `${node.id}:${node.status}:${node.progress}`).join('|'),
    async () => {
      await nextTick()
      scheduleMeasure()
    },
    { immediate: true },
  )

  return {
    canvasRef,
    sourceRef,
    canvasSize,
    links,
    setCardRef,
    scheduleMeasure,
  }
}

function sameGeometry(previous: LinkGeometry[], next: LinkGeometry[]) {
  if (previous.length !== next.length) return false
  return previous.every((item, index) => {
    const target = next[index]
    return Boolean(
      target
      && item.id === target.id
      && item.x === target.x
      && item.y === target.y
      && item.d === target.d,
    )
  })
}
