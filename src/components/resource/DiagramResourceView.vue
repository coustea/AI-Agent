<template>
  <div class="diagram-resource" :class="{ compact }">
    <div v-if="mermaidSource" class="diagram-panel diagram-container" :data-diagram-type="diagramType">

      <div class="diagram-header">
        <div>
          <div class="diagram-kicker">知识图解</div>
          <h3>{{ diagramTitle }}</h3>
        </div>
        <div class="diagram-badges">
          <span class="diagram-badge type">{{ diagramTypeLabel }}</span>
          <span class="diagram-badge category">{{ diagramCategory }}</span>
          <span class="diagram-badge quality">{{ qualityText }}</span>
        </div>
      </div>

      <div class="diagram-workspace">
        <aside v-if="!compact && hasInsightPanel" class="diagram-insights">
          <div class="insight-grid">
            <div v-for="item in statItems" :key="item.label" class="insight-stat">
              <strong>{{ item.value }}</strong>
              <span>{{ item.label }}</span>
            </div>
          </div>

          <div class="module-section type-focus">
            <div class="section-title">图解侧重点</div>
            <p>{{ diagramFocus }}</p>
          </div>

          <div v-if="moduleTitles.length" class="module-section">
            <div class="section-title">模块覆盖</div>
            <div class="module-list">
              <span v-for="module in moduleTitles" :key="module" class="module-chip">{{ module }}</span>
            </div>
          </div>

          <div v-if="coveredPoints.length" class="module-section">
            <div class="section-title">核心知识点</div>
            <ul class="point-list">
              <li v-for="point in visibleCoveredPoints" :key="point">{{ point }}</li>
            </ul>
          </div>
        </aside>

        <!-- Mermaid SVG 直接内联展示，避免先转 Canvas 导致跨域污染 -->
        <div class="diagram-canvas">
          <div class="canvas-toolbar">
            <span>{{ relationType }}</span>
            <div v-if="renderedMermaid" class="diagram-actions">
              <button class="diagram-action" @click="downloadSvg">导出 SVG</button>
              <button class="diagram-action primary" :disabled="pngExporting" @click="downloadPng">
                {{ pngExporting ? '导出中...' : '导出 PNG' }}
              </button>
            </div>
          </div>

          <div ref="diagramBodyRef" class="diagram-svg-wrapper">
            <div
              v-if="renderedMermaid"
              ref="mermaidSvgShell"
              class="mermaid-shell diagram-svg-shell"
              v-html="renderedMermaid"
            ></div>

            <div v-else-if="renderingError" class="error-box">
              <div class="error-icon">!</div>
              <div class="error-text">图解渲染失败：{{ renderingError }}</div>
            </div>

            <div v-else class="loading-box">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>正在渲染知识图解...</span>
            </div>
          </div>

          <div v-if="exportError" class="export-error">
            {{ exportError }}
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <div class="empty-frame">
        <div class="empty-icon">空</div>
        <p>暂无可渲染的知识图解数据</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import mermaid from 'mermaid'
import { Loading } from '@element-plus/icons-vue'
import { parseJsonObject, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  topic?: string
  compact?: boolean
}>()

const diagramBodyRef = ref<HTMLElement | null>(null)
const mermaidSvgShell = ref<HTMLElement | null>(null)
const renderedMermaid = ref('')
const renderingError = ref('')
const exportError = ref('')
const pngExporting = ref(false)

let renderToken = 0
let resizeObserver: ResizeObserver | null = null

const unwrappedData = computed<Record<string, any>>(() => {
  if (!props.resultData) return {}
  if (typeof props.resultData === 'string') return { content: props.resultData }

  let data: any = props.resultData

  if (data.resource && typeof data.resource === 'object') {
    data = data.resource
  }

  return data && typeof data === 'object' ? data : {}
})

const parsedContent = computed<Record<string, any> | null>(() => parseJsonObject(unwrappedData.value.content))

const mermaidSource = computed<string>(() => {
  const data = unwrappedData.value
  const content = data.content

  if (typeof content === 'string' && content.trim()) {
    if (parsedContent.value) {
      if (typeof parsedContent.value.mermaid === 'string') return parsedContent.value.mermaid
      if (typeof parsedContent.value.source === 'string') return parsedContent.value.source
      if (typeof parsedContent.value.mermaid_source === 'string') return parsedContent.value.mermaid_source
      if (typeof parsedContent.value.code === 'string') return parsedContent.value.code
    }
    return content
  }

  if (typeof content === 'object' && content !== null) {
    if (typeof content.mermaid === 'string') return content.mermaid
    if (typeof content.source === 'string') return content.source
    if (typeof content.mermaid_source === 'string') return content.mermaid_source
    if (typeof content.code === 'string') return content.code
  }

  if (typeof data.mermaid === 'string') return data.mermaid
  if (typeof data.source === 'string') return data.source
  if (typeof data.mermaid_source === 'string') return data.mermaid_source
  if (typeof data.code === 'string') return data.code

  return ''
})

