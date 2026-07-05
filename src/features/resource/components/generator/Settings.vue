<template>
  <div class="phase-view personalize-view">
    <div class="personalize-container">
      <!-- Page Title Header -->
      <div class="view-header">
        <span class="settings-eyebrow">Orchestrator Settings</span>
        <h2>多智能体参数定制</h2>
        <p>配置各智能体的加工参数，定制设置将直接作为最高优先级指令传入生成系统。</p>
      </div>

      <!-- Scenario Selector Cards -->
      <div class="scenario-selector-v2">
        <div
          v-for="s in scenarioOptions"
          :key="s.value"
          :class="['scenario-card', { active: learningScenario === s.value }]"
          @click="selectScenario(s.value)"
        >
          <div class="scenario-icon-box">{{ s.icon }}</div>
          <div class="scenario-info">
            <span class="s-name">{{ s.name }}</span>
            <span class="s-desc">{{ getScenarioDesc(s.value) }}</span>
          </div>
          <div class="active-dot" v-if="learningScenario === s.value"></div>
        </div>
      </div>

      <!-- Configurator Workspace Layout -->
      <div class="workspace-card shadow-sm border border-slate-100 rounded-3xl bg-white overflow-hidden mt-6">
        <AgentTabs
          :active-id="activeAgentId"
          :enabled-ids="enabledAgentIds"
          :configs="localConfigs"
          @select="activeAgentId = $event"
          @toggle="toggleAgent"
        />

        <!-- 2-Column Split Workspace Body -->
        <div class="workspace-body grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 min-h-[500px]">
          <!-- Left Column: Parameter Configurator form (7 columns span) -->
          <div class="lg:col-span-7 flex flex-col justify-between">
            <div class="form-content-area">
              <div class="flex items-center justify-between mb-6 border-b border-slate-100 pb-4">
                <div class="flex items-center gap-2">
                  <div class="w-8 h-8 rounded-lg flex items-center justify-center" :class="getActiveAgentMeta.colorClass">
                    <component :is="getActiveAgentMeta.icon" class="w-4 h-4" />
                  </div>
                  <h3 class="text-base font-extrabold text-slate-800 tracking-wide m-0">{{ getActiveAgentMeta.name }} 参数配置</h3>
                </div>
                <div class="status-indicator-badge flex items-center gap-2">
                  <span class="w-2.5 h-2.5 rounded-full" :class="isAgentEnabled(activeAgentId) ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300'"></span>
                  <span class="text-xs font-bold" :class="isAgentEnabled(activeAgentId) ? 'text-emerald-700' : 'text-slate-400'">
                    {{ isAgentEnabled(activeAgentId) ? '就绪 / 正常工作' : '暂停 / 未启用该资源' }}
                  </span>
                </div>
              </div>

              <!-- Switch warning info if disabled -->
              <div v-if="!isAgentEnabled(activeAgentId)" class="p-4 bg-slate-50 border border-slate-200 rounded-2xl flex flex-col gap-1.5 mb-6 animate-fade">
                <span class="text-sm font-bold text-slate-700">🚫 该智能体当前处于未启用状态</span>
                <span class="text-xs text-slate-400 leading-relaxed">您可以点击该标签页左侧的拨动开关启用它，启用后系统将协同该智能体生成并输出对应的“{{ getActiveAgentOutputLabel }}”。</span>
              </div>

              <div class="configs-inputs-grid grid grid-cols-1 md:grid-cols-2 gap-6" :class="{ 'opacity-50 pointer-events-none filter grayscale-[30%]': !isAgentEnabled(activeAgentId) }">
                
                <!-- CONTENT Agent parameters -->
                <template v-if="activeAgentId === 'content'">
                  <div class="ctrl-group">
                    <label>讲解结构</label>
                    <select v-model="localConfigs.content.structure">
                      <option value="progressive">渐进式引导 (Progressive)</option>
                      <option value="summary_first">先总后分 (Summary First)</option>
                      <option value="exam_points">考点驱动 (Exam Points)</option>
                      <option value="case_driven">案例驱动 (Case Driven)</option>
                    </select>
                    <p class="ctrl-helper">控制文本讲述的排版结构，满足不同思维偏好的学习场景</p>
                  </div>

                  <div class="ctrl-group">
                    <label>讲解深度</label>
                    <div class="flex gap-1.5 bg-slate-50 p-1.5 rounded-xl border border-slate-100">
                      <button
                        v-for="opt in [
                          { label: '快速', value: 'quick' },
                          { label: '标准', value: 'standard' },
                          { label: '深度', value: 'deep' }
                        ]"
                        :key="opt.value"
                        type="button"
                        class="flex-1 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                        :class="localConfigs.content.depth_level === opt.value ? 'bg-white text-slate-900 shadow-sm border border-slate-200' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                        @click="localConfigs.content.depth_level = opt.value as any"
                      >
                        {{ opt.label }}
                      </button>
                    </div>
                    <p class="ctrl-helper">调节生成文本的概念展开细度与底层学术证明的详尽水平</p>
                  </div>

                  <div class="ctrl-group">
                    <label>侧重模式</label>
                    <select v-model="localConfigs.content.focus_mode">
                      <option value="weak_points">薄弱点巩固 (Weak Points)</option>
                      <option value="key_concepts">核心概念 (Key Concepts)</option>
                      <option value="full_coverage">全景覆盖 (Full Coverage)</option>
                    </select>
                    <p class="ctrl-helper">指引智能体在加工时聚焦的核心关注面，或执行自适应全覆盖</p>
                  </div>

                  <div class="ctrl-switch-v2 flex justify-between items-center py-2 bg-slate-50/40 px-4 rounded-2xl border border-slate-100/50 mt-1">
                    <div class="sw-info flex flex-col gap-0.5">
                      <span class="sw-label">丰富生活化示例</span>
                      <span class="sw-desc">使用生动的类比和案例辅助理解抽象理论</span>
                    </div>
                    <label class="relative inline-flex items-center cursor-pointer select-none">
                      <input type="checkbox" v-model="localConfigs.content.include_examples" class="sr-only peer" />
                      <div class="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-main"></div>
                    </label>
                  </div>
                </template>

                <!-- MINDMAP Agent parameters -->
                <template v-if="activeAgentId === 'mindmap'">
                  <div class="ctrl-group">
                    <label>导图生成策略</label>
                    <select v-model="localConfigs.mindmap.map_type">
                      <option value="knowledge_tree">核心知识树 (Knowledge Tree)</option>
                      <option value="exam_map">高频考点图 (Exam Map)</option>
                      <option value="comparison_map">对比复习图 (Comparison)</option>
                    </select>
                    <p class="ctrl-helper">思维导图的组织骨架，对比复习图将强化横向对比维度</p>
                  </div>

                  <div class="ctrl-group">
                    <div class="slider-label-row flex justify-between items-center mb-1">
                      <label class="m-0">节点发散层级</label>
                      <span class="text-xs font-bold text-primary-main"><b>{{ localConfigs.mindmap.max_depth }}</b> 层</span>
                    </div>
                    <input
                      type="range"
                      v-model.number="localConfigs.mindmap.max_depth"
                      :min="2"
                      :max="5"
                      :step="1"
                      class="w-full"
                    />
                    <p class="ctrl-helper">限制思维树向下延伸的最深层级，数值越小越精炼</p>
                  </div>

                  <div class="ctrl-group">
                    <label>叶节点粒度</label>
                    <div class="flex gap-1.5 bg-slate-50 p-1.5 rounded-xl border border-slate-100">
                      <button
                        v-for="opt in [
                          { label: '关键词', value: 'keyword' },
                          { label: '简要', value: 'brief_note' },
                          { label: '详注', value: 'annotated' }
                        ]"
                        :key="opt.value"
                        type="button"
                        class="flex-1 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                        :class="localConfigs.mindmap.leaf_detail === opt.value ? 'bg-white text-slate-900 shadow-sm border border-slate-200' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                        @click="localConfigs.mindmap.leaf_detail = opt.value as any"
                      >
                        {{ opt.label }}
                      </button>
                    </div>
                    <p class="ctrl-helper">调节叶节点附加详细注释的冗余程度，详注占用更大篇幅</p>
                  </div>

                  <div class="ctrl-switch-v2 flex justify-between items-center py-2 bg-slate-50/40 px-4 rounded-2xl border border-slate-100/50 mt-1">
                    <div class="sw-info flex flex-col gap-0.5">
                      <span class="sw-label">绘制关联横向线</span>
                      <span class="sw-desc">用虚线标明非层级关系的分支关联</span>
                    </div>
                    <label class="relative inline-flex items-center cursor-pointer select-none">
                      <input type="checkbox" v-model="localConfigs.mindmap.show_relations" class="sr-only peer" />
                      <div class="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-main"></div>
                    </label>
                  </div>
                </template>

                <!-- CODE Agent parameters -->
                <template v-if="activeAgentId === 'code'">
                  <div class="ctrl-group">
                    <label>开发语言</label>
                    <select v-model="localConfigs.code.programming_language">
                      <option value="python">Python 3</option>
                      <option value="java">Java (JDK 17)</option>
                      <option value="cpp">C++ (C++17)</option>
                      <option value="c">C (C11)</option>
                      <option value="go">Go (Golang)</option>
                      <option value="javascript">JavaScript (ES6)</option>
                      <option value="typescript">TypeScript</option>
                    </select>
                    <p class="ctrl-helper">选择要生成的实战案例目标编程语言环境</p>
                  </div>

                  <div class="ctrl-group">
                    <label>代码难度等级</label>
                    <div class="flex gap-1.5 bg-slate-50 p-1.5 rounded-xl border border-slate-100">
                      <button
                        v-for="opt in [
                          { label: '入门', value: 'beginner' },
                          { label: '进阶', value: 'intermediate' },
                          { label: '挑战', value: 'advanced' }
                        ]"
                        :key="opt.value"
                        type="button"
                        class="flex-1 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                        :class="localConfigs.code.difficulty === opt.value ? 'bg-white text-slate-900 shadow-sm border border-slate-200' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                        @click="localConfigs.code.difficulty = opt.value as any"
                      >
                        {{ opt.label }}
                      </button>
                    </div>
                    <p class="ctrl-helper">控制实例的代码行数规模与算法/并发设计复杂度</p>
                  </div>

                  <div class="ctrl-group">
                    <label>案例风格</label>
                    <select v-model="localConfigs.code.case_type">
                      <option value="basic_demo">基础演示模版 (Demo)</option>
                      <option value="algorithm_template">核心算法模板 (Algorithm)</option>
                      <option value="debug_demo">调试纠错练习 (Debug)</option>
                    </select>
                    <p class="ctrl-helper">案例的形式。纠错练习将有意埋入Bug，指导学员纠错</p>
                  </div>

                  <div class="ctrl-group">
                    <label>讲解侧重点</label>
                    <select v-model="localConfigs.code.focus">
                      <option value="syntax">语法要素解析 (Syntax)</option>
                      <option value="application">工程实践应用 (Practice)</option>
                      <option value="debugging">代码逻辑调试 (Logics)</option>
                    </select>
                    <p class="ctrl-helper">控制生成的代码解析注释侧重的视角与分析详尽度</p>
                  </div>
                </template>

                <!-- QUIZ Agent parameters -->
                <template v-if="activeAgentId === 'quiz'">
                  <div class="ctrl-group">
                    <label>出题难度策略</label>
                    <select v-model="localConfigs.quiz.difficulty_mode">
                      <option value="basic">概念基础巩固 (Basic)</option>
                      <option value="adaptive">自适应智能测试 (Adaptive)</option>
                      <option value="exam">硬核考研真题 (Exam Hard)</option>
                    </select>
                    <p class="ctrl-helper">测试强度的定位。考研真题策略将生成具备高混淆度的硬核题目</p>
                  </div>

                  <div class="ctrl-group">
                    <div class="slider-label-row flex justify-between items-center mb-1">
                      <label class="m-0">测验题目数量</label>
                      <span class="text-xs font-bold text-primary-main"><b>{{ localConfigs.quiz.question_count }}</b> 题</span>
                    </div>
                    <input
                      type="range"
                      v-model.number="localConfigs.quiz.question_count"
                      :min="3"
                      :max="10"
                      :step="1"
                      class="w-full"
                    />
                    <p class="ctrl-helper">设定试卷容量，不宜过多，保障自适应加工的敏捷性</p>
                  </div>

                  <div class="ctrl-group">
                    <label>拟合考试风格</label>
                    <select v-model="localConfigs.quiz.exam_style">
                      <option value="school">普通期末考试 (Final Exam)</option>
                      <option value="postgrad">名校考研试卷 (Postgraduate)</option>
                      <option value="certification">行业专业认证 (Certification)</option>
                      <option value="interview">大厂技术面试 (Tech Interview)</option>
                    </select>
                    <p class="ctrl-helper">决定出题话术和题干场景拟合，大厂面试将偏向真实工程场景</p>
                  </div>

                  <div class="ctrl-group">
                    <label>允许考核题型 (多选)</label>
                    <div class="grid grid-cols-2 gap-2 mt-1">
                      <button
                        v-for="opt in [
                          { label: '单选题', value: 'single' },
                          { label: '多选题', value: 'multiple' },
                          { label: '判断题', value: 'judge' },
                          { label: '填空题', value: 'fill' }
                        ]"
                        :key="opt.value"
                        type="button"
                        :class="localConfigs.quiz.question_types.includes(opt.value as any) ? 'bg-emerald-50 text-emerald-800 border-emerald-300' : 'bg-white text-slate-400 hover:text-slate-600'"
                        @click="toggleQuestionType(opt.value)"
                      >
                        {{ opt.label }}
                        <span v-if="localConfigs.quiz.question_types.includes(opt.value as any)" class="text-[9px]">✔</span>
                      </button>
                    </div>
                  </div>
                </template>

                <!-- READING Agent parameters -->
                <template v-if="activeAgentId === 'reading'">
                  <div class="ctrl-group">
                    <label>拓展阅读方向</label>
                    <select v-model="localConfigs.reading.reading_depth">
                      <option value="course_extended">课程延展学习 (Extended)</option>
                      <option value="engineering">工业界落地实践 (Engineering)</option>
                      <option value="frontier">前沿学术论文 (Frontier)</option>
                    </select>
                    <p class="ctrl-helper">挑选推荐资料的目标深度。前沿学术将推荐最新頂会/期刊论文</p>
                  </div>

                  <div class="ctrl-group">
                    <div class="slider-label-row flex justify-between items-center mb-1">
                      <label class="m-0">最大推荐文献数</label>
                      <span class="text-xs font-bold text-primary-main">最多 <b>{{ localConfigs.reading.max_items }}</b> 篇</span>
                    </div>
                    <input
                      type="range"
                      v-model.number="localConfigs.reading.max_items"
                      :min="2"
                      :max="6"
                      :step="1"
                      class="w-full"
                    />
                    <p class="ctrl-helper">规定拓展阅读列表的最大条数，避免认知负荷过载</p>
                  </div>

                  <div class="ctrl-group">
                    <label>语言偏好</label>
                    <select v-model="localConfigs.reading.language_preference">
                      <option value="chinese">中文文献优先 (Chinese)</option>
                      <option value="both">中英双语混合 (Bilingual)</option>
                      <option value="english">仅限英文学术 (English Only)</option>
                    </select>
                    <p class="ctrl-helper">指导智能体检索资料的目标语言</p>
                  </div>

                  <div class="ctrl-group">
                    <label>源载体侧重</label>
                    <select v-model="localConfigs.reading.focus">
                      <option value="textbook">经典教材/学术专著</option>
                      <option value="engineering">技术博客/官方白皮书</option>
                      <option value="paper">顶会论文/前沿报告</option>
                    </select>
                    <p class="ctrl-helper">偏爱的文献媒介来源，学术论文偏向 arXiv/IEEE 等期刊</p>
                  </div>
                </template>

                <!-- PPT Agent parameters -->
                <template v-if="activeAgentId === 'ppt'">
                  <div class="ctrl-group">
                    <label>演示模版主题</label>
                    <select v-model="localConfigs.ppt.template">
                      <option value="auto">系统自动推荐 (Auto)</option>
                      <option v-for="t in pptTemplates" :key="t.id" :value="t.id">
                        {{ t.name }} ({{ t.id }})
                      </option>
                    </select>
                    <p class="ctrl-helper">{{ selectedPptTemplateDescription }}</p>
                  </div>

                  <div class="ctrl-group">
                    <label>内容讲解风格</label>
                    <select v-model="localConfigs.ppt.explanation_style">
                      <option value="concept">经典概念精讲 (Concepts)</option>
                      <option value="case_driven">项目案例驱动 (Case-driven)</option>
                      <option value="problem_led">启发问题引导 (Problem-led)</option>
                      <option value="review">复习要点提炼 (Review)</option>
                    </select>
                    <p class="ctrl-helper">幻灯片内文讲解的行文逻辑结构</p>
                  </div>

                  <div class="ctrl-group">
                    <label>排版信息密度</label>
                    <select v-model="localConfigs.ppt.density">
                      <option value="concise">极简精炼排版 (Concise)</option>
                      <option value="standard">标准教学排版 (Standard)</option>
                      <option value="detailed">图文丰富详尽 (Detailed)</option>
                    </select>
                    <p class="ctrl-helper">单页幻灯片文字/图表承载的饱满水平</p>
                  </div>

                  <div class="ctrl-group">
                    <label>大纲重点内容 (多选)</label>
                    <div class="grid grid-cols-2 gap-2 mt-1">
                      <button
                        v-for="opt in [
                          { label: '核心概念', value: 'core_concepts' },
                          { label: '典型案例', value: 'cases' },
                          { label: '避坑指南', value: 'pitfalls' },
                          { label: '数学推导', value: 'derivation' }
                        ]"
                        :key="opt.value"
                        type="button"
                        :class="localConfigs.ppt.focus.includes(opt.value as any) ? 'bg-pink-50 text-pink-800 border-pink-300' : 'bg-white text-slate-400 hover:text-slate-600'"
                        @click="togglePptFocus(opt.value)"
                      >
                        {{ opt.label }}
                        <span v-if="localConfigs.ppt.focus.includes(opt.value as any)" class="text-[9px]">✔</span>
                      </button>
                    </div>
                  </div>
                </template>

                <!-- CARTOON Agent parameters -->
                <template v-if="activeAgentId === 'cartoon'">
                  <div class="ctrl-group">
                    <label>视觉风格</label>
                    <select v-model="localConfigs.cartoon.style">
                      <option value="diagram">教学图解</option>
                      <option value="minimal">简约扁平</option>
                      <option value="dark_tech">暗黑科技</option>
                      <option value="chalkboard">黑板粉笔</option>
                    </select>
                    <p class="ctrl-helper">视频画面的视觉主题风格</p>
                  </div>
                  <div class="ctrl-group">
                    <label>讲解深度</label>
                    <div class="seg-ctrl">
                      <button v-for="opt in [{ label: '快速概览', value: 'overview' }, { label: '标准讲解', value: 'standard' }, { label: '深度剖析', value: 'deep' }]" :key="opt.value" type="button" class="seg-btn" :class="{ active: localConfigs.cartoon.depth === opt.value }" @click="localConfigs.cartoon.depth = opt.value as any">{{ opt.label }}</button>
                    </div>
                    <p class="ctrl-helper">控制讲解深度和动画复杂度</p>
                  </div>
                  <div class="ctrl-group">
                    <label>动画节奏</label>
                    <div class="seg-ctrl">
                      <button v-for="opt in [{ label: '快速', value: 'fast' }, { label: '正常', value: 'normal' }, { label: '慢速', value: 'slow' }]" :key="opt.value" type="button" class="seg-btn" :class="{ active: localConfigs.cartoon.pace === opt.value }" @click="localConfigs.cartoon.pace = opt.value as any">{{ opt.label }}</button>
                    </div>
                    <p class="ctrl-helper">控制动画播放速度</p>
                  </div>
                  <div class="ctrl-group">
                    <label>画面丰富度</label>
                    <div class="seg-ctrl">
                      <button v-for="opt in [{ label: '简洁', value: 'clean' }, { label: '平衡', value: 'balanced' }, { label: '详细', value: 'detailed' }]" :key="opt.value" type="button" class="seg-btn" :class="{ active: localConfigs.cartoon.visuals === opt.value }" @click="localConfigs.cartoon.visuals = opt.value as any">{{ opt.label }}</button>
                    </div>
                    <p class="ctrl-helper">控制画面元素数量和标注</p>
                  </div>
                </template>

              </div>
            </div>
          </div>

          <!-- Right Column: Preview Card wrapper -->
          <div class="lg:col-span-5">
            <div class="preview-wrapper">
              <Preview
                :active-id="activeAgentId"
                :configs="localConfigs"
                :enabled="isAgentEnabled(activeAgentId)"
                :natural-input="naturalInput"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Footer: selected agents + action buttons -->
      <div class="settings-footer">
        <!-- Selected agents pill bar -->
        <div class="agents-bar">
          <span class="agents-bar-label">已选智能体</span>
          <div class="agents-bar-pills">
            <span
              v-for="id in enabledAgentIds"
              :key="id"
              class="agent-pill"
            >
              <component :is="getAgentMeta(id).icon" class="w-3 h-3" />
              {{ getAgentMeta(id).name }}
            </span>
            <span v-if="enabledAgentIds.length === MIN_AGENTS" class="agents-bar-warn">已达最低限制</span>
          </div>
        </div>

        <!-- CTA buttons -->
        <div class="footer-actions">
          <button type="button" @click="emit('back')" class="btn-back">← 返回修改需求</button>
          <button type="button" class="btn-launch" @click="emit('launch')">
            确认配置，启动多智能体
            <Position class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  PhPaperPlaneTilt as Position
} from '@phosphor-icons/vue'
import { toast } from 'vue-sonner'
import AgentTabs from '../settings/AgentTabs.vue'
import Preview from '../settings/Preview.vue'
import {
  getPptTemplates,
  type PptTemplateOption,
} from '@/features/resource/api/resource'
import type { LearningScenario, ResourceAgentId } from '@/features/resource/model/resource'
import {
  MIN_AGENTS,
  getAgentMeta,
  scenarioOptions,
  getScenarioDesc,
  SCENARIO_DEFAULTS,
  type AnyAgentConfigs,
} from '../../model/catalog'

