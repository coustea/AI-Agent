<template>
  <div class="phase-view personalize-view">
    <div class="personalize-container">
      <div class="view-header">
        <span class="inline-flex items-center gap-1.5 px-3 py-1 text-[10px] font-bold tracking-wide uppercase bg-slate-900 text-white rounded-full mb-4">
          AI CONFIGURATION
        </span>
        <h2>多智能体参数定制中心</h2>
        <p>请为即将出场 AI 智能体配置加工参数，您的指令将作为最高优先级要求贯穿全局。</p>
      </div>

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

      <div class="config-section-v2">
        <div class="agent-configs-grid">
          <div 
            class="config-card-v2 bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md transition-all duration-300 flex flex-col" 
            :class="{
              'agent-off': !isAgentEnabled(agent.id),
              'ppt-config-card': agent.id === 'ppt',
            }"
            v-for="agent in personalizeAgents" 
            :key="agent.id"
          >
            <div class="cc-header-v2 border-b border-dashed border-slate-100 pb-4 mb-4 flex items-center gap-3">
              <div class="cc-icon-wrap w-9 h-9 rounded-xl flex items-center justify-center text-slate-700 bg-slate-50 border border-slate-100" :class="agent.colorClass">
                <component :is="agent.icon" class="w-4 h-4" />
              </div>
              <span class="cc-title font-extrabold text-slate-800 text-sm tracking-wide">{{ agent.name }}</span>
              
              <div class="cc-header-switch ml-auto">
                <label class="relative inline-flex items-center cursor-pointer select-none">
                  <input 
                    type="checkbox" 
                    :checked="isAgentEnabled(agent.id)" 
                    @change="toggleAgent(agent.id)"
                    class="sr-only peer"
                  />
                  <div class="w-10 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue"></div>
                </label>
              </div>
            </div>

            <div class="cc-body-v2 flex-1 flex flex-col gap-5" :class="{ 'body-disabled': !isAgentEnabled(agent.id) }">
              <!-- Content Agent -->
              <template v-if="agent.id === 'content'">
                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">讲解结构</label>
                  <select 
                    v-model="localConfigs.content.structure" 
                    class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl outline-none bg-white focus:border-blue"
                  >
                    <option value="progressive">渐进式引导 (Progressive)</option>
                    <option value="summary_first">先总后分 (Summary First)</option>
                    <option value="exam_points">考点驱动 (Exam Points)</option>
                    <option value="case_driven">案例驱动 (Case Driven)</option>
                  </select>
                </div>
                
                <div class="ctrl-switch-group-v2 flex flex-col gap-4">
                  
                  <div class="ctrl-switch-v2 flex justify-between items-start">
                    <div class="sw-info flex flex-col">
                      <span class="sw-label text-sm font-semibold text-slate-800">丰富生活化示例</span>
                      <span class="sw-desc text-xs text-slate-400">用直观的案例辅助理解抽象概念</span>
                    </div>
                    <label class="relative inline-flex items-center cursor-pointer select-none">
                      <input 
                        type="checkbox" 
                        v-model="localConfigs.content.include_examples" 
                        class="sr-only peer"
                      />
                      <div class="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue"></div>
                    </label>
                  </div>
                </div>
              </template>

              <!-- Mindmap Agent -->
              <template v-if="agent.id === 'mindmap'">
                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">导图生成策略</label>
                  <select
                    v-model="localConfigs.mindmap.map_type"
                    class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl outline-none bg-white focus:border-blue"
                  >
                    <option value="knowledge_tree">核心知识树 (Knowledge Tree)</option>
                    <option value="exam_map">高频考点图 (Exam Map)</option>
                    <option value="comparison_map">对比复习图 (Comparison)</option>
                  </select>
                </div>

                <div class="ctrl-group flex flex-col gap-1.5">
                  <div class="slider-label-row flex justify-between items-center mb-1">
                    <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">节点发散层级</label>
                    <span class="text-xs font-bold text-blue"><b>{{ localConfigs.mindmap.max_depth }}</b> 层</span>
                  </div>
                  <input
                    type="range"
                    v-model.number="localConfigs.mindmap.max_depth"
                    :min="2"
                    :max="5"
                    :step="1"
                    class="w-full h-1.5 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue focus:outline-none"
                  />
                </div>

                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">叶节点粒度</label>
                  <div class="flex gap-1.5 bg-slate-50 p-1 rounded-xl">
                    <button
                      v-for="opt in [
                        { label: '关键词', value: 'keyword' },
                        { label: '简要', value: 'brief_note' },
                        { label: '详注', value: 'annotated' }
                      ]"
                      :key="opt.value"
                      type="button"
                      class="flex-1 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                      :class="localConfigs.mindmap.leaf_detail === opt.value ? 'bg-white text-slate-900 shadow-sm' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                      @click="localConfigs.mindmap.leaf_detail = opt.value as 'keyword' | 'brief_note' | 'annotated'"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                </div>

                <div class="ctrl-switch-v2 flex justify-between items-start">
                  <div class="sw-info flex flex-col">
                    <span class="sw-label text-sm font-semibold text-slate-800">标注概念关系</span>
                    <span class="sw-desc text-xs text-slate-400">在节点旁标注因果、对比、依赖等关系</span>
                  </div>
                  <label class="relative inline-flex items-center cursor-pointer select-none">
                    <input
                      type="checkbox"
                      v-model="localConfigs.mindmap.show_relations"
                      class="sr-only peer"
                    />
                    <div class="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue"></div>
                  </label>
                </div>
              </template>

              <!-- Code Agent -->
              <template v-if="agent.id === 'code'">
                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">编程语言目标</label>
                  <select 
                    v-model="localConfigs.code.programming_language" 
                    class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl outline-none bg-white focus:border-blue"
                  >
                    <option value="python">Python</option>
                    <option value="c">C</option>
                    <option value="javascript">JavaScript</option>
                    <option value="typescript">TypeScript</option>
                    <option value="cpp">C++</option>
                    <option value="java">Java</option>
                    <option value="go">Go</option>
                  </select>
                </div>
                
                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">难度等级</label>
                  <div class="flex gap-1.5 bg-slate-50 p-1 rounded-xl">
                    <button
                      v-for="opt in [
                        { label: '入门', value: 'beginner' },
                        { label: '进阶', value: 'intermediate' },
                        { label: '挑战', value: 'advanced' }
                      ]"
                      :key="opt.value"
                      type="button"
                      class="flex-1 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                      :class="localConfigs.code.difficulty === opt.value ? 'bg-white text-slate-900 shadow-sm' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                      @click="setCodeDifficulty(opt.value)"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                </div>

                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">练习模板</label>
                  <div class="flex gap-1.5 bg-slate-50 p-1 rounded-xl">
                    <button
                      v-for="opt in [
                        { label: '基础教学', value: 'basic_demo' },
                        { label: '算法模板', value: 'algorithm_template' }
                      ]"
                      :key="opt.value"
                      type="button"
                      class="flex-1 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                      :class="localConfigs.code.case_type === opt.value ? 'bg-white text-slate-900 shadow-sm' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                      @click="setCodeCaseType(opt.value)"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                </div>
              </template>

              <!-- Quiz Agent -->
              <template v-if="agent.id === 'quiz'">
                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">考察策略</label>
                  <div class="flex gap-1.5 bg-slate-50 p-1 rounded-xl">
                    <button
                      v-for="opt in [
                        { label: '基础巩固', value: 'basic' },
                        { label: '动态自适应', value: 'adaptive' },
                        { label: '硬核考研', value: 'exam' }
                      ]"
                      :key="opt.value"
                      type="button"
                      class="flex-1 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                      :class="localConfigs.quiz.difficulty_mode === opt.value ? 'bg-white text-slate-900 shadow-sm' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                      @click="setQuizDifficultyMode(opt.value)"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                </div>

                <div class="ctrl-group flex flex-col gap-1.5">
                  <div class="slider-label-row flex justify-between items-center mb-1">
                    <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">生成题量</label>
                    <span class="text-xs font-bold text-blue"><b>{{ localConfigs.quiz.question_count }}</b> 道题</span>
                  </div>
                  <input 
                    type="range" 
                    v-model.number="localConfigs.quiz.question_count" 
                    :min="1" 
                    :max="20" 
                    :step="1"
                    class="w-full h-1.5 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue focus:outline-none"
                  />
                </div>
              </template>

              <!-- Reading Agent -->
              <template v-if="agent.id === 'reading'">
                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">文献拓宽深度</label>
                  <select 
                    v-model="localConfigs.reading.reading_depth" 
                    class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl outline-none bg-white focus:border-blue"
                  >
                    <option value="course_extended">课程内延展 (Course Extended)</option>
                    <option value="engineering">工程化实践 (Engineering)</option>
                    <option value="frontier">前沿学术论文 (Frontier)</option>
                  </select>
                </div>
                
                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">语言偏好</label>
                  <div class="flex gap-1.5 bg-slate-50 p-1 rounded-xl">
                    <button
                      v-for="opt in [
                        { label: '中文优先', value: 'chinese' },
                        { label: '中英双语', value: 'both' },
                        { label: '英文原版', value: 'english' }
                      ]"
                      :key="opt.value"
                      type="button"
                      class="flex-1 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                      :class="localConfigs.reading.language_preference === opt.value ? 'bg-white text-slate-900 shadow-sm' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                      @click="setReadingLanguagePreference(opt.value)"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                </div>

                <div class="ctrl-group flex flex-col gap-1.5">
                  <div class="slider-label-row flex justify-between items-center mb-1">
                    <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">拓展上限</label>
                    <span class="text-xs font-bold text-blue"><b>{{ localConfigs.reading.max_items }}</b> 篇</span>
                  </div>
                  <input 
                    type="range" 
                    v-model.number="localConfigs.reading.max_items" 
                    :min="1" 
                    :max="10" 
                    :step="1"
                    class="w-full h-1.5 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue focus:outline-none"
                  />
                </div>
              </template>

              <!-- PPT Agent -->
              <template v-if="agent.id === 'ppt'">
                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">模板</label>
                  <select
                    v-model="localConfigs.ppt.template"
                    class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl outline-none bg-white focus:border-blue"
                  >
                    <option value="auto">自动推荐</option>
                    <option
                      v-for="template in pptTemplates"
                      :key="template.id"
                      :value="template.id"
                    >
                      {{ template.name }}
                    </option>
                  </select>
                  <p class="m-0 text-[11px] leading-5 text-slate-400">
                    {{ selectedPptTemplateDescription }}
                  </p>
                </div>

                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">讲解方式</label>
                  <div class="flex gap-1.5 bg-slate-50 p-1 rounded-xl">
                    <button
                      v-for="opt in [
                        { label: '概念讲解', value: 'concept' },
                        { label: '案例驱动', value: 'case_driven' },
                        { label: '问题引导', value: 'problem_led' },
                        { label: '复习提炼', value: 'review' }
                      ]"
                      :key="opt.value"
                      type="button"
                      class="flex-1 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                      :class="localConfigs.ppt.explanation_style === opt.value ? 'bg-white text-slate-900 shadow-sm' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                      @click="localConfigs.ppt.explanation_style = opt.value as any"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                </div>

                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">内容深度</label>
                  <div class="flex gap-1.5 bg-slate-50 p-1 rounded-xl">
                    <button
                      v-for="opt in [
                        { label: '精炼', value: 'concise' },
                        { label: '标准', value: 'standard' },
                        { label: '深入', value: 'detailed' }
                      ]"
                      :key="opt.value"
                      type="button"
                      class="flex-1 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                      :class="localConfigs.ppt.density === opt.value ? 'bg-white text-slate-900 shadow-sm' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                      @click="localConfigs.ppt.density = opt.value as any"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                </div>

                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">内容侧重</label>
                  <div class="flex flex-wrap gap-1.5 bg-slate-50 p-1.5 rounded-xl">
                    <button
                      v-for="opt in [
                        { label: '核心概念', value: 'core_concepts' },
                        { label: '案例', value: 'cases' },
                        { label: '易错点', value: 'pitfalls' },
                        { label: '过程推导', value: 'derivation' }
                      ]"
                      :key="opt.value"
                      type="button"
                      class="px-3 py-1.5 text-xs font-semibold rounded-lg border cursor-pointer transition-all"
                      :class="localConfigs.ppt.focus.includes(opt.value as 'core_concepts' | 'cases' | 'pitfalls' | 'derivation') ? 'bg-white text-slate-900 border-slate-200 shadow-sm' : 'bg-transparent text-slate-400 border-transparent hover:text-slate-600'"
                      @click="togglePptFocus(opt.value as 'core_concepts' | 'cases' | 'pitfalls' | 'derivation')"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                </div>
              </template>

              <!-- Cartoon Agent -->
              <template v-if="agent.id === 'cartoon'">
                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">动画视觉</label>
                  <select
                    v-model="localConfigs.cartoon.style"
                    class="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl outline-none bg-white focus:border-blue"
                  >
                    <option value="diagram">清晰图解</option>
                    <option value="minimal">简约教学</option>
                    <option value="dark_tech">暗黑科技</option>
                  </select>
                  <p class="m-0 text-[11px] leading-5 text-slate-400">
                    动画用于解释结构、状态和执行过程，不添加无意义炫技效果
                  </p>
                </div>

                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">讲解重点</label>
                  <div class="grid grid-cols-2 gap-1.5 bg-slate-50 p-1 rounded-xl">
                    <button
                      v-for="opt in [
                        { label: '概念原理', value: 'concept' },
                        { label: '过程演示', value: 'process' },
                        { label: '对比辨析', value: 'comparison' },
                        { label: '实践应用', value: 'practice' }
                      ]"
                      :key="opt.value"
                      type="button"
                      class="py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                      :class="localConfigs.cartoon.focus === opt.value ? 'bg-white text-slate-900 shadow-sm' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                      @click="localConfigs.cartoon.focus = opt.value as any"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                </div>

                <div class="ctrl-group flex flex-col gap-1.5">
                  <div class="slider-label-row flex justify-between items-center mb-1">
                    <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">成片时长</label>
                    <span class="text-xs font-bold text-blue">约 <b>{{ localConfigs.cartoon.video_length_seconds }}</b> 秒</span>
                  </div>
                  <input
                    v-model.number="localConfigs.cartoon.video_length_seconds"
                    type="range"
                    :min="60"
                    :max="180"
                    :step="30"
                    class="w-full h-1.5 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue focus:outline-none"
                  />
                  <p class="m-0 text-[11px] leading-5 text-slate-400">
                    系统根据知识完整度动态安排场景，不会重复内容凑时长
                  </p>
                </div>

                <div class="ctrl-group flex flex-col gap-1.5">
                  <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">配音角色</label>
                  <div class="flex gap-1.5 bg-slate-50 p-1 rounded-xl">
                    <button
                      v-for="opt in [
                        { label: '沉稳教师', value: 'teacher' },
                        { label: '互动教练', value: 'coach' }
                      ]"
                      :key="opt.value"
                      type="button"
                      class="flex-1 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                      :class="localConfigs.cartoon.voice === opt.value ? 'bg-white text-slate-900 shadow-sm' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                      @click="localConfigs.cartoon.voice = opt.value as any"
                    >
                      {{ opt.label }}
                    </button>
                  </div>
                </div>
              </template>

            </div>
          </div>
        </div>
      </div>

      <div class="personalize-footer-v2 flex flex-col items-center gap-6 mt-4 pb-16">
        <div class="selected-agents-bar flex items-center gap-4 flex-wrap justify-center bg-white border border-slate-100 rounded-3xl px-6 py-4 max-w-[860px] shadow-sm">
          <span class="sab-label font-bold text-xs text-slate-500 tracking-wider">已选智能体工位：</span>
          <div class="sab-pills flex gap-2 flex-wrap">
            <span
              v-for="id in enabledAgentIds"
              :key="id"
              class="inline-flex items-center gap-1.5 px-3.5 py-1 text-xs font-semibold text-slate-700 bg-slate-50 border border-slate-100 rounded-full"
            >
              <component :is="getAgentMeta(id).icon" class="w-3.5 h-3.5 text-blue" />
              {{ getAgentMeta(id).name }}
            </span>
          </div>
          <span class="sab-hint text-xs font-bold text-slate-400" v-if="enabledAgentIds.length === MIN_AGENTS">⚠️ 已达最低要求</span>
        </div>

        <div class="footer-btns flex gap-4">
          <button type="button" @click="emit('back')" class="btn btn-outline footer-back-btn px-6 py-3 rounded-full font-bold">返回修改需求</button>
          <button type="button" class="btn btn-primary launch-btn-v2 px-8 py-3 rounded-full font-bold flex items-center gap-2" @click="emit('launch')">
            确认配置，启动多智能体加工 <Position class="w-4 h-4" />
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
import {
  getPptTemplates,
  type PptTemplateOption,
} from '@/features/resource/api/resource'
import type { LearningScenario, ResourceAgentId } from '@/features/resource/model/resource'
import {
  MIN_AGENTS,
  agentMetaList,
  getAgentMeta,
  scenarioOptions,
  getScenarioDesc,
  SCENARIO_DEFAULTS,
  type AnyAgentConfigs,
} from '@/features/resource/model/ResourceGeneratorConstants'