const summaryData = computed<Record<string, any>>(() => {
  const data = unwrappedData.value
  const metadata = data.metadata && typeof data.metadata === 'object' ? data.metadata : {}
  const content = typeof data.content === 'object' && data.content !== null ? data.content : {}
  const candidates = [
    data.summary_data,
    data.summaryData,
    parsedContent.value?.summary_data,
    parsedContent.value?.summaryData,
    content.summary_data,
    content.summaryData,
    content.quality,
    parsedContent.value?.quality,
    metadata.quality,
  ]
  return candidates.find((item) => item && typeof item === 'object' && !Array.isArray(item)) || {}
})

const diagramType = computed(() => {
  const data = unwrappedData.value
  return String(
    summaryData.value.diagram_type ||
    data.diagram_type ||
    parsedContent.value?.diagram_type ||
    data.content?.diagram_type ||
    'diagram',
  )
})

const diagramProfiles: Record<string, {
  label: string
  category: string
  relation: string
  focus: string
  statLabels: [string, string, string]
}> = {
  hierarchy: {
    label: '层级结构图',
    category: '知识结构',
    relation: '层级拆解',
    focus: '从核心概念向分类、性质、方法和考点展开，适合建立知识骨架。',
    statLabels: ['知识节点', '模块分区', '层级关系'],
  },
  flow: {
    label: '顺序流程图',
    category: '过程机制',
    relation: '步骤流转',
    focus: '突出学习对象的输入、处理、判断、输出和反馈路径。',
    statLabels: ['流程节点', '阶段分区', '流转关系'],
  },
  compare: {
    label: '对比结构图',
    category: '差异辨析',
    relation: '对比关系',
    focus: '围绕对比对象、维度、共同点、差异点和适用场景组织。',
    statLabels: ['对比要点', '维度分区', '差异关系'],
  },
  relation: {
    label: '关系网络图',
    category: '概念关联',
    relation: '依赖/因果',
    focus: '把依赖、因果、约束、影响和前置知识连成可追踪网络。',
    statLabels: ['概念节点', '关系分区', '连接关系'],
  },
  sequence: {
    label: '交互时序图',
    category: '交互过程',
    relation: '消息时序',
    focus: '展示参与者之间的调用顺序、响应路径、反馈和异常交互。',
    statLabels: ['交互单元', '参与角色', '消息数量'],
  },
  state: {
    label: '状态转移图',
    category: '生命周期',
    relation: '状态变化',
    focus: '强调状态、触发条件、异常回退和终止路径。',
    statLabels: ['状态节点', '状态簇', '转移关系'],
  },
  class: {
    label: '类结构图',
    category: '代码结构',
    relation: '类型关系',
    focus: '呈现类、接口、属性、方法，以及继承、组合和依赖关系。',
    statLabels: ['类型单元', '类/接口', '结构关系'],
  },
  er: {
    label: '实体关系图',
    category: '数据建模',
    relation: '实体基数',
    focus: '展示实体、字段、主线关系和一对多/多对多等基数约束。',
    statLabels: ['字段要素', '实体数量', '实体关系'],
  },
  block: {
    label: '模块方块图',
    category: '系统结构',
    relation: '模块分层',
    focus: '把入口、核心处理、存储、输出和外部依赖组织成架构方块。',
    statLabels: ['模块节点', '结构层次', '依赖关系'],
  },
  packet: {
    label: '协议包结构图',
    category: '网络协议',
    relation: '字段布局',
    focus: '按字段偏移、长度、标志位、校验和选项展示协议包结构。',
    statLabels: ['字段段', '字段组', '相邻关系'],
  },
  git: {
    label: 'Git 演进图',
    category: '版本演进',
    relation: '分支合并',
    focus: '展示主线、分支、提交、切换和合并形成的演进路径。',
    statLabels: ['提交节点', '分支数量', '演进关系'],
  },
  activity: {
    label: '活动流程图',
    category: '任务活动',
    relation: '活动流',
    focus: '强调开始、动作、判断、并行或回退以及结束节点。',
    statLabels: ['活动节点', '泳道/分区', '活动关系'],
  },
  usecase: {
    label: '用例关系图',
    category: '需求分析',
    relation: '角色用例',
    focus: '围绕角色、目标用例、include/extend 和系统边界表达需求。',
    statLabels: ['用例节点', '角色分区', '用例关系'],
  },
  component: {
    label: '组件依赖图',
    category: '软件架构',
    relation: '组件依赖',
    focus: '展示组件、接口、服务依赖和跨层调用方向。',
    statLabels: ['组件节点', '架构分层', '依赖关系'],
  },
  package: {
    label: '包依赖图',
    category: '代码组织',
    relation: '包依赖',
    focus: '呈现领域包、公共包、基础设施包之间的依赖边界。',
    statLabels: ['包节点', '包分组', '依赖关系'],
  },
  deployment: {
    label: '部署拓扑图',
    category: '运行环境',
    relation: '部署连接',
    focus: '展示客户端、服务、数据库、缓存和外部系统的运行拓扑。',
    statLabels: ['运行节点', '环境分区', '连接关系'],
  },
  object: {
    label: '对象实例图',
    category: '运行时状态',
    relation: '对象引用',
    focus: '表达对象实例、状态值、集合归属和运行时引用关系。',
    statLabels: ['对象实例', '对象分组', '引用关系'],
  },
  communication: {
    label: '通信协作图',
    category: '对象协作',
    relation: '编号消息',
    focus: '展示对象之间的消息编号、协作顺序、返回和控制流。',
    statLabels: ['协作对象', '协作分区', '消息关系'],
  },
}

