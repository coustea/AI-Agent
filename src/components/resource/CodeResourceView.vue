<template>
  <div class="code-resource" :class="{ compact }">
    <div v-if="parsedData" class="code-card-content">
      <!-- 顶部信息栏：语言与简述 -->
      <div v-if="!compact" class="code-header-meta">
        <el-tag v-if="parsedData.language" type="primary" effect="dark" class="lang-tag">
          {{ parsedData.language.toUpperCase() }}
        </el-tag>
        <span v-if="parsedData.explanation" class="code-summary-text">{{ parsedData.explanation }}</span>
      </div>

      <!-- 核心内容区：渲染 Markdown 或 纯代码 -->
      <div class="code-main-body">
        <div 
          v-if="displayMarkdown" 
          class="markdown-body markdown-shell" 
          v-html="renderMarkdown(displayMarkdown)"
        ></div>
        <div v-else-if="pureCode" class="pure-code-block">
          <pre><code :class="'language-' + (parsedData.language || 'text')">{{ pureCode }}</code></pre>
        </div>
      </div>

      <!-- 底部辅助信息：复杂度、运行步骤、练习等 -->
      <div v-if="!compact && hasExtraInfo" class="code-footer-extras">
        <el-divider content-position="left">实操要点</el-divider>
        
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
            <div class="extra-label"><el-icon><Warning /></el-icon> 调试与避坑</div>
            <ul class="tips-list">
              <li v-for="(tip, idx) in parsedData.debug_tips" :key="idx">{{ tip }}</li>
            </ul>
          </div>
        </div>

        <!-- 扩展练习 -->
        <div v-if="parsedData.exercises?.length" class="extra-item exercises-info">
          <div class="extra-label"><el-icon><EditPen /></el-icon> 巩固练习</div>
          <div class="exercises-container">
            <div v-for="(ex, idx) in parsedData.exercises" :key="idx" class="exercise-item">
              <span class="ex-num">{{ Number(idx) + 1 }}</span>
              <span class="ex-text">{{ typeof ex === 'string' ? ex : ex.question || ex.title }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else-if="markdownContent" class="markdown-body markdown-shell" v-html="renderMarkdown(markdownContent)"></div>
    
    <div v-else class="code-empty">
      <el-empty description="暂未收到可展示的代码内容" :image-size="60" />
    </div>
  </div>
</template>

<script setup lang="ts">
import 'github-markdown-css/github-markdown-light.css'
import { computed, onMounted, nextTick, watch } from 'vue'
import { Timer, Warning, EditPen } from '@element-plus/icons-vue'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css' // 使用亮色主题
import { renderMarkdown, parseJsonObject, type ResourceArtifactLike } from './resourceViewUtils'

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
  hljs.highlightAll()
}

onMounted(performHighlight)
watch(parsedData, performHighlight)
watch(markdownContent, performHighlight)
</script>

<style scoped>
.code-resource {
  min-width: 0;
  width: 100%;
}

.code-card-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.code-header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.lang-tag {
  font-weight: 800;
  letter-spacing: 0.5px;
}

.code-summary-text {
  font-size: 0.95rem;
  color: #475569;
  font-weight: 500;
}

.markdown-shell {
  color: #1e293b;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.markdown-shell :deep(pre) {
  border-radius: 8px;
  background: #ffffff; /* 修改为白色背景 */
  padding: 16px;
  margin: 16px 0;
  border: 1px solid #e2e8f0; /* 添加边框 */
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

.markdown-shell :deep(code) {
  white-space: pre-wrap;
  font-family: 'Fira Code', 'Cascadia Code', Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace;
  color: #1e293b;
}

.pure-code-block pre {
  margin: 0;
  padding: 16px;
  background: #ffffff; /* 修改为白色背景 */
  border-radius: 8px;
  overflow: auto;
  border: 1px solid #e2e8f0; /* 添加边框 */
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

.pure-code-block code {
  color: #1e293b;
  font-family: 'Fira Code', 'Cascadia Code', monospace;
  font-size: 0.9rem;
}

.code-footer-extras {
  margin-top: 8px;
  background: #f8fafc;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.extras-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-bottom: 16px;
}

.extra-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.extra-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  font-weight: 700;
  color: #6366f1;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.extra-content {
  font-size: 0.9rem;
  color: #334155;
}

.extra-content code {
  background: #eef2ff;
  color: #4f46e5;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.tips-list {
  margin: 0;
  padding-left: 18px;
  font-size: 0.88rem;
  color: #475569;
  line-height: 1.6;
}

.exercises-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
}

.exercise-item {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  font-size: 0.9rem;
  color: #334155;
  align-items: flex-start;
}

.ex-num {
  width: 20px;
  height: 20px;
  background: #e0e7ff;
  color: #6366f1;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 800;
  flex-shrink: 0;
  margin-top: 1px;
}

.ml-4 { margin-left: 16px; }

.compact .markdown-shell {
  max-height: 180px;
  overflow: hidden;
  font-size: 0.86rem;
  mask-image: linear-gradient(to bottom, #000 70%, transparent 100%);
}

.compact .markdown-shell :deep(h1),
.compact .markdown-shell :deep(h2),
.compact .markdown-shell :deep(h3) {
  margin-top: 0;
  border-bottom: 0;
  font-size: 1rem;
}

.code-empty {
  padding: 20px;
  border: 1px dashed #cbd5e1;
  border-radius: 12px;
  background: #f8fafc;
}

@media (max-width: 640px) {
  .extras-grid {
    grid-template-columns: 1fr;
  }
}
</style>