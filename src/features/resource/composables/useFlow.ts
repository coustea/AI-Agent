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

// 单条连线的几何信息：唯一标识、终点坐标、SVG path 字符串
type LinkGeometry = {
  id: string
  x: number
  y: number
  d: string
}

// 流程图连线布局组合式函数：测量源节点到各卡片节点的贝塞尔曲线几何，返回响应式连线数据
export function useFlow(nodes: ComputedRef<DagNodeState[]>) {
  // 画布容器 DOM 引用，用于计算相对坐标
  const canvasRef = ref<HTMLElement | null>(null)
  // 连线起点的源节点 DOM 引用
  const sourceRef = ref<HTMLElement | null>(null)
  // 各节点卡片 DOM 的缓存映射表，key 为节点 id
  const cardRefs = new Map<string, HTMLElement>()
  // 画布尺寸，供 SVG viewport 使用
  const canvasSize = ref({ width: 1000, height: 700 })
  // 最近一次测量得到的连线几何数据
  const measuredLinks = ref<LinkGeometry[]>([])
  // requestAnimationFrame 句柄，用于合并多次测量请求
  let measureFrame = 0
  // 画布尺寸监听器，当画布大小变化时重新测量连线
  let resizeObserver: ResizeObserver | null = null

  // 合并测量的几何数据与节点状态，输出带 status 的最终连线列表
  const links = computed(() => {
    const measured = new Map(measuredLinks.value.map(link => [link.id, link]))
    return nodes.value.flatMap((node) => {
      const link = measured.get(node.id)
      return link ? [{ ...link, status: node.status }] : []
    })
  })

  // 注册或移除某个节点卡片的 DOM 引用，随后触发重新测量
  function setCardRef(id: string, element: unknown) {
    const previous = cardRefs.get(id)
    if (previous && previous !== element) {
      resizeObserver?.unobserve(previous)
    }

    if (element instanceof HTMLElement) {
      cardRefs.set(id, element)
      resizeObserver?.observe(element)
    } else {
      cardRefs.delete(id)
    }
    scheduleMeasure()
  }

  // 用 requestAnimationFrame 合并测量请求，避免一帧内重复计算
  function scheduleMeasure() {
    if (typeof window === 'undefined') return
    if (measureFrame) window.cancelAnimationFrame(measureFrame)
    measureFrame = window.requestAnimationFrame(() => {
      measureFrame = 0
      measure()
    })
  }

  // 核心测量逻辑：根据源节点和各卡片的实际位置计算贝塞尔曲线 path
  function measure() {
    const canvas = canvasRef.value
    const source = sourceRef.value
    if (!canvas || !source) return

    const canvasRect = canvas.getBoundingClientRect()
    const width = Math.max(1, Math.round(canvasRect.width))
    const height = Math.max(1, Math.round(canvasRect.height))
    // 画布尺寸变化时更新响应式尺寸
    if (canvasSize.value.width !== width || canvasSize.value.height !== height) {
      canvasSize.value = { width, height }
    }

    // 计算源节点底部中心点作为所有连线的起点
    const sourceRect = source.getBoundingClientRect()
    const startX = Math.round(sourceRect.left - canvasRect.left + sourceRect.width / 2)
    const startY = Math.round(sourceRect.bottom - canvasRect.top + 8)

    // 遍历所有节点，为已挂载的卡片计算贝塞尔曲线几何
    const nextLinks = nodes.value
      .map((node) => {
        const card = cardRefs.get(node.id)
        if (!card) return null

        // 卡片顶部中心点作为连线终点
        const cardRect = card.getBoundingClientRect()
        const endX = Math.round(cardRect.left - canvasRect.left + cardRect.width / 2)
        const endY = Math.round(cardRect.top - canvasRect.top - 8)
        // 垂直距离最小值保证曲线有足够弧度
        const distanceY = Math.max(42, endY - startY)
        const distanceX = endX - startX
        // 控制点水平拉伸量，使曲线两侧向内收拢形成 S 形
        const sidePull = Math.min(120, Math.max(28, Math.abs(distanceX) * 0.18))
        // 起点和终点两个控制点的坐标，根据水平偏移方向调整
        const c1X = Math.round(startX + (distanceX > 0 ? sidePull : -sidePull))
        const c2X = Math.round(endX - (distanceX > 0 ? sidePull : -sidePull))
        const c1Y = Math.round(startY + distanceY * 0.36)
        const c2Y = Math.round(endY - distanceY * 0.28)

        // 拼接三阶贝塞尔曲线 path 字符串
        return {
          id: node.id,
          x: endX,
          y: endY,
          d: `M ${startX} ${startY} C ${c1X} ${c1Y}, ${c2X} ${c2Y}, ${endX} ${endY}`,
        }
      })
      .filter((link): link is LinkGeometry => Boolean(link))

    // 仅当几何确实变化时才更新，避免无意义的响应式触发
    if (!sameGeometry(measuredLinks.value, nextLinks)) {
      measuredLinks.value = nextLinks
    }
  }

  // 组件挂载后首次测量，并注册 resize 和 ResizeObserver 监听
  onMounted(async () => {
    await nextTick()
    scheduleMeasure()
    window.addEventListener('resize', scheduleMeasure)

    // 若环境支持 ResizeObserver，监听画布容器尺寸变化
    if (typeof ResizeObserver !== 'undefined' && canvasRef.value) {
      resizeObserver = new ResizeObserver(scheduleMeasure)
      resizeObserver.observe(canvasRef.value)
      cardRefs.forEach(card => resizeObserver?.observe(card))
    }
  })

  // 组件卸载前清理事件监听和定时器，防止内存泄漏
  onBeforeUnmount(() => {
    if (typeof window !== 'undefined') {
      window.removeEventListener('resize', scheduleMeasure)
      if (measureFrame) window.cancelAnimationFrame(measureFrame)
    }
    resizeObserver?.disconnect()
  })

  // 监听节点的 id、状态和进度变化，DOM 更新后重新测量连线几何
  watch(
    () => nodes.value.map(node => `${node.id}:${node.status}:${node.progress}:${node.currentMessage}`).join('|'),
    async () => {
      await nextTick()
      scheduleMeasure()
    },
    { immediate: true },
  )

  // 返回模板所需的画布引用、源节点引用、画布尺寸、连线数据、卡片注册函数和测量调度函数
  return {
    canvasRef,
    sourceRef,
    canvasSize,
    links,
    setCardRef,
    scheduleMeasure,
  }
}

// 比较两组连线几何是否完全相同，用于决定是否需要触发响应式更新
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