const diagramProfile = computed(() => diagramProfiles[diagramType.value] || {
  label: '知识图解',
  category: '智能图解',
  relation: '知识关系',
  focus: '围绕核心知识、关键关系和学习路径组织可视化内容。',
  statLabels: ['知识节点', '模块分区', '关键关系'],
})

const diagramTypeLabel = computed(() => diagramProfile.value.label)
const diagramCategory = computed(() => diagramProfile.value.category)
const diagramFocus = computed(() => diagramProfile.value.focus)

const diagramTitle = computed(() => {
  const data = unwrappedData.value
  return String(data.title || parsedContent.value?.title || props.topic || '知识图解')
})

const qualityText = computed(() => {
  const level = String(summaryData.value.quality_level || 'rich')
  const labels: Record<string, string> = {
    complete: '内容完整',
    rich: '覆盖丰富',
    basic: '基础图解',
    thin: '待深化',
  }
  return labels[level] || '覆盖丰富'
})

const relationType = computed(() => String(summaryData.value.relation_type || diagramProfile.value.relation))

const toNumber = (value: unknown): number => {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0
}

const statItems = computed(() => {
  const nodes = toNumber(summaryData.value.node_count)
  const modules = toNumber(summaryData.value.module_count)
  const edges = toNumber(summaryData.value.edge_count)
  const [nodeLabel, moduleLabel, edgeLabel] = diagramProfile.value.statLabels
  return [
    { label: nodeLabel, value: nodes },
    { label: moduleLabel, value: modules },
    { label: edgeLabel, value: edges },
  ].filter((item) => item.value > 0)
})

const moduleTitles = computed<string[]>(() => {
  const raw = summaryData.value.module_titles
  return Array.isArray(raw) ? raw.map((item) => String(item)).filter(Boolean).slice(0, 8) : []
})

const coveredPoints = computed<string[]>(() => {
  const raw = summaryData.value.covered_points
  return Array.isArray(raw) ? raw.map((item) => String(item)).filter(Boolean).slice(0, 12) : []
})

const visibleCoveredPoints = computed(() => coveredPoints.value.slice(0, 8))

const hasInsightPanel = computed(() => statItems.value.length > 0 || moduleTitles.value.length > 0 || coveredPoints.value.length > 0)

mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  fontFamily: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  flowchart: {
    htmlLabels: true,
    useMaxWidth: false,
  },
  sequence: {
    useMaxWidth: false,
  },
  gantt: {
    useMaxWidth: false,
  },
})