const props = defineProps<{
  learningScenario: LearningScenario
  enabledAgentIds: ResourceAgentId[]
  agentConfigs: AnyAgentConfigs
  naturalInput?: string
}>()

const emit = defineEmits<{
  'update:learningScenario': [value: LearningScenario]
  'update:enabledAgentIds': [value: ResourceAgentId[]]
  'update:agentConfigs': [value: AnyAgentConfigs]
  back: []
  launch: []
}>()

// Active Focused Agent Tab
const activeAgentId = ref<ResourceAgentId>('content')

const learningScenario = computed({
  get: () => props.learningScenario,
  set: (v) => emit('update:learningScenario', v),
})

const enabledAgentIds = computed({
  get: () => props.enabledAgentIds,
  set: (v) => emit('update:enabledAgentIds', v),
})

const localConfigs = ref<AnyAgentConfigs>(JSON.parse(JSON.stringify(props.agentConfigs)))
const pptTemplates = ref<PptTemplateOption[]>([])

const getActiveAgentMeta = computed(() => {
  return getAgentMeta(activeAgentId.value)
})

const getActiveAgentOutputLabel = computed(() => {
  const map: Record<string, string> = {
    content: '课程讲解文档',
    mindmap: '思维导图图片',
    code: '代码实操案例',
    quiz: '随堂练习题库',
    reading: '拓展阅读文献',
    ppt: '演示幻灯课件',
    cartoon: '动画讲解视频',
  }
  return map[activeAgentId.value] || '学习资源'
})

