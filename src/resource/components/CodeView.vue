<template>
  <div class="code-resource" :class="{ compact }" @click="handleMessageClick">
    <div v-if="parsedData || markdownContent" class="technical-frame code-card-content">

      <!-- 顶部信息栏：简述 -->
      <div v-if="!compact && parsedData?.explanation" class="code-header-meta">
        <span class="code-summary-text">{{ parsedData.explanation }}</span>
      </div>

      <!-- 核心内容区：渲染 Markdown 或 纯代码 -->
      <div class="code-main-body">
        <div 
          v-if="displayMarkdown" 
          class="markdown-shell"
        >
          <MarkdownPreview :content="displayMarkdown" />
        </div>
        <div v-else-if="pureCode" class="pure-code-block">
          <pre><code :class="'language-' + (parsedData.language || 'text')">{{ pureCode }}</code></pre>
        </div>
        <div v-else-if="markdownContent" class="markdown-shell">
          <MarkdownPreview :content="markdownContent" />
        </div>
      </div>

      <!-- 底部辅助信息：复杂度、运行步骤、练习等 -->
      <div v-if="!compact && hasExtraInfo" class="code-footer-extras">
        <div class="footer-divider">
          <span class="divider-label">实现指标</span>
          <div class="divider-line"></div>
        </div>
        
        <div class="extras-grid">
          <!-- 复杂度 -->
          <div v-if="hasComplexity" class="extra-item complexity-info">
            <div class="extra-label"><el-icon><Timer /></el-icon> 复杂度分析</div>
            <div class="extra-content">
              <span v-if="parsedData.complexity.time">时间: <code>{{ parsedData.complexity.time }}</code></span>
              <span v-if="parsedData.complexity.space" class="ml-4">空间: <code>{{ parsedData.complexity.space }}</code></span>
            </div>
          </div>

          <!-- 避坑指南 -->
          <div v-if="parsedData.debug_tips?.length" class="extra-item tips-info">
            <div class="extra-label"><el-icon><Warning /></el-icon> 调试建议</div>
            <ul class="tips-list">
              <li v-for="(tip, idx) in parsedData.debug_tips" :key="idx">{{ tip }}</li>
            </ul>
          </div>
        </div>

        <!-- 扩展练习 -->
        <div v-if="parsedData.exercises?.length" class="extra-item exercises-info">
          <div class="extra-label"><el-icon><EditPen /></el-icon> 练习序列</div>
          <div class="exercises-container">
            <div v-for="(ex, idx) in parsedData.exercises" :key="idx" class="exercise-item">
              <span class="ex-num">{{ (Number(idx) + 1).toString().padStart(2, '0') }}</span>
              <span class="ex-text">{{ typeof ex === 'string' ? ex : ex.question || ex.title }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="frame-footer">
        <span class="mono-tag">可执行</span>
        <div class="footer-line"></div>
      </div>
    </div>
    
    <div v-else class="code-empty-hud">
      <div class="empty-frame">
        <div class="empty-icon">NULL</div>
        <p>未检测到代码内容</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, nextTick, watch } from 'vue'
import { Timer, Warning, EditPen } from '@element-plus/icons-vue'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import { ElMessage } from 'element-plus'
import MarkdownPreview from '@/components/common/MarkdownPreview.vue'
import { parseJsonObject, type ResourceArtifactLike } from './resourceViewUtils'

const props = defineProps<{
  resultData: ResourceArtifactLike
  compact?: boolean
}>()

// 提取并解包数据
const parsedData = computed(() => {
  if (!props.resultData) return null
  
  let raw = props.resultData
  // 如果是字符串，尝试解析
  if (typeof raw === 'string') {
    const p = parseJsonObject(raw)
    if (p) raw = p
    else return null // 无法解析的非 Markdown 字符串
  }

  let data = raw as Record<string, any>
  // 解包 resource 层级
  if (data.resource && typeof data.resource === 'object') {
    data = data.resource
  }

  // 解包 content 层级
  const content = data.content
  if (content && typeof content === 'object') {
    return content
  }
  
  // 尝试解析 content 字符串
  const pc = parseJsonObject(content)
  if (pc) return pc

  // 如果 data 本身看起来就像内容（例如有 code 或 language 字段）
  if (data.code || data.language) return data

  return null
})

