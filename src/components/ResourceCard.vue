<template>
  <el-card shadow="hover" class="resource-card slide-up-anim">
    <div class="res-header">
      <div class="res-type">
        <el-icon><component :is="meta.icon" /></el-icon>
        {{ meta.name }}
      </div>
      <el-tag size="small" type="success" effect="dark" round>
        <el-icon><Check /></el-icon>
      </el-tag>
    </div>

    <div class="res-body">
      <div class="ai-badge" v-if="badgeText">{{ badgeText }}</div>

      <!-- File Preview -->
      <div v-if="hasFile" class="file-preview-container">
        
        <video 
          v-if="fileCategory === 'video'" 
          :src="fileUrl" 
          controls 
          class="media-preview"
        ></video>
        
        <el-image 
          v-else-if="fileCategory === 'image'" 
          :src="fileUrl" 
          fit="contain" 
          :preview-src-list="[fileUrl]" 
          class="media-preview" 
        />
        
        <iframe 
          v-else-if="fileCategory === 'html'" 
          :src="fileUrl" 
          class="html-preview" 
          frameborder="0"
        ></iframe>
        
        <div v-else-if="fileCategory === 'ppt'" class="doc-placeholder ppt-style">
          <el-icon class="doc-icon"><DataBoard /></el-icon>
          <span class="doc-name">{{ fileName }}</span>
          <span class="doc-desc">PPT演示文稿已生成完毕</span>
        </div>
        
        <div v-else class="doc-placeholder">
          <el-icon class="doc-icon"><Document /></el-icon>
          <span class="doc-name">{{ fileName }}</span>
          <span class="doc-desc">文件资源已就绪</span>
        </div>

      </div>

      <!-- Text Content Preview -->
      <div v-if="hasTextContent" class="content-preview-container" :class="{'mt-12': hasFile}">
        
        <div 
          v-if="['content', 'reading', 'ppt'].includes(agentId)" 
          class="markdown-preview markdown-body" 
          v-html="parseMarkdown(resultData.content || resultData.outline)"
        ></div>
        
        <div v-else-if="agentId === 'code'" class="code-block">
          <pre><code>{{ extractCode(resultData.content) }}</code></pre>
        </div>
        
        <div v-else-if="agentId === 'mindmap'" class="code-block">
          <pre><code>{{ resultData.agent_output || resultData.content }}</code></pre>
        </div>
        
        <div v-else-if="agentId === 'quiz'" class="quiz-preview">
          <div class="q-item" v-for="(q, i) in (resultData.questions || []).slice(0, 2)" :key="i">
            <strong>Q{{ Number(i) + 1 }}:</strong> {{ q.stem }}
          </div>
          <div class="q-more" v-if="resultData.questions?.length > 2">
            ...等共 {{ resultData.questions.length }} 道专项练习
          </div>
        </div>
        
        <div v-else class="mock-text">{{ resultData.content || resultData.agent_output }}</div>

      </div>

      <!-- Mock Preview -->
      <div v-if="!hasFile && !hasTextContent" class="mock-preview-container">
        <div v-if="['content', 'ppt', 'reading'].includes(agentId)" class="mock-text">
          <p>《{{ topic }}》的相关内容已由 AI 智能体根据您的学习习惯定制生成完毕。</p>
        </div>
        <div v-else-if="agentId === 'mindmap'" class="mock-code">
          ROOT: {{ topic }}<br />├── 核心概念解析<br />└── 易错点靶向图谱
        </div>
        <div v-else-if="agentId === 'code'" class="mock-code">
          # 为您生成的实操沙盒代码<br />def handle_logic():<br />    pass
        </div>
        <div v-else-if="agentId === 'quiz'" class="mock-text">
          包含单选、多选与深度解析的专属题库构建完毕。
        </div>
        <div v-else class="mock-text">多模态数据处理完毕，可投入学习使用。</div>
      </div>
    </div>

    <div class="res-footer">
      <el-button type="primary" plain size="small" @click="handlePreview">
        查看完整内容
      </el-button>
      <el-button size="small" @click="handleDownload">导出资源</el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Check, DataBoard, Document } from '@element-plus/icons-vue'
