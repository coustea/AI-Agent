<template>
  <!-- 参数定制视图：场景选择 + 智能体配置工作台 + 预览 + 底部操作栏 -->
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
      <!-- ── 内联 AgentTabs：智能体选择标签页栏 ── -->
        <div class="workspace-tabs-bar grid grid-cols-2 border-b border-slate-100 bg-slate-50/50 p-4 gap-3 md:grid-cols-8">
          <button
            v-for="agent in agents"
            :key="agent.id"
            type="button"
            class="agent-tab-item relative flex cursor-pointer select-none flex-col items-center justify-center rounded-2xl border border-slate-200 p-4 transition-all"
            :class="[
              `tab-theme-${agent.id}`,
              {
                active: activeAgentId === agent.id,
                'disabled-tab': isAgentEnabled(agent.id) === false,
              },
            ]"
            @click="activeAgentId = agent.id as ResourceAgentId"
          >
            <span class="tab-switch absolute right-2 top-2" @click.stop>
              <input
                class="sr-only peer"
                type="checkbox"
                :checked="isAgentEnabled(agent.id)"
                :aria-label="`${isAgentEnabled(agent.id) ? '停用' : '启用'}${agent.name}`"
                @change="toggleAgent(agent.id)"
              />
              <span class="flex h-4 w-4 items-center justify-center rounded-full border border-slate-200 bg-white text-transparent transition-all peer-checked:border-emerald-500 peer-checked:bg-emerald-500 peer-checked:text-white">
                <svg class="h-2.5 w-2.5" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"></path>
                </svg>
              </span>
            </span>
            <span
              class="tab-icon-wrap mb-2 flex h-8 w-8 items-center justify-center rounded-xl border transition-all"
              :class="isAgentEnabled(agent.id) ? agent.colorClass : 'border-slate-200 bg-slate-50 text-slate-400'"
            >
              <component :is="agent.icon" class="h-4 w-4" />
            </span>
            <span class="tab-title text-xs font-bold tracking-wide">{{ agent.name }}</span>
            <span class="tab-desc mt-1 w-full truncate text-center text-[9px] font-bold text-slate-400">
              {{ isAgentEnabled(agent.id) ? getAgentSummary(agent.id) : '已关闭' }}
            </span>
          </button>
        </div>

      <!-- 2-Column Split Workspace Body -->
      <!-- 左右两栏布局：左侧参数表单(7列) + 右侧实时预览(5列) -->
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
                    <label>代码输出风格</label>
                    <div class="flex gap-1.5 bg-slate-50 p-1.5 rounded-xl border border-slate-100">
                      <button
                        v-for="opt in [
                          { label: '教学演示', value: 'tutorial' },
                          { label: '参考实现', value: 'reference' },
                          { label: '挑战练习', value: 'challenge' }
                        ]"
                        :key="opt.value"
                        type="button"
                        class="flex-1 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                        :class="localConfigs.code.output_style === opt.value ? 'bg-white text-slate-900 shadow-sm border border-slate-200' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                        @click="localConfigs.code.output_style = opt.value as any"
                      >
                        {{ opt.label }}
                      </button>
                    </div>
                    <p class="ctrl-helper">教学演示=完整代码+逐步注释；参考实现=精简代码+关键注释；挑战练习=框架代码+留空引导</p>
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

                  <div class="ctrl-switch-v2 flex justify-between items-center py-2 bg-slate-50/40 px-4 rounded-2xl border border-slate-100/50 mt-1">
                    <div class="sw-info flex flex-col gap-0.5">
                      <span class="sw-label">附带测试用例</span>
                      <span class="sw-desc">在代码末尾生成 assert 或单元测试验证正确性</span>
                    </div>
                    <label class="relative inline-flex items-center cursor-pointer select-none">
                      <input type="checkbox" v-model="localConfigs.code.include_tests" class="sr-only peer" />
                      <div class="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-main"></div>
                    </label>
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
                    <label>出题侧重</label>
                    <select v-model="localConfigs.quiz.emphasis">
                      <option value="foundations">概念基础辨析 (Foundations)</option>
                      <option value="application">场景应用分析 (Application)</option>
                      <option value="analysis">原理深度推导 (Analysis)</option>
                    </select>
                    <p class="ctrl-helper">决定出题角度：概念辨析侧重定义区分，场景应用侧重综合运用，原理推导侧重底层机制</p>
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
                    <label>推荐覆盖范围</label>
                    <div class="flex gap-1.5 bg-slate-50 p-1.5 rounded-xl border border-slate-100">
                      <button
                        v-for="opt in [
                          { label: '精选', value: 'core' },
                          { label: '延伸', value: 'extended' },
                          { label: '广泛', value: 'broad' }
                        ]"
                        :key="opt.value"
                        type="button"
                        class="flex-1 py-1.5 text-xs font-semibold rounded-lg border-none cursor-pointer transition-all"
                        :class="localConfigs.reading.coverage === opt.value ? 'bg-white text-slate-900 shadow-sm border border-slate-200' : 'bg-transparent text-slate-400 hover:text-slate-600'"
                        @click="localConfigs.reading.coverage = opt.value as any"
                      >
                        {{ opt.label }}
                      </button>
                    </div>
                    <p class="ctrl-helper">精选=3-5个最核心资源；延伸=均衡各类型；广泛=覆盖入门到前沿全链路</p>
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
                      <option value="research">顶会论文/前沿报告</option>
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

                <!-- VIDEO Agent parameters -->
                <template v-if="activeAgentId === 'video'">
                  <div class="ctrl-group">
                    <label>视觉风格</label>
                    <select v-model="localConfigs.video.style">
                      <option value="precision_light">精确明亮 (Precision Light)</option>
                      <option value="systems_dark">系统深色 (Systems Dark)</option>
                      <option value="editorial_classroom">编辑式课堂 (Editorial Classroom)</option>
                    </select>
                    <p class="ctrl-helper">视频画面的整体视觉风格与配色基调</p>
                  </div>
                  <div class="ctrl-group">
                    <label>叙事焦点</label>
                    <select v-model="localConfigs.video.focus">
                      <option value="concept">概念精讲 (Concept)</option>
                      <option value="process">流程演示 (Process)</option>
                      <option value="comparison">对比分析 (Comparison)</option>
                      <option value="practice">实战演练 (Practice)</option>
                    </select>
                    <p class="ctrl-helper">视频讲解的叙事策略与内容侧重点</p>
                  </div>
                  <div class="ctrl-group">
                    <label>配音音色</label>
                    <div class="seg-ctrl">
                      <button v-for="opt in [{ label: '教师', value: 'teacher' }, { label: '教练', value: 'coach' }]" :key="opt.value" type="button" class="seg-btn" :class="{ active: localConfigs.video.voice === opt.value }" @click="localConfigs.video.voice = opt.value as any">{{ opt.label }}</button>
                    </div>
                    <p class="ctrl-helper">TTS 语音合成的音色风格</p>
                  </div>
                  <div class="ctrl-group">
                    <label>画面比例</label>
                    <div class="seg-ctrl">
                      <button v-for="opt in [{ label: '16:9', value: '16:9' }, { label: '9:16', value: '9:16' }, { label: '1:1', value: '1:1' }]" :key="opt.value" type="button" class="seg-btn" :class="{ active: localConfigs.video.aspect_ratio === opt.value }" @click="localConfigs.video.aspect_ratio = opt.value as any">{{ opt.label }}</button>
                    </div>
                    <p class="ctrl-helper">视频输出分辨率与画面比例</p>
                  </div>
                </template>

              </div>
            </div>
          </div>

          <!-- Right Column: ── 内联 Preview + 7 预览 ── -->
          <div class="lg:col-span-5">
            <div class="preview-wrapper">
              <aside class="preview-panel" :class="{ disabled: !isAgentEnabled(activeAgentId) }">
                <div class="preview-header">
                  <div class="preview-header-left">
                    <span class="preview-eyebrow">内容预演</span>
                    <p class="preview-desc">模拟生成后打开此资源的阅读体验</p>
                  </div>
                  <span class="state-badge" :class="isAgentEnabled(activeAgentId) ? 'state-on' : 'state-off'">
                    <i></i>{{ isAgentEnabled(activeAgentId) ? '已加入生成' : '未启用' }}
                  </span>
                </div>

                <div class="preview-window" :class="{ 'window-disabled': !isAgentEnabled(activeAgentId) }">
                  <div class="window-titlebar">
                    <div class="titlebar-dots">
                      <span></span><span></span><span></span>
                    </div>
                    <div class="titlebar-label" v-if="previewAgentMeta">
                      <component :is="previewAgentMeta.icon" class="titlebar-icon" />
                      <span>{{ previewAgentMeta.name }}</span>
                    </div>
                    <span class="titlebar-tag">内容预演</span>
                  </div>

                  <div class="preview-content-area" v-if="previewAgentMeta">
                    <!-- content / Doc -->
                    <template v-if="activeAgentId === 'content'">
                      <div class="doc">
                        <small>{{ docStructure }} · {{ docDepth }}</small>
                        <h3>{{ previewTopic }}</h3>
                        <p class="lead">{{ docLead }}</p>
                        <div class="outline"><b>本节脉络</b><span>01 核心概念</span><span>02 底层原理</span><span>03 实际应用</span></div>
                        <article>
                          <b>01</b>
                          <div>
                            <h5>先建立一个清晰的理解框架</h5>
                            <p>{{ docParagraph }}</p>
                            <blockquote v-if="localConfigs.content.include_examples"><b>举个例子</b><span>把抽象机制放进真实学习场景中，对照输入、过程与结果理解它如何运作。</span></blockquote>
                          </div>
                        </article>
                      </div>
                    </template>

                    <!-- mindmap / Map -->
                    <template v-else-if="activeAgentId === 'mindmap'">
                      <div class="map">
                        <div class="grid"></div>
                        <div class="root">{{ mapShortTopic }}</div>
                        <div class="branch a"><b>核心概念</b><small>{{ mapLeaf }}</small></div>
                        <div class="branch b"><b>原理拆解</b><small>{{ localConfigs.mindmap.max_depth }} 层结构</small></div>
                        <div class="branch c"><b>实践应用</b><small>{{ mapRelation }}</small></div>
                        <i class="line la"></i><i class="line lb"></i><i class="line lc"></i>
                      </div>
                    </template>

                    <!-- code / Code -->
                    <template v-else-if="activeAgentId === 'code'">
                      <div class="code">
                        <header>
                          <div class="tabs">
                            <span class="tab active">{{ codeFilename }}</span>
                            <span class="tab">输出</span>
                          </div>
                          <small>{{ codeOutputStyle }} · {{ codeFocus }}</small>
                        </header>
                        <pre><code><i># {{ previewTopic }}</i>
