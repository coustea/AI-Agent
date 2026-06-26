<template>
  <div class="ppt-preview">
    <!-- 幻灯片缩略图列表 -->
    <div class="slide-thumbnails" v-if="slides.length > 0">
      <div
        v-for="(slide, index) in slides"
        :key="slide.id || index"
        class="thumbnail-item"
        :class="{ active: currentSlideIndex === index }"
        @click="currentSlideIndex = index"
      >
        <div class="thumbnail-number">{{ index + 1 }}</div>
        <div class="thumbnail-title">{{ slide.title }}</div>
      </div>
    </div>

    <!-- 当前幻灯片预览区域 -->
    <div class="slide-preview-area">
      <div class="slide-container" ref="slideContainerRef">
        <div class="slide-canvas" :style="slideCanvasStyle">
          <!-- 简化的幻灯片预览：显示标题和关键信息 -->
          <div class="slide-header">
            <h2 class="slide-title">{{ currentSlide?.title }}</h2>
            <p class="slide-subtitle" v-if="currentSlide?.subtitle">{{ currentSlide.subtitle }}</p>
          </div>
          <div class="slide-content">
            <div class="block-preview" v-for="(blocks, slotName) in currentSlide?.slots" :key="slotName">
              <div class="slot-label">{{ slotName }}</div>
              <div class="block-item" v-for="block in blocks" :key="block.block_id">
                <div class="block-type">{{ block.type }}</div>
                <div class="block-content">{{ getBlockPreview(block) }}</div>
              </div>
            </div>
          </div>
          <div class="slide-footer">
            <span class="slide-role">{{ currentSlide?.role }}</span>
            <span class="slide-takeaway">{{ currentSlide?.takeaway }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 导出按钮 -->
    <div class="export-actions">
      <el-button type="primary" :loading="isExporting" @click="handleExport">
        <el-icon v-if="!isExporting" style="margin-right: 4px;"><Download /></el-icon>
        {{ isExporting ? '导出中...' : '下载 PPTX' }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElButton, ElIcon, ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import type { PPTDocument, SlideBlock } from '../../types/ppt'
import { renderPPT, downloadPPTX } from '../index'

const props = defineProps<{
  documentData: PPTDocument
}>()

const slides = computed(() => props.documentData.slides || [])
const currentSlideIndex = ref(0)
const currentSlide = computed(() => slides.value[currentSlideIndex.value])
const isExporting = ref(false)

// 幻灯片画布样式（16:9 比例）
const slideCanvasStyle = computed(() => ({
  width: '100%',
  aspectRatio: '16 / 9',
}))

// 获取 Block 预览内容
function getBlockPreview(block: SlideBlock): string {
  switch (block.type) {
    case 'Text':
      return block.content.slice(0, 100) + (block.content.length > 100 ? '...' : '')
    case 'KeyPoint':
      return `[${block.label}] ${block.content.slice(0, 50)}...`
    case 'Callout':
      return `${block.intent}: ${block.content.slice(0, 50)}...`
    case 'Diagram':
      return `图解: ${block.nodes.length} 个节点, ${block.edges.length} 条边`
    case 'FlowChart':
      return `流程图: ${block.steps.length} 个步骤`
    case 'Table':
      return `表格: ${block.columns.length} 列 x ${block.rows.length} 行`
    case 'CardList':
      return `卡片列表: ${block.cards.length} 个卡片`
    case 'Formula':
      return block.formula
    case 'CodeSnippet':
      return `${block.language}: ${block.code.slice(0, 50)}...`
    default:
      return '未知类型'
  }
}

// 导出 PPTX
async function handleExport() {
  isExporting.value = true
  try {
    const pptx = renderPPT(props.documentData)
    const filename = `${props.documentData.title || 'presentation'}.pptx`
    await downloadPPTX(pptx, filename)
    ElMessage.success('PPTX 导出成功')
  } catch (error) {
    console.error('Export error:', error)
    ElMessage.error('导出失败，请重试')
  } finally {
    isExporting.value = false
  }
}

// 当 slides 变化时重置索引
watch(slides, () => {
  currentSlideIndex.value = 0
})
</script>

<style scoped>
.ppt-preview {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: #f8fafc;
  border-radius: 8px;
  overflow: hidden;
}

.slide-thumbnails {
  display: flex;
  gap: 8px;
  padding: 12px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  overflow-x: auto;
}

.thumbnail-item {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.thumbnail-item:hover {
  background: #e2e8f0;
}

.thumbnail-item.active {
  background: #2563eb;
  color: white;
  border-color: #2563eb;
}

.thumbnail-number {
  font-size: 12px;
  font-weight: 600;
  opacity: 0.7;
}

.thumbnail-title {
  font-size: 13px;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.slide-preview-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: auto;
}

.slide-container {
  width: 100%;
  max-width: 960px;
  display: flex;
  justify-content: center;
}

.slide-canvas {
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 40px;
  display: flex;
  flex-direction: column;
}

.slide-header {
  margin-bottom: 24px;
  border-bottom: 2px solid #2563eb;
  padding-bottom: 16px;
}

.slide-title {
  font-size: 28px;
  font-weight: 700;
  color: #1e3a5f;
  margin: 0 0 8px 0;
}

.slide-subtitle {
  font-size: 16px;
  color: #64748b;
  margin: 0;
}

.slide-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.block-preview {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px;
}

.slot-label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.block-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #e2e8f0;
}

.block-item:last-child {
  border-bottom: none;
}

.block-type {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  color: #2563eb;
  background: #dbeafe;
  padding: 2px 8px;
  border-radius: 4px;
}

.block-content {
  font-size: 13px;
  color: #1e293b;
  line-height: 1.5;
}

.slide-footer {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.slide-role {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
}

.slide-takeaway {
  font-size: 12px;
  color: #64748b;
  font-style: italic;
}

.export-actions {
  display: flex;
  justify-content: center;
  padding: 16px;
  background: #ffffff;
  border-top: 1px solid #e2e8f0;
}
</style>