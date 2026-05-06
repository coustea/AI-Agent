<template>
  <div class="diagram-resource" :class="{ compact }">
    <div v-if="mermaidSource" class="technical-frame diagram-container">
      <div class="frame-corners top-left"></div>
      <div class="frame-corners top-right"></div>
      <div class="frame-corners bottom-left"></div>
      <div class="frame-corners bottom-right"></div>

      <div class="frame-header">
        <div class="status-indicator"></div>
        <span class="technical-label">SCHEMATIC_RENDER // SYSTEM_DIAGRAM // MODE_VECTOR</span>
      </div>

      <!-- 隐藏原生 Mermaid 的 SVG 渲染容器，只作提取用 -->
      <div
        ref="mermaidHiddenShell"
        class="mermaid-shell mermaid-offscreen"
        v-html="renderedMermaid"
      ></div>

      <!-- 图片预览区域 -->
      <div v-if="imageUrl" class="diagram-image-wrapper">
        <el-image
          class="diagram-image"
          :src="imageUrl"
          :preview-src-list="[imageUrl]"
          fit="contain"
          hide-on-click-modal
        />
        <div class="diagram-actions">
           <button class="hud-btn-small" @click="downloadImage">
             DOWNLOAD_SCHEMATIC
           </button>
        </div>
      </div>
      <div v-else-if="renderingError" class="error-box-hud">
        <div class="error-icon">!</div>
        <div class="error-text">RENDER_EXCEPTION: {{ renderingError }}</div>
      </div>
      <div v-else class="loading-box-hud">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>INITIALIZING_RENDER_ENGINE...</span>
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
  
  // 1. 处理 resource 包装层
  if (data.resource && typeof data.resource === 'object') {
    data = data.resource
  }

  const content = data.content
  
  // 2. content 是字符串
  if (typeof content === 'string' && content.trim()) {
    const parsed = parseJsonObject(content)
    if (parsed) {
      if (parsed.mermaid) return parsed.mermaid
      if (parsed.source) return parsed.source
    }
    return content
  }

  // 3. content 是对象
  if (typeof content === 'object' && content !== null) {
    if (content.mermaid) return content.mermaid
    if (content.source) return content.source
    if (content.mermaid_source) return content.mermaid_source
    if (content.code) return content.code
  }

  // 4. 回退到 data 第一层字段
  if (data.mermaid) return data.mermaid
  if (data.source) return data.source
  if (data.mermaid_source) return data.mermaid_source

  return ''
})

// Mermaid 初始化
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  fontFamily: 'Fira Code, monospace'
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
        svgWidth = attrWidth || 800
        svgHeight = attrHeight || 600
      }
      
      const padding = 20
      svgWidth += padding * 2
      svgHeight += padding * 2

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
      }
    }
  } catch (err: any) {
    console.error('[DiagramResourceView] Render error:', err)
    renderingError.value = err.message || String(err)
  }
}

watch(mermaidSource, () => { renderDiagram() }, { immediate: true })

onMounted(() => {
  if (mermaidSource.value) { renderDiagram() }
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
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

.diagram-resource {
  width: 100%;
  --primary: #6366F1;
  --bg: #F5F3FF;
  --fg: #1E1B4B;
  --border: #E0E7FF;
  --accent: #059669;
}

/* 技术框架样式 */
.technical-frame {
  position: relative;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 44px 32px 32px;
  box-shadow: 0 4px 24px rgba(99, 102, 241, 0.05);
  transition: all 0.3s ease;
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

.top-left { top: -1px; left: -1px; border-right: 0; border-bottom: 0; }
.top-right { top: -1px; right: -1px; border-left: 0; border-bottom: 0; }
.bottom-left { bottom: -1px; left: -1px; border-right: 0; border-top: 0; }
.bottom-right { bottom: -1px; right: -1px; border-left: 0; border-top: 0; }

/* 头部 HUD */
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
  box-shadow: 0 0 8px var(--accent);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.2); }
  100% { opacity: 1; transform: scale(1); }
}

.technical-label {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.7rem;
  color: var(--primary);
  letter-spacing: 1px;
}

/* 底部 HUD */
.frame-footer {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.mono-tag {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.65rem;
  color: var(--primary);
  background: rgba(99, 102, 241, 0.1);
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
}

.mermaid-offscreen {
  visibility: hidden;
  position: absolute;
  left: -9999px;
  top: -9999px;
}

.diagram-image-wrapper {
  background: white;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  background-image: 
    linear-gradient(rgba(99, 102, 241, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99, 102, 241, 0.03) 1px, transparent 1px);
  background-size: 20px 20px;
}

.diagram-image {
  max-width: 100%;
  max-height: 500px;
  border-radius: 2px;
}

.diagram-actions {
  display: flex;
  justify-content: flex-end;
  width: 100%;
}

.hud-btn-small {
  background: transparent;
  border: 1px solid var(--primary);
  color: var(--primary);
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.7rem;
  padding: 4px 12px;
  border-radius: 2px;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 1px;
}

.hud-btn-small:hover {
  background: var(--primary);
  color: white;
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.3);
}

.error-box-hud, .loading-box-hud {
  padding: 40px;
  border: 1px dashed var(--border);
  border-radius: 4px;
  text-align: center;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.8rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #64748B;
}

.error-box-hud {
  background: rgba(220, 38, 38, 0.05);
  border-color: rgba(220, 38, 38, 0.2);
  color: #DC2626;
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
  font-family: 'Share Tech Mono', monospace;
  font-size: 2rem;
  color: var(--primary);
  opacity: 0.3;
  margin-bottom: 12px;
}

.empty-frame p {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.8rem;
  color: #94A3B8;
  letter-spacing: 1px;
}

.compact .diagram-image { max-height: 240px; }
.compact .technical-frame {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
}
.compact .frame-corners,
.compact .frame-header,
.compact .frame-footer {
  display: none;
}
</style>