import { marked } from 'marked'
import 'github-markdown-css/github-markdown-light.css'
import { recordLearningEvent } from '@/api/ai'

// ================= 定义外部传入的 Props =================
const props = defineProps({
  agentId: { type: String, required: true },
  meta: { type: Object, required: true }, // 包含 name, icon 等元数据
  topic: { type: String, default: '默认课题' },
  gap: { type: String, default: '' },
  resultData: { type: Object, default: null } // 后端真实返回的 Artifact 数据
})

const emit = defineEmits(['preview'])

// ================= 1. 文件路径嗅探与分类核心逻辑 =================
// 自动兼容后端的字段名：file_url / fileUrl / path
const fileUrl = computed(() => {
  if (!props.resultData) return ''
  return props.resultData.file_url || props.resultData.fileUrl || props.resultData.path || ''
})

const hasFile = computed(() => !!fileUrl.value)

const hasTextContent = computed(() => {
  if (!props.resultData) return false
  return !!(props.resultData.content || props.resultData.outline || props.resultData.agent_output || props.resultData.questions)
})

// 提取文件后缀名
const fileExt = computed(() => {
  if (!fileUrl.value) return ''
  // 处理带参数的 URL，如 .mp4?token=xxx
  const cleanUrl = fileUrl.value.split('?')[0]
  const parts = cleanUrl.split('.')
  return parts.length > 1 ? parts.pop()?.toLowerCase() || '' : ''
})

// 提取文件名
const fileName = computed(() => {
  if (!fileUrl.value) return '未命名文件'
  const cleanUrl = fileUrl.value.split('?')[0]
  const parts = cleanUrl.split('/')
  return parts.pop() || '未命名文件'
})

// 文件分类器
const fileCategory = computed(() => {
  const ext = fileExt.value
  if (['mp4', 'webm', 'ogg', 'mov'].includes(ext)) return 'video'
  if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) return 'image'
  if (['html', 'htm'].includes(ext)) return 'html'
  if (['pptx', 'ppt'].includes(ext)) return 'ppt'
  if (['pdf'].includes(ext)) return 'pdf'
  return 'other'
})

// ================= 2. 文本辅助与渲染逻辑 =================
const gapSummary = computed(() => {
  return props.gap.length > 8 ? props.gap.substring(0, 8) : props.gap
})

// 动态计算卡片顶部的 AI 角标文案
const badgeText = computed(() => {
  if (hasFile.value) {
    if (fileCategory.value === 'video') return '🎬 视频渲染完成'
    if (fileCategory.value === 'image') return '🖼️ 配图生成完成'
    if (fileCategory.value === 'html') return '🕸️ 动态拓扑图谱已就绪'
    if (fileCategory.value === 'ppt') return '📊 演示文稿已生成'
  }
  if (props.agentId === 'mindmap') return '🧠 知识拓扑提取完成'
  if (props.agentId === 'code' && props.resultData?.detected_language) return `💻 语言: ${props.resultData.detected_language}`
  if (props.agentId === 'quiz') return `📝 已生成 ${props.resultData?.questions?.length || '专属'} 道练习`
  return `✨ 已针对痛点 [${gapSummary.value}...] 优化`
})

const parseMarkdown = (text: string) => {
  if (!text) return ''
  return marked.parse(text)
}

const extractCode = (text: string) => {
  if (!text) return ''
  return text.replace(/```[\w]*\n/g, '').replace(/```/g, '')
}

// ================= 3. 操作事件 =================
const handlePreview = () => {
  recordLearningEvent({
    event_type: 'resource_viewed',
    course: props.topic,
    topic: props.meta.name,
    metadata: { agent: props.agentId },
  }).catch((err) => {
    console.warn('[ResourceCard] record learning event failed:', err)
  })
  emit('preview', {
    agentId: props.agentId,
    title: props.meta.name,
    hasFile: hasFile.value,
    fileUrl: fileUrl.value,
    fileCategory: fileCategory.value,
    resultData: props.resultData
  })
}