const selectedPptTemplateDescription = computed(() => {
  if (localConfigs.value.ppt.template === 'auto') {
    return '系统会根据知识类型自动匹配最合适的模板'
  }
  return pptTemplates.value.find(
    template => template.id === localConfigs.value.ppt.template,
  )?.description || '所选模板当前不可用，请重新选择'
})

onMounted(async () => {
  try {
    const response = await getPptTemplates()
    const templates = response.data?.data
    if (!Array.isArray(templates) || templates.length === 0) {
      throw new Error('PPT 模板列表为空')
    }
    pptTemplates.value = templates
  } catch (error) {
    console.error('PPT 模板列表加载失败', error)
  }
})

// Watch parent prop changes (e.g. when scenario changes or is initialized)
watch(() => props.agentConfigs, (newVal) => {
  localConfigs.value = JSON.parse(JSON.stringify(newVal))
}, { deep: true })

// Emit changes back to parent
watch(localConfigs, (newVal) => {
  emit('update:agentConfigs', JSON.parse(JSON.stringify(newVal)))
}, { deep: true })

const isAgentEnabled = (id: string) => enabledAgentIds.value.includes(id as ResourceAgentId)

const toggleAgent = (id: string) => {
  const idx = enabledAgentIds.value.indexOf(id as ResourceAgentId)
  if (idx >= 0) {
    if (enabledAgentIds.value.length <= MIN_AGENTS) {
      toast.warning(`至少需要保留 ${MIN_AGENTS} 个智能体才能生成有效的个性化学习资源`)
      return
    }
    const next = [...enabledAgentIds.value]
    next.splice(idx, 1)
    emit('update:enabledAgentIds', next)
  } else {
    emit('update:enabledAgentIds', [...enabledAgentIds.value, id as ResourceAgentId])
  }
}

