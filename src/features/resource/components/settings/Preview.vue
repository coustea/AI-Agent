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
        <div class="titlebar-label">
          <component :is="agentMeta.icon" class="titlebar-icon" />
          <span>{{ agentMeta.name }}</span>
        </div>
        <span class="titlebar-tag">内容预演</span>
      </div>

      <!-- The actual per-agent content preview component -->
      <div class="preview-content-area">
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
import { computed } from 'vue'
import {
  PhGear,
  PhSparkle,
  PhDotOutline,
  PhBooks as Books,
  PhCheckSquare as CheckSquare,
  PhCode as CodeIcon,
  PhFileText as FileText,
  PhFilmStrip as FilmStrip,
  PhPresentationChart as Presentation,
  PhShareNetwork as ShareNetwork,
} from '@phosphor-icons/vue'
import type { ResourceAgentId } from '../../model/resource'
import type { AnyAgentConfigs } from '../../model/catalog'
import Doc      from './preview/Doc.vue'
import MapView  from './preview/Map.vue'
import CodeView from './preview/Code.vue'
import QuizView from './preview/Quiz.vue'
import Read     from './preview/Read.vue'
import Slide    from './preview/Slide.vue'
import Video    from './preview/Video.vue'

const props = defineProps<{
  activeId: ResourceAgentId
  configs: AnyAgentConfigs
  enabled: boolean
  naturalInput?: string
}>()

const topic = computed(() =>
  props.naturalInput?.trim() || '零基础学习 Python 多线程：底层原理与代码实践'
)

const activeConfig = computed(() => props.configs[props.activeId])

// Agent metadata
const agentMeta = computed(() => ({
  content:  { name: '课程讲解文档',  icon: FileText,     view: Doc      },
  mindmap:  { name: '知识思维导图',  icon: ShareNetwork,  view: MapView  },
  code:     { name: '代码实操案例',  icon: CodeIcon,      view: CodeView },
  quiz:     { name: '随堂测验练习',  icon: CheckSquare,   view: QuizView },
  reading:  { name: '拓展阅读推荐',  icon: Books,         view: Read     },
  ppt:      { name: '演示幻灯课件',  icon: Presentation,  view: Slide    },
  cartoon:  { name: '动画讲解视频',  icon: FilmStrip,     view: Video    },
})[props.activeId])

// ── Impact lines ──────────────────────────────────────────────────────────────
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
    const dLines: Record<string, string>  = { beginner: '入门级代码，注释详尽', intermediate: '进阶难度，含设计模式或并发场景', advanced: '挑战级，涵盖复杂算法与性能优化' }
    const tLines: Record<string, string>  = { basic_demo: '基础演示模板，逐行可读', algorithm_template: '核心算法模板，可直接复用', debug_demo: '有意内置 Bug，引导定位修复' }
    return [
      `使用 ${langMap[c.code.programming_language] ?? c.code.programming_language} 生成实战案例`,
      dLines[c.code.difficulty],
      tLines[c.code.case_type],
    ].filter(Boolean) as string[]
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
    const dLines: Record<string, string> = {
      course_extended: '推荐与课程内容直接衔接的延伸资料',
      engineering:     '侧重工业界落地实践与案例研究',
      frontier:        '精选顶会 / 期刊前沿论文',
    }
    const fLines: Record<string, string> = {
      textbook:    '来源以经典教材和学术专著为主',
      engineering: '来源以技术博客和官方文档为主',
      paper:       '来源以 arXiv / IEEE 等学术论文为主',
    }
    return [dLines[c.reading.reading_depth], `最多推荐 ${c.reading.max_items} 篇`, fLines[c.reading.focus]].filter(Boolean) as string[]
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
    const sLines: Record<string, string> = { diagram: '立体结构图解，3D 视角可视化', minimal: '简约扁平风格，清晰无干扰', dark_tech: '暗黑荧光科技感，适合算法 / 底层' }
    const fLines: Record<string, string> = { concept: '以概念原理解释为核心叙事', process: '逐帧追踪执行过程与状态变化', comparison: '多维对比辨析，强化理解差异', practice: '真实代码演练，边写边讲' }
    return [sLines[c.cartoon.style], fLines[c.cartoon.focus], `视频时长上限 ${c.cartoon.video_length_seconds} 秒`].filter(Boolean) as string[]
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