<b>{{ codeKeyword }}</b> <em>learn_step</em>(concept):
    <b>if</b> <em>understood</em>(concept):
        <b>return</b> <q>"进入实践"</q>

    example = <em>build_example</em>(concept)
    <b>return</b> <em>explain</em>(example)</code></pre>
                        <footer>
                          <small>OUTPUT</small>
                          <p>✓ 示例运行完成，下一步将逐行解释关键逻辑</p>
                        </footer>
                      </div>
                    </template>

                    <!-- quiz / Quiz -->
                    <template v-else-if="activeAgentId === 'quiz'">
                      <div class="quiz">
                        <div class="progress"><span>第 1 题 / 共 {{ localConfigs.quiz.question_count }} 题</span><i><b></b></i></div>
                        <small>{{ quizDifficulty }} · {{ quizEmphasis }}</small>
                        <h3>关于"{{ quizShortTopic }}"，下面哪一项描述最准确？</h3>
                        <div class="options">
                          <div><b>A</b><span>只关注最终结果，不需要理解中间过程</span></div>
                          <div class="answer"><b>B</b><span>先建立概念模型，再通过实例验证理解</span></div>
                          <div><b>C</b><span>记住所有细节后才可以开始实践</span></div>
                        </div>
                        <p>作答后显示解析与对应知识点</p>
                      </div>
                    </template>

                    <!-- reading / Read -->
                    <template v-else-if="activeAgentId === 'reading'">
                      <div class="read">
                        <header><small>{{ readCoverage }}</small><h3>{{ previewTopic }} · 延伸阅读</h3><p>按相关性与阅读成本排序，帮助你从课程内容自然过渡到更深入的资料。</p></header>
                        <article v-for="item in readItems" :key="item.index"><b>{{ item.index }}</b><div><h5>{{ item.title }}</h5><p>{{ item.source }} · {{ readLanguage }}</p></div><span>{{ item.time }}</span></article>
                      </div>
                    </template>

                    <!-- ppt / Slide -->
                    <template v-else-if="activeAgentId === 'ppt'">
                      <div class="slides">
                        <aside>
                          <div class="thumb active">
                            <div class="thumb-bar"></div>
                            <div class="thumb-line"></div>
                            <div class="thumb-line short"></div>
                            <span>01</span>
                          </div>
                          <div class="thumb">
                            <div class="thumb-bar"></div>
                            <div class="thumb-line"></div>
                            <span>02</span>
                          </div>
                          <div class="thumb">
                            <div class="thumb-line"></div>
                            <div class="thumb-line short"></div>
                            <span>03</span>
                          </div>
                        </aside>
                        <main>
                          <div class="accent-bar"></div>
                          <div class="html-badge">HTML</div>
                          <small>{{ slideStyle }} / 01</small>
                          <h3>{{ previewTopic }}</h3>
                          <p>从一个关键问题开始，建立本次学习的核心理解框架。</p>
                          <div class="tags">
                            <span v-for="item in slideFocus" :key="item">{{ item }}</span>
                          </div>
                          <b class="slide-num">01 — 08</b>
                        </main>
                      </div>
                    </template>

                    <!-- cartoon / video / Video -->
                    <template v-else-if="activeAgentId === 'cartoon' || activeAgentId === 'video'">
                      <div class="video">
                        <div class="stage">
                          <div class="poster">
                            <span class="topic-text">{{ videoShortTopic }}</span>
                            <button type="button" aria-label="播放预演" tabindex="-1">
                              <PhPlay weight="fill" />
                            </button>
                          </div>
                          <div class="scene-bar">
                            <span v-for="scene in videoScenes" :key="scene">{{ scene }}</span>
                          </div>
                        </div>
                        <div class="controls">
                          <div class="timeline">
                            <span class="time">00:00</span>
                            <div class="track"><div class="fill"></div></div>
                            <span class="time">03:00</span>
                          </div>
                          <span class="mp4-badge">MP4</span>
                        </div>
                        <div class="story">
                          <div class="scene-card" v-for="scene in videoScenes" :key="scene">
                            <div class="scene-icon">▷</div>
                            <span>{{ scene }}</span>
                          </div>
                        </div>
                      </div>
                    </template>
                  </div>
                </div>

                <div class="impact-section" v-if="isAgentEnabled(activeAgentId) && impactLines.length">
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

                <div class="preview-note">
                  <PhSparkle class="note-icon" />
                  <span>内容结构示意 · 实际内容由多智能体完整生成</span>
                </div>
              </aside>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer: selected agents + action buttons -->
      <!-- 底部区域：已选智能体标签条 + 返回/启动操作按钮 -->
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
// 引入 Vue 响应式原语与生命周期钩子
import { computed, onMounted, ref, watch } from 'vue'
// Phosphor 图标（启动按钮 + 预览面板内联所需）
import {
  PhPaperPlaneTilt as Position,
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
  PhPlay,
} from '@phosphor-icons/vue'
// 轻量 toast 提示
import { toast } from 'vue-sonner'
// PPT 模板列表查询接口与类型
import {
  getPptTemplates,
  type PptTemplateOption,
} from '@/features/resource/api/resource'
// 学习场景与资源智能体 ID 类型
import type { LearningScenario, ResourceAgentId } from '@/features/resource/model/resource'
// 智能体元信息、场景选项与场景默认配置
import {
  MIN_AGENTS,
  getAgentMeta,
  scenarioOptions,
  getScenarioDesc,
  SCENARIO_DEFAULTS,
  agentMetaList,
  type AnyAgentConfigs,
} from '../model/catalog'