const selectScenario = (scenario: LearningScenario) => {
  emit('update:learningScenario', scenario)
  const defaults = SCENARIO_DEFAULTS[scenario]
  if (defaults) {
    localConfigs.value = JSON.parse(JSON.stringify({
      ...localConfigs.value,
      ...defaults,
    }))
  }
}

function toggleQuestionType(type: any) {
  const types = [...localConfigs.value.quiz.question_types]
  const idx = types.indexOf(type)
  if (idx >= 0) {
    if (types.length <= 1) {
      toast.warning('至少需要选定一种考核题型')
      return
    }
    types.splice(idx, 1)
  } else {
    types.push(type)
  }
  localConfigs.value.quiz.question_types = types
}

function togglePptFocus(item: any) {
  const list = [...localConfigs.value.ppt.focus]
  const idx = list.indexOf(item)
  if (idx >= 0) {
    if (list.length <= 1) {
      toast.warning('大纲重点至少包含一项')
      return
    }
    list.splice(idx, 1)
  } else {
    list.push(item)
  }
  localConfigs.value.ppt.focus = list
}
</script>

<style scoped>
.personalize-view {
  width: 100%;
  padding: 28px clamp(18px, 3vw, 48px) 48px;
  overflow-y: auto;
  background: #f4f7fb;
  font-family: var(--font-ui);
}