const props = defineProps<{
  learningScenario: LearningScenario
  enabledAgentIds: ResourceAgentId[]
  agentConfigs: AnyAgentConfigs
}>()

const emit = defineEmits<{
  'update:learningScenario': [value: LearningScenario]
  'update:enabledAgentIds': [value: ResourceAgentId[]]
  'update:agentConfigs': [value: AnyAgentConfigs]
  back: []
  launch: []
}>()

const personalizeAgents = computed(() => agentMetaList.filter(
  agent => !['master', 'assembler'].includes(agent.id),
))

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
  if (!defaults) return
  const merged = JSON.parse(JSON.stringify(localConfigs.value)) as AnyAgentConfigs
  Object.keys(defaults).forEach((key) => {
    const agentKey = key as keyof AnyAgentConfigs
    const agentDefaults = defaults[agentKey]
    if (agentDefaults && merged[agentKey]) {
      ;(merged as any)[agentKey] = { ...(merged as any)[agentKey], ...agentDefaults }
    }
  })
  localConfigs.value = merged
}

const setCodeDifficulty = (val: any) => {
  if (localConfigs.value.code) localConfigs.value.code.difficulty = val
}
const setCodeCaseType = (val: any) => {
  if (localConfigs.value.code) localConfigs.value.code.case_type = val
}
const setQuizDifficultyMode = (val: any) => {
  if (localConfigs.value.quiz) localConfigs.value.quiz.difficulty_mode = val
}
const setReadingLanguagePreference = (val: any) => {
  if (localConfigs.value.reading) localConfigs.value.reading.language_preference = val
}
const togglePptFocus = (value: 'core_concepts' | 'cases' | 'pitfalls' | 'derivation') => {
  const focus = localConfigs.value.ppt.focus
  if (focus.includes(value)) {
    if (focus.length === 1) {
      toast.warning('至少保留一个 PPT 讲解重点')
      return
    }
    localConfigs.value.ppt.focus = focus.filter(item => item !== value)
    return
  }
  localConfigs.value.ppt.focus = [...focus, value]
}
</script>