// 决定显示 Markdown 还是纯代码
const displayMarkdown = computed(() => {
  const data = parsedData.value
  if (!data) return ''
  
  const codeContent = data.code || data.full_code || ''
  // 如果代码内容本身就是一份完整的 Markdown 文档
  if (typeof codeContent === 'string' && (codeContent.includes('# ') || codeContent.includes('## '))) {
    return codeContent
  }
  return ''
})

const pureCode = computed(() => {
  if (displayMarkdown.value) return ''
  const data = parsedData.value
  if (!data) return ''
  return data.code || data.full_code || ''
})

const markdownContent = computed(() => {
  if (parsedData.value) return '' // 已由 parsedData 处理
  if (typeof props.resultData === 'string') return props.resultData
  return ''
})

const hasExtraInfo = computed(() => {
  const d = parsedData.value
  if (!d) return false
  return !!(d.complexity?.time || d.complexity?.space || d.debug_tips?.length || d.exercises?.length)
})

const hasComplexity = computed(() => {
  const c = parsedData.value?.complexity
  return !!(c?.time || c?.space)
})

const performHighlight = async () => {
  await nextTick()
  if (typeof document !== 'undefined') {
    const preBlocks = document.querySelectorAll('.code-resource .pure-code-block pre')
    preBlocks.forEach((pre) => {
      const code = pre.querySelector('code')
      if (code) {
        hljs.highlightElement(code as HTMLElement)
        
        // 如果还没有复制按钮，则添加一个
        if (!pre.querySelector('.copy-code-btn')) {
          const btn = document.createElement('button')
          btn.className = 'copy-code-btn'
          btn.type = 'button'
          btn.innerText = '复制'
          btn.setAttribute('data-code', code.innerText)
          pre.appendChild(btn)
        }
      }
    })
  }
}

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success({ message: '代码已复制', plain: true })
  } catch (err) {
    ElMessage.error({ message: '复制失败，请重试', plain: true })
  }
}

const handleMessageClick = (e: MouseEvent) => {
  const target = e.target as HTMLElement
  if (target && target.classList.contains('copy-code-btn')) {
    const code = target.getAttribute('data-code')
    if (code) {
      copyToClipboard(code)
      const originalText = target.innerText
      target.innerText = '已复制'
      target.classList.add('copied')
      setTimeout(() => {
        target.innerText = originalText
        target.classList.remove('copied')
      }, 2000)
    }
  }
}

onMounted(performHighlight)
watch(parsedData, performHighlight)
watch(pureCode, performHighlight)
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

.code-resource {
  min-width: 0;
  width: 100%;
  --primary: #475569; /* Slate 600 */
  --bg: #FFFFFF;
  --fg: #334155; /* Slate 700 */
  --border: #E2E8F0;
  --accent: #6366F1; /* Indigo 500 */
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
  gap: 16px;
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
  margin-top: 16px;
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

.code-header-meta {
  margin-bottom: 4px;
}

.code-summary-text {
  font-family: 'Fira Code', monospace;
  font-size: 0.95rem;
  color: #475569;
  font-weight: 500;
  line-height: 1.5;
}

/* Markdown 与代码块样式 */
.markdown-shell {
  color: var(--fg);
  line-height: 1.65;
  overflow-wrap: anywhere;
  font-family: 'Fira Code', monospace;
}

/* 统一代码块外观 */
:deep(pre), .pure-code-block pre {
  border-radius: 8px;
  background: #FFFFFF !important;
  border: 1px solid #334155;
  padding: 20px;
  margin: 1.2em 0;
  overflow: auto;
  position: relative;
}

:deep(pre)::before, .pure-code-block pre::before {
  content: '•••';
  position: absolute;
  top: 8px;
  left: 12px;
  color: #334155;
  font-size: 14px;
  letter-spacing: 2px;
}

/* 复制按钮样式 */
:deep(.copy-code-btn) {
  position: absolute;
  top: 10px;
  right: 12px;
  background: rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.2);
  color: var(--primary);
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.65rem;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 10;
  opacity: 0;
}

