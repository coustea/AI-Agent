<template>
  <div class="diagram-resource" :class="{ compact }">
    <div v-if="mermaidSource" class="technical-frame diagram-container">

      <div class="frame-header">
        <div class="status-indicator"></div>
        <span class="technical-label">SCHEMATIC_RENDER // SYSTEM_DIAGRAM // MODE_VECTOR</span>
      </div>

      <!-- Mermaid SVG 直接内联展示，避免先转 Canvas 导致跨域污染 -->
      <div ref="diagramBodyRef" class="diagram-svg-wrapper">
        <div
          v-if="renderedMermaid"
          ref="mermaidSvgShell"
          class="mermaid-shell diagram-svg-shell"
          v-html="renderedMermaid"
        ></div>

        <div v-else-if="renderingError" class="error-box-hud">
          <div class="error-icon">!</div>
          <div class="error-text">RENDER_EXCEPTION: {{ renderingError }}</div>
        </div>

        <div v-else class="loading-box-hud">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>INITIALIZING_RENDER_ENGINE...</span>
        </div>
      </div>

      <div v-if="renderedMermaid" class="diagram-actions">
        <button class="hud-btn-small" @click="downloadSvg">DOWNLOAD_SVG</button>
        <button class="hud-btn-small" :disabled="pngExporting" @click="downloadPng">
          {{ pngExporting ? 'EXPORTING_PNG...' : 'DOWNLOAD_PNG' }}
        </button>
      </div>

      <div v-if="exportError" class="export-error-hud">
        {{ exportError }}
      </div>

      <div class="frame-footer">
        <span class="mono-tag">VECTOR_DATA_READY</span>
        <div class="footer-line"></div>
      </div>
    </div>

    <div v-else class="empty-state-hud">
      <div class="empty-frame">
        <div class="empty-icon">NULL</div>
        <p>NO_SCHEMATIC_DATA_DETECTED</p>
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

const mermaidSource = computed<string>(() => {
  if (!props.resultData) return ''
  if (typeof props.resultData === 'string') return props.resultData

  let data: any = props.resultData

  if (data.resource && typeof data.resource === 'object') {
    data = data.resource
  }

  const content = data.content

  if (typeof content === 'string' && content.trim()) {
    const parsed = parseJsonObject(content)
    if (parsed) {
      if (typeof parsed.mermaid === 'string') return parsed.mermaid
      if (typeof parsed.source === 'string') return parsed.source
      if (typeof parsed.mermaid_source === 'string') return parsed.mermaid_source
      if (typeof parsed.code === 'string') return parsed.code
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

mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
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
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
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
  --primary: #000000;
  --bg: #FFFFFF;
  --fg: #000000;
  --border: #E5E7EB;
  --accent: #000000;
}

.technical-frame {
  position: relative;
  background: var(--bg);
  border: none;
  border-radius: 4px;
  padding: 44px 32px 32px;
  box-shadow: none;
  transition: box-shadow 0.3s ease, border-color 0.3s ease, background-color 0.3s ease;
  display: flex;
  flex-direction: column;
}

.frame-corners {
  position: absolute;
  width: 12px;
  height: 12px;
  border: 2px solid var(--primary);
  pointer-events: none;
}

.top-left {
  top: -1px;
  left: -1px;
  border-right: 0;
  border-bottom: 0;
}

.top-right {
  top: -1px;
  right: -1px;
  border-left: 0;
  border-bottom: 0;
}

.bottom-left {
  bottom: -1px;
  left: -1px;
  border-right: 0;
  border-top: 0;
}

.bottom-right {
  bottom: -1px;
  right: -1px;
  border-left: 0;
  border-top: 0;
}

.frame-header {
  position: absolute;
  top: 12px;
  left: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-indicator {
  width: 6px;
  height: 6px;
  background: var(--accent);
  border-radius: 50%;
  box-shadow: none;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

.technical-label {
  font-family: 'Share Tech Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.7rem;
  color: var(--primary);
  letter-spacing: 1px;
}

.frame-footer {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.mono-tag {
  font-family: 'Share Tech Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.65rem;
  color: var(--primary);
  background: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 2px;
}

.footer-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, var(--border), transparent);
}

.diagram-container {
  width: 100%;
  min-height: 360px;
}

.diagram-svg-wrapper {
  width: 100%;
  min-height: 320px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 20px;
  overflow: auto;
  background-image: none;
  background-size: 20px 20px;
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
}

.diagram-svg-shell :deep(.nodeLabel),
.diagram-svg-shell :deep(.edgeLabel),
.diagram-svg-shell :deep(text),
.diagram-svg-shell :deep(tspan) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.diagram-actions {
  display: flex;
  justify-content: flex-end;
  width: 100%;
  gap: 8px;
  margin-top: 12px;
}

.hud-btn-small {
  background: transparent;
  border: 1px solid var(--primary);
  color: var(--primary);
  font-family: 'Share Tech Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.7rem;
  padding: 4px 12px;
  border-radius: 2px;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s, box-shadow 0.2s, opacity 0.2s;
  letter-spacing: 1px;
}

.hud-btn-small:hover:not(:disabled) {
  background: var(--primary);
  color: white;
  box-shadow: none;
}

.hud-btn-small:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.error-box-hud,
.loading-box-hud {
  min-height: 260px;
  padding: 40px;
  border: 1px dashed var(--border);
  border-radius: 4px;
  text-align: center;
  font-family: 'Share Tech Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.8rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #64748b;
}

.error-box-hud {
  background: rgba(0, 0, 0, 0.05);
  border-color: rgba(0, 0, 0, 0.2);
  color: #dc2626;
}

.export-error-hud {
  margin-top: 10px;
  padding: 8px 10px;
  border: 1px dashed rgba(0, 0, 0, 0.25);
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.05);
  color: #dc2626;
  font-size: 0.75rem;
  line-height: 1.5;
}

.error-icon {
  font-size: 1.5rem;
  opacity: 0.8;
}

.empty-state-hud {
  padding: 40px;
  display: flex;
  justify-content: center;
}

.empty-frame {
  text-align: center;
  border: 1px dashed var(--border);
  padding: 40px 60px;
  border-radius: 4px;
}

.empty-icon {
  font-family: 'Share Tech Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 2rem;
  color: var(--primary);
  opacity: 0.3;
  margin-bottom: 12px;
}

.empty-frame p {
  font-family: 'Share Tech Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.8rem;
  color: #94a3b8;
  letter-spacing: 1px;
}

.compact .technical-frame {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
  min-height: 0;
}

.compact .frame-corners,
.compact .frame-header,
.compact .frame-footer {
  display: none;
}

.compact .diagram-svg-wrapper {
  min-height: 220px;
  max-height: 280px;
  padding: 12px;
}

.compact .diagram-actions {
  justify-content: center;
}
</style>