// 组件 props：学习场景、已启用智能体、各智能体配置与自然语言输入
const props = defineProps<{
  learningScenario: LearningScenario
  enabledAgentIds: ResourceAgentId[]
  agentConfigs: AnyAgentConfigs
  naturalInput?: string
}>()

// 事件输出：双向更新场景/智能体列表/配置，以及返回与启动动作
const emit = defineEmits<{
  'update:learningScenario': [value: LearningScenario]
  'update:enabledAgentIds': [value: ResourceAgentId[]]
  'update:agentConfigs': [value: AnyAgentConfigs]
  back: []
  launch: []
}>()

// 当前聚焦（选中）的智能体标签页 ID
const activeAgentId = ref<ResourceAgentId>('content')

// 学习场景双向计算属性：读 props、写时 emit 更新
const learningScenario = computed({
  get: () => props.learningScenario,
  set: (v) => emit('update:learningScenario', v),
})

// 已启用智能体列表双向计算属性
const enabledAgentIds = computed({
  get: () => props.enabledAgentIds,
  set: (v) => emit('update:enabledAgentIds', v),
})

// 本地配置深拷贝，避免直接修改父组件引用
const localConfigs = ref<AnyAgentConfigs>(JSON.parse(JSON.stringify(props.agentConfigs)))
// PPT 模板选项列表（onMounted 时从后端加载）
const pptTemplates = ref<PptTemplateOption[]>([])

// 当前激活智能体的元信息（名称、图标、颜色类）
const getActiveAgentMeta = computed(() => {
  return getAgentMeta(activeAgentId.value)
})