:deep(pre:hover .copy-code-btn) {
  opacity: 1;
}

:deep(.copy-code-btn:hover) {
  background: var(--primary);
  color: white;
}

:deep(.copy-code-btn.copied) {
  background: var(--accent);
  color: white;
  border-color: var(--accent);
}

:deep(code), .pure-code-block code {
  font-family: 'Fira Code', monospace;
  font-size: 0.85em;
  background: transparent !important;
}

/* 优化代码高亮对比度，拒绝灰色和浅色 */
:deep(.hljs-comment), .pure-code-block .hljs-comment,
:deep(.hljs-quote), .pure-code-block .hljs-quote {
  color: #475569 !important; /* 深蓝灰色，提高对比度 */
  font-style: italic;
}

:deep(.hljs-keyword), .pure-code-block .hljs-keyword,
:deep(.hljs-selector-tag), .pure-code-block .hljs-selector-tag {
  color: #9333EA !important; /* 深紫色 */
  font-weight: bold;
}

:deep(.hljs-string), .pure-code-block .hljs-string,
:deep(.hljs-title), .pure-code-block .hljs-title,
:deep(.hljs-section), .pure-code-block .hljs-section,
:deep(.hljs-attribute), .pure-code-block .hljs-attribute,
:deep(.hljs-literal), .pure-code-block .hljs-literal,
:deep(.hljs-template-tag), .pure-code-block .hljs-template-tag,
:deep(.hljs-template-variable), .pure-code-block .hljs-template-variable,
:deep(.hljs-type), .pure-code-block .hljs-type,
:deep(.hljs-addition), .pure-code-block .hljs-addition {
  color: #0284C7 !important; /* 深蓝色 */
  font-weight: 600;
}

:deep(.hljs-string), .pure-code-block .hljs-string {
  color: #16A34A !important; /* 深绿色 */
  font-weight: normal;
}

:deep(.hljs-number), .pure-code-block .hljs-number,
:deep(.hljs-built_in), .pure-code-block .hljs-built_in,
:deep(.hljs-builtin-name), .pure-code-block .hljs-builtin-name,
:deep(.hljs-literal), .pure-code-block .hljs-literal {
  color: #D97706 !important; /* 深橙色 */
}

/* 页脚扩展信息 */
.code-footer-extras {
  margin-top: 16px;
  background: rgba(0, 0, 0, 0.03);
  padding: 20px;
  border-radius: 8px;
  border: 1px solid var(--border);
}

.footer-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.divider-label {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.75rem;
  color: var(--primary);
  letter-spacing: 1px;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, var(--border), transparent);
}

.extras-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
  margin-bottom: 20px;
}

.extra-item {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.extra-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.85rem;
  font-weight: bold;
  color: var(--primary);
  letter-spacing: 0.5px;
}

.extra-content {
  font-family: 'Fira Code', monospace;
  font-size: 0.9rem;
  color: #334155;
}

.extra-content code {
  background: rgba(0, 0, 0, 0.1);
  color: var(--primary);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.tips-list {
  margin: 0;
  padding-left: 20px;
  font-family: 'Fira Code', monospace;
  font-size: 0.88rem;
  color: #475569;
  line-height: 1.6;
}

.exercises-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 4px;
}

.exercise-item {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  background: white;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: 'Fira Code', monospace;
  font-size: 0.9rem;
  color: #334155;
  align-items: flex-start;
  transition: all 0.2s;
}

.exercise-item:hover {
  border-color: var(--primary);
  transform: translateX(4px);
}

.ex-num {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.8rem;
  color: var(--primary);
  background: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 2px;
  flex-shrink: 0;
}

.ml-4 { margin-left: 16px; }

/* 紧凑模式 */
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

.compact .markdown-shell {
  max-height: 180px;
  overflow: hidden;
  font-size: 0.86rem;
  mask-image: linear-gradient(to bottom, #000 70%, transparent 100%);
}

.code-empty-hud {
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

@media (max-width: 640px) {
  .extras-grid {
    grid-template-columns: 1fr;
  }
}
</style>