const handleDownload = () => {
  if (hasFile.value) {
    window.open(fileUrl.value, '_blank')
  } else if (hasTextContent.value || props.resultData) {
    let content = ''
    let ext = '.txt'
    
    if (props.agentId === 'quiz' || typeof props.resultData === 'object' && !props.resultData.content && !props.resultData.agent_output) {
      content = JSON.stringify(props.resultData, null, 2)
      ext = '.json'
    } else {
      content = props.resultData.content || props.resultData.agent_output || String(props.resultData)
      ext = '.md'
    }
    
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${props.meta.name}_${props.agentId}${ext}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }
}
</script>

<style scoped>
.resource-card {
  display: flex; flex-direction: column; border-radius: 12px; border: 1px solid #E2E8F0;
  height: 100%; transition: transform 0.2s, box-shadow 0.2s;
}
.resource-card:hover { transform: translateY(-4px); box-shadow: 0 10px 20px rgba(0,0,0,0.05); }

.res-header {
  padding: 16px; border-bottom: 1px solid #F1F5F9; display: flex; justify-content: space-between; align-items: center;
}
.res-type { font-weight: 700; font-size: 1.05rem; display: flex; align-items: center; gap: 8px; color: #0F172A; }

.res-body { padding: 20px; flex: 1; display: flex; flex-direction: column; overflow: auto; }

.ai-badge {
  display: inline-block; padding: 4px 8px; background: #EEF2FF; color: #4F46E5; 
  border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-bottom: 12px; align-self: flex-start; flex-shrink: 0;
}

/* ================= 1. 文件展示区样式 ================= */
.file-preview-container {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: #F8FAFC; border-radius: 8px; overflow: hidden; border: 1px solid #E2E8F0;
  min-height: 150px; flex-shrink: 0;
}
.media-preview {
  width: 100%; height: 100%; max-height: 160px; object-fit: contain; background: #0F172A;
}
.html-preview {
  width: 100%; height: 160px; border: none; background: #FFFFFF; pointer-events: none; /* 防止卡片内部误触 iframe 滚动 */
}
.doc-placeholder {
  display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; text-align: center;
}
.doc-icon { font-size: 48px; color: #94A3B8; margin-bottom: 12px; }
.ppt-style .doc-icon { color: #F26B50; /* PPT 专属橘红色 */ }
.doc-name { font-size: 0.9rem; font-weight: 600; color: #1E293B; margin-bottom: 4px; word-break: break-all; padding: 0 10px;}
.doc-desc { font-size: 0.8rem; color: #64748B; }

/* ================= 2. 文本/代码/文档样式 ================= */
.content-preview-container, .mock-preview-container { display: flex; flex-direction: column; flex-shrink: 0; }
.mt-12 { margin-top: 12px; }
.mock-text p { margin: 0; font-size: 0.9rem; color: #475569; line-height: 1.6; }

.code-block, .mock-code {
  background: #1E293B; border-radius: 8px; padding: 12px; color: #E2E8F0; 
  font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; overflow: hidden; 
  text-overflow: ellipsis; max-height: 120px;
}
.code-block pre { margin: 0; white-space: pre-wrap; }

.quiz-preview { font-size: 0.85rem; color: #334155; line-height: 1.6; }
.q-item { margin-bottom: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.q-more { color: #94A3B8; font-style: italic; margin-top: 4px; }

/* Markdown 预览定制 (截断并使用渐变遮罩) */
.markdown-preview {
  font-size: 0.85rem; color: #334155; max-height: 120px; overflow: hidden;
  mask-image: linear-gradient(to bottom, black 60%, transparent 100%);
}
.markdown-preview :deep(h1), .markdown-preview :deep(h2), .markdown-preview :deep(h3) { font-size: 1rem; margin-top: 0; border: none; }

.res-footer { padding: 12px 16px; border-top: 1px solid #F1F5F9; display: flex; justify-content: flex-end; gap: 10px; margin-top: auto; }

@keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
.slide-up-anim { animation: slideUp 0.5s cubic-bezier(0.2, 0.8, 0.2, 1) forwards; }
</style>