const safeFileName = computed(() => {
  const raw = props.topic || 'diagram'
  return raw.replace(/[\\/:*?"<>|\s]+/g, '_').replace(/^_+|_+$/g, '') || 'diagram'
})

const getSvgElement = (): SVGSVGElement | null => {
  return mermaidSvgShell.value?.querySelector('svg') ?? null
}

const getFallbackSize = () => {
  const container = diagramBodyRef.value
  const width = Math.max(container?.clientWidth || 0, props.compact ? 360 : 900)
  const height = props.compact ? 260 : 560
  return { width, height }
}

const parseSvgLength = (value: string | null): number => {
  if (!value) return 0
  if (value.endsWith('%')) return 0
  const parsed = Number.parseFloat(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 0
}

const normalizeSvgSize = (svg: SVGSVGElement) => {
  const fallback = getFallbackSize()
  const rect = svg.getBoundingClientRect()

  let width = rect.width > 0 ? rect.width : parseSvgLength(svg.getAttribute('width'))
  let height = rect.height > 0 ? rect.height : parseSvgLength(svg.getAttribute('height'))

  const viewBox = svg.getAttribute('viewBox')
  if ((!width || !height) && viewBox) {
    const parts = viewBox.split(/[\s,]+/).map(Number)
    if (parts.length === 4 && parts.every(Number.isFinite)) {
      width = width || (parts[2] as number)
      height = height || (parts[3] as number)
    }
  }

  width = Math.max(Math.ceil(width || fallback.width), 320)
  height = Math.max(Math.ceil(height || fallback.height), 220)

  if (!viewBox) {
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`)
  }

  // 关键修复：D3 / Mermaid 的缩放手势不能稳定解析 100% 这类相对长度。
  svg.setAttribute('width', String(width))
  svg.setAttribute('height', String(height))
  svg.style.width = '100%'
  svg.style.maxWidth = '100%'
  svg.style.height = 'auto'
  svg.style.display = 'block'

  return { width, height }
}

const removeExternalResources = (svg: SVGSVGElement) => {
  const externalPattern = /(?:https?:)?\/\//i

  svg.querySelectorAll('image').forEach((node) => {
    const href = node.getAttribute('href') || node.getAttribute('xlink:href') || ''
    if (externalPattern.test(href)) {
      node.remove()
    }
  })

  svg.querySelectorAll('*').forEach((node) => {
    const style = node.getAttribute('style')
    if (style && /url\((['"]?)(?:https?:)?\/\//i.test(style)) {
      node.removeAttribute('style')
    }
  })

  const styleNodes = svg.querySelectorAll('style')
  styleNodes.forEach((node) => {
    node.textContent = (node.textContent || '').replace(/url\((['"]?)(?:https?:)?\/\/[^)]+\)/gi, 'none')
  })
}

const prepareSvgForExport = (svgElement: SVGSVGElement): { svgText: string; width: number; height: number } => {
  const clonedSvg = svgElement.cloneNode(true) as SVGSVGElement
  const { width, height } = normalizeSvgSize(clonedSvg)

  clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  clonedSvg.setAttribute('width', String(width))
  clonedSvg.setAttribute('height', String(height))
  clonedSvg.style.width = `${width}px`
  clonedSvg.style.height = `${height}px`
  clonedSvg.style.maxWidth = 'none'
  clonedSvg.style.background = '#ffffff'

  removeExternalResources(clonedSvg)

  const style = document.createElementNS('http://www.w3.org/2000/svg', 'style')
  style.textContent = `
    svg { background: #ffffff; }
    text, tspan, foreignObject, div, span {
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
  `
  clonedSvg.insertBefore(style, clonedSvg.firstChild)

  const svgText = new XMLSerializer().serializeToString(clonedSvg)
  return { svgText, width, height }
}

const triggerDownload = (url: string, filename: string) => {
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const downloadSvg = () => {
  exportError.value = ''
  const svgElement = getSvgElement()
  if (!svgElement) return

  try {
    const { svgText } = prepareSvgForExport(svgElement)
    const blob = new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    triggerDownload(url, `${safeFileName.value}.svg`)
    URL.revokeObjectURL(url)
  } catch (err: any) {
    exportError.value = err?.message || 'SVG 导出失败'
  }
}

const downloadPng = async () => {
  exportError.value = ''
  const svgElement = getSvgElement()
  if (!svgElement || pngExporting.value) return

  pngExporting.value = true

  try {
    const { svgText, width, height } = prepareSvgForExport(svgElement)
    const blob = new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' })
    const blobUrl = URL.createObjectURL(blob)

    const image = new Image()
    image.crossOrigin = 'anonymous'

    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve()
      image.onerror = () => reject(new Error('SVG 图片加载失败，建议直接导出 SVG'))
      image.src = blobUrl
    })

    const scale = Math.max(window.devicePixelRatio || 1, 2)
    const canvas = document.createElement('canvas')
    canvas.width = Math.ceil(width * scale)
    canvas.height = Math.ceil(height * scale)

    const ctx = canvas.getContext('2d')
    if (!ctx) {
      URL.revokeObjectURL(blobUrl)
      throw new Error('Canvas 初始化失败')
    }

    ctx.setTransform(scale, 0, 0, scale, 0, 0)
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, width, height)
    ctx.drawImage(image, 0, 0, width, height)

    const pngUrl = canvas.toDataURL('image/png')
    triggerDownload(pngUrl, `${safeFileName.value}.png`)
    URL.revokeObjectURL(blobUrl)
  } catch (err: any) {
    console.error('[DiagramResourceView] PNG export error:', err)
    exportError.value = 'PNG 导出失败：当前图中可能包含跨域资源，已建议使用 SVG 导出。'
  } finally {
    pngExporting.value = false
  }
}

const renderDiagram = async () => {
  const source = mermaidSource.value.trim()
  const currentToken = ++renderToken

  if (!source) {
    renderedMermaid.value = ''
    renderingError.value = ''
    exportError.value = ''
    return
  }

  renderingError.value = ''
  exportError.value = ''
  renderedMermaid.value = ''

  try {
    const id = `mermaid-${Date.now()}-${Math.random().toString(16).slice(2)}`
    const { svg } = await mermaid.render(id, source)

    if (currentToken !== renderToken) return

    renderedMermaid.value = svg
    await nextTick()

    requestAnimationFrame(() => {
      if (currentToken !== renderToken) return
      const svgElement = getSvgElement()
      if (svgElement) {
        normalizeSvgSize(svgElement)
      }
    })
  } catch (err: any) {
    console.error('[DiagramResourceView] Render error:', err)
    if (currentToken === renderToken) {
      renderingError.value = err?.message || String(err)
    }
  }
}

watch(mermaidSource, () => {
  renderDiagram()
}, { immediate: true })

onMounted(() => {
  if (diagramBodyRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      const svgElement = getSvgElement()
      if (svgElement) {
        normalizeSvgSize(svgElement)
      }
    })
    resizeObserver.observe(diagramBodyRef.value)
  }
})

onBeforeUnmount(() => {
  renderToken++
  resizeObserver?.disconnect()
  resizeObserver = null
})
</script>

<style scoped>
.diagram-resource {
  width: 100%;
  --diagram-ink: #172033;
  --diagram-muted: #64748b;
  --diagram-line: #dbe4f0;
  --diagram-surface: #ffffff;
  --diagram-soft: #f6f9fc;
  --diagram-blue: #2563eb;
  --diagram-green: #059669;
  --diagram-amber: #d97706;
}

.diagram-panel {
  background:
    linear-gradient(135deg, rgba(37, 99, 235, 0.08), transparent 34%),
    linear-gradient(315deg, rgba(5, 150, 105, 0.08), transparent 28%),
    var(--diagram-surface);
  border: 1px solid var(--diagram-line);
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.diagram-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.diagram-kicker {
  color: var(--diagram-blue);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  margin-bottom: 4px;
}

.diagram-header h3 {
  margin: 0;
  color: var(--diagram-ink);
  font-size: 18px;
  line-height: 1.35;
  font-weight: 750;
}

.diagram-badges {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.diagram-badge {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.diagram-badge.type {
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
}

.diagram-badge.quality {
  color: #047857;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
}

.diagram-badge.category {
  color: #7c2d12;
  background: #fff7ed;
  border: 1px solid #fed7aa;
}

.diagram-workspace {
  display: grid;
  grid-template-columns: minmax(190px, 260px) minmax(0, 1fr);
  gap: 16px;
  align-items: stretch;
}

.diagram-insights {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(219, 228, 240, 0.9);
  border-radius: 8px;
  padding: 14px;
}

.insight-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.insight-stat {
  min-width: 0;
  padding: 10px 8px;
  border-radius: 8px;
  background: var(--diagram-soft);
  border: 1px solid #e6edf6;
  text-align: center;
}

.insight-stat strong {
  display: block;
  color: var(--diagram-ink);
  font-size: 20px;
  line-height: 1;
  margin-bottom: 6px;
}

.insight-stat span {
  color: var(--diagram-muted);
  font-size: 12px;
  line-height: 1.2;
}

.module-section {
  margin-top: 16px;
}

.section-title {
  color: var(--diagram-ink);
  font-size: 13px;
  font-weight: 750;
  margin-bottom: 9px;
}

.type-focus {
  margin-top: 14px;
  padding: 12px;
  border-radius: 8px;
  background: #f8fbff;
  border: 1px solid #e6edf6;
}

.type-focus p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.55;
}

.module-list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

.module-chip {
  max-width: 100%;
  padding: 5px 9px;
  border-radius: 999px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #9a3412;
  font-size: 12px;
  line-height: 1.3;
}

.point-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 7px;
}

.point-list li {
  position: relative;
  padding-left: 12px;
  color: #334155;
  font-size: 13px;
  line-height: 1.45;
}

.point-list li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--diagram-green);
}

.diagram-canvas {
  min-width: 0;
  background: #ffffff;
  border: 1px solid #dfe7f2;
  border-radius: 8px;
  overflow: hidden;
}

.canvas-toolbar {
  min-height: 46px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid #e6edf6;
  background: #f8fbff;
  color: var(--diagram-muted);
  font-size: 13px;
}

.diagram-svg-wrapper {
  width: 100%;
  min-height: 320px;
  background:
    linear-gradient(#eef4fb 1px, transparent 1px),
    linear-gradient(90deg, #eef4fb 1px, transparent 1px),
    #ffffff;
  background-size: 28px 28px;
  padding: 22px;
  overflow: auto;
}

.diagram-svg-shell {
  width: 100%;
  min-width: 0;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.diagram-svg-shell :deep(svg) {
  display: block;
  max-width: 100%;
  height: auto;
  background: #ffffff;
  border-radius: 6px;
  filter: drop-shadow(0 12px 22px rgba(15, 23, 42, 0.08));
}

.diagram-svg-shell :deep(.nodeLabel),
.diagram-svg-shell :deep(.edgeLabel),
.diagram-svg-shell :deep(text),
.diagram-svg-shell :deep(tspan) {
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.diagram-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.diagram-action {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 10px;
  cursor: pointer;
  transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.diagram-action:hover:not(:disabled) {
  border-color: var(--diagram-blue);
  color: var(--diagram-blue);
  transform: translateY(-1px);
}

.diagram-action.primary {
  background: var(--diagram-blue);
  border-color: var(--diagram-blue);
  color: #ffffff;
}

.diagram-action.primary:hover:not(:disabled) {
  background: #1d4ed8;
  color: #ffffff;
}

.diagram-action:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.error-box,
.loading-box {
  min-height: 260px;
  padding: 40px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  text-align: center;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #64748b;
}

.error-box {
  background: #fff7ed;
  border-color: #fed7aa;
  color: #dc2626;
}

.export-error {
  margin: 12px 14px 14px;
  padding: 9px 11px;
  border: 1px dashed #fecaca;
  border-radius: 6px;
  background: #fef2f2;
  color: #dc2626;
  font-size: 13px;
  line-height: 1.5;
}

.error-icon {
  font-size: 1.5rem;
  opacity: 0.8;
}

.empty-state {
  padding: 40px;
  display: flex;
  justify-content: center;
}

.empty-frame {
  text-align: center;
  border: 1px dashed var(--diagram-line);
  padding: 40px 60px;
  border-radius: 8px;
  color: var(--diagram-muted);
}

.empty-icon {
  font-size: 24px;
  color: var(--diagram-blue);
  opacity: 0.75;
  margin-bottom: 12px;
}

.empty-frame p {
  font-size: 13px;
  color: #94a3b8;
}

.compact .diagram-panel {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
  min-height: 0;
  gap: 0;
}

.compact .diagram-header,
.compact .diagram-insights,
.compact .canvas-toolbar {
  display: none;
}

.compact .diagram-workspace {
  display: block;
}

.compact .diagram-canvas {
  border: none;
  background: transparent;
}

.compact .diagram-svg-wrapper {
  min-height: 220px;
  max-height: 280px;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

@media (max-width: 960px) {
  .diagram-workspace {
    grid-template-columns: 1fr;
  }

  .diagram-insights {
    order: 2;
  }
}

@media (max-width: 640px) {
  .diagram-panel {
    padding: 14px;
  }

  .diagram-header,
  .canvas-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .diagram-badges,
  .diagram-actions {
    justify-content: flex-start;
  }

  .insight-grid {
    grid-template-columns: repeat(3, minmax(72px, 1fr));
  }

  .diagram-svg-wrapper {
    padding: 14px;
  }
}
</style>