.personalize-container {
  max-width: 1280px;
  margin: 0 auto;
}

/* Header */
.view-header {
  text-align: center;
  margin-bottom: 4px;
}

.settings-eyebrow {
  display: inline-block;
  margin-bottom: 10px;
  padding: 4px 12px;
  border-radius: 999px;
  background: #0f172a;
  color: #fff;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.view-header h2 {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--color-text-strong);
  margin: 0 0 8px;
  letter-spacing: -0.02em;
}

.view-header p {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  max-width: 560px;
  margin: 0 auto;
  line-height: 1.6;
}

.scenario-selector-v2 {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-top: 24px;
}

.scenario-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 20px;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0,0,0,0.01);
  transition: all 0.25s cubic-bezier(0.3, 0.7, 0.1, 1);
}

.scenario-card:hover {
  transform: translateY(-2px);
  border-color: rgba(99, 102, 241, 0.2);
  box-shadow: 0 6px 16px rgba(16, 24, 40, 0.04);
}

.scenario-card.active {
  background: #ffffff;
  border-color: var(--color-primary);
  box-shadow: 0 10px 25px rgba(99, 102, 241, 0.08);
}

.scenario-icon-box {
  width: 40px;
  height: 40px;
  background: #f1f5f9;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.15rem;
  font-weight: bold;
  color: var(--color-text-strong);
}

