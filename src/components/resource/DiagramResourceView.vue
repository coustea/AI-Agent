<template>
  <div class="diagram-resource" :class="{ compact }">
    <div v-if="mermaidSource" class="diagram-container">
      <!-- 隐藏原生 Mermaid 的 SVG 渲染容器，只作提取用 -->
      <!-- 使用 visibility:hidden + absolute 代替 v-show="false"，
           避免 display:none 导致 getBoundingClientRect 返回 0 -->
      <div
        ref="mermaidHiddenShell"
        class="mermaid-shell mermaid-offscreen"
        v-html="renderedMermaid"
      ></div>

      <!-- 图片预览区域：使用 Element Plus Image 组件支持放大 -->
      <div v-if="imageUrl" class="diagram-image-wrapper">
        <el-image
          class="diagram-image"
          :src="imageUrl"
          :preview-src-list="[imageUrl]"
          fit="contain"
          hide-on-click-modal
        />
        <div class="diagram-actions">
           <el-button @click="downloadImage" size="small" type="primary" plain>下载图解</el-button>
        </div>
      </div>
      <div v-else-if="renderingError" class="error-box">
        <el-alert type="error" :title="renderingError" show-icon />
      </div>
      <div v-else class="loading-box">
        <el-icon class="is-loading"><Loading /></el-icon> 正在渲染图解…
      </div>
    </div>
    <div v-else class="empty-state">
      <el-empty description="暂无图解数据" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import mermaid from 'mermaid'
import { Loading } from '@element-plus/icons-vue'
import { parseJsonObject, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  topic?: string
  compact?: boolean
}>()

const mermaidHiddenShell = ref<HTMLElement | null>(null)
const renderedMermaid = ref('')
const imageUrl = ref('')
const renderingError = ref('')

// 从 resultData 中提取 mermaid 源字符串
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
      if (parsed.mermaid) return parsed.mermaid
      if (parsed.source) return parsed.source
    }
    return content
  }

  if (typeof content === 'object' && content !== null) {
    if (content.mermaid) return content.mermaid
    if (content.source) return content.source
  }

  if (data.mermaid) return data.mermaid
  if (data.source) return data.source

  return ''
})

// Mermaid 初始化
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  fontFamily: 'Inter, system-ui, sans-serif'
})

// 将 SVG 转换为 PNG
const convertSvgToPng = async (svgElement: SVGSVGElement): Promise<string> => {
  return new Promise((resolve, reject) => {
    try {
      const clonedSvg = svgElement.cloneNode(true) as SVGSVGElement
      
      let svgWidth = 0
      let svgHeight = 0
      
      const rect = svgElement.getBoundingClientRect()
      if (rect.width > 0 && rect.height > 0) {
        svgWidth = rect.width
        svgHeight = rect.height
      } else {
        const attrWidth = parseFloat(svgElement.getAttribute('width') || '0')
        const attrHeight = parseFloat(svgElement.getAttribute('height') || '0')
        if (attrWidth > 0 && attrHeight > 0) {
          svgWidth = attrWidth
          svgHeight = attrHeight
        } else {
          const viewBox = svgElement.getAttribute('viewBox')
          if (viewBox) {
            const parts = viewBox.split(/[\s,]+/).map(Number)
            const vbW = parts[2] ?? 0
            const vbH = parts[3] ?? 0
            if (parts.length >= 4 && vbW > 0 && vbH > 0) {
              svgWidth = vbW
              svgHeight = vbH
            }
          }
        }
      }
      
      const padding = 20
      svgWidth += padding * 2
      svgHeight += padding * 2

      if (svgWidth <= padding * 2 || svgHeight <= padding * 2) {
        throw new Error('无效的 SVG 尺寸')
      }

      clonedSvg.setAttribute('width', svgWidth.toString())
      clonedSvg.setAttribute('height', svgHeight.toString())
      clonedSvg.style.backgroundColor = '#ffffff'
      
      const gElements = clonedSvg.querySelectorAll('g')
      gElements.forEach(g => {
        g.setAttribute('transform', `translate(${padding}, ${padding})`)
      })

      const svgData = new XMLSerializer().serializeToString(clonedSvg)
      const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
      const URL = window.URL || window.webkitURL || window
      const blobURL = URL.createObjectURL(blob)

      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement('canvas')
        const scale = 2
        canvas.width = svgWidth * scale
        canvas.height = svgHeight * scale
        
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          URL.revokeObjectURL(blobURL)
          reject(new Error('Canvas context is null'))
          return
        }
        
        ctx.scale(scale, scale)
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(0, 0, svgWidth, svgHeight)
        ctx.drawImage(img, 0, 0, svgWidth, svgHeight)
        
        const pngUrl = canvas.toDataURL('image/png')
        URL.revokeObjectURL(blobURL)
        resolve(pngUrl)
      }
      img.onerror = () => {
        URL.revokeObjectURL(blobURL)
        reject(new Error('Image load failed'))
      }
      img.src = blobURL
    } catch (err) {
      reject(err)
    }
  })
}

// 渲染 Mermaid
const renderDiagram = async () => {
  const source = mermaidSource.value
  if (!source) return

  renderingError.value = ''
  imageUrl.value = ''
  renderedMermaid.value = ''

  try {
    const id = `mermaid-${Date.now()}`
    const { svg } = await mermaid.render(id, source)
    renderedMermaid.value = svg

    await nextTick()

    if (mermaidHiddenShell.value) {
      const svgElement = mermaidHiddenShell.value.querySelector('svg')
      if (svgElement) {
        const pngDataUrl = await convertSvgToPng(svgElement)
        imageUrl.value = pngDataUrl
      } else {
        throw new Error('未生成 SVG 元素')
      }
    }
  } catch (err: any) {
    console.error('[DiagramResourceView] Render error:', err)
    renderingError.value = `图解渲染失败: ${err.message || String(err)}`
  }
}

watch(mermaidSource, () => {
  renderDiagram()
}, { immediate: true })

onMounted(() => {
  if (mermaidSource.value) {
    renderDiagram()
  }
})

const downloadImage = () => {
  if (!imageUrl.value) return
  const link = document.createElement('a')
  link.href = imageUrl.value
  link.download = `${props.topic || 'diagram'}.png`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}
</script>

<style scoped>
.diagram-resource {
  width: 100%;
}

.diagram-container {
  width: 100%;
  position: relative;
}

.mermaid-offscreen {
  visibility: hidden;
  position: absolute;
  left: -9999px;
  top: -9999px;
}

.diagram-image-wrapper {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.diagram-image {
  max-width: 100%;
  max-height: 500px;
  border-radius: 4px;
}

.diagram-actions {
  display: flex;
  justify-content: flex-end;
  width: 100%;
}

.error-box, .loading-box, .empty-state {
  padding: 24px;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  display: flex;
  justify-content: center;
  align-items: center;
  color: #64748b;
}

.error-box {
  background: #fef2f2;
  border-color: #fecaca;
  color: #991b1b;
}

.compact .diagram-image {
  max-height: 240px;
}
</style>