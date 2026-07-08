<template>
  <aside class="preview-panel" :class="{ disabled: !enabled }">

    <!-- Header -->
    <div class="preview-header">
      <div class="preview-header-left">
        <span class="preview-eyebrow">内容预演</span>
        <p class="preview-desc">模拟生成后打开此资源的阅读体验</p>
      </div>
      <span class="state-badge" :class="enabled ? 'state-on' : 'state-off'">
        <i></i>{{ enabled ? '已加入生成' : '未启用' }}
      </span>
    </div>

    <!-- Content preview window — simulates what PreviewDialog renders -->
    <div class="preview-window" :class="{ 'window-disabled': !enabled }">
      <!-- Browser-like title bar -->
      <div class="window-titlebar">
        <div class="titlebar-dots">
          <span></span><span></span><span></span>
        </div>
        <div class="titlebar-label" v-if="agentMeta">
          <component :is="agentMeta.icon" class="titlebar-icon" />
          <span>{{ agentMeta.name }}</span>
        </div>
        <span class="titlebar-tag">内容预演</span>
      </div>

      <!-- The actual per-agent content preview component -->
      <div class="preview-content-area" v-if="agentMeta">
        <!-- eslint-disable-next-line @typescript-eslint/no-explicit-any -->
        <component :is="agentMeta.view" :config="(activeConfig as any)" :topic="topic" />
      </div>
    </div>

    <!-- Parameter impact -->
    <div class="impact-section" v-if="enabled && impactLines.length">
      <div class="impact-header">
        <PhGear class="impact-icon" />
        <span>当前参数将影响</span>
      </div>
      <ul class="impact-list">
        <li v-for="line in impactLines" :key="line">
          <PhDotOutline weight="fill" class="dot-icon" />
          <span>{{ line }}</span>
        </li>
      </ul>
    </div>

    <!-- Footer note -->
    <div class="preview-note">
      <PhSparkle class="note-icon" />
      <span>内容结构示意 · 实际内容由多智能体完整生成</span>
    </div>
  </aside>
</template>

<script setup lang="ts">
// 引入 Vue 计算属性
import { computed } from 'vue'
// 引入预览面板所需的 Phosphor 图标
import {
  PhGear,
  PhSparkle,
  PhDotOutline,
  PhBooks as Books,
  PhCheckSquare as CheckSquare,
  PhCode as CodeIcon,
  PhFileText as FileText,
  PhFilmStrip as FilmStrip,
  PhVideoCamera as VideoCamera,
  PhPresentationChart as Presentation,
  PhShareNetwork as ShareNetwork,
} from '@phosphor-icons/vue'
// 引入智能体标识类型与配置联合类型
import type { ResourceAgentId } from '../../model/resource'
import type { AnyAgentConfigs } from '../../model/catalog'
// 引入各智能体对应的内容预览子组件
import Doc      from './preview/Doc.vue'
import MapView  from './preview/Map.vue'
import CodeView from './preview/Code.vue'
import QuizView from './preview/Quiz.vue'
import Read     from './preview/Read.vue'
import Slide    from './preview/Slide.vue'
import Video    from './preview/Video.vue'

// 组件入参：当前激活智能体、配置、是否启用、自然语言输入
const props = defineProps<{
  activeId: ResourceAgentId
  configs: AnyAgentConfigs
  enabled: boolean
  naturalInput?: string
}>()

// 预览主题：优先使用用户输入，缺省为示例主题
const topic = computed(() =>
  props.naturalInput?.trim() || '零基础学习 Python 多线程：底层原理与代码实践'
)

// 当前激活智能体的配置对象
const activeConfig = computed(() => props.configs[props.activeId])

// 根据激活智能体返回对应的名称、图标与预览子组件
const agentMeta = computed(() => ({
  content:  { name: '课程讲解文档',  icon: FileText,     view: Doc      },
  mindmap:  { name: '知识思维导图',  icon: ShareNetwork,  view: MapView  },
  code:     { name: '代码实操案例',  icon: CodeIcon,      view: CodeView },
  quiz:     { name: '随堂测验练习',  icon: CheckSquare,   view: QuizView },
  reading:  { name: '拓展阅读推荐',  icon: Books,         view: Read     },
  ppt:      { name: '演示幻灯课件',  icon: Presentation,  view: Slide    },
  cartoon:  { name: '动画讲解视频',  icon: FilmStrip,     view: Video    },
  video:    { name: '讲解视频',      icon: VideoCamera,   view: Video    },
})[props.activeId])

