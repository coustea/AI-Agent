# PPT渲染与导出使用指南

## 🎯 快速开始

### 1. 基础渲染

```vue
<template>
  <PptistRenderer :documentData="pptDocument" :editMode="false" />
</template>

<script setup lang="ts">
import PptistRenderer from '@/features/resource/components/ppt-engine/PptistRenderer.vue'

const pptDocument = {
  template_id: 'teaching-lesson',
  theme_id: 'paper-light',
  title: '我的PPT',
  slides: [/* ... */]
}
</script>
```

### 2. 导出PPTX

**方式一：通过组件按钮（推荐）**

组件已集成导出按钮，用户点击"📥 PPTX"按钮即可导出。

**方式二：编程式导出**

```typescript
import { exportToPptx } from '@/features/resource/components/ppt-engine/utils/exportUtils'
import { convertToPptistSlides } from '@/features/resource/components/ppt-engine/converters/slideConverter'

// 1. 转换数据
const slides = convertToPptistSlides(pptDocument)

// 2. 导出PPTX
await exportToPptx(slides, '文件名')
```

### 3. 导出PDF

```typescript
import { exportToPdf } from '@/features/resource/components/ppt-engine/utils/exportUtils'

await exportToPdf(slides, '文件名')
// 提示：使用浏览器打印功能，选择"打印到PDF"
```

## 🔧 在ResourceDetail.vue中集成

```vue
<template>
  <div class="resource-detail">
    <!-- 其他内容 -->

    <!-- PPT区域 -->
    <div v-if="resource.ppt_document" class="ppt-viewer">
      <PptistRenderer
        :documentData="resource.ppt_document"
        :editMode="false"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import PptistRenderer from '@/features/resource/components/ppt-engine/PptistRenderer.vue'
</script>
```

## 📊 数据格式

参考测试数据：
- `test-data-linkedlist.json` - 链表示例
- `test-data-binarytree.json` - 二叉树示例

## 🎨 支持的内容类型

✅ Text（文本）
✅ KeyPoint（要点）
✅ CardList（卡片列表）
✅ CodeSnippet（代码高亮）
✅ Diagram（数据结构图）
✅ FlowChart（流程图）
✅ Table（表格）
✅ Callout（提示框）
✅ Formula（公式）

## 📝 注意事项

- PPTX导出将HTML转为文本，复杂样式可能简化
- PDF导出使用浏览器打印功能
- 建议按需加载PPTist组件（动态导入）