<style scoped>
.personalize-view {
  --font-sans: var(--font-ui);
  --agent-body-font: var(--font-body);

  background: transparent;
  align-items: center;
  overflow-y: auto;
  padding: 60px var(--space-5);
  position: relative;
  font-family: var(--font-sans);
}
.personalize-container { width: 100%; max-width: 1160px; display: flex; flex-direction: column; gap: var(--space-12); position: relative; z-index: 10; }
.view-header { text-align: center; margin-bottom: 0; }
.view-header h2 {
  font-size: 2.5rem;
  font-weight: 800;
  margin: 0 0 12px 0;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, var(--color-text-strong), var(--cat-resource));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.view-header p { font-family: var(--agent-body-font); font-size: 1.1rem; color: var(--color-text-muted); margin: 0; max-width: 600px; margin: 0 auto; line-height: 1.6; }
.scenario-selector-v2 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; margin-bottom: 40px; }
.scenario-card { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(24px); border: 2px solid var(--color-border); border-radius: 20px; padding: 20px 24px; display: flex; align-items: center; gap: 16px; cursor: pointer; transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); position: relative; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04); }
.scenario-card:hover { transform: translateY(-4px) scale(1.02); border-color: var(--color-border-hover); box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08); background: #ffffff; }
.scenario-card.active { border-color: var(--color-primary); box-shadow: 0 12px 32px var(--color-primary-glow, rgba(99, 102, 241, 0.25)); background: #ffffff; }
.scenario-icon-box { width: 48px; height: 48px; background: var(--color-bg); border: 2px solid var(--color-border); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 1.3rem; color: var(--color-text-secondary); transition: all 0.3s; }
.scenario-card.active .scenario-icon-box { background: var(--color-primary); color: var(--color-surface); border-color: var(--color-primary); transform: scale(1.05); }
.scenario-info { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.s-name { font-weight: 800; font-size: 1.1rem; color: var(--color-text-strong); letter-spacing: 0.02em; }
.s-desc { font-family: var(--agent-body-font); font-size: 0.8rem; color: var(--color-text-muted); line-height: 1.4; opacity: 0.8; }
.active-dot { position: absolute; top: 16px; right: 16px; width: 10px; height: 10px; background: var(--color-primary); border-radius: 50%; box-shadow: 0 0 12px var(--color-primary-glow, rgba(99, 102, 241, 0.3)); }
.config-section-v2 { margin-top: 10px; }
.agent-configs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.config-card-v2 { transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.config-card-v2:hover { transform: translateY(-4px); border-color: var(--color-primary-border); box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08); background: #ffffff; }
.config-card-v2.agent-off { border-color: #E5E7EB; opacity: 0.85; }
.cc-header-switch { margin-left: auto; flex-shrink: 0; }
.cc-body-v2.body-disabled { opacity: 0.38; pointer-events: none; filter: grayscale(60%); }
.cc-title { font-family: var(--font-sans); font-weight: 800; font-size: 1.15rem; color: var(--color-text); letter-spacing: 0.02em; }
.cc-body-v2 { padding: 0; display: flex; flex-direction: column; gap: 20px; flex: 1; }
.ctrl-group { display: flex; flex-direction: column; gap: var(--space-3); }
.ctrl-group label { font-size: 0.85rem; color: var(--color-text-muted); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: 0.02em; }
.ctrl-switch-group-v2 { display: flex; flex-direction: column; gap: var(--space-5); }
.ctrl-switch-v2 { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-4); }
.sw-info { display: flex; flex-direction: column; gap: 2px; }
.sw-label { font-size: 0.9rem; font-weight: var(--weight-semibold); color: var(--color-text-strong); }
.sw-desc { font-family: var(--agent-body-font); font-size: 0.75rem; color: var(--color-text-faint); line-height: 1.4; }

/* 精致表单控件样式优化 */
select {
  appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  background-size: 14px;
  padding-right: 36px !important;
  border: 1px solid rgba(15, 23, 42, 0.08) !important;
  border-radius: 12px !important;
  color: var(--color-text);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
  transition: border-color 0.2s, box-shadow 0.2s;
}
select:focus {
  border-color: var(--color-primary) !important;
  box-shadow: 0 0 0 3px var(--color-primary-glow, rgba(99, 102, 241, 0.12));
}

/* 滑块样式优化 */
input[type="range"] {
  -webkit-appearance: none;
  appearance: none;
  background: rgba(15, 23, 42, 0.06);
  border-radius: 99px;
  height: 6px;
  outline: none;
}
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #ffffff;
  border: 2px solid var(--color-primary);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  transition: transform 0.15s, background-color 0.15s;
}
input[type="range"]::-webkit-slider-thumb:hover {
  transform: scale(1.15);
  background: var(--color-primary-soft, #f5f3ff);
}

/* 开关样式优化 */
.peer-checked\:bg-blue {
  background-color: var(--color-primary) !important;
}

/* 智能体卡片微动效与玻璃拟态 */
.config-card-v2 {
  background: rgba(255, 255, 255, 0.8) !important;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(15, 23, 42, 0.06) !important;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.01) !important;
}
.config-card-v2:hover {
  border-color: rgba(99, 102, 241, 0.25) !important;
  box-shadow: 0 12px 30px rgba(99, 102, 241, 0.06) !important;
}
.config-card-v2.agent-off {
  background: rgba(248, 250, 252, 0.5) !important;
  border-color: rgba(15, 23, 42, 0.04) !important;
  box-shadow: none !important;
}

/* 按钮组与页脚优化 */
.launch-btn-v2 {
  background: var(--color-primary) !important;
  color: #ffffff !important;
  box-shadow: 0 4px 14px var(--color-primary-glow, rgba(99, 102, 241, 0.3)) !important;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
}
.launch-btn-v2:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px var(--color-primary-glow, rgba(99, 102, 241, 0.45)) !important;
}
.launch-btn-v2:active {
  transform: translateY(0) scale(0.98);
}
.footer-back-btn {
  border: 1px solid rgba(15, 23, 42, 0.08) !important;
  background: #ffffff !important;
  color: var(--color-text-secondary) !important;
  transition: all 0.2s !important;
}
.footer-back-btn:hover {
  border-color: var(--color-text-muted) !important;
  color: var(--color-text-strong) !important;
  background: var(--color-bg) !important;
}
</style>