// 根据当前智能体配置生成“当前参数将影响”的中文说明列表
const impactLines = computed((): string[] => {
  const id = props.activeId
  const c  = props.configs

  if (id === 'content') {
    const sLines: Record<string, string> = {
      progressive:   '讲解从直观认识起步，逐步深入底层原理',
      summary_first: '先呈现全景结构图，再逐层进入关键细节',
      exam_points:   '内容优先覆盖高频考点与常见题型',
      case_driven:   '以真实问题为起点，在解题过程中引出概念',
    }
    const dLines: Record<string, string> = {
      quick:    '快速讲述模式，简洁覆盖核心要点',
      standard: '标准讲解深度，概念与推导均衡展开',
      deep:     '深入剖析底层机制，含学术层面论证',
    }
    const lines = [sLines[c.content.structure], dLines[c.content.depth_level]]
    if (c.content.include_examples) lines.push('穿插生动类比与案例辅助理解抽象理论')
    return lines.filter(Boolean) as string[]
  }
  if (id === 'mindmap') {
    const tLines: Record<string, string> = {
      knowledge_tree: '以核心知识树组织，梳理层级关系',
      exam_map:       '聚焦高频考点，节点标注考察频率',
      comparison_map: '横向对比维度，强化多概念辨析',
    }
    const lLines: Record<string, string> = {
      keyword:    '叶节点仅保留关键词，结构精炼',
      brief_note: '叶节点附简要注释，便于自查',
      annotated:  '叶节点含详细说明，适合深度复习',
    }
    const lines = [tLines[c.mindmap.map_type], `节点深度限制 ${c.mindmap.max_depth} 层`, lLines[c.mindmap.leaf_detail]]
    if (c.mindmap.show_relations) lines.push('用虚线标注跨分支的非层级关联')
    return lines.filter(Boolean) as string[]
  }
  if (id === 'code') {
    const langMap: Record<string, string> = { python: 'Python', java: 'Java', cpp: 'C++', c: 'C', go: 'Go', javascript: 'JavaScript', typescript: 'TypeScript' }
    const sLines: Record<string, string>  = { tutorial: '完整可运行代码，含逐步注释和运行说明', reference: '精简参考实现，聚焦核心逻辑和接口', challenge: '框架代码+提示引导，关键实现留空' }
    const lines = [`使用 ${langMap[c.code.programming_language] ?? c.code.programming_language} 生成实战案例`, sLines[c.code.output_style]]
    if (c.code.include_tests) lines.push('代码末尾附带 assert 或单元测试用例')
    return lines.filter(Boolean) as string[]
  }
  if (id === 'quiz') {
    const dLines: Record<string, string> = {
      basic:    '题目侧重概念巩固，难度友好',
      adaptive: '根据知识点自动调节难度梯度',
      exam:     '仿考研真题风格，高混淆度选项',
    }
    const types = (c.quiz.question_types as string[])
      .map((t) => ({ single: '单选', multiple: '多选', judge: '判断', fill: '填空' })[t])
      .filter(Boolean)
    return [
      dLines[c.quiz.difficulty_mode],
      `共 ${c.quiz.question_count} 道题，题型：${types.join(' / ')}`,
    ].filter(Boolean) as string[]
  }
  if (id === 'reading') {
    const cLines: Record<string, string> = {
      core: '精选最核心、最权威的 3-5 个资源',
      extended: '均衡推荐各类型延伸资料',
      broad: '广泛覆盖从入门到前沿的全链路',
    }
    const fLines: Record<string, string> = {
      textbook: '来源以经典教材和学术专著为主',
      engineering: '来源以技术博客和官方文档为主',
      research: '来源以 arXiv / IEEE 等学术论文为主',
    }
    return [cLines[c.reading.coverage], `最多推荐 ${c.reading.max_items} 篇`, fLines[c.reading.focus]].filter(Boolean) as string[]
  }
  if (id === 'ppt') {
    const sLines: Record<string, string> = {
      concept:     '以经典概念精讲结构组织幻灯片',
      case_driven: '以项目案例驱动每张幻灯片叙述',
      problem_led: '从启发性问题引出每个知识点',
      review:      '提炼考点要素，适合复习冲刺',
    }
    const dLines: Record<string, string> = {
      concise:  '极简排版，每页聚焦单一要点',
      standard: '标准教学密度，图文均衡',
      detailed: '图文丰富，覆盖完整推导与案例',
    }
    const focusLabels = (c.ppt.focus as string[])
      .map((f) => ({ core_concepts: '核心概念', cases: '典型案例', pitfalls: '避坑指南', derivation: '数学推导' })[f])
      .filter(Boolean)
    return [sLines[c.ppt.explanation_style], dLines[c.ppt.density], focusLabels.length ? `大纲重点：${focusLabels.join('、')}` : null].filter(Boolean) as string[]
  }
  if (id === 'cartoon') {
    const sLines: Record<string, string> = { diagram: '立体结构图解，3D 视角可视化', minimal: '简约扁平风格，清晰无干扰', dark_tech: '暗黑荧光科技感，适合算法 / 底层', chalkboard: '黑板粉笔风格，经典教学感' }
    const dLines: Record<string, string> = { overview: '快速概览，适合预习', standard: '标准讲解深度', deep: '深度剖析，适合复习强化' }
    const pLines: Record<string, string> = { fast: '快速演示节奏', normal: '正常讲解节奏', slow: '慢速细看节奏' }
    const vLines: Record<string, string> = { clean: '简洁画面，突出核心', balanced: '平衡画面，图文并重', detailed: '详细画面，含辅助标注' }
    return [sLines[c.cartoon.style], dLines[c.cartoon.depth], pLines[c.cartoon.pace], vLines[c.cartoon.visuals]].filter(Boolean) as string[]
  }
  if (id === 'video') {
    const sLines: Record<string, string> = { precision_light: '精确明亮演算视图，适合算法/代码', systems_dark: '深色系统图谱，适合操作系统/网络', editorial_classroom: '编辑式课堂表达，适合概念讲解' }
    const fLines: Record<string, string> = { concept: '侧重概念解释与定义', process: '侧重步骤追踪与状态变化', comparison: '侧重多维对比与辨析', practice: '侧重实战演示与代码演练' }
    const rLines: Record<string, string> = { '16:9': '横屏 1920×1080，传统播放', '9:16': '竖屏 1080×1920，短视频平台', '1:1': '方形 1080×1080，社交媒体' }
    return [sLines[c.video.style], fLines[c.video.focus], rLines[c.video.aspect_ratio]].filter(Boolean) as string[]
  }
  return []
})
</script>