// 当前激活智能体的产出物中文标签（用于未启用提示）
const getActiveAgentOutputLabel = computed(() => {
  const map: Record<string, string> = {
    content: '课程讲解文档',
    mindmap: '思维导图图片',
    code: '代码实操案例',
    quiz: '随堂练习题库',
    reading: '拓展阅读文献',
    ppt: '演示幻灯课件',
    cartoon: '动画讲解视频',
    video: '讲解视频',
  }
  return map[activeAgentId.value] || '学习资源'
})

// 当前选中 PPT 模板的描述文案（自动模式或具体模板）
const selectedPptTemplateDescription = computed(() => {
  if (localConfigs.value.ppt.template === 'auto') {
    return '系统会根据知识类型自动匹配最合适的模板'
  }
  return pptTemplates.value.find(
    template => template.id === localConfigs.value.ppt.template,
  )?.description || '所选模板当前不可用，请重新选择'
})

// 组件挂载时从后端加载 PPT 模板列表
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

// 监听父组件 props 变化（场景切换/初始化等），同步深拷贝到本地副本
watch(() => props.agentConfigs, (newVal) => {
  localConfigs.value = JSON.parse(JSON.stringify(newVal))
}, { deep: true })

// 本地配置变更时同步 emit 回传父组件
watch(localConfigs, (newVal) => {
  emit('update:agentConfigs', JSON.parse(JSON.stringify(newVal)))
}, { deep: true })

// 判断指定智能体是否在已启用列表中
const isAgentEnabled = (id: string) => enabledAgentIds.value.includes(id as ResourceAgentId)

// 切换智能体启用/禁用，禁用时强制保留最低数量限制
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

// 选择学习场景并合并该场景的默认配置到本地配置
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

// 切换题型多选：至少保留一种题型
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

// 切换 PPT 大纲重点多选：至少保留一项
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

// ── 内联自 AgentTabs.vue ──────────────────────────────────────────────────────
const agents = computed(() => agentMetaList)

function getAgentSummary(id: string) {
  const configs = localConfigs.value
  if (id === 'content') {
    const structure: Record<string, string> = { progressive: '渐进式', summary_first: '先总后分', exam_points: '考点驱动', case_driven: '案例驱动' }
    const depth: Record<string, string> = { quick: '快速', standard: '标准', deep: '深度' }
    return `${structure[configs.content.structure] || configs.content.structure} · ${depth[configs.content.depth_level] || configs.content.depth_level}`
  }
  if (id === 'mindmap') {
    const type: Record<string, string> = { knowledge_tree: '知识树', exam_map: '考点图', comparison_map: '对比图' }
    return `${type[configs.mindmap.map_type] || configs.mindmap.map_type} · ${configs.mindmap.max_depth}层`
  }
  if (id === 'quiz') {
    const difficulty: Record<string, string> = { basic: '基础', adaptive: '自适应', exam: '考研' }
    return `${difficulty[configs.quiz.difficulty_mode] || configs.quiz.difficulty_mode} · ${configs.quiz.question_count}题`
  }
  if (id === 'code') {
    const language: Record<string, string> = { python: 'Python', c: 'C', cpp: 'C++', java: 'Java', go: 'Go', javascript: 'JS', typescript: 'TS' }
    const outputStyle: Record<string, string> = { tutorial: '教学', reference: '参考', challenge: '挑战' }
    return `${language[configs.code.programming_language] || configs.code.programming_language} · ${outputStyle[configs.code.output_style] || configs.code.output_style}`
  }
  if (id === 'reading') {
    const coverage: Record<string, string> = { core: '精选', extended: '延伸', broad: '广泛' }
    return `${coverage[configs.reading.coverage] || configs.reading.coverage} · ${configs.reading.max_items}篇`
  }
  if (id === 'ppt') {
    const style: Record<string, string> = { concept: '概念', case_driven: '案例', problem_led: '问题', review: '复习' }
    const density: Record<string, string> = { concise: '精炼', standard: '标准', detailed: '深入' }
    return `${style[configs.ppt.explanation_style] || configs.ppt.explanation_style} · ${density[configs.ppt.density] || configs.ppt.density}`
  }
  if (id === 'cartoon') {
    const style: Record<string, string> = { diagram: '图解', minimal: '简约', dark_tech: '暗黑', chalkboard: '黑板' }
    const depth: Record<string, string> = { overview: '概览', standard: '标准', deep: '深度' }
    return `${style[configs.cartoon.style] || configs.cartoon.style} · ${depth[configs.cartoon.depth] || configs.cartoon.depth}`
  }
  if (id === 'video') {
    const style: Record<string, string> = { precision_light: '精确明亮', systems_dark: '系统深色', editorial_classroom: '编辑式课堂' }
    const focus: Record<string, string> = { concept: '概念', process: '过程', comparison: '对比', practice: '实战' }
    return `${style[configs.video.style] || configs.video.style} · ${focus[configs.video.focus] || configs.video.focus}`
  }
  return id
}

// ── 内联自 Preview.vue ────────────────────────────────────────────────────────
const previewTopic = computed(() =>
  props.naturalInput?.trim() || '零基础学习 Python 多线程：底层原理与代码实践'
)

const previewAgentMeta = computed(() => ({
  content:  { name: '课程讲解文档',  icon: FileText,     },
  mindmap:  { name: '知识思维导图',  icon: ShareNetwork,  },
  code:     { name: '代码实操案例',  icon: CodeIcon,      },
  quiz:     { name: '随堂测验练习',  icon: CheckSquare,   },
  reading:  { name: '拓展阅读推荐',  icon: Books,         },
  ppt:      { name: '演示幻灯课件',  icon: Presentation,  },
  cartoon:  { name: '动画讲解视频',  icon: FilmStrip,     },
  video:    { name: '讲解视频',      icon: VideoCamera,   },
})[activeAgentId.value])

