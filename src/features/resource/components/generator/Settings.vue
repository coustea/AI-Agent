<template>
  <div class="phase-view personalize-view">
    <div class="personalize-container">
      <!-- Page Title Header -->
      <div class="view-header text-center">
        <span class="inline-flex items-center gap-1.5 px-3 py-1 text-[10px] font-bold tracking-wide uppercase bg-slate-900 text-white rounded-full mb-3">
          Orchestrator Settings
        </span>
        <h2>多智能体参数定制中心</h2>
        <p>配置各智能体加工参数。您的定制设置将直接传递给多智能体系统作为最高生成指南。</p>
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
        <div class="workspace-body grid grid-cols-1 lg:grid-cols-12 gap-8 p-8 min-h-[500px]">
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
                    <label>视觉讲解风格</label>
                    <select v-model="localConfigs.cartoon.style">
                      <option value="diagram">立体结构图解 (Diagrams)</option>
                      <option value="minimal">简约平面扁平 (Minimal)</option>
                      <option value="dark_tech">暗黑荧光科技 (Neon Dark)</option>
                    </select>
                    <p class="ctrl-helper">视频图画的主流美学色调</p>
                  </div>

                  <div class="ctrl-group">
                    <label>讲解侧重点</label>
                    <select v-model="localConfigs.cartoon.focus">
                      <option value="concept">概念原理解释 (Concept)</option>
                      <option value="process">过程演化追踪 (Process)</option>
                      <option value="comparison">多维对比辨析 (Comparison)</option>
                      <option value="practice">真实代码演练 (Practice)</option>
                    </select>
                    <p class="ctrl-helper">视频内容推进和图形动画的核心围绕主体</p>
                  </div>

                  <div class="ctrl-group">
                    <label>配音角色</label>
                    <select v-model="localConfigs.cartoon.voice">
                      <option value="teacher">稳重资深教师 (Teacher)</option>
                      <option value="coach">互动实战教练 (Coach)</option>
                    </select>
                    <p class="ctrl-helper">生成配音音频的TTS音色特质</p>
                  </div>

                  <div class="ctrl-group">
                    <div class="slider-label-row flex justify-between items-center mb-1">
                      <label class="m-0">视频时长上限</label>
                      <span class="text-xs font-bold text-primary-main"><b>{{ localConfigs.cartoon.video_length_seconds }}</b> 秒</span>
                    </div>
                    <input
                      type="range"
                      v-model.number="localConfigs.cartoon.video_length_seconds"
                      :min="60"
                      :max="180"
                      :step="30"
                      class="w-full"
                    />
                    <p class="ctrl-helper">限制生成视频在剪辑及合成时的总时间跨度</p>
                  </div>
                </template>

              </div>
            </div>
          </div>

          <Preview
            class="lg:col-span-5"
            :active-id="activeAgentId"
            :configs="localConfigs"
            :enabled="isAgentEnabled(activeAgentId)"
            :natural-input="naturalInput"
          />
        </div>
      </div>

      <!-- Action Pills and Action Buttons -->
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
  padding: 24px clamp(18px, 3vw, 42px) 36px;
  overflow-y: auto;
  background: #f4f7fb;
  font-family: var(--font-ui);
}

.personalize-container {
  max-width: 1280px;
  margin: 0 auto;
}

.view-header h2 {
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--color-text-strong);
  margin-bottom: 8px;
}

.view-header p {
  font-size: 0.95rem;
  color: var(--color-text-secondary);
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

.ctrl-group select,
.ctrl-group input[type="range"] {
  height: 40px;
  padding: 0 12px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 12px;
  font-family: inherit;
  font-size: 0.85rem;
  color: var(--color-text-strong);
  background: #ffffff;
  outline: none;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
  transition: border-color 0.2s ease;
}

.ctrl-group select:focus {
  border-color: var(--color-primary);
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

.sab-label {
  color: #64748b;
}

.launch-btn-v2 {
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.25);
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
}
</style>