.scenario-card.active .scenario-icon-box {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.scenario-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.s-name {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text-strong);
}

.s-desc {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 3px;
}

.active-dot {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
}

.workspace-card {
  background: #ffffff;
}

/* Preview wrapper */
.preview-wrapper {
  height: 100%;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.ctrl-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ctrl-group label {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-text-strong);
}

.ctrl-group select {
  width: 100%;
  height: 40px;
  padding: 0 36px 0 12px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 10px;
  font-family: inherit;
  font-size: 0.85rem;
  font-weight: 500;
  color: #1e293b;
  background-color: #ffffff;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  appearance: none;
  -webkit-appearance: none;
  outline: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

/* 下拉菜单白色背景、向下展开 */
.ctrl-group select::-webkit-dropdown-button {
  background-color: #ffffff;
}

.ctrl-group select option {
  background-color: #ffffff;
  color: #1e293b;
  padding: 8px 12px;
}

.ctrl-group select option:checked,
.ctrl-group select option:hover {
  background-color: #f1f5f9;
  color: #1e293b;
}

.ctrl-group select:hover {
  border-color: rgba(15, 23, 42, 0.22);
}

.ctrl-group select:focus {
  border-color: var(--color-primary, #6366f1);
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12);
}

.ctrl-helper {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin: 0;
}

.ctrl-switch-v2 {
  background: #f8fafc;
  border-color: rgba(15, 23, 42, 0.04);
}

.sw-label {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--color-text-strong);
}

