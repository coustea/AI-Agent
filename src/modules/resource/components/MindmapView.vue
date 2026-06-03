<template>
  <div class="mindmap-resource" :class="{ compact }">
    <div v-if="markdownContent" class="technical-frame mindmap-container">


      <div ref="markmapRef" class="markmap-shell"></div>

      <div class="frame-footer">
        <span class="mono-tag">导图同步中</span>
        <div class="footer-line"></div>
      </div>
    </div>
    <div v-else class="mindmap-empty-hud">
      <div class="empty-frame">
        <div class="empty-icon">NULL</div>
        <p>NO_TOPOLOGY_DATA_FOUND</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, nextTick } from 'vue'
import { Transformer } from 'markmap-lib'
import { Markmap } from 'markmap-view'
import { parseJsonObject, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

const markmapRef = ref<HTMLElement | null>(null)
let markmapInstance: Markmap | null = null

const transformer = new Transformer()

// 提取 Markdown 内容
const markdownContent = computed<string>(() => {
  if (!props.resultData) return ''
  if (typeof props.resultData === 'string') return props.resultData

  // 1. 如果有包裹 resource 结构
  let data: Record<string, any> = props.resultData as Record<string, any>
  if (data.resource && typeof data.resource === 'object') {
    data = data.resource
  }

  // 2. 从 data 或 data.content 中提取 markdown 字符串
  const content = data.content
  
  // 2.1 content 是字符串（可能是 JSON 字符串或直接的 Markdown）
  if (typeof content === 'string' && content.trim()) {
    // 尝试解析 JSON 字符串
    const parsed = parseJsonObject(content)
    if (parsed) {
      if (parsed.markdown_content) return parsed.markdown_content
      if (parsed.outline) return parsed.outline
      if (parsed.source) return parsed.source
    }
    // 如果不是 JSON，直接返回（可能是直接的 Markdown）
    return content
  }

  // 2.2 content 是对象（后端返回的嵌套结构）
  if (typeof content === 'object' && content !== null) {
    if (content.markdown_content) return content.markdown_content
    if (content.outline) return content.outline
    if (content.source) return content.source
    if (content.markdown) return content.markdown
  }

  // 3. 回退策略：直接在 data 第一层找
  if (data.markdown_content) return data.markdown_content
  if (data.outline) return data.outline
  if (data.source) return data.source
  if (data.markdown) return data.markdown

  return ''
})

// 预处理内容，兼容 LLM 误生成的 Mermaid mindmap 语法
const preprocessContent = (text: string): string => {
  let content = text.trim()
  // 移除可能存在的代码块包裹
  if (content.startsWith('```')) {
    content = content.replace(/^```[a-z]*\n/i, '').replace(/\n```$/, '').trim()
  }

  if (content.startsWith('mindmap')) {
    const lines = content.split('\n')
    const mdLines: string[] = []
    let rootFound = false
    let baseIndent = 0

    for (let line of lines) {
      if (line.trim() === 'mindmap') continue
      if (!line.trim()) continue

      const match = line.match(/^(\s*)(.*)/)
      const rawIndent = match?.[1] || ''
      const rawNodeText = match?.[2] || ''
      if (rawNodeText.trim()) {
        const indent = rawIndent.length
        // 移除 Mermaid 形状符号如 (( )), [ ], {{ }} 等
        let nodeText = rawNodeText.replace(/^[\(\[\{]+|[\)\]\}]+$/g, '').trim()

        if (!rootFound) {
          mdLines.push(`# ${nodeText}`)
          rootFound = true
          baseIndent = indent
        } else {
          // 启发式层级计算：假设至少每级缩进 2 个空格
          let depth = Math.floor((indent - baseIndent) / 2)
          if (depth <= 0) depth = 1
          
          if (depth === 1) {
            mdLines.push(`## ${nodeText}`)
          } else {
            const listIndent = '  '.repeat(depth - 2)
            mdLines.push(`${listIndent}- ${nodeText}`)
          }
        }
      }
    }
    return mdLines.join('\n')
  }

  return text
}

// 渲染 markmap
const renderMarkmap = async (rawContent: string) => {
  if (!rawContent.trim() || !markmapRef.value) return
  
  const content = preprocessContent(rawContent)

  // Wait for container to have layout so SVG can resolve relative lengths
  await nextTick()

  try {
    const { root } = transformer.transform(content)

    // 创建 SVG 容器
    let svg = markmapRef.value.querySelector('svg')
    if (!svg) {
      svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
      // Use explicit pixel width from container to avoid "Could not resolve relative length" error
      const containerWidth = markmapRef.value.clientWidth || 800
      const height = props.compact ? 240 : 500
      svg.setAttribute('width', String(containerWidth))
      svg.setAttribute('height', String(height))
      svg.style.width = `${containerWidth}px`
      svg.style.height = `${height}px`
      markmapRef.value.appendChild(svg)
    }

    if (!markmapInstance) {
      markmapInstance = new Markmap(svg, {
        autoFit: true,
        duration: 400,
        maxWidth: 320,
        paddingX: 30, // 增加水平间距
        style: (id) => `
          .${id}-g {
            font-family: 'Fira Code', monospace;
            font-size: 15px;
          }
          .${id}-g foreignObject {
            overflow: visible;
          }
          .${id}-g .markmap-node text {
            fill: #000000;
          }
          .${id}-g .markmap-link {
            stroke: #000000;
            stroke-width: 1.5px;
            opacity: 0.6;
          }
          .${id}-g .markmap-node circle {
            fill: #FFFFFF;
            stroke: #000000;
            stroke-width: 2px;
          }
        `
      })
    }

    markmapInstance.setData(root)
  } catch (err) {
    console.error('[MindmapResourceView] Markmap render error:', err)
    
    const errorMsg = err instanceof Error ? err.message : String(err)
    if (markmapRef.value) {
      markmapRef.value.innerHTML = `<pre class="markmap-error">SYSTEM_RENDER_FAIL: ${errorMsg}</pre>`
    }
  }
}

watch(markdownContent, (content) => {
  renderMarkmap(content)
}, { immediate: true })

onMounted(() => {
  if (markdownContent.value) {
    renderMarkmap(markdownContent.value)
  }
})
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

.mindmap-resource {
  width: 100%;
  --primary: #000000;
  --bg: #FFFFFF;
  --fg: #000000;
  --border: #E5E7EB;
  --accent: #000000;
}

/* 技术框架样式 */
.technical-frame {
  position: relative;
  background: var(--bg);
  border: none;
  border-radius: 4px;
  padding: 24px 32px 32px;
  box-shadow: none;
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
  box-shadow: none;
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
  background: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 2px;
}

.footer-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, var(--border), transparent);
}

.markmap-shell {
  width: 100%;
  min-height: 420px;
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
  background-image: none;
  background-size: 32px 32px;
}

.markmap-shell :deep(svg) {
  width: 100%;
  height: 500px;
}

.markmap-shell :deep(.markmap-node) {
  cursor: pointer;
  transition: opacity 0.2s;
}

.markmap-shell :deep(.markmap-node:hover) {
  opacity: 0.8;
}

.markmap-shell :deep(.markmap-node[data-depth="0"] text) {
  font-size: 1.3rem;
  font-weight: 700;
  fill: var(--primary) !important;
}

.markmap-error {
  padding: 20px;
  background: rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  color: #000000;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.85rem;
}

.compact .technical-frame {
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
}
.compact .frame-header,
.compact .frame-footer {
  display: none;
}
.compact .markmap-shell {
  min-height: 240px;
  background-size: 20px 20px;
}

.compact .markmap-shell :deep(svg) {
  height: 240px;
}

.mindmap-empty-hud {
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

@media (max-width: 768px) {
  .markmap-shell { min-height: 320px; }
  .markmap-shell :deep(svg) { height: 320px; }
  .compact .markmap-shell { min-height: 180px; }
  .compact .markmap-shell :deep(svg) { height: 180px; }
}
</style>