<style scoped>
.preview-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  align-self: stretch;
}

/* ── Header ──────────────────────────────────── */
.preview-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.preview-header-left {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.preview-eyebrow {
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #758196;
}

.preview-desc {
  margin: 0;
  font-size: 11px;
  color: #9aa3b0;
  line-height: 1.5;
}

.state-badge {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  border: 1px solid;
}

.state-on { color: #24765b; background: #eef9f4; border-color: #cfeade; }
.state-on i {
  width: 6px; height: 6px; border-radius: 50%; background: #20b986; flex-shrink: 0;
  animation: pulse-dot 2s ease-in-out infinite;
}

.state-off { color: #8b95a4; background: #f1f3f6; border-color: #e0e5eb; }
.state-off i { width: 6px; height: 6px; border-radius: 50%; background: #aeb6c1; flex-shrink: 0; }

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.5; transform: scale(1.3); }
}

/* ── Preview window ───────────────────────────── */
.preview-window {
  border: 1px solid #dce2ea;
  border-radius: 14px;
  background: #ffffff;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(30, 50, 80, 0.07);
  transition: opacity 0.2s ease, filter 0.2s ease;
  flex: 1;
}

.window-disabled {
  opacity: 0.45;
  filter: grayscale(30%);
  pointer-events: none;
}

/* Title bar mimics a browser / app chrome */
.window-titlebar {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 38px;
  padding: 0 14px;
  border-bottom: 1px solid #edf0f4;
  background: #f7f9fb;
}

.titlebar-dots {
  display: flex;
  gap: 5px;
}
.titlebar-dots span {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #d5d9e0;
}
.titlebar-dots span:nth-child(1) { background: #f9897b; }
.titlebar-dots span:nth-child(2) { background: #f9c461; }
.titlebar-dots span:nth-child(3) { background: #5fc96e; }

.titlebar-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #2c3a4d;
  flex: 1;
}

.titlebar-icon {
  width: 13px;
  height: 13px;
  color: #2c8f87;
}

.titlebar-tag {
  font-size: 9px;
  font-weight: 700;
  color: #aab2be;
  letter-spacing: 0.06em;
}

.preview-content-area {
  overflow: hidden;
  max-height: 380px;
  overflow-y: auto;
}

/* ── Impact section ───────────────────────────── */
.impact-section {
  background: #f8fafc;
  border: 1px solid #edf1f5;
  border-radius: 11px;
  padding: 12px 14px;
}

.impact-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 9px;
  font-size: 9.5px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #7b8899;
}

.impact-icon { width: 12px; height: 12px; color: #2c8f87; }

.impact-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.impact-list li {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 11px;
  color: #4a5568;
  line-height: 1.55;
}

.dot-icon { width: 13px; height: 13px; color: #3a9b91; flex-shrink: 0; margin-top: 1px; }

/* ── Footer note ──────────────────────────────── */
.preview-note {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 2px 0 0;
  color: #9aa3b0;
  font-size: 10px;
}

.note-icon { width: 11px; height: 11px; color: #3c958c; }

/* ── Disabled ─────────────────────────────────── */
.preview-panel.disabled .impact-section,
.preview-panel.disabled .preview-header {
  opacity: 0.6;
}
</style>
