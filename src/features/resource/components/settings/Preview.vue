<template>
  <aside class="preview-panel" :class="{ disabled: !enabled }">
    <header>
      <div>
        <span class="eyebrow">内容预演</span>
        <h4>生成后大致会是这样</h4>
        <p>根据当前参数模拟内容结构，实际结果会由智能体完整生成。</p>
      </div>
      <span class="state"><i></i>{{ enabled ? '已加入生成' : '未启用' }}</span>
    </header>

    <section class="canvas">
      <div class="canvas-bar">
        <div>
          <component :is="meta.icon" />
          <span>{{ meta.name }}</span>
        </div>
        <span>结构预演</span>
      </div>
      <component
        :is="meta.view"
        :config="activeConfig"
        :topic="topic"
      />
    </section>

    <footer>
      <Sparkle />
      <span>切换左侧参数，预演内容会同步调整</span>
    </footer>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  PhBooks as Books,
  PhCheckSquare as CheckSquare,
  PhCode as CodeIcon,
  PhFileText as FileText,
  PhFilmStrip as FilmStrip,
  PhPresentationChart as Presentation,
  PhShareNetwork as ShareNetwork,
  PhSparkle as Sparkle,
} from '@phosphor-icons/vue'
import type { ResourceAgentId } from '../../model/resource'
import type { AnyAgentConfigs } from '../../model/catalog'
import Doc from './preview/Doc.vue'
import MapView from './preview/Map.vue'
import CodeView from './preview/Code.vue'
import QuizView from './preview/Quiz.vue'
import Read from './preview/Read.vue'
import Slide from './preview/Slide.vue'
import Video from './preview/Video.vue'

const props = defineProps<{
  activeId: ResourceAgentId
  configs: AnyAgentConfigs
  enabled: boolean
  naturalInput?: string
}>()

const meta = computed(() => ({
  content: { name: '课程讲解', icon: FileText, view: Doc },
  mindmap: { name: '思维导图', icon: ShareNetwork, view: MapView },
  code: { name: '代码实操', icon: CodeIcon, view: CodeView },
  quiz: { name: '随堂练习', icon: CheckSquare, view: QuizView },
  reading: { name: '拓展阅读', icon: Books, view: Read },
  ppt: { name: '演示幻灯', icon: Presentation, view: Slide },
  cartoon: { name: '动画讲解', icon: FilmStrip, view: Video },
})[props.activeId])

const topic = computed(() => (
  props.naturalInput?.trim() || '零基础学习 Python 多线程：底层原理与代码实践'
))
const activeConfig = computed(() => props.configs[props.activeId])
</script>

<style scoped>
.preview-panel {
  display: flex;
  min-width: 0;
  align-self: stretch;
  flex-direction: column;
  padding: 26px;
  border: 1px solid #e3e9ef;
  border-radius: 18px;
  background: #f6f8fb;
}

header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.eyebrow {
  color: #758196;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .14em;
}

h4 {
  margin: 6px 0;
  color: #1f2c3d;
  font-size: 17px;
  letter-spacing: -.02em;
}

p {
  max-width: 410px;
  margin: 0;
  color: #7c8798;
  font-size: 12px;
  line-height: 1.6;
}

.state {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
  padding: 6px 9px;
  border: 1px solid #cfeade;
  border-radius: 999px;
  color: #24765b;
  background: #eef9f4;
  font-size: 10px;
  font-weight: 700;
}

.state i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #20b986;
}

.disabled .state {
  border-color: #e0e5eb;
  color: #8b95a4;
  background: #f1f3f6;
}

.disabled .state i {
  background: #aeb6c1;
}

.canvas {
  min-height: 460px;
  margin-top: 20px;
  overflow: hidden;
  border: 1px solid #e1e6ec;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 12px 32px rgb(35 53 73 / 7%);
}

.canvas-bar {
  display: flex;
  height: 46px;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid #edf0f3;
}

.canvas-bar div {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #26384a;
  font-size: 11px;
  font-weight: 750;
}

.canvas-bar svg {
  width: 15px;
  height: 15px;
  color: #2c8f87;
}

.canvas-bar > span {
  color: #98a1ae;
  font-size: 9px;
  font-weight: 750;
  letter-spacing: .08em;
}

footer {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 13px;
  color: #7b8796;
  font-size: 10px;
}

footer svg {
  width: 13px;
  height: 13px;
  color: #3c958c;
}

@media (max-width: 720px) {
  .preview-panel { padding: 18px; }
  header { flex-direction: column; }
  .canvas { min-height: 410px; }
}
</style>