const impactLines = computed((): string[] => {
  const id = activeAgentId.value
  const c = localConfigs.value

  if (id === 'content') {
    const sLines: Record<string, string> = { progressive: '讲解从直观认识起步，逐步深入底层原理', summary_first: '先呈现全景结构图，再逐层进入关键细节', exam_points: '内容优先覆盖高频考点与常见题型', case_driven: '以真实问题为起点，在解题过程中引出概念' }
    const dLines: Record<string, string> = { quick: '快速讲述模式，简洁覆盖核心要点', standard: '标准讲解深度，概念与推导均衡展开', deep: '深入剖析底层机制，含学术层面论证' }
    const lines = [sLines[c.content.structure], dLines[c.content.depth_level]]
    if (c.content.include_examples) lines.push('穿插生动类比与案例辅助理解抽象理论')
    return lines.filter(Boolean) as string[]
  }
  if (id === 'mindmap') {
    const tLines: Record<string, string> = { knowledge_tree: '以核心知识树组织，梳理层级关系', exam_map: '聚焦高频考点，节点标注考察频率', comparison_map: '横向对比维度，强化多概念辨析' }
    const lLines: Record<string, string> = { keyword: '叶节点仅保留关键词，结构精炼', brief_note: '叶节点附简要注释，便于自查', annotated: '叶节点含详细说明，适合深度复习' }
    const lines = [tLines[c.mindmap.map_type], `节点深度限制 ${c.mindmap.max_depth} 层`, lLines[c.mindmap.leaf_detail]]
    if (c.mindmap.show_relations) lines.push('用虚线标注跨分支的非层级关联')
    return lines.filter(Boolean) as string[]
  }
  if (id === 'code') {
    const langMap: Record<string, string> = { python: 'Python', java: 'Java', cpp: 'C++', c: 'C', go: 'Go', javascript: 'JavaScript', typescript: 'TypeScript' }
    const sLines: Record<string, string> = { tutorial: '完整可运行代码，含逐步注释和运行说明', reference: '精简参考实现，聚焦核心逻辑和接口', challenge: '框架代码+提示引导，关键实现留空' }
    const lines = [`使用 ${langMap[c.code.programming_language] ?? c.code.programming_language} 生成实战案例`, sLines[c.code.output_style]]
    if (c.code.include_tests) lines.push('代码末尾附带 assert 或单元测试用例')
    return lines.filter(Boolean) as string[]
  }
  if (id === 'quiz') {
    const dLines: Record<string, string> = { basic: '题目侧重概念巩固，难度友好', adaptive: '根据知识点自动调节难度梯度', exam: '仿考研真题风格，高混淆度选项' }
    const types = (c.quiz.question_types as string[]).map((t) => ({ single: '单选', multiple: '多选', judge: '判断', fill: '填空' })[t]).filter(Boolean)
    return [dLines[c.quiz.difficulty_mode], `共 ${c.quiz.question_count} 道题，题型：${types.join(' / ')}`].filter(Boolean) as string[]
  }
  if (id === 'reading') {
    const cLines: Record<string, string> = { core: '精选最核心、最权威的 3-5 个资源', extended: '均衡推荐各类型延伸资料', broad: '广泛覆盖从入门到前沿的全链路' }
    const fLines: Record<string, string> = { textbook: '来源以经典教材和学术专著为主', engineering: '来源以技术博客和官方文档为主', research: '来源以 arXiv / IEEE 等学术论文为主' }
    return [cLines[c.reading.coverage], `最多推荐 ${c.reading.max_items} 篇`, fLines[c.reading.focus]].filter(Boolean) as string[]
  }
  if (id === 'ppt') {
    const sLines: Record<string, string> = { concept: '以经典概念精讲结构组织幻灯片', case_driven: '以项目案例驱动每张幻灯片叙述', problem_led: '从启发性问题引出每个知识点', review: '提炼考点要素，适合复习冲刺' }
    const dLines: Record<string, string> = { concise: '极简排版，每页聚焦单一要点', standard: '标准教学密度，图文均衡', detailed: '图文丰富，覆盖完整推导与案例' }
    const focusLabels = (c.ppt.focus as string[]).map((f) => ({ core_concepts: '核心概念', cases: '典型案例', pitfalls: '避坑指南', derivation: '数学推导' })[f]).filter(Boolean)
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

// ── 内联自 7 个 preview/*.vue 的计算属性 ───────────────────────────────────────
// Doc (content)
const docStructure = computed(() => ({ progressive: '渐进式引导', summary_first: '先总后分', exam_points: '考点驱动', case_driven: '案例驱动' })[localConfigs.value.content.structure])
const docDepth = computed(() => ({ quick: '快速讲述', standard: '标准深度', deep: '深度剖析' })[localConfigs.value.content.depth_level])
const docLead = computed(() => ({
  exam_points: '围绕高频考点组织讲解，明确常见题型、判断依据与易错边界。',
  case_driven: '从一个真实问题出发，在解决过程里逐步拆开概念与实现方法。',
  summary_first: '先用一张全景图说明知识结构，再逐层进入关键细节。',
  progressive: '从直观认识开始，逐步走到底层机制，最后把概念放进真实实践中。',
})[localConfigs.value.content.structure])
const docParagraph = computed(() => ({
  weak_points: '优先澄清容易混淆的概念，通过对比说明它们在边界条件和实际行为上的差异。',
  full_coverage: '覆盖定义、运行机制、常见用法和限制条件，让知识点形成完整闭环。',
  key_concepts: '聚焦最关键的概念与因果关系，先抓住理解后续内容所需的主干。',
})[localConfigs.value.content.focus_mode])

// Map (mindmap)
const mapShortTopic = computed(() => previewTopic.value.length > 22 ? `${previewTopic.value.slice(0, 22)}…` : previewTopic.value)
const mapLeaf = computed(() => ({ keyword: '关键词', brief_note: '简要注释', annotated: '详细说明' })[localConfigs.value.mindmap.leaf_detail])
const mapRelation = computed(() => localConfigs.value.mindmap.show_relations ? '含跨分支关联' : '纯树状脉络')

// Code (code)
const codeFilename = computed(() => `practice.${({ python: 'py', c: 'c', cpp: 'cpp', java: 'java', go: 'go', javascript: 'js', typescript: 'ts' })[localConfigs.value.code.programming_language]}`)
const codeKeyword = computed(() => localConfigs.value.code.programming_language === 'python' ? 'def' : 'function')
const codeOutputStyle = computed(() => ({ tutorial: '教学演示', reference: '参考实现', challenge: '挑战练习' })[localConfigs.value.code.output_style])
const codeFocus = computed(() => ({ syntax: '语法讲解', application: '工程应用', debugging: '调试分析' })[localConfigs.value.code.focus])

// Quiz (quiz)
const quizShortTopic = computed(() => previewTopic.value.length > 18 ? `${previewTopic.value.slice(0, 18)}…` : previewTopic.value)
const quizDifficulty = computed(() => ({ basic: '概念巩固', adaptive: '自适应难度', exam: '考试强化' })[localConfigs.value.quiz.difficulty_mode])
const quizEmphasis = computed(() => ({ foundations: '概念辨析', application: '场景应用', analysis: '原理推导' })[localConfigs.value.quiz.emphasis])

// Read (reading)
const readCoverage = computed(() => ({ core: '精选核心', extended: '课程延伸', broad: '广泛覆盖' })[localConfigs.value.reading.coverage])
const readLanguage = computed(() => ({ chinese: '中文', english: '英文', both: '中英双语' })[localConfigs.value.reading.language_preference])
const readItems = computed(() => [
  { index: '01', title: '核心机制：从概念模型到运行过程', source: '基础导读', time: '8 min' },
  { index: '02', title: '把关键原理放进真实项目中验证', source: localConfigs.value.reading.focus === 'research' ? '研究论文' : '实践指南', time: '12 min' },
  { index: '03', title: '常见误区、边界条件与进一步探索', source: '进阶资料', time: '15 min' },
].slice(0, Math.min(3, localConfigs.value.reading.max_items)))

// Slide (ppt)
const slideStyle = computed(() => ({ concept: '概念精讲', case_driven: '案例驱动', problem_led: '问题引导', review: '复习提炼' })[localConfigs.value.ppt.explanation_style])
const slideFocus = computed(() => localConfigs.value.ppt.focus.slice(0, 3).map((item: string) => ({ core_concepts: '核心概念', cases: '案例分析', pitfalls: '易错提醒', derivation: '推导过程' } as Record<string, string>)[item]))

// Video (cartoon + video)
const videoShortTopic = computed(() => previewTopic.value.length > 18 ? `${previewTopic.value.slice(0, 18)}…` : previewTopic.value)
const videoScenes = computed(() => {
  if (activeAgentId.value === 'video') {
    return ({ concept: ['提出问题', '解释概念', '总结要点'], process: ['起始状态', '过程演化', '结果回顾'], comparison: ['对象 A', '差异对照', '对象 B'], practice: ['任务说明', '动手演示', '运行结果'] })[localConfigs.value.video.focus] ?? ['开场', '讲解', '总结']
  }
  // cartoon
  return ({ overview: ['概念引入', '核心要点', '快速回顾'], standard: ['问题引入', '原理解析', '操作演示', '要点总结'], deep: ['问题引入', '原理剖析', '逐步演示', '变体讨论', '深度总结'] })[localConfigs.value.cartoon.depth] ?? ['开场', '讲解', '总结']
})
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

/* ── 内联自 AgentTabs.vue ────────────────────────────────────────────────── */
.agent-tab-item {
  border-color: rgb(15 23 42 / 6%);
  background: #fff;
}
.agent-tab-item:hover {
  border-color: rgb(15 23 42 / 15%);
}
.agent-tab-item.active {
  border-color: var(--color-primary);
  box-shadow: 0 4px 16px rgb(99 102 241 / 6%);
}
.agent-tab-item.disabled-tab {
  opacity: 0.55;
  background: rgb(248 250 252 / 80%);
}
.tab-icon-wrap {
  border-color: rgb(15 23 42 / 5%);
}
.tab-title {
  color: var(--color-text-strong);
}

/* ── 内联自 Preview.vue ──────────────────────────────────────────────────── */
.preview-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  align-self: stretch;
}
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
.state-on i { width: 6px; height: 6px; border-radius: 50%; background: #20b986; flex-shrink: 0; animation: pulse-dot 2s ease-in-out infinite; }
.state-off { color: #8b95a4; background: #f1f3f6; border-color: #e0e5eb; }
.state-off i { width: 6px; height: 6px; border-radius: 50%; background: #aeb6c1; flex-shrink: 0; }
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.5; transform: scale(1.3); }
}
.preview-window {
  border: 1px solid #dce2ea;
  border-radius: 14px;
  background: #ffffff;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(30, 50, 80, 0.07);
  transition: opacity 0.2s ease, filter 0.2s ease;
  flex: 1;
}
.window-disabled { opacity: 0.45; filter: grayscale(30%); pointer-events: none; }
.window-titlebar {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 38px;
  padding: 0 14px;
  border-bottom: 1px solid #edf0f4;
  background: #f7f9fb;
}
.titlebar-dots { display: flex; gap: 5px; }
.titlebar-dots span { width: 9px; height: 9px; border-radius: 50%; background: #d5d9e0; }
.titlebar-dots span:nth-child(1) { background: #f9897b; }
.titlebar-dots span:nth-child(2) { background: #f9c461; }
.titlebar-dots span:nth-child(3) { background: #5fc96e; }
.titlebar-label { display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 700; color: #2c3a4d; flex: 1; }
.titlebar-icon { width: 13px; height: 13px; color: #2c8f87; }
.titlebar-tag { font-size: 9px; font-weight: 700; color: #aab2be; letter-spacing: 0.06em; }
.preview-content-area { overflow: hidden; max-height: 380px; overflow-y: auto; }
.impact-section { background: #f8fafc; border: 1px solid #edf1f5; border-radius: 11px; padding: 12px 14px; }
.impact-header { display: flex; align-items: center; gap: 6px; margin-bottom: 9px; font-size: 9.5px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; color: #7b8899; }
.impact-icon { width: 12px; height: 12px; color: #2c8f87; }
.impact-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.impact-list li { display: flex; align-items: flex-start; gap: 6px; font-size: 11px; color: #4a5568; line-height: 1.55; }
.dot-icon { width: 13px; height: 13px; color: #3a9b91; flex-shrink: 0; margin-top: 1px; }
.preview-note { display: flex; align-items: center; justify-content: center; gap: 6px; padding: 2px 0 0; color: #9aa3b0; font-size: 10px; }
.note-icon { width: 11px; height: 11px; color: #3c958c; }
.preview-panel.disabled .impact-section,
.preview-panel.disabled .preview-header { opacity: 0.6; }

/* ── 内联自 preview/Doc.vue ──────────────────────────────────────────────── */
.doc { padding: 30px 32px; color: #6d7989; }
.doc small { color: #2c8f87; font-size: 9px; font-weight: 800; }
.doc h3 { max-width: 520px; margin: 9px 0 8px; color: #182637; font-size: 22px; line-height: 1.3; letter-spacing: -.025em; }
.doc p { margin: 0; font-size: 11px; line-height: 1.75; }
.lead { max-width: 560px; font-size: 12px; }
.outline { display: flex; flex-wrap: wrap; gap: 14px; margin: 24px 0; padding: 13px 0; border-block: 1px solid #edf0f3; font-size: 9px; }
.outline b { margin-right: auto; color: #647285; }
.doc article { display: grid; grid-template-columns: 28px 1fr; gap: 14px; }
.doc article > b { color: #2c8f87; font-size: 10px; }
.doc h5 { margin: 0 0 7px; color: #263648; font-size: 13px; }
.doc blockquote { display: grid; gap: 4px; margin: 14px 0 0; padding: 11px 13px; border-left: 2px solid #46a99b; background: #f3f8f7; font-size: 10px; line-height: 1.55; }
.doc blockquote b { color: #276f68; }

/* ── 内联自 preview/Map.vue ──────────────────────────────────────────────── */
.map { position: relative; min-height: 414px; overflow: hidden; background: #fbfcfd; }
.map .grid { position: absolute; inset: 0; opacity: .45; background-image: radial-gradient(#ccd5df 1px, transparent 1px); background-size: 18px 18px; }
.root,.branch { position: absolute; z-index: 2; border: 1px solid #dce5e7; border-radius: 10px; background: #fff; box-shadow: 0 8px 22px rgb(35 53 73 / 7%); }
.root { top: 172px; left: 50%; width: 162px; padding: 13px; transform: translateX(-50%); color: #1d514e; background: #e9f5f3; font-size: 11px; font-weight: 800; text-align: center; }
.branch { display: grid; width: 126px; gap: 4px; padding: 11px 12px; color: #344355; font-size: 10px; }
.branch small { color: #8b96a4; font-size: 8px; }
.a { top: 78px; left: 7%; }
.b { top: 78px; right: 7%; }
.c { right: 12%; bottom: 54px; }
.line { position: absolute; z-index: 1; width: 120px; height: 1px; background: #a9c9c4; transform-origin: left; }
.la { top: 177px; left: 27%; transform: rotate(18deg); }
.lb { top: 177px; right: 25%; transform: rotate(162deg); }
.lc { top: 208px; left: 59%; transform: rotate(34deg); }

/* ── 内联自 preview/Code.vue ─────────────────────────────────────────────── */
.code { min-height: 320px; color: #2d3748; background: #fafaf8; display: flex; flex-direction: column; }
.code header { display: flex; height: 42px; align-items: center; justify-content: space-between; padding: 0 16px; border-bottom: 1px solid #e8eaf0; background: #f0f1f5; }
.code .tabs { display: flex; gap: 0; height: 100%; align-items: flex-end; }
.code .tab { padding: 0 14px; height: 32px; line-height: 32px; font: 10px var(--font-mono, monospace); color: #8b9ab0; border-radius: 6px 6px 0 0; cursor: default; }
.code .tab.active { background: #fafaf8; color: #2d3748; border: 1px solid #e8eaf0; border-bottom: 1px solid #fafaf8; margin-bottom: -1px; }
.code header small { color: #8b9ab0; font-size: 9px; letter-spacing: .04em; }
.code pre { margin: 0; padding: 20px 22px; overflow: auto; font: 11px/2 var(--font-mono, monospace); flex: 1; background: #fafaf8; }
.code i { color: #8b9ab0; font-style: normal; }
.code b { color: #4776ab; font-weight: 700; }
.code em { color: #3a7d44; font-style: normal; }
.code q { color: #b07a2a; quotes: none; }
.code footer { margin: 0 16px 16px; padding: 10px 14px; border: 1px solid #e2e8f0; border-radius: 8px; background: #f0faf5; font: 9px/1.5 var(--font-mono, monospace); }
.code footer small { color: #8b9ab0; font-weight: 700; letter-spacing: .05em; }
.code footer p { margin: 5px 0 0; color: #2d7a50; }

/* ── 内联自 preview/Quiz.vue ─────────────────────────────────────────────── */
.quiz { padding: 28px 30px; }
.quiz .progress { display: grid; gap: 8px; color: #8390a1; font-size: 9px; }
.quiz .progress i { height: 3px; overflow: hidden; border-radius: 3px; background: #edf1f4; }
.quiz .progress b { display: block; width: 18%; height: 100%; background: #3a9b91; }
.quiz small { display: inline-block; margin-top: 22px; color: #2f8179; font-size: 9px; font-weight: 800; }
.quiz h3 { margin: 9px 0 18px; color: #182637; font-size: 17px; line-height: 1.45; }
.options { display: grid; gap: 9px; }
.options div { display: flex; align-items: center; gap: 11px; padding: 11px 12px; border: 1px solid #e5e9ee; border-radius: 9px; color: #627083; font-size: 10px; }
.options b { display: grid; width: 22px; height: 22px; place-items: center; border-radius: 6px; color: #7c899a; background: #f2f4f7; font-size: 9px; }
.options .answer { border-color: #abd5ce; color: #275d59; background: #f2f9f7; }
.options .answer b { color: #fff; background: #3a9b91; }
.quiz p { margin: 14px 0 0; color: #9aa3af; font-size: 9px; }

/* ── 内联自 preview/Read.vue ─────────────────────────────────────────────── */
.read { padding: 28px 30px; }
.read header { padding-bottom: 18px; border-bottom: 1px solid #edf0f3; }
.read small { color: #2f8179; font-size: 9px; font-weight: 800; }
.read h3 { margin: 7px 0; color: #182637; font-size: 18px; }
.read header p { margin: 0; color: #778496; font-size: 10px; line-height: 1.6; }
.read article { display: grid; grid-template-columns: 28px 1fr auto; align-items: center; gap: 10px; padding: 16px 0; border-bottom: 1px solid #edf0f3; }
.read article > b { color: #b0b7c1; font-size: 9px; }
.read h5 { margin: 0 0 4px; color: #344355; font-size: 11px; }
.read article p, .read article > span { margin: 0; color: #909aa8; font-size: 8px; }

/* ── 内联自 preview/Slide.vue ────────────────────────────────────────────── */
.slides { display: grid; min-height: 320px; grid-template-columns: 64px 1fr; background: #f4f5f7; }
.slides aside { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 16px 8px; border-right: 1px solid #e2e5ea; background: #f4f5f7; }
.thumb { position: relative; width: 44px; min-height: 30px; padding: 5px 6px 16px; border: 1px solid #dde1e8; border-radius: 3px; background: #fff; display: flex; flex-direction: column; gap: 4px; cursor: default; }
.thumb.active { border-color: #5c6bc0; box-shadow: 0 0 0 1px #5c6bc0; }
.thumb-bar { height: 4px; border-radius: 2px; background: #c5cae9; }
.thumb.active .thumb-bar { background: #5c6bc0; }
.thumb-line { height: 2px; border-radius: 1px; background: #e8eaf0; }
.thumb-line.short { width: 60%; }
.thumb span { position: absolute; bottom: 3px; right: 4px; font-size: 6px; color: #9fa8b0; }
.slides main { position: relative; padding: 0 36px 28px; background: #fff; display: flex; flex-direction: column; justify-content: center; overflow: hidden; }
.accent-bar { position: absolute; top: 0; left: 0; right: 0; height: 5px; background: linear-gradient(90deg, #5c6bc0 0%, #7986cb 100%); }
.html-badge { position: absolute; top: 14px; right: 16px; padding: 2px 7px; border: 1px solid #c5cae9; border-radius: 4px; background: #e8eaf0; color: #5c6bc0; font-size: 8px; font-weight: 700; letter-spacing: .06em; }
.slides main small { color: #7986cb; font-size: 8px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; margin-bottom: 8px; }
.slides h3 { max-width: 380px; margin: 0 0 10px; color: #1a202c; font-size: 20px; line-height: 1.25; }
.slides p { max-width: 340px; margin: 0; color: #718096; font-size: 10px; line-height: 1.7; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 20px; }
.tags span { padding: 5px 9px; border: 1px solid #e2e8f0; border-radius: 5px; background: #f7f8fc; color: #4a5568; font-size: 8px; }
.slide-num { position: absolute; right: 20px; bottom: 16px; color: #a0aec0; font-size: 8px; font-weight: 600; }

/* ── 内联自 preview/Video.vue ────────────────────────────────────────────── */
.video { min-height: 320px; padding: 16px; background: #fff; display: flex; flex-direction: column; gap: 12px; }
.stage { position: relative; border-radius: 10px; overflow: hidden; border: 1px solid #e2e8f0; aspect-ratio: 16 / 9; background: #e8f0fe; flex-shrink: 0; }
.poster { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 100%; gap: 14px; }
.topic-text { max-width: 70%; color: #3c4a6b; font-size: 13px; font-weight: 600; text-align: center; line-height: 1.4; }
.video button { display: grid; width: 40px; height: 40px; place-items: center; border: 0; border-radius: 50%; color: #fff; background: #4f6ef7; box-shadow: 0 4px 16px rgb(79 110 247 / 30%); cursor: default; pointer-events: none; }
.video button svg { width: 15px; height: 15px; }
.scene-bar { position: absolute; bottom: 0; left: 0; right: 0; display: flex; gap: 0; background: rgb(255 255 255 / 82%); backdrop-filter: blur(4px); border-top: 1px solid rgb(0 0 0 / 6%); }
.scene-bar span { flex: 1; padding: 6px 4px; color: #4a5568; font-size: 7.5px; font-weight: 500; text-align: center; border-right: 1px solid rgb(0 0 0 / 6%); }
.scene-bar span:last-child { border-right: none; }
.controls { display: flex; align-items: center; gap: 10px; padding: 0 2px; }
.timeline { display: flex; flex: 1; align-items: center; gap: 8px; }
.time { color: #8b9ab0; font: 8px var(--font-mono, monospace); white-space: nowrap; }
.track { flex: 1; height: 3px; border-radius: 2px; background: #e2e8f0; }
.fill { width: 28%; height: 100%; border-radius: 2px; background: #4f9e9a; }
.mp4-badge { padding: 2px 7px; border: 1px solid #c5cae9; border-radius: 4px; background: #eef0fb; color: #5c6bc0; font-size: 8px; font-weight: 700; letter-spacing: .06em; white-space: nowrap; }
.story { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.scene-card { display: flex; flex-direction: column; align-items: center; gap: 5px; padding: 10px 6px; border: 1px solid #e8eaf0; border-radius: 8px; background: #fff; }
.scene-icon { color: #4f6ef7; font-size: 12px; }
.scene-card span { color: #4a5568; font-size: 8px; text-align: center; }
</style>
