# PPT JSON 简化协议

## ✅ 已删除的非核心字段

### 顶层字段
| 字段 | 原状态 | 现状态 | 说明 |
|------|--------|--------|------|
| `template_id` | 必需 | **可选** | 前端默认 `"teaching-lesson"` |
| `theme_id` | 必需 | **可选** | 前端默认 `"logic-blue"`，用户可通过UI选择 |

### 幻灯片字段
| 字段 | 原状态 | 现状态 | 说明 |
|------|--------|--------|------|
| `id` | 必需 | **可选** | 前端自动生成 `slide-${index + 1}` |
| `index` | 必需 | **可选** | 前端根据数组位置计算 |
| `layout` | 必需 | **可选** | 前端根据 `role` 自动推断 |
| `speaker_notes` | 必需 | **可选** | 非核心内容，不影响渲染 |

---

## 📋 后端最小化 JSON 示例

```json
{
  "title": "快速排序算法",
  "audience": "计算机大二学生",
  "slides": [
    {
      "role": "cover",
      "title": "快速排序：分而治之",
      "slots": {
        "main": [
          {
            "block_id": "intro",
            "type": "Text",
            "content": "通过分区实现高效排序",
            "format": "plain"
          }
        ]
      },
      "takeaway": "选基准、分区、递归"
    },
    {
      "role": "objectives",
      "title": "学习目标",
      "slots": {
        "featured": [
          {
            "block_id": "obj-keypoint",
            "type": "KeyPoint",
            "label": "核心",
            "content": "掌握快速排序的核心思想"
          }
        ],
        "cards": [
          {
            "block_id": "obj-cards",
            "type": "CardList",
            "cards": [
              {"title": "理解分区", "content": "掌握分区操作的执行过程"},
              {"title": "分析复杂度", "content": "理解时间空间复杂度分析"}
            ]
          }
        ]
      },
      "takeaway": "三分区、两递归、一基准"
    }
  ]
}
```

---

## 🔧 前端自动补全逻辑

前端提供 `normalizePptDocument()` 函数，自动补全缺失字段：

```typescript
import { normalizePptDocument } from '@/features/resource/components/ppt-engine/types/ppt'

// 后端返回的简化 JSON
const backendData = {
  title: "...",
  audience: "...",
  slides: [...]
}

// 前端自动补全
const fullData = normalizePptDocument(backendData)
// 结果:
// {
//   template_id: "teaching-lesson",  // 自动补全
//   theme_id: "logic-blue",          // 自动补全
//   title: "...",
//   audience: "...",
//   slides: [
//     {
//       id: "slide-1",              // 自动生成
//       index: 0,                   // 自动计算
//       role: "cover",
//       layout: "HeroCover",        // 根据 role 推断
//       ...
//     }
//   ]
// }
```

---

## 📊 Role → Layout 自动映射

| Role | 自动推断的 Layout |
|------|------------------|
| `cover` | `HeroCover` |
| `objectives` | `CardCluster` |
| `prerequisite` | `DualPane` |
| `problem_intro` | `DualPane` |
| `roadmap` | `KnowledgeMap` |
| `concept` | `DualPane` |
| `analogy` | `DualPane` |
| `principle_diagram` | `DiagramFocus` |
| `process_demo` | `FlowCanvas` |
| `mechanism_breakdown` | `TriplePane` |
| `concept_relation` | `DiagramFocus` |
| `concept_compare` | `CompareTable` |
| `misconception` | `DualPane` |
| `summary` | `CardCluster` |
| `next_steps` | `DualPane` |
| `algorithm_visualization` | `FlowCanvas` |
| `code_walkthrough` | `DualPane` |
| `architecture_diagram` | `DiagramFocus` |

---

## ✅ 后端只需关注的核心内容

1. **必须提供**：
   - `title` - 课件标题
   - `audience` - 受众描述
   - `slides[].role` - 决定布局模板
   - `slides[].title` - 每页标题
   - `slides[].slots` - 内容块（**最重要**）
   - `slides[].takeaway` - 要点总结

2. **可选提供**：
   - `theme_id` - 主题ID（用户选择，前端传入）
   - `slides[].subtitle` - 副标题
   - `slides[].speaker_notes` - 演讲者备注

3. **无需关心**：
   - ❌ 幻灯片ID和序号
   - ❌ 布局类型（由 role 决定）
   - ❌ 模板ID（固定值）