.sw-desc {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

/* Footer */
.settings-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  margin-top: 8px;
  padding-bottom: 48px;
}

.agents-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.07);
  border-radius: 999px;
  padding: 10px 20px;
  max-width: 860px;
  box-shadow: 0 1px 4px rgba(16, 24, 40, 0.04);
}

.agents-bar-label {
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  white-space: nowrap;
}

.agents-bar-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.agent-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border: 1px solid rgba(15, 23, 42, 0.07);
  border-radius: 999px;
  background: #f8fafc;
  color: #334155;
  font-size: 11px;
  font-weight: 600;
}

.agents-bar-warn {
  font-size: 10px;
  font-weight: 700;
  color: #f59e0b;
  padding: 4px 10px;
  border-radius: 999px;
  background: #fffbeb;
  border: 1px solid #fde68a;
}

.footer-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.btn-back {
  padding: 10px 22px;
  border-radius: 999px;
  border: 1.5px solid rgba(15, 23, 42, 0.14);
  background: #ffffff;
  color: #475569;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-back:hover {
  border-color: rgba(15, 23, 42, 0.25);
  color: #1e293b;
}

.btn-launch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 11px 28px;
  border-radius: 999px;
  border: none;
  background: var(--color-primary, #6366f1);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.28);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-launch:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.36);
}

.btn-launch:active {
  transform: translateY(0);
}

@media (max-width: 980px) {
  .scenario-selector-v2 {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .scenario-selector-v2 {
    grid-template-columns: 1fr;
  }

  .preview-wrapper {
    border-left: none;
    border-top: 1px solid #edf1f5;
    border-radius: 0 0 24px 24px;
  }
}
</style>
