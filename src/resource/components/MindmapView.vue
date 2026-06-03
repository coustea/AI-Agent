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
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { parseJsonObject, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

type MarkmapInstance = {
  setData: (root: unknown) => void
}

type MarkmapRuntime = {
  transformer: { transform: (content: string) => { root: unknown } }
  createMarkmap: (svg: SVGElement) => MarkmapInstance
}

const markmapRef = ref<HTMLElement | null>(null)
let markmapInstance: MarkmapInstance | null = null
let markmapRuntimePromise: Promise<MarkmapRuntime> | null = null

const loadMarkmapRuntime = async (): Promise<MarkmapRuntime> => {
  if (!markmapRuntimePromise) {
    markmapRuntimePromise = Promise.all([
      import('markmap-lib'),
      import('markmap-view'),
    ]).then(([markmapLib, markmapView]) => {
      const transformer = new markmapLib.Transformer()

      const createMarkmap = (svg: SVGElement): MarkmapInstance => {
        const instance = new markmapView.Markmap(svg, {
          autoFit: true,
          duration: 400,
          maxWidth: 320,
          paddingX: 30,
          style: (id: string) => `
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
          `,
        })
        return {
          setData: (root: unknown) => { instance.setData(root as any) },
        }
      }

      return { transformer, createMarkmap } as MarkmapRuntime
    })
  }

  return markmapRuntimePromise
}

const markdownContent = computed<string>(() => {
  if (!props.resultData) return ''
  if (typeof props.resultData === 'string') return props.resultData

  let data: Record<string, any> = props.resultData as Record<string, any>
  if (data.resource && typeof data.resource === 'object') {
    data = data.resource
  }

  const content = data.content

  if (typeof content === 'string' && content.trim()) {
    const parsed = parseJsonObject(content)
    if (parsed) {
      if (parsed.markdown_content) return parsed.markdown_content
      if (parsed.outline) return parsed.outline
      if (parsed.source) return parsed.source
    }

    return content
  }

  if (typeof content === 'object' && content !== null) {
    if (content.markdown_content) return content.markdown_content
    if (content.outline) return content.outline
    if (content.source) return content.source
    if (content.markdown) return content.markdown
  }

  if (data.markdown_content) return data.markdown_content
  if (data.outline) return data.outline
  if (data.source) return data.source
  if (data.markdown) return data.markdown

  return ''
})

const preprocessContent = (text: string): string => {
  let content = text.trim()
  if (content.startsWith('```')) {
    content = content.replace(/^```[a-z]*\n/i, '').replace(/\n```$/, '').trim()
  }

  if (!content.startsWith('mindmap')) {
    return text
  }

  const lines = content.split('\n')
  const markdownLines: string[] = []
  let rootFound = false
  let baseIndent = 0

  for (const line of lines) {
    if (line.trim() === 'mindmap' || !line.trim()) continue

    const match = line.match(/^(\s*)(.*)/)
    const rawIndent = match?.[1] || ''
    const rawNodeText = match?.[2] || ''
    if (!rawNodeText.trim()) continue

    const indent = rawIndent.length
    const nodeText = rawNodeText.replace(/^[\(\[\{]+|[\)\]\}]+$/g, '').trim()

    if (!rootFound) {
      markdownLines.push(`# ${nodeText}`)
      rootFound = true
      baseIndent = indent
      continue
    }

    let depth = Math.floor((indent - baseIndent) / 2)
    if (depth <= 0) depth = 1

    if (depth === 1) {
      markdownLines.push(`## ${nodeText}`)
      continue
    }

    const listIndent = '  '.repeat(depth - 2)
    markdownLines.push(`${listIndent}- ${nodeText}`)
  }

  return markdownLines.join('\n')
}

const renderMarkmap = async (rawContent: string) => {
  if (!rawContent.trim() || !markmapRef.value) return

  const content = preprocessContent(rawContent)
  await nextTick()

  try {
    const { transformer, createMarkmap } = await loadMarkmapRuntime()
    const { root } = transformer.transform(content)

    let svg = markmapRef.value.querySelector('svg')
    if (!svg) {
      svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
      const containerWidth = markmapRef.value.clientWidth || 800
      const height = props.compact ? 240 : 500
      svg.setAttribute('width', String(containerWidth))
      svg.setAttribute('height', String(height))
      svg.style.width = `${containerWidth}px`
      svg.style.height = `${height}px`
      markmapRef.value.appendChild(svg)
    }

    if (!markmapInstance) {
      markmapInstance = createMarkmap(svg)
    }

    markmapInstance.setData(root)
  } catch (err) {
    console.error('[MindmapResourceView] Markmap render error:', err)

    const errorMessage = err instanceof Error ? err.message : String(err)
    if (markmapRef.value) {
      markmapRef.value.innerHTML = `<pre class="markmap-error">SYSTEM_RENDER_FAIL: ${errorMessage}</pre>`
    }
  }
}

watch(markdownContent, (content) => {
  void renderMarkmap(content)
}, { immediate: true })

onMounted(() => {
  if (markdownContent.value) {
    void renderMarkmap(markdownContent.value)
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
