<template>
  <div class="elegant-generator-layout">
    <transition name="page-slide" mode="out-in">

      <div v-if="currentPhase === 'input'" class="phase-view input-view" key="input">
        <div class="input-container">
          <div class="welcome-header">
            <div class="sparkle-icon"><el-icon><MagicStick /></el-icon></div>
            <h1 class="greeting-title">今天想学点什么？</h1>
            <p class="greeting-subtitle">
              请用自然语言描述你的学习需求，系统将直接向多智能体发送指令。
            </p>
          </div>

          <div class="search-box-wrapper" :class="{ 'is-focused': isInputFocused }">
            <el-input
              v-model="naturalInput"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 8 }"
              placeholder="例如：我是软件工程大二学生，明天考《操作系统》。我搞不懂死锁的四个必要条件，我喜欢看知识图谱，请帮我生成复习资料和几道自测题…"
              class="elegant-textarea"
              @focus="isInputFocused = true"
              @blur="isInputFocused = false"
              @keydown.enter.exact.prevent="goToPersonalize"
            />
            <div class="search-actions">
              <div class="action-left">
                <span class="ai-hint"><el-icon><Cpu /></el-icon> 多智能体协同，全自动构建个性化资源流</span>
              </div>
              <el-button
                type="primary"
                class="generate-btn"
                round
                :disabled="!naturalInput.trim()"
                @click="goToPersonalize"
              >
                下一步：配置智能体 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
              </el-button>
            </div>
          </div>

          <div class="suggestion-area">
            <span class="suggestion-label">快捷指令：</span>
            <div class="suggestion-tags">
              <el-tag v-for="(prompt, index) in quickPrompts" :key="index" class="s-tag" effect="plain" round @click="naturalInput = prompt">
                {{ prompt }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="currentPhase === 'personalize'" class="phase-view personalize-view" key="personalize">
        <div class="aurora-background"></div>
        <div class="personalize-container">
          <div class="view-header">
            <el-tag size="small" effect="dark" round class="header-badge">AI CONFIGURATION</el-tag>
            <h2>多智能体参数定制中心</h2>
            <p>请为即将出场的 AI 智能体配置加工参数，您的指令将作为最高优先级要求贯穿全局。</p>
          </div>

          <div class="scenario-selector-v2">
            <div
              v-for="s in [
                { icon: '备', name: '考试备考', value: 'exam_prep' },
                { icon: '学', name: '日常学习', value: 'daily_review' },
                { icon: '践', name: '项目实践', value: 'project_practice' },
                { icon: '预', name: '预习自学', value: 'self_study' }
              ]"
              :key="s.value"
              :class="['scenario-card', { active: learningScenario === s.value }]"
              @click="learningScenario = s.value as LearningScenario; applyScenarioDefaults(learningScenario)"
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
              <div class="config-card-v2" :class="{ disabled: agent.disabled, 'agent-off': !isAgentEnabled(agent.id) && !agent.disabled }" v-for="agent in personalizeAgents" :key="agent.id">
                <div class="cc-header-v2">
                  <div class="cc-icon-wrap" :class="agent.colorClass">
                    <el-icon><component :is="agent.icon" /></el-icon>
                  </div>
                  <span class="cc-title">{{ agent.name }}</span>
                  <div class="cc-header-switch">
                    <el-switch
                      v-if="!agent.disabled"
                      :model-value="isAgentEnabled(agent.id)"
                      @change="toggleAgent(agent.id)"
                      active-color="#0369A1"
                    />
                    <el-tag v-else size="small" type="info">敬请期待</el-tag>
                  </div>
                </div>

                <div class="cc-body-v2" :class="{ 'body-disabled': !isAgentEnabled(agent.id) && !agent.disabled }">
                  <template v-if="agent.id === 'content'">
                    <div class="ctrl-group">
                      <label>讲解结构</label>
                      <el-select v-model="agentConfigs.content.structure" size="default" class="w-full custom-select">
                        <el-option label="渐进式引导 (Progressive)" value="progressive" />
                        <el-option label="先总后分 (Summary First)" value="summary_first" />
                        <el-option label="考点驱动 (Exam Points)" value="exam_points" />
                        <el-option label="案例驱动 (Case Driven)" value="case_driven" />
                      </el-select>
                    </div>
                    <div class="ctrl-group ctrl-switch-group-v2">
                      <div class="ctrl-switch-v2">
                        <div class="sw-info">
                          <span class="sw-label">涵盖易错点解析</span>
                          <span class="sw-desc">针对常见误区进行深度剖析</span>
                        </div>
                        <el-switch v-model="agentConfigs.content.include_common_mistakes" />
                      </div>
                      <div class="ctrl-switch-v2">
                        <div class="sw-info">
                          <span class="sw-label">丰富生活化示例</span>
                          <span class="sw-desc">用直观的案例辅助理解抽象概念</span>
                        </div>
                        <el-switch v-model="agentConfigs.content.include_examples" />
                      </div>
                    </div>
                  </template>

                  <template v-if="agent.id === 'knowledge_graph'">
                    <div class="ctrl-group">
                      <label>图谱布局</label>
                      <el-select v-model="agentConfigs.knowledge_graph.layout_mode" size="default" class="w-full custom-select">
                        <el-option label="力导向网络" value="force" />
                        <el-option label="环形知识簇" value="radial" />
                        <el-option label="层级结构" value="hierarchy" />
                      </el-select>
                    </div>
                    <div class="ctrl-group">
                      <div class="slider-label-row">
                        <label>最大知识点</label>
                        <span class="slider-value"><b>{{ agentConfigs.knowledge_graph.max_nodes }}</b> 个</span>
                      </div>
                      <el-slider v-model="agentConfigs.knowledge_graph.max_nodes" :min="6" :max="32" :step="1" class="custom-slider-v2" />
                    </div>
                    <div class="ctrl-group">
                      <label>重点标注</label>
                      <el-radio-group v-model="agentConfigs.knowledge_graph.highlight_mode" size="small" class="custom-radio-group">
                        <el-radio-button label="weak_points">薄弱点</el-radio-button>
                        <el-radio-button label="key_points">关键点</el-radio-button>
                        <el-radio-button label="all">全部</el-radio-button>
                      </el-radio-group>
                    </div>

                  </template>

                  <template v-if="agent.id === 'mindmap'">
                    <div class="ctrl-group">
                      <label>导图生成策略</label>
                      <el-select v-model="agentConfigs.mindmap.map_type" size="default" class="w-full custom-select">
                        <el-option label="核心知识树 (Knowledge Tree)" value="knowledge_tree" />
                        <el-option label="高频考点图 (Exam Map)" value="exam_map" />
                        <el-option label="对比复习图 (Comparison)" value="comparison_map" />
                      </el-select>
                    </div>
                    <div class="ctrl-group">
                      <div class="slider-label-row">
                        <label>节点发散层级</label>
                        <span class="slider-value"><b>{{ agentConfigs.mindmap.max_depth }}</b> 层</span>
                      </div>
                      <el-slider v-model="agentConfigs.mindmap.max_depth" :min="2" :max="5" :step="1" class="custom-slider-v2" show-stops />
                    </div>
                  </template>

                  <template v-if="agent.id === 'code'">
                    <div class="ctrl-group">
                      <label>编程语言目标</label>
                      <el-select v-model="agentConfigs.code.programming_language" size="default" class="w-full custom-select">
                        <el-option label="Python" value="python" />
                        <el-option label="C" value="c" />
                        <el-option label="JavaScript" value="javascript" />
                        <el-option label="TypeScript" value="typescript"/>
                        <el-option label="C++" value="cpp" />
                        <el-option label="Java" value="java" />
                        <el-option label="Go" value="go" />
                      </el-select>
                    </div>
                    <div class="ctrl-group">
                      <label>案例难度级别</label>
                      <el-radio-group v-model="agentConfigs.code.difficulty" size="small" class="custom-radio-group">
                        <el-radio-button label="beginner">入门</el-radio-button>
                        <el-radio-button label="intermediate">进阶</el-radio-button>
                        <el-radio-button label="advanced">挑战</el-radio-button>
                      </el-radio-group>
                    </div>
                    <div class="ctrl-group">
                      <label>案例交付形态</label>
                      <el-radio-group v-model="agentConfigs.code.case_type" size="small" class="custom-radio-group">
                        <el-radio-button label="basic_demo">基础教学</el-radio-button>
                        <el-radio-button label="algorithm_template">算法模板</el-radio-button>
                      </el-radio-group>
                    </div>
                  </template>

                  <template v-if="agent.id === 'quiz'">
                    <div class="ctrl-group">
                      <label>测验难度引擎</label>
                      <el-radio-group v-model="agentConfigs.quiz.difficulty_mode" size="small" class="custom-radio-group">
                        <el-radio-button label="basic">基础巩固</el-radio-button>
                        <el-radio-button label="adaptive">动态自适应</el-radio-button>
                        <el-radio-button label="exam">硬核考研</el-radio-button>
                      </el-radio-group>
                    </div>
                    <div class="ctrl-group">
                      <label>题型偏好（可多选）</label>
                      <el-checkbox-group v-model="agentConfigs.quiz.question_types" class="question-type-group">
                        <el-checkbox label="single">单选题</el-checkbox>
                        <el-checkbox label="multiple">多选题</el-checkbox>
                        <el-checkbox label="judge">判断题</el-checkbox>
                        <el-checkbox label="fill">填空题</el-checkbox>
                      </el-checkbox-group>
                    </div>
                    <div class="ctrl-group">
                      <div class="slider-label-row">
                        <label>生成题目数量</label>
                        <span class="slider-value"><b>{{ agentConfigs.quiz.question_count }}</b> 道</span>
                      </div>
                      <el-slider v-model="agentConfigs.quiz.question_count" :min="1" :max="20" :step="1" class="custom-slider-v2" />
                    </div>
                  </template>

                  <template v-if="agent.id === 'reading'">
                    <div class="ctrl-group">
                      <label>阅读文献深度</label>
                      <el-select v-model="agentConfigs.reading.reading_depth" size="default" class="w-full custom-select">
                        <el-option label="课程内延展 (Course Extended)" value="course_extended" />
                        <el-option label="工程化实践 (Engineering)" value="engineering" />
                        <el-option label="前沿学术论文 (Frontier)" value="frontier" />
                      </el-select>
                    </div>
                    <div class="ctrl-group">
                      <label>资料语言偏好</label>
                      <el-radio-group v-model="agentConfigs.reading.language_preference" size="small" class="custom-radio-group">
                        <el-radio-button label="chinese">中文优先</el-radio-button>
                        <el-radio-button label="bilingual">中英双语</el-radio-button>
                        <el-radio-button label="english">英文原版</el-radio-button>
                      </el-radio-group>
                    </div>
                    <div class="ctrl-group">
                      <div class="slider-label-row">
                        <label>文献推送数量</label>
                        <span class="slider-value"><b>{{ agentConfigs.reading.max_items }}</b> 篇</span>
                      </div>
                      <el-slider v-model="agentConfigs.reading.max_items" :min="1" :max="10" :step="1" class="custom-slider-v2" />
                    </div>
                  </template>

                  <template v-if="agent.id === 'ppt'">
                    <div class="ctrl-group">
                      <label>输出格式</label>
                      <el-radio-group v-model="agentConfigs.ppt.output_format" size="small" class="custom-radio-group">
                        <el-radio-button label="preview">在线预览</el-radio-button>
                        <el-radio-button label="pptx">生成PPTX源文件</el-radio-button>
                      </el-radio-group>
                    </div>
                    <div class="ctrl-group">
                      <label>幻灯片主题风格</label>
                      <el-select v-model="agentConfigs.ppt.template_id" size="default" class="w-full custom-select">
                        <el-option label="经典学术蓝 (Logic Blue)" value="theme-logic-blue" />
                        <el-option label="现代开发绿 (Dev Green)" value="theme-dev-green" />
                        <el-option label="未来科技靛 (Tech Indigo)" value="theme-tech-indigo" />
                      </el-select>
                    </div>
                    <div class="ctrl-group">
                      <label>内容深度/难度</label>
                      <el-radio-group v-model="agentConfigs.ppt.difficulty" size="small" class="custom-radio-group">
                        <el-radio-button label="beginner">入门演示</el-radio-button>
                        <el-radio-button label="intermediate">进阶讲解</el-radio-button>
                        <el-radio-button label="advanced">硬核干货</el-radio-button>
                      </el-radio-group>
                    </div>
                    <div class="ctrl-group">
                      <div class="slider-label-row">
                        <label>期望生成页数</label>
                        <span class="slider-value"><b>{{ agentConfigs.ppt.page_count }}</b> 页</span>
                      </div>
                      <el-slider v-model="agentConfigs.ppt.page_count" :min="3" :max="20" :step="1" class="custom-slider-v2" />
                    </div>
                  </template>

                  <template v-if="agent.id === 'video'">
                    <div class="coming-soon-panel">
                      <el-icon><VideoPlay /></el-icon>
                      <div>
                        <strong>视频动画脚本即将支持</strong>
                        <span>当前不会加入本次生成请求，后端接入 VideoAgent 后自动开放。</span>
                      </div>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>

          <div class="personalize-footer-v2">
            <div class="selected-agents-bar">
              <span class="sab-label">本次将调度 {{ enabledAgentIds.length }} 个智能体：</span>
              <div class="sab-pills">
                <el-tag
                  v-for="id in enabledAgentIds"
                  :key="id"
                  size="small"
                  effect="plain"
                  round
                  class="sab-pill"
                >
                  <el-icon><component :is="getAgentMeta(id).icon" /></el-icon>
                  {{ getAgentMeta(id).name }}
                </el-tag>
              </div>
              <span class="sab-hint" v-if="enabledAgentIds.length === MIN_AGENTS">⚠️ 已达最低要求</span>
            </div>
            <div class="footer-btns">
              <el-button plain round size="large" @click="currentPhase = 'input'" class="footer-back-btn">返回修改需求</el-button>
              <el-button type="primary" round size="large" class="launch-btn-v2" @click="startGeneration">
                确认配置，启动多智能体加工 <el-icon class="el-icon--right"><VideoPlay /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="currentPhase === 'generating'" class="phase-view generating-view" key="generating">
        <div class="generation-workbench">
          <section class="compact-hero-bar" aria-live="polite">
            <div class="hero-bar-left">
              <el-tag class="hero-kicker" effect="plain" round>
                <span class="ping-dot"></span>
                STREAMING
              </el-tag>
              <div class="hero-bar-text">
                <h2 class="hero-bar-title">多智能体协同生成中</h2>
                <p class="hero-bar-message">{{ currentMessage || '系统正在建立 SSE 流，准备展示实时动作。' }}</p>
              </div>
            </div>
            <div class="hero-bar-right">
              <div class="progress-info-v2">
                <div class="pi-item"><span>阶段</span><b>{{ currentStageLabel }}</b></div>
                <div class="pi-item"><span>资源</span><b>{{ completedResourceCount }}/{{ expectedResourceCount }}</b></div>
              </div>
              <div class="mini-progress">
                <el-progress type="dashboard" :percentage="totalProgress" :width="54" :stroke-width="5" color="#0369A1" :show-text="false" />
                <span class="mini-progress-text">{{ totalProgress }}%</span>
              </div>
            </div>
          </section>

          <el-alert
            v-if="generationError"
            class="generation-error"
            type="error"
            :closable="false"
            show-icon
            :title="generationError"
          />

          <div class="generation-focus-grid">
            <main class="flow-canvas-card" aria-label="多智能体流程动画">
              <header class="flow-card-header">
                <div>
                  <span class="layer-index">MULTI-AGENT FLOW</span>
                  <h3>多智能体实时协同流水线</h3>
                </div>
                <el-tag effect="plain">{{ Object.keys(activeAgents).length }} 个 Agent 已被调度</el-tag>
              </header>

              <div class="flow-canvas">
                <div class="flow-canvas-inner">
                  <svg class="flow-lines" viewBox="0 0 1000 680" preserveAspectRatio="none" aria-hidden="true">
                    <line
                      v-for="edge in flowConnections"
                      :key="`${edge.from}-${edge.to}`"
                      :x1="edge.x1"
                      :y1="edge.y1"
                      :x2="edge.x2"
                      :y2="edge.y2"
                      :class="['flow-edge', edge.status, { active: edge.active }]"
                    />
                  </svg>
                  <button
                    v-for="node in flowNodes"
                    :key="node.id"
                    type="button"
                    class="flow-node"
                    :class="[`is-${node.status}`, { focused: focusedAgent?.id === node.id }]"
                    :style="{ left: `${node.x}%`, top: `${node.y}%` }"
                    @click="focusFlowNode(node.id)"
                  >
                    <div class="node-head">
                      <span class="node-icon"><el-icon><component :is="node.icon" /></el-icon></span>
                      <div class="node-title-group">
                        <span class="node-label">{{ node.label }}</span>
                        <small>{{ getNodeStatusText(node.id, node.status) }}</small>
                      </div>
                    </div>

                    <transition name="log-fade" mode="out-in">
                      <div
                        :key="getLatestNodeBubble(node.id)?.id || `${node.id}-${node.status}`"
                        class="node-live-log"
                      >
                        <div class="node-live-log-meta">
                          <span>{{ getFlowLogTypeLabel(getLatestNodeBubble(node.id)?.event_type) }}</span>
                          <em v-if="getLatestNodeBubble(node.id)?.timestamp">{{ formatEventTime(getLatestNodeBubble(node.id)?.timestamp || '') }}</em>
                          <em v-else>{{ getStatusLabel(node.status) }}</em>
                        </div>
                        <p>{{ getNodeProcessMessage(node.id, node.status) }}</p>
                      </div>
                    </transition>

                    <div v-if="node.status === 'running'" class="node-progress" aria-hidden="true">
                      <span></span>
                    </div>
                  </button>
                </div>
              </div>

              <div class="workflow-stage-strip">
                <button
                  v-for="stage in workflowStages"
                  :key="stage.key"
                  type="button"
                  class="stage-chip"
                  :class="`is-${stage.status}`"
                  @click="focusStage(stage.key)"
                >
                  <span></span>{{ stage.label }}
                </button>
              </div>
            </main>
          </div>

          <div class="bottom-panels">
            <section class="compact-resource-panel">
              <div class="panel-header-minimal">
                <div class="phm-left">
                  <el-icon><Collection /></el-icon>
                  <span>已生成资源</span>
                  <el-tag size="small" effect="plain" round v-if="generatedResources.length">{{ generatedResources.length }} 项</el-tag>
                </div>
              </div>
              <div v-if="generatedResources.length" class="generated-resource-row">
                <article
                  v-for="resource in sortedGeneratedResources"
                  :key="resource.id || resource.type"
                  class="mini-resource-card"
                  :class="getResourceToneClass(resource.type)"
                  @click="previewGeneratedResource(resource)"
                >
                  <div class="mrc-icon">
                    <el-icon><component :is="getAgentMeta(resource.type).icon" /></el-icon>
                  </div>
                  <div class="mrc-info">
                    <h4>{{ resource.title || getResourceTypeLabel(resource.type) }}</h4>
                    <span>{{ getResourceStageLabel(resource.type) }}</span>
                  </div>
                </article>
              </div>
              <div v-else class="side-empty minimal">
                <span class="loading-dots">等待资源生成中...</span>
              </div>
            </section>

            <section class="live-event-timeline">
              <div class="let-header">
                <div class="let-title-group">
                  <span class="let-ping"></span>
                  <span class="let-title">实时事件流</span>
                </div>
                <span class="let-count" v-if="flowEventBubbles.length">{{ flowEventBubbles.length }} 条事件</span>
              </div>
              <div class="let-body" v-if="flowEventBubbles.length">
                <transition-group name="event-slide" tag="div" class="let-list">
                  <div
                    v-for="evt in [...flowEventBubbles].reverse().slice(0, 12)"
                    :key="evt.id"
                    class="let-row"
                    :class="`evt-${evt.status}`"
                  >
                    <div class="let-dot-col">
                      <span class="let-dot"></span>
                      <span class="let-line" v-if="true"></span>
                    </div>
                    <div class="let-content">
                      <div class="let-top">
                        <span class="let-agent">{{ getAgentMeta(evt.nodeId).name }}</span>
                        <el-tag size="small" :type="evt.status === 'success' ? 'success' : evt.status === 'failed' ? 'danger' : evt.status === 'running' ? '' : 'info'" effect="plain" class="let-type-tag">
                          {{ getFlowLogTypeLabel(evt.event_type) }}
                        </el-tag>
                        <time class="let-time">{{ formatEventTime(evt.timestamp) }}</time>
                      </div>
                      <p class="let-msg">{{ stringifyCompact(evt.message, 100) }}</p>
                    </div>
                  </div>
                </transition-group>
              </div>
              <div v-else class="let-empty">
                <span class="loading-dots">等待智能体事件...</span>
              </div>
            </section>
          </div>
        </div>
      </div>

      <div v-else-if="currentPhase === 'result'" class="phase-view results-view result-dashboard-view" key="result">
        <header class="result-hero-compact">
          <div class="hero-content-left">
            <div class="hero-status-tag-mini success-glow">
              <el-icon><CircleCheckFilled /></el-icon>
              <span>已完成</span>
            </div>
            <h1 class="hero-title-compact">{{ finalBundle?.title || '个性化学习资源已就绪' }}</h1>
            <p class="hero-subtitle-compact">多智能体协同加工完成，已为您生成专属多模态知识图谱</p>
          </div>
          <div class="hero-actions-right">
            <el-button round size="small" @click="resetGenerator">
              <el-icon><RefreshLeft /></el-icon> 新建任务
            </el-button>
          </div>
        </header>

        <main class="results-body-bento">
          <div class="bento-grid-container">
            <div class="premium-resource-grid">
              <article
                v-for="(res, index) in resultResources"
                :key="res.id || res.title"
                class="premium-res-card"
                :class="getResourceToneClass(res.type)"
                :style="{...getBentoCardGridStyle(index, resultResources.length), animationDelay: `${index * 0.08}s`}"
                @click="handlePreview({ agentId: res.type, resultData: res.content, title: res.title })"
              >
                <div class="card-bg-glow"></div>
                <div class="card-header">
                  <div class="type-icon-box">
                    <el-icon><component :is="getAgentMeta(res.type).icon" /></el-icon>
                  </div>
                  <div class="type-info">
                    <span class="type-label">{{ getResourceTypeLabel(res.type) }}</span>
                    <span class="format-tag">{{ res.format || getDefaultResourceFormat(res.type) }}</span>
                  </div>
                </div>

                <div class="card-body">
                  <h4 class="card-title">{{ formatBentoTitle(res.title, res.type) }}</h4>
                  <p class="card-summary">{{ stringifyCompact(res.summary || getResourceUsageHint(res.type), 100) }}</p>
                  
                  <div class="card-metrics-modern">
                    <div class="metric-badge">
                      <el-icon><Odometer /></el-icon> {{ getDifficultyLabel(res.metadata?.difficulty) }}
                    </div>
                    <div class="metric-badge">
                      <el-icon><Clock /></el-icon> {{ res.metadata?.estimated_time || getEstimatedTime(res.type) }}
                    </div>
                  </div>
                </div>

                <div class="card-footer">
                  <button class="modern-text-btn">
                    查看详情 <span>&rarr;</span>
                  </button>
                </div>
              </article>
            </div>
          </div>
        </main>
      </div>

    </transition>

    <el-drawer
      v-model="agentDetailVisible"
      title="Agent 执行详情"
      direction="rtl"
      size="420px"
      class="agent-detail-drawer"
      @close="closeAgentDetail"
    >
      <div v-if="focusedAgent" class="drawer-agent-detail">
        <div class="drawer-agent-header">
          <div class="drawer-agent-icon">
            <el-icon><component :is="getAgentMeta(focusedAgent.id).icon" /></el-icon>
          </div>
          <div>
            <h3>{{ focusedAgent.agent_role || getAgentMeta(focusedAgent.id).name }}</h3>
            <p>{{ getRuntimeStatusLabel(focusedAgent.status) }} · {{ focusedAgent.layer_name || '多智能体工作流' }}</p>
          </div>
        </div>

        <section class="drawer-section">
          <h4>当前阶段</h4>
          <p>{{ focusedAgent.layer_name || '多智能体工作流' }}</p>
        </section>

        <section class="drawer-section">
          <h4>当前动作</h4>
          <p>{{ focusedAgent.current_action || focusedAgent.step_label || focusedAgent.message || '暂无当前动作' }}</p>
        </section>

        <section class="drawer-section">
          <h4>当前状态消息</h4>
          <p>{{ focusedAgent.message || '暂无状态消息' }}</p>
        </section>

        <section class="drawer-section" v-if="focusedAgent.current_step || focusedAgent.total_steps">
          <h4>步骤进度</h4>
          <div class="drawer-progress-row">
            <span>{{ focusedAgent.current_step || 0 }} / {{ focusedAgent.total_steps || '-' }}</span>
            <el-progress :percentage="getAgentProgress(focusedAgent.status)" :stroke-width="8" :show-text="false" />
          </div>
        </section>

        <section class="drawer-section">
          <h4>时间信息</h4>
          <div class="drawer-kv-list">
            <div><span>开始时间</span><b>{{ focusedAgent.startedAt ? formatEventTime(focusedAgent.startedAt) : '-' }}</b></div>
            <div><span>最近更新时间</span><b>{{ focusedAgent.updated_at ? formatEventTime(focusedAgent.updated_at) : '-' }}</b></div>
            <div><span>耗时</span><b>{{ formatElapsedMs(focusedAgent.elapsedMs || 0) }}</b></div>
          </div>
        </section>

        <section class="drawer-section" v-if="focusedAgent.recentLogs?.length">
          <h4>最近执行日志</h4>
          <div class="drawer-log-list">
            <div
              v-for="log in focusedAgent.recentLogs"
              :key="log.id"
              class="drawer-log-item"
            >
              <span>{{ formatEventTime(log.time) }} | {{ getRuntimeStatusLabel(log.status) }}</span>
              <p>{{ log.message }}</p>
            </div>
          </div>
        </section>
      </div>

      <el-empty v-else description="请选择一个 Agent 查看详情" />
    </el-drawer>

    <el-dialog v-model="previewVisible" :title="previewData?.title || '资源预览'" width="78%" top="6vh" destroy-on-close class="elegant-dialog">
      <div v-if="previewData" class="preview-dialog-body">
        <MindmapView v-if="previewData.agentId === 'mindmap'" :result-data="previewData.resultData" />
        <QuizView v-else-if="previewData.agentId === 'quiz'" :result-data="previewData.resultData" />
        <KnowledgeGraphView v-else-if="previewData.agentId === 'knowledge_graph'" :result-data="previewData.resultData" />
        <CodeView v-else-if="previewData.agentId === 'code'" :result-data="previewData.resultData" />
        <ReadingView v-else-if="previewData.agentId === 'reading'" :result-data="previewData.resultData" />
        <PptView v-else-if="previewData.agentId === 'ppt'" :result-data="previewData.resultData" />
        <MarkdownView v-else :result-data="previewData.resultData" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import {
  MagicStick, ArrowRight, Cpu,
  CircleCheckFilled, RefreshLeft, Position, VideoPlay,
  Document, Share, Edit, Collection,
  Clock, Odometer, DataBoard
} from '@element-plus/icons-vue'

import MindmapView from '@/components/resource/MindmapView.vue'
import MarkdownView from '@/components/resource/MarkdownView.vue'
import QuizView from '@/components/resource/QuizView.vue'
import KnowledgeGraphView from '@/components/resource/KnowledgeGraphView.vue'
import CodeView from '@/components/resource/CodeView.vue'
import ReadingView from '@/components/resource/ReadingView.vue'
import PptView from '@/components/resource/PptView.vue'

import { generateResources, type ResourceAgentId, type LearningScenario, type ResourceGenerateEvent } from '@/api/resource'

defineOptions({ name: 'ResourceGenerator' })

type WorkflowStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped'

// Use ResourceGenerateEvent from api/resource.ts - local type not needed

type AgentRuntimeStatus = 'waiting' | 'running' | 'success' | 'failed' | 'skipped'

type AgentLogItem = {
  id: string
  time: string
  eventType: string
  stage?: string
  status: AgentRuntimeStatus
  message: string
  action?: string
  stepLabel?: string
  currentStep?: number
  totalSteps?: number
}

type AgentRuntimeState = {
  id: string
  agent_role?: string
  status: AgentRuntimeStatus
  layer?: number
  layer_name?: string
  resource_type?: string
  message?: string
  action?: string
  current_action?: string
  current_step?: number
  total_steps?: number
  step_label?: string
  task_description?: string
  planning_reason?: string
  depends_on?: string[]
  upstream_agents?: string[]
  has_profile?: boolean
  input_params?: Record<string, any>
  output_requirements?: Record<string, any>
  personalized_constraints?: string[]
  resource_id?: string
  title?: string
  summary?: string
  progress?: number | null
  updated_at?: string
  startedAt?: string
  finishedAt?: string
  displayOrder?: number
  resourceGeneratedAt?: string
  elapsedMs: number
  recentLogs: AgentLogItem[]
  resourceGenerated?: boolean
}

type GeneratedResourceItem = Record<string, any> & {
  generatedAt?: string
  displayOrder?: number
}

type FlowEventBubble = {
  id: string
  nodeId: string
  event_type: string
  agent?: string | null
  status: WorkflowStatus
  message: string
  timestamp: string
}

type WorkflowStage = {
  key: string
  label: string
  status: WorkflowStatus
}

// ===================== 场景默认配置 =====================
type QuizQuestionType = 'single' | 'multiple' | 'judge' | 'fill'
type AnyAgentConfigs = {
  content: { structure: string; include_common_mistakes: boolean; include_examples: boolean; focus_mode: string; depth_level: string }
  mindmap: { map_type: string; max_depth: number; highlight_weak: boolean; expand_weak_points: boolean; include_prerequisites: boolean }
  knowledge_graph: { layout_mode: string; max_nodes: number; relation_depth: number; highlight_mode: string; store_neo4j: boolean; include_orphan_points: boolean }
  quiz: { question_count: number; difficulty_mode: string; weak_point_weight: number; exam_style: string; include_analysis: boolean; question_types?: QuizQuestionType[] }
  code: { programming_language: string; case_type: string; comment_level: string; include_test: boolean; difficulty: string }
  reading: { reading_depth: string; max_items: number; resource_quality: string; include_practice: boolean; language_preference: string }
  video: { script_style: string; estimated_duration: number }
  ppt: { template_id: string; page_count: number; difficulty: string; output_format: string }
}

const SCENARIO_DEFAULTS: Record<string, Partial<AnyAgentConfigs>> = {
  exam_prep: { content: { structure: 'exam_points', include_common_mistakes: true, include_examples: true, focus_mode: 'weak_points', depth_level: 'standard' }, quiz: { question_count: 5, difficulty_mode: 'exam', weak_point_weight: 70, exam_style: '考研', include_analysis: true }, knowledge_graph: { layout_mode: 'force', max_nodes: 18, relation_depth: 2, highlight_mode: 'weak_points', store_neo4j: true, include_orphan_points: true }, mindmap: { map_type: 'exam_map', max_depth: 3, highlight_weak: true, expand_weak_points: true, include_prerequisites: false }, code: { programming_language: 'python', case_type: 'algorithm_template', comment_level: 'standard', include_test: false, difficulty: 'intermediate' }, reading: { reading_depth: 'course_extended', max_items: 3, resource_quality: 'classic', include_practice: false, language_preference: 'chinese' }, ppt: { template_id: 'theme-logic-blue', page_count: 8, difficulty: 'advanced', output_format: 'preview' } },
  daily_review: { content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'weak_points', depth_level: 'quick' }, quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 50, exam_style: 'school', include_analysis: true }, knowledge_graph: { layout_mode: 'force', max_nodes: 16, relation_depth: 2, highlight_mode: 'key_points', store_neo4j: true, include_orphan_points: true }, mindmap: { map_type: 'knowledge_tree', max_depth: 3, highlight_weak: true, expand_weak_points: true, include_prerequisites: false }, code: { programming_language: 'python', case_type: 'basic_demo', comment_level: 'standard', include_test: false, difficulty: 'beginner' }, reading: { reading_depth: 'course_extended', max_items: 3, resource_quality: 'balanced', include_practice: false, language_preference: 'chinese' }, ppt: { template_id: 'theme-dev-green', page_count: 5, difficulty: 'intermediate', output_format: 'preview' } },
  project_practice: { content: { structure: 'case_driven', include_common_mistakes: true, include_examples: true, focus_mode: 'full_coverage', depth_level: 'deep' }, quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 30, exam_style: 'school', include_analysis: true }, knowledge_graph: { layout_mode: 'radial', max_nodes: 24, relation_depth: 3, highlight_mode: 'all', store_neo4j: true, include_orphan_points: true }, mindmap: { map_type: 'knowledge_tree', max_depth: 4, highlight_weak: false, expand_weak_points: false, include_prerequisites: true }, code: { programming_language: 'python', case_type: 'basic_demo', comment_level: 'standard', include_test: true, difficulty: 'intermediate' }, reading: { reading_depth: 'engineering', max_items: 5, resource_quality: 'latest', include_practice: true, language_preference: 'chinese' }, ppt: { template_id: 'theme-tech-indigo', page_count: 10, difficulty: 'intermediate', output_format: 'preview' } },
  self_study: { content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'key_concepts', depth_level: 'deep' }, quiz: { question_count: 5, difficulty_mode: 'basic', weak_point_weight: 40, exam_style: 'school', include_analysis: true }, knowledge_graph: { layout_mode: 'force', max_nodes: 20, relation_depth: 2, highlight_mode: 'key_points', store_neo4j: true, include_orphan_points: true }, mindmap: { map_type: 'knowledge_tree', max_depth: 4, highlight_weak: false, expand_weak_points: false, include_prerequisites: true }, code: { programming_language: 'python', case_type: 'basic_demo', comment_level: 'verbose', include_test: false, difficulty: 'beginner' }, reading: { reading_depth: 'course_extended', max_items: 3, resource_quality: 'balanced', include_practice: false, language_preference: 'chinese' }, ppt: { template_id: 'theme-logic-blue', page_count: 6, difficulty: 'beginner', output_format: 'preview' } },
}

// ===================== 1. 核心状态 =====================
type Phase = 'input' | 'personalize' | 'generating' | 'result'
const currentPhase = ref<Phase>('input')

const naturalInput = ref('')
const isInputFocused = ref(false)
const learningScenario = ref<LearningScenario>('daily_review')

const quickPrompts = [
  "复习《计算机网络》TCP三次握手，我喜欢看时序图，请多出几道难题",
  "零基础学习 Python 多线程，需要底层原理知识图谱和带详细注释的代码",
  "考研冲刺《数据结构》二叉树，帮我精简思维导图，重点标注高频考点"
]

const agentMetaList = [
  { id: 'master', name: '多智能体调度', icon: Cpu, colorClass: 'text-blue' },
  { id: 'reviewer', name: '资源审查', icon: CircleCheckFilled, colorClass: 'text-emerald' },
  { id: 'assembler', name: '资源组装', icon: Position, colorClass: 'text-indigo' },
  { id: 'content', name: '核心知识讲解', icon: Document, colorClass: 'text-blue' },
  { id: 'knowledge_graph', name: '知识图谱构建', icon: Share, colorClass: 'text-orange' },
  { id: 'mindmap', name: '知识结构图谱', icon: Share, colorClass: 'text-purple' },
  { id: 'code', name: '实战代码沙箱', icon: Cpu, colorClass: 'text-red' },
  { id: 'quiz', name: '自测题训练', icon: Edit, colorClass: 'text-emerald' },
  { id: 'reading', name: '拓展阅读推荐', icon: Collection, colorClass: 'text-indigo' },
  { id: 'ppt', name: 'PPT文稿生成', icon: DataBoard, colorClass: 'text-pink' },
  { id: 'video', name: '视频动画脚本', icon: VideoPlay, colorClass: 'text-slate', disabled: true }
]

const getAgentMeta = (id: string) => agentMetaList.find(a => a.id === id) || { name: id, icon: Document, colorClass: 'text-blue' }
const enabledAgentIds = ref<ResourceAgentId[]>(['content', 'mindmap', 'knowledge_graph', 'code', 'quiz', 'reading', 'ppt'])

const isAgentEnabled = (id: string) => enabledAgentIds.value.includes(id as ResourceAgentId)

const MIN_AGENTS = 3

const toggleAgent = (id: string) => {
  const idx = enabledAgentIds.value.indexOf(id as ResourceAgentId)
  if (idx >= 0) {
    if (enabledAgentIds.value.length <= MIN_AGENTS) {
      ElMessage.warning({ message: `至少需要保留 ${MIN_AGENTS} 个智能体才能生成有效的个性化学习资源`, plain: true })
      return
    }
    enabledAgentIds.value.splice(idx, 1)
  } else {
    enabledAgentIds.value.push(id as ResourceAgentId)
  }
}

const personalizeAgents = computed(() => agentMetaList.filter(agent => !['master', 'reviewer', 'assembler'].includes(agent.id)))

const getScenarioDesc = (scenario: string) => {
  const descMap: Record<string, string> = {
    exam_prep: '针对考试重点进行高强度强化训练',
    daily_review: '循序渐进地巩固每日所学知识点',
    project_practice: '侧重于代码实战与工程化应用能力',
    self_study: '系统化地探索新知识领域的基础架构'
  }
  return descMap[scenario] || ''
}

// ===================== 2. 参数配置状态 =====================
const agentConfigs = reactive({
  content: { structure: 'progressive' as const, include_common_mistakes: true, include_examples: true, focus_mode: 'full_coverage' as const, depth_level: 'standard' as const },
  mindmap: { map_type: 'knowledge_tree' as const, max_depth: 3, highlight_weak: true, expand_weak_points: false, include_prerequisites: false },
  knowledge_graph: { layout_mode: 'force' as const, max_nodes: 18, relation_depth: 2, highlight_mode: 'key_points' as const, store_neo4j: true, include_orphan_points: true },
  quiz: { question_count: 5, difficulty_mode: 'adaptive' as const, weak_point_weight: 50, exam_style: 'school' as const, include_analysis: true, question_types: ['single', 'multiple', 'judge'] as QuizQuestionType[] },
  code: { programming_language: 'python' as const, case_type: 'basic_demo' as const, comment_level: 'standard' as const, include_test: false, difficulty: 'beginner' as const },
  reading: { reading_depth: 'course_extended' as const, max_items: 3, resource_quality: 'balanced' as const, include_practice: false, language_preference: 'chinese' as const },
  video: { script_style: 'concept_animation', estimated_duration: 3 },
  ppt: { template_id: 'theme-logic-blue' as const, page_count: 6, difficulty: 'intermediate' as const, output_format: 'preview' as const },
})

const applyScenarioDefaults = (scenario: LearningScenario) => {
  const defaults = SCENARIO_DEFAULTS[scenario]
  if (!defaults) return
  Object.keys(defaults).forEach((key) => {
    const agentKey = key as keyof typeof agentConfigs
    const agentDefaults = defaults[agentKey]
    if (agentDefaults) Object.assign(agentConfigs[agentKey], agentDefaults)
  })
}

const goToPersonalize = () => {
  if (!naturalInput.value.trim()) return
  currentPhase.value = 'personalize'
}

// ===================== 3. 工作流与生成逻辑 =====================
const totalProgress = ref(0)
const currentMessage = ref('')
const activeAgents = reactive<Record<string, AgentRuntimeState>>({})
const generatedResources = ref<GeneratedResourceItem[]>([])
const reviewResult = ref<any | null>(null)
const finalBundle = ref<any | null>(null)
const profileSummary = ref<Record<string, any> | null>(null)
const isGenerating = ref(false)
const generationError = ref<string | null>(null)
const streamController = ref<AbortController | null>(null)
const focusedAgentId = ref<string | null>(null)
const agentDetailVisible = ref(false)
const flowEventBubbles = ref<FlowEventBubble[]>([])
const agentDisplayCounter = ref(0)
const resourceDisplayCounter = ref(0)
const USE_FIXED_RESULT_PAGE = false

const createWorkflowStages = (): WorkflowStage[] => [
  { key: 'planning', label: '多智能体调度', status: 'pending' },
  { key: 'generating', label: '全链路并发生成', status: 'pending' },
  { key: 'reviewing', label: '资源审查', status: 'pending' },
  { key: 'assembling', label: '资源组装', status: 'pending' },
  { key: 'completed', label: '生成完成', status: 'pending' },
]

const workflowStages = reactive<WorkflowStage[]>(createWorkflowStages())

const focusedAgent = computed(() => {
  if (focusedAgentId.value && activeAgents[focusedAgentId.value]) {
    return activeAgents[focusedAgentId.value]
  }
  if (focusedAgentId.value) {
    const node = flowNodes.value.find(item => item.id === focusedAgentId.value)
    if (node) {
      return {
        id: node.id,
        agent_role: node.label,
        status: node.status === 'pending' ? 'waiting' : node.status,
        current_action: getNodeCurrentStage(node.id, node.status),
        message: getNodeCurrentStage(node.id, node.status),
        layer_name: '多智能体流程节点',
        updated_at: new Date().toISOString(),
        elapsedMs: 0,
        recentLogs: [],
      } as AgentRuntimeState
    }
  }
  const running = Object.values(activeAgents).find(agent => agent.status === 'running')
  if (running) return running
  const latest = Object.values(activeAgents)
    .filter(agent => agent.updated_at)
    .sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)))[0]
  return latest || null
})

const currentStageLabel = computed(() => {
  const running = workflowStages.find(stage => stage.status === 'running')
  const latestSuccess = [...workflowStages].reverse().find(stage => stage.status === 'success')
  return running?.label || latestSuccess?.label || '等待任务创建'
})


const completedResourceCount = computed(() => generatedResources.value.length)
const expectedResourceCount = computed(() => Math.max(Object.keys(activeAgents).length, enabledAgentIds.value.length))

const DEFAULT_RESOURCE_SEQUENCE = ['content', 'mindmap', 'knowledge_graph', 'code', 'quiz', 'reading', 'ppt', 'video']

// 每个 agent 属于哪个「阶段层」及在流图中的 x 坐标（固定）
const PHASE_LAYOUT: { x: number; agents: string[] }[] = [
  { x: 28, agents: ['content', 'mindmap'] },
  { x: 52, agents: ['knowledge_graph', 'code', 'quiz'] },
  { x: 72, agents: ['reading', 'ppt'] },
]

const flowAgentMeta: Record<string, { label: string; icon: any }> = {
  content: { label: '课程讲解', icon: Document },
  mindmap: { label: '思维导图', icon: Share },
  knowledge_graph: { label: '知识图谱', icon: Share },
  code: { label: '代码案例', icon: Cpu },
  quiz: { label: '练习题', icon: Edit },
  reading: { label: '拓展阅读', icon: Collection },
  ppt: { label: 'PPT生成', icon: DataBoard },
}

// 动态只保留已启用 agent 所在的 phase
const flowAgentPhases = computed(() =>
  PHASE_LAYOUT.map(p => ({
    x: p.x,
    agents: p.agents.filter(id => enabledAgentIds.value.includes(id as ResourceAgentId)),
  })).filter(p => p.agents.length > 0)
)

const fixedFlowNodes = [
  { id: 'master', label: '多智能体调度', x: 8, y: 50, icon: Cpu },
]

// 所有可能的有向边（含 reviewer / assembler）
const ALL_FLOW_EDGES: [string, string][] = [
  ['master', 'content'],
  ['master', 'mindmap'],
  ['content', 'knowledge_graph'],
  ['mindmap', 'knowledge_graph'],
  ['content', 'code'],
  ['content', 'quiz'],
  ['knowledge_graph', 'reading'],
  ['code', 'reading'],
  ['quiz', 'reading'],
  ['knowledge_graph', 'ppt'],
  ['mindmap', 'ppt'],
  ['content', 'reviewer'],
  ['mindmap', 'reviewer'],
  ['knowledge_graph', 'reviewer'],
  ['code', 'reviewer'],
  ['reading', 'reviewer'],
  ['ppt', 'reviewer'],
  ['quiz', 'reviewer'],
  ['reviewer', 'assembler'],
]

// 动态过滤：只保留两端节点均在本次启用列表（或 master/reviewer/assembler）中的边
const systemNodes = new Set(['master', 'reviewer', 'assembler'])
const activeFlowEdges = computed(() => {
  const enabled = new Set([...enabledAgentIds.value, ...systemNodes])
  return ALL_FLOW_EDGES.filter(([from, to]) => enabled.has(from) && enabled.has(to))
})

const getDistributedY = (index: number, total: number) => {
  if (total <= 1) return 50
  const start = total === 2 ? 34 : 24
  const end = total === 2 ? 66 : 76
  return start + ((end - start) * index) / (total - 1)
}

const getDefaultResourceIndex = (agentId: string) => {
  const index = DEFAULT_RESOURCE_SEQUENCE.indexOf(agentId)
  return index >= 0 ? index : DEFAULT_RESOURCE_SEQUENCE.length
}

const hasRuntimeActivity = (agentId: string) => {
  const runtime = activeAgents[agentId]
  return Boolean(
    runtime?.displayOrder
    || runtime?.startedAt
    || runtime?.resourceGeneratedAt
    || (runtime && runtime.status !== 'waiting')
  )
}

const sortAgentIdsByRuntime = (agentIds: string[]) => [...agentIds].sort((a, b) => {
  const aActive = hasRuntimeActivity(a) ? 0 : 1
  const bActive = hasRuntimeActivity(b) ? 0 : 1
  if (aActive !== bActive) return aActive - bActive

  const aRuntime = activeAgents[a]
  const bRuntime = activeAgents[b]
  const aOrder = aRuntime?.displayOrder ?? Number.POSITIVE_INFINITY
  const bOrder = bRuntime?.displayOrder ?? Number.POSITIVE_INFINITY
  if (aOrder !== bOrder) return aOrder - bOrder

  return getDefaultResourceIndex(a) - getDefaultResourceIndex(b)
})

const flowNodeDefinitions = computed(() => {
  const nodes = [...fixedFlowNodes]
  flowAgentPhases.value.forEach((phase) => {
    const sortedAgents = sortAgentIdsByRuntime(phase.agents)
    sortedAgents.forEach((agentId, index) => {
      const meta = flowAgentMeta[agentId]
      if (!meta) return
      nodes.push({
        id: agentId,
        label: meta.label,
        x: phase.x,
        y: getDistributedY(index, sortedAgents.length),
        icon: meta.icon,
      })
    })
  })
  nodes.push(
    { id: 'reviewer', label: '资源审查', x: 86, y: 38, icon: CircleCheckFilled },
    { id: 'assembler', label: '资源组装', x: 94, y: 66, icon: Position },
  )
  return nodes
})

const flowNodes = computed(() => flowNodeDefinitions.value.map(node => ({
  ...node,
  status: getFlowNodeStatus(node.id),
})))

const flowConnections = computed(() => activeFlowEdges.value.map(([from, to]) => {
  const source = flowNodes.value.find(node => node.id === from)
  const target = flowNodes.value.find(node => node.id === to)
  const sourceStatus = source?.status || 'pending'
  const targetStatus = target?.status || 'pending'
  return {
    from,
    to,
    x1: `${source?.x || 0}%`,
    y1: `${source?.y || 0}%`,
    x2: `${target?.x || 0}%`,
    y2: `${target?.y || 0}%`,
    status: targetStatus,
    active: sourceStatus === 'running' || targetStatus === 'running' || (sourceStatus === 'success' && targetStatus !== 'pending'),
  }
}))

const getLatestNodeBubble = (nodeId: string) => {
  const logs = getNodeBubbles(nodeId, 1)
  return logs[logs.length - 1] || null
}


const resultResources = computed(() => {
  const resources = finalBundle.value?.resources
  return Array.isArray(resources) && resources.length ? resources : generatedResources.value
})

// Computed properties for result display logic removed as they are no longer used in the condensed header.




const getResourceTypeLabel = (type: string) => {
  const labelMap: Record<string, string> = {
    content: '专业讲解',
    mindmap: '知识导图',
    knowledge_graph: '知识图谱',
    code: '代码案例',
    quiz: '自测题',
    reading: '拓展阅读',
    ppt: '演示文稿',
    video: '视频脚本',
    reviewer: '质量审查',
  }
  return labelMap[type] || getAgentMeta(type).name || type
}

const getResourceUsageHint = (type: string) => {
  const hintMap: Record<string, string> = {
    content: '先阅读讲解，建立基础概念和关键术语理解。',
    mindmap: '用于梳理知识层级、概念关系和复习框架。',
    knowledge_graph: '用图谱理解知识点依赖、包含、扩展和易混关系。',
    code: '通过代码案例把知识点落到实践，适合边运行边理解。',
    quiz: '完成自测题，检查掌握情况并定位仍然薄弱的知识点。',
    reading: '用于课后拓展和深入理解，适合完成基础资源后阅读。',
    ppt: '精美的自动生成幻灯片，可用于直接演示或快速概览。',
    video: '可作为后续视频或动画讲解的脚本基础。',
  }
  return hintMap[type] || '建议结合本次学习目标使用该资源。'
}

const getResourceStageLabel = (type: string) => {
  const stageMap: Record<string, string> = {
    content: '概念理解',
    mindmap: '结构梳理',
    knowledge_graph: '图谱探索',
    code: '实践验证',
    quiz: '检测巩固',
    reading: '拓展提升',
    ppt: '总结展示',
    video: '讲解呈现',
  }
  return stageMap[type] || '资源学习'
}

const getDefaultResourceFormat = (type: string) => {
  const formatMap: Record<string, string> = {
    content: 'Markdown',
    mindmap: 'Markdown / Tree',
    knowledge_graph: 'Graph JSON',
    code: 'Code',
    quiz: 'Quiz JSON',
    reading: 'Reading List',
    ppt: 'PPT JSON',
    video: 'Script',
  }
  return formatMap[type] || 'Resource'
}

const getEstimatedTime = (type: string) => {
  const timeMap: Record<string, string> = {
    content: '10-15 分钟',
    mindmap: '5-8 分钟',
    knowledge_graph: '6-10 分钟',
    code: '15-25 分钟',
    quiz: '10-20 分钟',
    reading: '20-30 分钟',
    ppt: '5-10 分钟',
    video: '3-5 分钟',
  }
  return timeMap[type] || '待评估'
}

const getDifficultyLabel = (difficulty?: string) => {
  const difficultyMap: Record<string, string> = {
    basic: '基础',
    beginner: '入门',
    intermediate: '进阶',
    advanced: '提高',
    hard: '挑战',
    exam: '考试强化',
  }
  return difficultyMap[String(difficulty || '').toLowerCase()] || difficulty || '自适应'
}

const getResourceToneClass = (type: string) => {
  const toneMap: Record<string, string> = {
    content: 'tone-blue',
    mindmap: 'tone-purple',
    knowledge_graph: 'tone-amber',
    code: 'tone-rose',
    quiz: 'tone-emerald',
    reading: 'tone-indigo',
    ppt: 'tone-pink',
    video: 'tone-slate',
  }
  return toneMap[type] || 'tone-blue'
}

// 运行中已生成资源列表：模拟栈，后生成的资源优先展示在顶部
const sortedGeneratedResources = computed(() => {
  return [...generatedResources.value].sort((a, b) => {
    const aOrder = typeof a.displayOrder === 'number' ? a.displayOrder : -1
    const bOrder = typeof b.displayOrder === 'number' ? b.displayOrder : -1
    if (aOrder !== bOrder) return bOrder - aOrder
    return getDefaultResourceIndex(a.type) - getDefaultResourceIndex(b.type)
  })
})

const getBentoCardGridStyle = (index: number, total: number) => {
  const baseCols = 4
  const totalRows = Math.ceil(total / baseCols)
  const rowIndex = Math.floor(index / baseCols)
  const isLastRow = rowIndex === totalRows - 1
  if (!isLastRow) return {}

  const remainder = total % baseCols
  if (remainder === 0) return {}

  const spanMap: Record<number, number> = { 1: 12, 2: 6, 3: 4 }
  return { gridColumn: `span ${spanMap[remainder] || 3}` }
}

// 预览运行中已生成的单个资源
const previewGeneratedResource = (resource: any) => {
  handlePreview({
    agentId: resource.type,
    resultData: resource.content,
    title: resource.title || getResourceTypeLabel(resource.type)
  })
}

const startGeneration = async () => {
  if (USE_FIXED_RESULT_PAGE) {
    applyFixedResultPage()
    return
  }
  currentPhase.value = 'generating'
  resetGenerationState()
  isGenerating.value = true
  currentMessage.value = '正在将配置参数发送至后端资源生成工作流…'

  const requestAgentConfigs = {
    content: agentConfigs.content,
    mindmap: agentConfigs.mindmap,
    knowledge_graph: agentConfigs.knowledge_graph,
    quiz: agentConfigs.quiz,
    code: agentConfigs.code,
    reading: agentConfigs.reading,
    ppt: agentConfigs.ppt,
  }

  streamController.value = generateResources(
    {
      learning_need: naturalInput.value,
      learning_scenario: learningScenario.value,
      selected_agents: enabledAgentIds.value.map((id, index) => ({ agent_id: id, enabled: true, priority: index })).filter(a => a.enabled),
      agent_configs: requestAgentConfigs,
      output_options: { output_format: 'json' }
    },
    handleSseEvent,
    () => {
      if (!generationError.value && currentPhase.value === 'generating') {
        isGenerating.value = false
        setWorkflowStageStatus('completed', 'success')
        totalProgress.value = 100
        currentPhase.value = 'result'
      }
    },
    (err: any) => {
      generationError.value = err.message || '生成中断，请稍后重试'
      isGenerating.value = false
      markWorkflowFailed()
      ElMessage.error(generationError.value || '生成中断，请稍后重试')
    }
  )
}

const applyFixedResultPage = () => {
  const now = new Date().toISOString()
  resetGenerationState()
  totalProgress.value = 100
  currentPhase.value = 'result'
  currentMessage.value = '固定结果页模式已加载（仅用于页面调试）'
  setWorkflowStageStatus('completed', 'success')

  naturalInput.value = '复习《计算机网络》TCP三次握手，我喜欢看时序图，请多出几道难题'

  const mockResources: GeneratedResourceItem[] = [
    {
      id: 'mock-content-tcp-handshake',
      type: 'content',
      title: 'TCP三次握手高频考点速讲',
      summary: '从为什么不是两次或四次出发，覆盖SYN/ACK语义、半连接队列、旧连接报文干扰与RST处理。',
      format: 'Markdown',
      metadata: { difficulty: 'intermediate', estimated_time: '12-18 分钟' },
      content: { title: 'TCP三次握手高频考点速讲', markdown: '# TCP 三次握手...' },
    },
    {
      id: 'mock-mindmap-tcp-handshake',
      type: 'mindmap',
      title: 'TCP三次握手思维导图（复习版）',
      summary: '按目的、流程、状态、常见陷阱、面试追问组织，适合考前快速回忆。',
      format: 'Markdown / Tree',
      metadata: { difficulty: 'intermediate', estimated_time: '6-10 分钟' },
      content: { title: 'TCP三次握手思维导图', markdown: '# TCP 三次握手思维导图...' },
    },
    {
      id: 'mock-knowledge-graph-tcp',
      type: 'knowledge_graph',
      title: 'TCP三次握手知识图谱',
      summary: '用知识点网络展示 SYN/ACK 语义、状态迁移、异常处理和安全风险之间的关系。',
      format: 'Graph JSON',
      metadata: { difficulty: 'advanced', estimated_time: '10-15 分钟' },
      content: {
        topic: 'TCP三次握手',
        summary: '连接建立过程的知识点关系',
        nodes: [
          { id: 'kp1', label: 'SYN 请求', category: 'core', description: '客户端发起同步请求' },
          { id: 'kp2', label: 'SYN-ACK', category: 'core', description: '服务端同步并确认' },
          { id: 'kp3', label: 'ACK 确认', category: 'important', description: '客户端完成最终确认' },
          { id: 'kp4', label: '旧报文干扰', category: 'weak', description: '两次握手无法抵御旧连接报文' },
        ],
        edges: [
          { source: 'kp1', target: 'kp2', relation_type: 'prerequisite', label: '前置' },
          { source: 'kp2', target: 'kp3', relation_type: 'extends', label: '推进' },
          { source: 'kp4', target: 'kp1', relation_type: 'related', label: '易混' },
        ],
      },
    },
    {
      id: 'mock-code-tcp',
      type: 'code',
      title: 'TCP握手抓包分析代码模板',
      summary: '提供抓包字段解析模板，帮助定位重传、乱序和异常握手。',
      format: 'Code',
      metadata: { difficulty: 'intermediate', estimated_time: '15-20 分钟' },
      content: { title: 'TCP抓包分析模板', code: 'print("tcp handshake analyzer")', language: 'python' },
    },
    {
      id: 'mock-quiz-tcp-hard',
      type: 'quiz',
      title: 'TCP三次握手难题自测（8题）',
      summary: '偏难题，覆盖半连接队列、SYN Cookie、抓包字段分析与故障定位。',
      format: 'Quiz JSON',
      metadata: { difficulty: 'hard', estimated_time: '18-25 分钟' },
      content: {
        title: 'TCP三次握手难题自测',
        questions: [
          { question_type: 'single_choice', stem: '为何第三次握手必要？', options: ['确认双向收发', '减少带宽', '避免拥塞', '提高吞吐'], answer: '确认双向收发' },
        ],
      },
    },
    {
      id: 'mock-reading-tcp-extend',
      type: 'reading',
      title: 'TCP握手扩展阅读清单',
      summary: '延伸到拥塞控制初始化、Fast Open、SYN Cookie 实现细节，便于深挖。',
      format: 'Reading List',
      metadata: { difficulty: 'advanced', estimated_time: '25-35 分钟' },
      content: {
        summary: '建议先完成时序图与难题，再扩展阅读。',
        resources: [
          { title: 'RFC 793 / RFC 9293 handshake sections', type: 'documentation' },
          { title: 'SYN Flood defense and SYN Cookie notes', type: 'article' },
        ],
      },
    },
  ]

  generatedResources.value = mockResources.map((item, index) => ({
    ...item,
    generatedAt: now,
    displayOrder: index + 1,
  }))

  finalBundle.value = {
    topic: naturalInput.value,
    gap: naturalInput.value,
    resources: generatedResources.value,
    metadata: {
      topic: naturalInput.value,
      gap: naturalInput.value,
      course: '计算机网络',
    },
  }
}

const resetGenerationState = () => {
  totalProgress.value = 0
  currentMessage.value = ''
  Object.keys(activeAgents).forEach(key => delete activeAgents[key])
  generatedResources.value = []
  reviewResult.value = null
  finalBundle.value = null
  profileSummary.value = null
  generationError.value = null
  focusedAgentId.value = null
  agentDetailVisible.value = false
  flowEventBubbles.value = []
  agentDisplayCounter.value = 0
  resourceDisplayCounter.value = 0
  isGenerating.value = false
  workflowStages.splice(0, workflowStages.length, ...createWorkflowStages())
}

const normalizeRuntimeStatus = (status?: string, fallback: AgentRuntimeStatus = 'waiting'): AgentRuntimeStatus => {
  if (status === 'running' || status === 'success' || status === 'failed' || status === 'skipped') return status
  if (status === 'pending') return 'waiting'
  return fallback
}

const ensureAgentRuntime = (agentId: string) => {
  const previous = activeAgents[agentId]
  if (previous) return previous
  const runtime: AgentRuntimeState = {
    id: agentId,
    status: 'waiting',
    current_action: '',
    current_step: undefined,
    total_steps: undefined,
    elapsedMs: 0,
    recentLogs: [],
  }
  activeAgents[agentId] = runtime
  return runtime
}

const markAgentRuntimeVisible = (runtime: AgentRuntimeState, time: string) => {
  if (typeof runtime.displayOrder !== 'number') {
    agentDisplayCounter.value += 1
    runtime.displayOrder = agentDisplayCounter.value
  }
  if (!runtime.startedAt) runtime.startedAt = time
}

const calculateElapsedMs = (start?: string, end?: string) => {
  if (!start || !end) return 0
  const startMs = new Date(start).getTime()
  const endMs = new Date(end).getTime()
  if (Number.isNaN(startMs) || Number.isNaN(endMs)) return 0
  return Math.max(0, endMs - startMs)
}

const appendEventToAgentRuntime = (event: ResourceGenerateEvent) => {
  const agentId = resolveEventAgentId(event)
  if (!agentId) return
  const runtime = ensureAgentRuntime(agentId)
  const time = event.timestamp || new Date().toISOString()
  const status = normalizeRuntimeStatus(event.status, runtime.status)
  const logItem: AgentLogItem = {
    id: `${Date.now()}-${Math.random()}`,
    time,
    eventType: event.event_type,
    stage: event.stage,
    status,
    message: event.message || runtime.message || '',
    action: event.payload?.action,
    stepLabel: event.payload?.step_label,
    currentStep: event.payload?.current_step,
    totalSteps: event.payload?.total_steps,
  }
  runtime.status = status
  runtime.layer_name = (event.payload?.layer_name as string | undefined) || runtime.layer_name
  runtime.layer = event.payload?.layer ?? runtime.layer
  runtime.agent_role = (event.payload?.agent_role as string | undefined) || runtime.agent_role
  runtime.current_action = (event.payload?.action as string | undefined) || runtime.current_action || ''
  runtime.step_label = (event.payload?.step_label as string | undefined) || runtime.step_label
  runtime.message = event.message || runtime.message
  runtime.current_step = event.payload?.current_step ?? runtime.current_step
  runtime.total_steps = event.payload?.total_steps ?? runtime.total_steps
  runtime.updated_at = time
  if (status !== 'waiting') markAgentRuntimeVisible(runtime, time)
  if (status === 'success' || status === 'failed' || status === 'skipped') runtime.finishedAt = time
  runtime.elapsedMs = calculateElapsedMs(runtime.startedAt, runtime.finishedAt || runtime.updated_at)
  runtime.recentLogs.unshift(logItem)
  runtime.recentLogs = runtime.recentLogs.slice(0, 8)
}

const resolveEventAgentId = (event: ResourceGenerateEvent): string | undefined => {
  if (event.agent) return event.agent
  const payloadAgent = event.payload?.agent_id
  return typeof payloadAgent === 'string' ? payloadAgent : undefined
}

const handleSseEvent = (event: ResourceGenerateEvent) => {
  if (!event?.event_type) return

  if (event.progress !== null && event.progress !== undefined) {
    totalProgress.value = Math.max(0, Math.min(100, event.progress))
  }
  currentMessage.value = event.message || currentMessage.value

  if (event.event_type === 'workflow') {
    setWorkflowStageStatus(event.stage, event.status)
    if (event.payload?.profile_summary) {
      profileSummary.value = event.payload.profile_summary
    }
  }

  if (event.event_type === 'planning') {
    setWorkflowStageStatus('planning', event.status)
    if (event.status === 'success') {
      // planningHistory reference removed
      ;(event.payload?.agents || []).forEach((agent: any) => {
        if (!agent.agent_id) return
        const runtime = ensureAgentRuntime(agent.agent_id)
        runtime.layer = event.payload.layer
        runtime.layer_name = event.payload.layer_name
        runtime.agent_role = agent.agent_role || getAgentMeta(agent.agent_id).name
        runtime.task_description = agent.task_description
        runtime.planning_reason = agent.planning_reason
        runtime.depends_on = agent.depends_on || []
        runtime.resource_type = agent.resource_type
        runtime.input_params = agent.input_params || {}
        runtime.output_requirements = agent.output_requirements || {}
        runtime.personalized_constraints = agent.personalized_constraints || []
        runtime.updated_at = event.timestamp
      })
    }
  }

  if ((event.event_type === 'agent_step' || event.event_type === 'agent') && resolveEventAgentId(event)) {
    appendEventToAgentRuntime(event)
    const agentId = resolveEventAgentId(event)!
    if (normalizeRuntimeStatus(event.status) === 'running') {
      focusedAgentId.value = agentId
    }
  }

  if (event.event_type === 'resource') {
    const resource = event.payload?.resource
    if (resource) {
      const eventTime = event.timestamp || new Date().toISOString()
      upsertResource(resource, eventTime)
      const agentId = (resource.type as string) || resolveEventAgentId(event)
      if (agentId) {
        const runtime = ensureAgentRuntime(agentId)
        markAgentRuntimeVisible(runtime, eventTime)
        runtime.resourceGenerated = true
        runtime.resourceGeneratedAt = eventTime
        runtime.updated_at = eventTime
        runtime.message = `${runtime.agent_role || getAgentMeta(agentId).name}资源已生成`
        if (runtime.status === 'waiting') runtime.status = 'success'
        if (!runtime.finishedAt) runtime.finishedAt = eventTime
        runtime.elapsedMs = calculateElapsedMs(runtime.startedAt, runtime.finishedAt)
      }
    }
  }

  if (event.event_type === 'review') {
    setWorkflowStageStatus('reviewing', event.status)
    if (event.payload?.review_result) {
      reviewResult.value = event.payload.review_result
    }
  }

  if (event.event_type === 'bundle') {
    setWorkflowStageStatus('assembling', event.status)
    if (event.payload?.bundle) {
      finalBundle.value = event.payload.bundle
    }
  }

  if (event.event_type === 'done') {
    finalBundle.value = event.payload?.bundle || finalBundle.value
    setWorkflowStageStatus('completed', 'success')
    totalProgress.value = 100
    isGenerating.value = false
    closeSseConnection()
    currentPhase.value = 'result'
  }

  if (event.event_type === 'error') {
    generationError.value = event.message
    isGenerating.value = false
    markWorkflowFailed(event.stage)
    closeSseConnection()
  }

  pushFlowEventBubble(event)
}

const upsertResource = (resource: any, timestamp?: string) => {
  const generatedAt = timestamp || new Date().toISOString()
  const index = generatedResources.value.findIndex(item => item.id === resource.id || (item.type === resource.type && item.title === resource.title))
  if (index >= 0) {
    const previous = generatedResources.value[index]!
    const displayOrder = typeof previous.displayOrder === 'number'
      ? previous.displayOrder
      : resourceDisplayCounter.value + 1
    if (typeof previous.displayOrder !== 'number') resourceDisplayCounter.value = displayOrder
    generatedResources.value[index] = {
      ...previous,
      ...resource,
      generatedAt: previous.generatedAt || generatedAt,
      displayOrder,
    }
    return
  }
  resourceDisplayCounter.value += 1
  generatedResources.value.push({
    ...resource,
    generatedAt,
    displayOrder: resourceDisplayCounter.value,
  })
}

const closeSseConnection = () => {
  streamController.value?.abort()
  streamController.value = null
}

const setWorkflowStageStatus = (stage: string, status: WorkflowStatus) => {
  const target = workflowStages.find(item => item.key === stage)
  if (target) target.status = status
}

const markWorkflowFailed = (stage?: string) => {
  const target = workflowStages.find(item => item.key === stage)
  if (target) {
    target.status = 'failed'
    return
  }
  const running = workflowStages.find(item => item.status === 'running')
  if (running) {
    running.status = 'failed'
    return
  }
  const latestActive = [...workflowStages].reverse().find(item => item.status !== 'pending')
  if (latestActive) latestActive.status = 'failed'
}

const resolveEventNodeId = (event: ResourceGenerateEvent): string => {
  if (event.event_type === 'planning') return 'master'
  if (event.event_type === 'review') return 'reviewer'
  if (event.event_type === 'bundle') return 'assembler'
  if (event.event_type === 'resource' && event.agent) return event.agent
  if (event.event_type === 'agent_step' && event.agent) return event.agent
  if (event.event_type === 'agent' && event.agent) return event.agent
  if (event.stage === 'created') return 'master'
  if (event.stage === 'profile') return 'master'
  if (event.stage === 'completed') return 'assembler'
  return 'master'
}

const pushFlowEventBubble = (event: ResourceGenerateEvent) => {
  const nodeId = resolveEventNodeId(event)
  const bubble: FlowEventBubble = {
    id: `${event.event_id || event.timestamp}-${nodeId}`,
    nodeId,
    event_type: event.event_type,
    agent: event.agent,
    status: event.status,
    message: event.message,
    timestamp: event.timestamp,
  }

  flowEventBubbles.value = [...flowEventBubbles.value, bubble].slice(-80)
}

const getNodeBubbles = (nodeId: string, limit = 2) => {
  return flowEventBubbles.value.filter(item => item.nodeId === nodeId).slice(-limit)
}

const getNodeStatusText = (nodeId: string, status: WorkflowStatus) => {
  const agent = activeAgents[nodeId]
  if (agent?.status === 'running') {
    return agent.step_label || agent.current_action || agent.message || '运行中'
  }
  return getStatusLabel(status)
}

const getNodeCurrentStage = (nodeId: string, status: WorkflowStatus) => {
  const agent = activeAgents[nodeId]
  if (agent?.current_action) return agent.current_action
  if (agent?.step_label) return agent.step_label
  if (agent?.message) return agent.message

  const bubbles = getNodeBubbles(nodeId)
  const latestBubble = bubbles[bubbles.length - 1]
  if (latestBubble?.message) return latestBubble.message

  if (status === 'success') return '已完成当前阶段'
  if (status === 'running') return '正在执行当前任务'
  if (status === 'failed') return '执行失败，请查看日志'
  if (status === 'skipped') return '已跳过当前任务'
  return '等待上游任务完成'
}

const formatFlowLogMessage = (log: FlowEventBubble) => {
  return stringifyCompact(log.message || getStatusLabel(log.status) || '正在处理任务', 72)
}

const getNodeProcessMessage = (nodeId: string, status: WorkflowStatus) => {
  const latestBubble = getLatestNodeBubble(nodeId)
  if (latestBubble) return formatFlowLogMessage(latestBubble)
  return stringifyCompact(getNodeCurrentStage(nodeId, status), 72)
}

const getFlowLogTypeLabel = (type?: string) => {
  const labels: Record<string, string> = {
    workflow: '流程',
    planning: '规划',
    agent_step: '执行步骤',
    agent: 'Agent',
    resource: '资源',
    review: '审查',
    bundle: '组装',
    error: '异常',
    done: '完成',
  }
  return labels[type || ''] || type || '事件'
}

const stringifyCompact = (value: any, maxLength = 80): string => {
  if (value === null || value === undefined || value === '') return ''
  if (Array.isArray(value)) return value.map(item => stringifyCompact(item, 24)).filter(Boolean).join('、')
  if (typeof value === 'object') {
    const text = JSON.stringify(value)
    return text.length > maxLength ? `${text.slice(0, maxLength)}…` : text
  }
  const text = String(value)
  return text.length > maxLength ? `${text.slice(0, maxLength)}…` : text
}

const formatBentoTitle = (title: string | undefined, type: string): string => {
  const fallback = getResourceTypeLabel(type)
  const raw = String(title || fallback).trim()
  if (!raw) return fallback
  const suffixPattern = /\s*[-－—]\s*(内容讲解|思维导图|知识图谱|代码实操案例|拓展阅读|自测题)\s*$/
  const matched = raw.match(suffixPattern)
  if (!matched) return raw
  const suffix = matched[1] || ''
  const prefix = raw.replace(suffixPattern, '').trim()
  return prefix ? `${prefix}\n- ${suffix}` : suffix
}

const getStatusLabel = (status: WorkflowStatus) => {
  const labels: Record<WorkflowStatus, string> = {
    pending: '等待',
    running: '运行中',
    success: '完成',
    failed: '失败',
    skipped: '跳过',
  }
  return labels[status]
}

const getRuntimeStatusLabel = (status: AgentRuntimeStatus) => {
  const labels: Record<AgentRuntimeStatus, string> = {
    waiting: '等待',
    running: '运行中',
    success: '完成',
    failed: '失败',
    skipped: '跳过',
  }
  return labels[status]
}

const getAgentProgress = (status: WorkflowStatus | AgentRuntimeStatus) => {
  if (status === 'waiting') return 0
  if (status === 'success') return 100
  if (status === 'running') return 58
  if (status === 'failed') return 100
  return 0
}

const formatElapsedMs = (elapsedMs: number) => {
  if (!elapsedMs || elapsedMs <= 0) return '0s'
  return `${Math.floor(elapsedMs / 1000)}s`
}

const getFlowNodeStatus = (nodeId: string): WorkflowStatus => {
  if (nodeId === 'master') return getStageStatus('planning')
  if (nodeId === 'reviewer') {
    if (reviewResult.value) return 'success'
    return getStageStatus('reviewing')
  }
  if (nodeId === 'assembler') {
    if (finalBundle.value) return 'success'
    return getStageStatus('assembling')
  }
  const status = activeAgents[nodeId]?.status
  if (!status || status === 'waiting') return 'pending'
  return status
}

const getStageStatus = (stage: string): WorkflowStatus => {
  return workflowStages.find(item => item.key === stage)?.status || 'pending'
}

const focusFlowNode = (nodeId: string) => {
  focusedAgentId.value = nodeId
  agentDetailVisible.value = true
}

const closeAgentDetail = () => {
  agentDetailVisible.value = false
}

const focusStage = (stage: string) => {
  const layerMap: Record<string, number> = {
    layer_0: 0,
    layer_1: 1,
    layer_2: 2,
  }
  const layer = layerMap[stage]
  if (layer === undefined) return
  const agent = Object.values(activeAgents).find(item => item.layer === layer && item.status === 'running')
    || Object.values(activeAgents).find(item => item.layer === layer)
  if (agent) focusedAgentId.value = agent.id
}

const formatEventTime = (timestamp: string) => {
  if (!timestamp) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(timestamp))
}

onMounted(() => {
  if (USE_FIXED_RESULT_PAGE) {
    applyFixedResultPage()
  }
})

onBeforeUnmount(() => {
  closeSseConnection()
})

// ===================== 4. UI 交互 =====================
const resetGenerator = () => {
  closeSseConnection()
  naturalInput.value = ''
  resetGenerationState()
  currentPhase.value = 'input'
}

const previewVisible = ref(false)
const previewData = ref<any>(null)
const handlePreview = (data: any) => {
  previewData.value = data
  previewVisible.value = true
}
</script>

<style scoped>
/* ================= 全局布局与转场 ================= */
.elegant-generator-layout { width: 100%; height: calc(100vh - 64px); background: var(--color-bg); font-family: var(--font-sans); overflow-x: hidden; position: relative; padding-top: var(--space-5); }
.phase-view { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; background: transparent; }
.page-slide-enter-active, .page-slide-leave-active { transition: opacity 0.4s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.page-slide-enter-from { opacity: 0; transform: translateY(30px) scale(0.98); }
.page-slide-leave-to { opacity: 0; transform: translateY(-30px) scale(1.02); }

/* ================= Phase 1: Input View ================= */
.input-view {
  align-items: center;
  justify-content: center;
  padding: 2.4rem 2rem;
  background:
    radial-gradient(circle at 50% -8%, rgba(37, 99, 235, 0.18) 0%, rgba(37, 99, 235, 0.08) 22%, transparent 56%),
    linear-gradient(180deg, #F2F7FF 0%, #F7FAFF 48%, #FCFEFF 100%);
}
.input-container { width: 100%; max-width: 800px; display: flex; flex-direction: column; align-items: center; margin-top: -8vh; }
.welcome-header { text-align: center; margin-bottom: 2.75rem; }
.sparkle-icon {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  width: 62px;
  height: 62px;
  background: linear-gradient(135deg, #F0F4FF 0%, #E0E7FF 100%);
  color: var(--color-primary);
  font-size: 1.9rem;
  border-radius: var(--radius-2xl);
  margin-bottom: 1.35rem;
  box-shadow: var(--shadow-md);
}
.greeting-title { font-size: clamp(2.1rem, 4.2vw, 3.15rem); font-weight: var(--weight-extrabold); color: var(--color-text); margin: 0 0 0.9rem; letter-spacing: -0.03em; }
.greeting-subtitle { font-size: 1.08rem; color: var(--color-text-muted); line-height: 1.75; max-width: 680px; margin: 0 auto; }
.search-box-wrapper {
  width: 100%;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(203, 213, 225, 0.6);
  border-radius: 28px; /* 增加圆角，使其比 2xl 更圆润，但又不像 pill 那么极端 */
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(12px);
  padding: var(--space-2);
  transition: border-color var(--transition-slow), box-shadow var(--transition-slow), transform var(--transition-slow);
}
.search-box-wrapper.is-focused {
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: var(--shadow-lg);
  transform: translateY(-4px) scale(1.005);
}
.elegant-textarea :deep(.el-textarea__inner) {
  border: none;
  background: transparent;
  box-shadow: none !important;
  font-size: 1.13rem;
  color: var(--color-text);
  padding: var(--space-6) 26px;
  line-height: 1.68;
  resize: none;
}
.elegant-textarea :deep(.el-textarea__inner)::placeholder { color: var(--color-text-faint); font-weight: var(--weight-medium); }
.search-actions { display: flex; justify-content: space-between; align-items: center; padding: var(--space-2) var(--space-4) 10px 24px; gap: var(--space-3); }
.ai-hint { font-size: 0.92rem; color: var(--color-text-muted); display: flex; align-items: center; gap: var(--space-2); font-weight: var(--weight-semibold); }
.ai-hint .el-icon { color: var(--color-info); font-size: 1rem; }
.generate-btn {
  padding: var(--space-3) var(--space-8);
  font-size: 1.02rem;
  font-weight: var(--weight-extrabold);
  border-radius: var(--radius-pill);
  background: var(--color-text) !important;
  border-color: transparent !important;
  box-shadow: var(--shadow-md);
  transition: transform var(--transition-base), box-shadow var(--transition-base), filter var(--transition-base);
}
.generate-btn:hover:not(:disabled) { transform: translateY(-1px); background: var(--color-text-strong) !important; box-shadow: var(--shadow-lg); filter: none; }
.suggestion-area { margin-top: 2.25rem; display: flex; flex-direction: column; align-items: center; gap: var(--space-3); }
.suggestion-label { font-size: 0.84rem; color: var(--color-text-faint); font-weight: var(--weight-bold); letter-spacing: 0.04em; }
.suggestion-tags { display: flex; gap: var(--space-3); flex-wrap: wrap; justify-content: center; }
.s-tag {
  cursor: pointer;
  background: var(--color-surface) !important;
  border-color: var(--color-primary-border) !important;
  color: var(--color-text-secondary) !important;
  padding: var(--space-2) var(--space-4);
  height: auto;
  font-size: 0.9rem;
  font-weight: var(--weight-semibold);
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-base), background-color var(--transition-base), border-color var(--transition-base), color var(--transition-base);
}
.s-tag:hover { transform: translateY(-1px); background: var(--color-info-soft) !important; border-color: #93C5FD !important; color: #1D4ED8 !important; }

/* ================= Phase 2: Personalize View ================= */
.personalize-view { background: var(--color-bg); align-items: center; overflow-y: auto; padding: 60px var(--space-5); position: relative; }
.aurora-background { position: absolute; top: -20%; left: -10%; width: 120%; height: 140%; z-index: 0; background: radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.05) 0%, transparent 40%), radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.05) 0%, transparent 40%), radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.02) 0%, transparent 60%); filter: blur(80px); pointer-events: none; }
.personalize-container { width: 100%; max-width: 1160px; display: flex; flex-direction: column; gap: var(--space-12); position: relative; z-index: 1; }
.view-header { text-align: center; margin-bottom: 0; }
.header-badge { margin-bottom: var(--space-4); font-weight: var(--weight-bold); letter-spacing: 0.05em; background: var(--color-text) !important; border: none; }
.view-header h2 { font-family: var(--font-sans); font-size: 2.5rem; font-weight: var(--weight-extrabold); color: var(--color-text); margin: 0 0 var(--space-4); letter-spacing: -0.02em; }
.view-header p { font-size: 1.1rem; color: var(--color-text-muted); margin: 0; max-width: 600px; margin: 0 auto; line-height: 1.6; }
.scenario-selector-v2 { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-5); }
.scenario-card { background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: var(--radius-2xl); padding: var(--space-5); display: flex; align-items: center; gap: var(--space-4); cursor: pointer; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); position: relative; box-shadow: var(--shadow-sm), var(--shadow-xs); }
.scenario-card:hover { transform: translateY(-3px); background: rgba(255, 255, 255, 0.75); border-color: rgba(148, 163, 184, 0.4); box-shadow: var(--shadow-lg), var(--shadow-sm); }
.scenario-card.active { background: var(--color-surface); border-color: var(--color-text); box-shadow: var(--shadow-lg); border-width: 1.5px; }
.scenario-icon-box { width: 48px; height: 48px; background: var(--color-bg); border-radius: var(--radius-lg); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: var(--weight-extrabold); color: #0369A1; transition: background-color var(--transition-slow), transform var(--transition-slow); }
.scenario-card.active .scenario-icon-box { background: var(--color-info-soft); transform: scale(1.1); }
.scenario-info { display: flex; flex-direction: column; gap: var(--space-1); flex: 1; }
.s-name { font-weight: var(--weight-bold); font-size: 1rem; color: var(--color-text); }
.s-desc { font-size: 0.75rem; color: var(--color-text-muted); line-height: 1.4; }
.active-dot { position: absolute; top: 12px; right: 12px; width: 8px; height: 8px; background: var(--color-text); border-radius: 50%; box-shadow: none; }
.config-section-v2 { margin-top: var(--space-2); }
.agent-configs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-8); }
.config-card-v2 { background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: var(--radius-2xl); overflow: hidden; display: flex; flex-direction: column; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); box-shadow: var(--shadow-sm), var(--shadow-xs); }
.config-card-v2:hover { transform: translateY(-3px); border-color: rgba(148, 163, 184, 0.4); box-shadow: var(--shadow-lg), var(--shadow-sm); }
.cc-header-v2 { padding: var(--space-6) var(--space-6) 16px; display: flex; align-items: center; gap: var(--space-3); }
.cc-icon-wrap { width: 40px; height: 40px; border-radius: var(--radius-lg); display: flex; align-items: center; justify-content: center; font-size: 1.25rem; background: var(--color-bg); }
.cc-icon-wrap.text-blue { background: var(--color-info-soft); color: var(--color-info); }
.cc-icon-wrap.text-orange { background: #FFF7ED; color: var(--color-warning); }
.cc-icon-wrap.text-purple { background: #F5F3FF; color: #8B5CF6; }
.cc-icon-wrap.text-red { background: var(--color-danger-soft); color: var(--color-danger); }
.cc-icon-wrap.text-emerald { background: var(--color-success-soft); color: var(--color-success); }
.cc-icon-wrap.text-indigo { background: var(--color-primary-soft); color: var(--color-primary); }
.cc-icon-wrap.text-slate { background: var(--color-surface-hover); color: var(--color-text-secondary); }
.config-card-v2.disabled { opacity: 0.74; background: var(--color-bg); }
.config-card-v2.agent-off { border-color: var(--color-border); opacity: 0.85; }
.cc-header-v2 { padding: var(--space-6) var(--space-6) 16px; display: flex; align-items: center; gap: var(--space-3); }
.cc-header-switch { margin-left: auto; flex-shrink: 0; }
.cc-body-v2.body-disabled { opacity: 0.38; pointer-events: none; filter: grayscale(60%); }
.question-type-group { display: flex; gap: var(--space-3); flex-wrap: wrap; }
.question-type-group :deep(.el-checkbox) { background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-1) var(--space-3); margin: 0; transition: all var(--transition-base); }
.question-type-group :deep(.el-checkbox.is-checked) { background: var(--color-info-soft); border-color: #93C5FD; }
.question-type-group :deep(.el-checkbox__label) { font-size: 0.88rem; font-weight: var(--weight-semibold); color: var(--color-text-strong); }
.question-type-group :deep(.el-checkbox.is-checked .el-checkbox__label) { color: #1D4ED8; }
.coming-soon-panel { min-height: 128px; border: 1px dashed var(--color-border-hover); border-radius: var(--radius-xl); background: var(--color-surface); display: flex; align-items: center; gap: var(--space-3); padding: var(--space-5); color: var(--color-text-secondary); }
.coming-soon-panel .el-icon { width: 42px; height: 42px; border-radius: var(--radius-lg); background: var(--color-surface-hover); color: var(--color-text-strong); font-size: 1.3rem; flex: 0 0 auto; }
.coming-soon-panel div { display: flex; flex-direction: column; gap: var(--space-1); }
.coming-soon-panel strong { color: var(--color-text); font-size: 0.98rem; }
.coming-soon-panel span { color: var(--color-text-muted); font-size: 0.82rem; line-height: 1.55; }
.cc-title { font-family: var(--font-sans); font-weight: var(--weight-bold); font-size: 1.1rem; color: var(--color-text); }
.cc-body-v2 { padding: 0 24px 24px; display: flex; flex-direction: column; gap: var(--space-6); flex: 1; }
.ctrl-group { display: flex; flex-direction: column; gap: var(--space-3); }
.ctrl-group label { font-size: 0.85rem; color: var(--color-text-muted); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: 0.02em; }
:deep(.custom-select .el-input__wrapper) { background-color: var(--color-bg); border-radius: var(--radius-lg); padding: var(--space-1) var(--space-3); box-shadow: 0 0 0 1px var(--color-border) inset !important; transition: background-color var(--transition-base), box-shadow var(--transition-base); }
:deep(.custom-select .el-input__wrapper:hover) { background-color: var(--color-surface-hover); box-shadow: 0 0 0 1px var(--color-border-hover) inset !important; }
:deep(.custom-select .el-input__wrapper.is-focus) { background-color: var(--color-surface); box-shadow: 0 0 0 2px var(--color-info) inset !important; }
.ctrl-switch-group-v2 { display: flex; flex-direction: column; gap: var(--space-5); }
.ctrl-switch-v2 { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--space-4); }
.sw-info { display: flex; flex-direction: column; gap: 2px; }
.sw-label { font-size: 0.9rem; font-weight: var(--weight-semibold); color: var(--color-text-strong); }
.sw-desc { font-size: 0.75rem; color: var(--color-text-faint); line-height: 1.4; }
.custom-radio-group { display: flex; gap: var(--space-2); width: 100%; }
:deep(.custom-radio-group .el-radio-button) { flex: 1; }
:deep(.custom-radio-group .el-radio-button__inner) { width: 100%; border-radius: var(--radius-md) !important; border: 1px solid transparent !important; background: rgba(241, 245, 249, 0.6); color: var(--color-text-muted); font-weight: var(--weight-semibold); transition: background-color var(--transition-base), border-color var(--transition-base), color var(--transition-base), box-shadow var(--transition-base); padding: 10px 0; }
:deep(.custom-radio-group .el-radio-button__original-radio:checked + .el-radio-button__inner) { background-color: var(--color-surface) !important; color: var(--color-text) !important; border-color: rgba(226, 232, 240, 0.8) !important; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06) !important; }
.slider-label-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: -4px; }
.slider-value { font-size: 0.9rem; color: var(--color-info); font-weight: var(--weight-bold); }
.custom-slider-v2 { padding: 0 var(--space-2); }
.personalize-footer-v2 { display: flex; flex-direction: column; align-items: center; gap: var(--space-5); margin-top: var(--space-4); padding-bottom: 40px; }
.footer-btns { display: flex; justify-content: center; gap: var(--space-6); }
.selected-agents-bar { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; justify-content: center; background: rgba(255,255,255,0.75); backdrop-filter: blur(12px); border: 1px solid var(--color-border); border-radius: var(--radius-xl); padding: var(--space-3) var(--space-5); max-width: 860px; }
.sab-label { font-size: 0.85rem; color: var(--color-text-muted); font-weight: var(--weight-bold); white-space: nowrap; }
.sab-pills { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.sab-pill { display: inline-flex; align-items: center; gap: var(--space-1); font-size: 0.82rem; font-weight: var(--weight-semibold); cursor: default; }
.sab-hint { font-size: 0.78rem; color: var(--tone-amber); font-weight: var(--weight-bold); }
.footer-back-btn { font-weight: var(--weight-bold); color: var(--color-text-muted); border: 1px solid var(--color-border); }
.launch-btn-v2 { font-family: var(--font-sans); font-weight: var(--weight-extrabold); padding: 0 var(--space-10); background: #0369A1 !important; border: none; box-shadow: var(--shadow-lg); transition: transform var(--transition-slow), box-shadow var(--transition-slow); }
.launch-btn-v2:hover { transform: translateY(-3px); box-shadow: var(--shadow-xl); }

/* ================= Phase 3: Generating View ================= */
.generating-view { background: var(--color-bg); overflow-y: auto; }
.generation-workbench { width: 100%; max-width: 1760px; margin: 0 auto; padding: var(--space-8); display: flex; flex-direction: column; gap: var(--space-5); color: var(--color-text); }
.workbench-hero { background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: var(--radius-2xl); padding: var(--space-6) var(--space-8); display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: var(--space-8); align-items: center; box-shadow: var(--shadow-sm), var(--shadow-xs); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.workbench-kicker { margin-bottom: var(--space-3); color: #0369A1 !important; border-color: #BAE6FD !important; background: #F0F9FF !important; font-weight: var(--weight-extrabold); letter-spacing: 0.05em; }
.workbench-hero h2 { margin: 0 0 var(--space-2); font-size: 2rem; line-height: 1.2; font-weight: var(--weight-extrabold); color: var(--color-text); text-wrap: balance; }
.workbench-hero p { margin: 0; max-width: 760px; color: var(--color-text-muted); line-height: 1.65; }
.progress-panel { grid-column: 1 / -1; background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-xl); padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-3); min-width: 0; }
.progress-number { font-size: 2.1rem; font-weight: var(--weight-extrabold); color: #0369A1; font-variant-numeric: tabular-nums; }
.current-message { color: var(--color-text-secondary); line-height: 1.5; word-break: break-word; }
.generation-error { border-radius: var(--radius-xl); }
.workbench-grid { display: grid; grid-template-columns: 260px minmax(0, 1fr) 340px; gap: var(--space-5); align-items: start; }
.workflow-timeline-panel, .side-card, .agent-layer-section, .workbench-collapse, .review-summary-card, .result-resource-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-2xl); box-shadow: var(--shadow-md); }
.workflow-timeline-panel { padding: var(--space-5); position: sticky; top: 20px; }
.panel-title { font-size: 0.92rem; font-weight: var(--weight-extrabold); color: var(--color-text); margin-bottom: var(--space-4); }
.workflow-stage-list { display: flex; flex-direction: column; gap: var(--space-3); }
.workflow-stage-item { min-height: 42px; display: grid; grid-template-columns: 14px minmax(0, 1fr) auto; gap: var(--space-3); align-items: center; color: var(--color-text-muted); }
.stage-dot { width: 10px; height: 10px; border-radius: var(--radius-pill); background: var(--color-border-hover); box-shadow: 0 0 0 4px var(--color-surface-hover); }
.workflow-stage-item.is-running .stage-dot { background: var(--color-info); box-shadow: 0 0 0 4px #DBEAFE; }
.workflow-stage-item.is-success .stage-dot { background: var(--tone-emerald); box-shadow: 0 0 0 4px #D1FAE5; }
.workflow-stage-item.is-failed .stage-dot { background: var(--color-danger); box-shadow: 0 0 0 4px #FEE2E2; }
.workflow-stage-item.is-skipped .stage-dot { background: var(--tone-amber); box-shadow: 0 0 0 4px #FEF3C7; }
.stage-label { min-width: 0; font-weight: var(--weight-bold); color: var(--color-text-strong); }
.agent-live-panel { display: flex; flex-direction: column; gap: var(--space-5); min-width: 0; }
.agent-layer-section { padding: var(--space-6); }
.layer-header { display: flex; justify-content: space-between; gap: var(--space-5); align-items: flex-start; margin-bottom: var(--space-5); }
.layer-index { display: inline-flex; color: #0369A1; font-size: 0.78rem; font-weight: var(--weight-extrabold); letter-spacing: 0.04em; margin-bottom: var(--space-1); }
.layer-header h3 { margin: 0 0 var(--space-1); font-size: 1.2rem; font-weight: var(--weight-extrabold); color: var(--color-text); }
.layer-header p { margin: 0; color: var(--color-text-muted); line-height: 1.5; }
.agent-card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: var(--space-4); }
.runtime-agent-card { border: 1px solid rgba(226, 232, 240, 0.8); border-radius: var(--radius-xl); background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-3); min-width: 0; box-shadow: var(--shadow-sm), var(--shadow-xs); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.runtime-agent-card.is-running { border-color: #93C5FD; box-shadow: var(--shadow-lg); }
.runtime-agent-card.is-success { border-color: #A7F3D0; }
.runtime-agent-card.is-failed { border-color: #FCA5A5; }
.agent-card-header, .agent-title-wrap { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); min-width: 0; }
.agent-title-wrap { justify-content: flex-start; flex: 1; }
.agent-icon { width: 42px; height: 42px; border-radius: var(--radius-lg); display: flex; align-items: center; justify-content: center; flex: 0 0 auto; background: rgba(15, 23, 42, 0.03); border: 1px solid rgba(15, 23, 42, 0.04); }
.agent-icon.text-blue { color: var(--color-info); }
.agent-icon.text-orange { color: #EA580C; }
.agent-icon.text-purple { color: #7C3AED; }
.agent-icon.text-red { color: var(--color-danger); }
.agent-icon.text-emerald { color: var(--tone-emerald); }
.agent-icon.text-indigo { color: var(--color-primary); }
.agent-title-wrap h4 { margin: 0 0 var(--space-1); color: var(--color-text); font-size: 1rem; font-weight: var(--weight-extrabold); overflow-wrap: anywhere; }
.agent-title-wrap span { color: var(--color-text-muted); font-size: 0.82rem; }
.agent-current-action { background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: var(--space-3); display: flex; flex-direction: column; gap: var(--space-1); }
.agent-current-action strong { color: var(--color-text); line-height: 1.45; overflow-wrap: anywhere; }
.agent-current-action span, .agent-info-block p, .output-preview p, .planning-card p, .live-resource-card p, .result-resource-card p { color: var(--color-text-muted); line-height: 1.58; margin: 0; overflow-wrap: anywhere; }
.agent-info-block { display: flex; flex-direction: column; gap: var(--space-3); }
.agent-info-block b { display: inline-flex; margin-right: 8px; color: #0369A1; }
.tag-field, .kv-grid, .output-preview { display: flex; flex-direction: column; gap: var(--space-2); }
.field-label { font-size: 0.76rem; color: var(--color-text-muted); font-weight: var(--weight-extrabold); text-transform: uppercase; letter-spacing: 0.03em; }
.tag-row { display: flex; gap: var(--space-2); flex-wrap: wrap; min-width: 0; }
.kv-row { display: grid; grid-template-columns: minmax(72px, 0.7fr) minmax(0, 1.3fr); gap: var(--space-3); align-items: start; padding: 8px 0; border-bottom: 1px solid rgba(15, 23, 42, 0.04); }
.kv-row span { color: var(--color-text-muted); font-size: 0.82rem; overflow-wrap: anywhere; }
.kv-row b { color: var(--color-text-strong); font-size: 0.82rem; font-weight: var(--weight-semibold); overflow-wrap: anywhere; }
.output-preview { background: var(--color-bg); border-radius: var(--radius-lg); padding: var(--space-3); }
.output-preview strong { color: var(--color-text); overflow-wrap: anywhere; }
.agent-progress { margin-top: auto; }
.empty-layer-state, .side-empty { border: 1px dashed var(--color-border-hover); border-radius: var(--radius-xl); color: var(--color-text-faint); background: var(--color-bg); padding: var(--space-6); text-align: center; line-height: 1.5; }
.resource-side-panel { display: flex; flex-direction: column; gap: var(--space-5); min-width: 0; position: sticky; top: 20px; }
.side-card { padding: var(--space-5); }
.profile-summary-grid { display: flex; flex-direction: column; gap: var(--space-3); }
.profile-summary-item { display: grid; grid-template-columns: 82px minmax(0, 1fr); gap: var(--space-3); padding-bottom: 10px; border-bottom: 1px solid rgba(15, 23, 42, 0.04); }
.profile-summary-item span { color: var(--color-text-muted); font-size: 0.82rem; }
.profile-summary-item b { color: var(--color-text-strong); font-size: 0.86rem; line-height: 1.45; overflow-wrap: anywhere; }
.live-resource-list { display: flex; flex-direction: column; gap: var(--space-3); }
.live-resource-card { border: 1px solid var(--color-border); border-radius: var(--radius-xl); padding: var(--space-3); display: flex; flex-direction: column; gap: var(--space-3); background: var(--color-surface); }
.live-resource-card h4 { margin: var(--space-2) 0 0; color: var(--color-text); font-size: 0.98rem; line-height: 1.35; overflow-wrap: anywhere; }
.resource-meta-line { display: flex; flex-wrap: wrap; gap: var(--space-2); color: var(--color-text-muted); font-size: 0.78rem; }
.workbench-collapse { padding: var(--space-1) var(--space-5); }
.planning-history-list { display: grid; gap: var(--space-3); }
.planning-card { border: 1px solid var(--color-border); border-radius: var(--radius-xl); padding: var(--space-4); }
.planning-card h4 { margin: 0 0 var(--space-2); color: var(--color-text); }
.planning-agent-list { display: grid; gap: var(--space-3); margin-top: var(--space-3); }
.planning-agent-item { background: var(--color-bg); border-radius: var(--radius-lg); padding: var(--space-3); display: grid; gap: var(--space-1); }
.planning-agent-item strong { color: #0369A1; }
.planning-agent-item span { color: var(--color-text-strong); line-height: 1.5; overflow-wrap: anywhere; }
.planning-agent-item em { color: var(--color-text-muted); font-style: normal; line-height: 1.5; overflow-wrap: anywhere; }
.event-log-list { display: flex; flex-direction: column; gap: var(--space-2); max-height: 360px; overflow-y: auto; }
.event-log-row { display: grid; grid-template-columns: 78px 86px 80px 72px minmax(0, 1fr); gap: var(--space-3); align-items: center; padding: 10px 0; border-bottom: 1px solid var(--color-surface-hover); }
.event-log-row span, .event-log-row b { color: var(--color-text-muted); font-size: 0.82rem; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.event-log-row p { margin: 0; color: var(--color-text-strong); line-height: 1.45; overflow-wrap: anywhere; }

.progress-metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-3); }
.progress-metrics span { min-width: 0; padding: var(--space-2); background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); color: var(--color-text-strong); line-height: 1.35; overflow-wrap: anywhere; }
.progress-metrics b { display: block; color: var(--color-text-faint); font-size: 0.72rem; margin-bottom: var(--space-1); }
.generation-focus-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--space-5); align-items: stretch; }
.flow-canvas-card, .resource-summary-card, .result-group-section { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-2xl); box-shadow: var(--shadow-md); }
.flow-canvas-card { padding: var(--space-6); min-width: 0; }
.flow-card-header, .result-group-header { display: flex; justify-content: space-between; gap: var(--space-4); align-items: flex-start; }
.flow-card-header h3, .result-group-header h3 { margin: var(--space-1) 0 0; color: var(--color-text); font-size: 1.18rem; font-weight: var(--weight-extrabold); }
.flow-canvas { position: relative; height: 720px; margin-top: var(--space-5); overflow: auto; border-radius: var(--radius-2xl); background: var(--color-bg); border: 1px solid rgba(226, 232, 240, 0.6); }
.flow-canvas-inner { position: relative; min-width: 1320px; height: 680px; }
.flow-lines { position: absolute; inset: 0; z-index: 1; width: 100%; height: 100%; pointer-events: none; }
.flow-edge { stroke: var(--color-border-hover); stroke-width: 2.4; stroke-linecap: round; opacity: 0.72; }
.flow-edge.success { stroke: var(--color-success); opacity: 0.92; }
.flow-edge.failed { stroke: var(--color-danger); opacity: 0.9; }
.flow-edge.running, .flow-edge.active { stroke: var(--color-primary); stroke-dasharray: 10 10; animation: flowDash 1.2s linear infinite; opacity: 1; }
@keyframes flowDash { to { stroke-dashoffset: -20; } }
.flow-node { position: absolute; z-index: 5; transform: translate(-50%, -50%); width: 186px; min-height: 112px; border: 1px solid rgba(203, 213, 225, 0.6); border-radius: var(--radius-xl); background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(12px); display: flex; flex-direction: column; align-items: stretch; justify-content: flex-start; gap: var(--space-2); cursor: pointer; color: var(--color-text-secondary); box-shadow: var(--shadow-sm); padding: var(--space-3); text-align: left; transition: transform var(--transition-base), border-color var(--transition-base), box-shadow var(--transition-base); }
.flow-node:hover, .flow-node.focused { transform: translate(-50%, -50%) translateY(-3px); border-color: var(--color-info); box-shadow: var(--shadow-lg); }
.node-head { display: flex; align-items: center; gap: var(--space-3); min-width: 0; }
.flow-node .node-icon { width: 34px; height: 34px; border-radius: var(--radius-lg); display: flex; align-items: center; justify-content: center; background: var(--color-surface-hover); color: var(--color-text-muted); flex: 0 0 auto; }
.node-title-group { min-width: 0; flex: 1; }
.flow-node .node-label { display: block; font-weight: var(--weight-extrabold); color: var(--color-text-strong); font-size: 0.9rem; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.flow-node small { display: block; margin-top: 2px; color: var(--color-text-faint); font-weight: var(--weight-bold); font-size: 0.72rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.node-live-log { border: 1px solid var(--color-border); background: linear-gradient(180deg, var(--color-surface) 0%, var(--color-bg) 100%); border-radius: var(--radius-lg); padding: 9px 10px; min-height: 64px; box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8); }
.node-live-log-meta { display: flex; justify-content: space-between; gap: var(--space-2); align-items: center; margin-bottom: var(--space-1); }
.node-live-log-meta span { color: var(--color-info); font-size: 0.66rem; font-weight: var(--weight-extrabold); letter-spacing: 0.05em; }
.node-live-log-meta em { color: var(--color-text-faint); font-size: 0.66rem; font-style: normal; font-variant-numeric: tabular-nums; }
.node-live-log p { margin: 0; color: var(--color-text-secondary); font-size: 0.72rem; line-height: 1.35; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.log-fade-enter-active, .log-fade-leave-active { transition: opacity var(--transition-base), transform var(--transition-base); }
.log-fade-enter-from { opacity: 0; transform: translateY(6px); }
.log-fade-leave-to { opacity: 0; transform: translateY(-6px); }
.node-progress { position: relative; height: 3px; margin-top: auto; overflow: hidden; border-radius: var(--radius-pill); background: var(--color-border); }
.node-progress span { position: absolute; inset: 0 auto 0 0; width: 45%; border-radius: inherit; background: var(--color-info); animation: nodeProgressMove 1.35s ease-in-out infinite; }
.flow-node.is-running { border-color: #A5B4FC; box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.08), var(--shadow-md); animation: nodePulse 2s ease-in-out infinite; }
.flow-node.is-running .node-icon { background: #DBEAFE; color: var(--color-info); }
.flow-node.is-running .node-live-log { border-color: #BFDBFE; background: var(--color-info-soft); }
.flow-node.is-success { border-color: #86EFAC; }
.flow-node.is-success .node-icon { background: #DCFCE7; color: #16A34A; }
.flow-node.is-failed { border-color: #FCA5A5; }
.flow-node.is-failed .node-icon { background: #FEE2E2; color: var(--color-danger); }
.flow-node.is-skipped { opacity: 0.68; }
@keyframes nodePulse { 50% { box-shadow: 0 0 0 6px rgba(99, 102, 241, 0.06), 0 10px 26px rgba(15, 23, 42, 0.08); } }
@keyframes nodeProgressMove { 0% { transform: translateX(-120%); } 100% { transform: translateX(260%); } }
.workflow-stage-strip { display: flex; flex-wrap: wrap; gap: var(--space-3); margin-top: var(--space-4); }
.stage-chip { border: 1px solid var(--color-border); background: var(--color-surface); border-radius: var(--radius-pill); padding: var(--space-2) var(--space-3); color: var(--color-text-muted); font-weight: var(--weight-bold); display: inline-flex; align-items: center; gap: var(--space-2); cursor: pointer; }
.stage-chip span { width: 8px; height: 8px; border-radius: var(--radius-pill); background: var(--color-border-hover); }
.stage-chip.is-running { color: #1D4ED8; border-color: #BFDBFE; background: var(--color-info-soft); }
.stage-chip.is-running span { background: var(--color-info); }
.stage-chip.is-success { color: #047857; border-color: #A7F3D0; background: var(--color-success-soft); }
.stage-chip.is-success span { background: var(--color-success); }
.stage-chip.is-failed { color: #B91C1C; border-color: #FCA5A5; background: var(--color-danger-soft); }
.stage-chip.is-failed span { background: var(--color-danger); }
.resource-summary-card { padding: var(--space-6); }
.interactive-resources-panel {
  min-height: 0;
  height: auto;
  padding-top: var(--space-1);
  padding-bottom: var(--space-1);
}
.resource-status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: var(--space-3); }
.resource-status-item { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: var(--space-3); align-items: start; border: 1px solid var(--color-border); background: var(--color-surface); border-radius: var(--radius-xl); padding: var(--space-3); }
.resource-status-item h4 { margin: 0 0 var(--space-1); color: var(--color-text); font-size: 0.96rem; line-height: 1.35; overflow-wrap: anywhere; }
.resource-status-item p { margin: 0; color: var(--color-text-muted); line-height: 1.5; overflow-wrap: anywhere; }
.side-empty.compact { padding: var(--space-3); }

/* ================= Phase 4: Premium Results View ================= */
.results-view {
  background: var(--color-bg);
  overflow-y: auto;
  padding-bottom: 80px;
  position: relative;
}
.results-view::before {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 100%; height: 500px;
  background: linear-gradient(180deg, rgba(224, 231, 255, 0.6) 0%, rgba(244, 247, 251, 0) 100%);
  pointer-events: none;
  z-index: 0;
}

.result-hero-compact {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-8);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-6);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: 100;
}
.hero-content-left { display: flex; flex-direction: column; gap: var(--space-1); }
.hero-status-tag-mini { display: inline-flex; align-items: center; gap: var(--space-1); color: var(--color-success); font-size: 0.75rem; font-weight: var(--weight-extrabold); }
.hero-title-compact { margin: 0; font-size: 1.25rem; font-weight: var(--weight-extrabold); color: var(--color-text-strong); }
.hero-subtitle-compact { margin: 0; font-size: 0.85rem; color: var(--color-text-muted); }
.hero-actions-right { display: flex; gap: var(--space-3); align-items: center; }
.action-btn-premium-mini {
  background: #0369A1 !important;
  color: white !important;
  font-weight: var(--weight-extrabold);
  font-size: 1.05rem;
  padding: var(--space-3) var(--space-8);
  height: auto;
  border-radius: var(--radius-lg);
  transition: all var(--transition-slow);
  border: none !important;
  position: relative;
  overflow: hidden;
}

.action-btn-premium-mini.glow-effect {
  box-shadow: var(--shadow-lg);
}
.action-btn-premium-mini:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-xl);
}
.action-btn-premium-mini::after {
  content: '';
  position: absolute;
  top: 0; left: -100%; width: 50%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  animation: btn-shine 3s infinite;
}
@keyframes btn-shine {
  0% { left: -100%; }
  20% { left: 200%; }
  100% { left: 200%; }
}

.results-body-bento {
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--space-10) 60px;
  display: flex;
  flex-direction: column;
  gap: var(--space-10);
  position: relative;
  z-index: 1;
}

.premium-stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-6);
}
.premium-stat-card {
  background: var(--color-surface);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: var(--radius-2xl);
  padding: var(--space-6) var(--space-8);
  display: flex;
  align-items: center;
  gap: var(--space-6);
  box-shadow: var(--shadow-md);
  transition: transform var(--transition-slow), box-shadow var(--transition-slow);
}
.premium-stat-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}
.stat-icon-wrapper {
  width: 64px; height: 64px;
  border-radius: var(--radius-xl);
  display: flex; align-items: center; justify-content: center;
  font-size: 2rem;
  background: var(--color-bg);
}
.stat-icon-wrapper.text-blue { background: var(--color-info-soft); color: var(--color-info); }
.stat-icon-wrapper.text-purple { background: #F5F3FF; color: #8B5CF6; }
.stat-icon-wrapper.text-emerald { background: var(--color-success-soft); color: var(--color-success); }

.stat-info { display: flex; flex-direction: column; gap: var(--space-1); }
.premium-stat-card .stat-v { font-size: 2.2rem; font-weight: var(--weight-extrabold); color: var(--color-text); line-height: 1; font-family: var(--font-sans); }
.premium-stat-card .stat-l { font-size: 0.9rem; font-weight: var(--weight-bold); color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.04em; }

.premium-resource-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: var(--space-8);
  align-items: stretch;
}
.premium-res-card {
  grid-column: span 3;
  background: var(--color-surface);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: var(--radius-2xl);
  padding: var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  position: relative;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.03);
  cursor: pointer;
  animation: fadeSlideUp 0.6s ease-out backwards;
}
@keyframes fadeSlideUp {
  0% { opacity: 0; transform: translateY(20px); }
  100% { opacity: 1; transform: translateY(0); }
}

.premium-res-card:hover {
  transform: translateY(-8px);
  box-shadow: var(--shadow-xl);
  border-color: transparent;
}
.card-bg-glow {
  position: absolute;
  top: 0; left: 0; right: 0; height: 100%;
  background: linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0) 100%);
  opacity: 0;
  transition: opacity 0.4s ease;
  z-index: 0;
  pointer-events: none;
}
.premium-res-card.tone-blue:hover { border-color: rgba(59, 130, 246, 0.3); }
.premium-res-card.tone-blue:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(59, 130, 246, 0.08) 0%, transparent 70%); opacity: 1; }
.premium-res-card.tone-purple:hover { border-color: rgba(139, 92, 246, 0.3); }
.premium-res-card.tone-purple:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(139, 92, 246, 0.08) 0%, transparent 70%); opacity: 1; }
.premium-res-card.tone-amber:hover { border-color: rgba(245, 158, 11, 0.3); }
.premium-res-card.tone-amber:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(245, 158, 11, 0.08) 0%, transparent 70%); opacity: 1; }
.premium-res-card.tone-rose:hover { border-color: rgba(225, 29, 72, 0.3); }
.premium-res-card.tone-rose:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(225, 29, 72, 0.08) 0%, transparent 70%); opacity: 1; }
.premium-res-card.tone-emerald:hover { border-color: rgba(16, 185, 129, 0.3); }
.premium-res-card.tone-emerald:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(16, 185, 129, 0.08) 0%, transparent 70%); opacity: 1; }
.premium-res-card.tone-indigo:hover { border-color: rgba(99, 102, 241, 0.3); }
.premium-res-card.tone-indigo:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.08) 0%, transparent 70%); opacity: 1; }
.premium-res-card.tone-slate:hover { border-color: rgba(100, 116, 139, 0.3); }
.premium-res-card.tone-slate:hover .card-bg-glow { background: radial-gradient(circle at 50% 0%, rgba(100, 116, 139, 0.08) 0%, transparent 70%); opacity: 1; }

.premium-res-card .card-header,
.premium-res-card .card-body,
.premium-res-card .card-footer {
  position: relative;
  z-index: 1;
}
.premium-res-card .type-icon-box {
  width: 48px; height: 48px;
  border-radius: var(--radius-lg);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem;
  background: rgba(15, 23, 42, 0.03); border: 1px solid rgba(15, 23, 42, 0.04);
}
.premium-res-card.tone-blue .type-icon-box { color: var(--color-info); }
.premium-res-card.tone-purple .type-icon-box { color: #7C3AED; }
.premium-res-card.tone-amber .type-icon-box { color: var(--tone-amber); }
.premium-res-card.tone-rose .type-icon-box { color: #E11D48; }
.premium-res-card.tone-emerald .type-icon-box { color: var(--tone-emerald); }
.premium-res-card.tone-indigo .type-icon-box { color: var(--color-primary); }
.premium-res-card.tone-slate .type-icon-box { color: var(--color-text-secondary); }

.premium-res-card .card-title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: var(--weight-extrabold);
  color: var(--color-text);
  line-height: 1.45;
  white-space: pre-line; display: -webkit-box; -webkit-line-clamp: 3; line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere;
}
.premium-res-card .card-summary {
  margin: 0;
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.card-metrics-modern {
  display: flex;
  gap: var(--space-3);
  margin-top: auto;
  padding-top: var(--space-3);
}
.metric-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  background: var(--color-bg);
  color: var(--color-text-secondary);
  padding: var(--space-1) var(--space-3);
  border: 1px solid rgba(15, 23, 42, 0.04);
  border-radius: var(--radius-md);
  font-size: 0.8rem;
  font-weight: var(--weight-bold);
}
.premium-res-card .card-footer {
  border-top: 1px solid rgba(226, 232, 240, 0.6);
  padding-top: var(--space-5);
  margin-top: var(--space-1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modern-text-btn {
  background: transparent;
  border: none;
  color: var(--color-text);
  font-weight: var(--weight-extrabold);
  font-size: 0.95rem;
  padding: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  transition: color var(--transition-base);
}
.modern-text-btn span {
  transition: transform var(--transition-slow);
}
.premium-res-card:hover .modern-text-btn {
  color: var(--color-info);
}
.premium-res-card:hover .modern-text-btn span {
  transform: translateX(4px);
}
.interactive-resources-panel .panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}
.interactive-resources-panel .panel-title > span {
  display: inline-flex;
  align-items: center;
  color: var(--color-text);
  font-size: 1rem;
  font-weight: var(--weight-extrabold);
}
.generated-resource-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  column-gap: var(--space-5);
  row-gap: 44px;
  align-items: stretch;
  margin-top: var(--space-3);
  padding-bottom: var(--space-4);
}
.generated-resource-card {
  --resource-accent: var(--color-info);
  --resource-soft: var(--color-info-soft);
  --resource-border: #BFDBFE;
  
  position: relative;
  min-width: 0;
  grid-column: span 3;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--space-3);
  align-items: start;
  height: 100%;
  min-height: 142px;
  padding: var(--space-5) var(--space-5) 16px;
  border: 1px solid rgba(15, 23, 42, 0.05);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  color: var(--color-text);
  cursor: pointer;
  box-shadow: var(--shadow-xs);
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.generated-resource-card::before {
  display: none;
}
.generated-resource-card:hover,
.generated-resource-card:focus-visible {
  transform: translateY(-4px);
  border-color: rgba(15, 23, 42, 0.12);
  box-shadow: var(--shadow-lg);
  outline: none;
}
.generated-resource-card.tone-blue { --resource-accent: var(--color-info); --resource-soft: var(--color-info-soft); --resource-border: #BFDBFE; }
.generated-resource-card.tone-purple { --resource-accent: #7C3AED; --resource-soft: #F5F3FF; --resource-border: #DDD6FE; }
.generated-resource-card.tone-amber { --resource-accent: var(--tone-amber); --resource-soft: var(--color-warning-soft); --resource-border: #FDE68A; }
.generated-resource-card.tone-rose { --resource-accent: #E11D48; --resource-soft: #FFF1F2; --resource-border: #FFE4E6; }
.generated-resource-card.tone-emerald { --resource-accent: var(--tone-emerald); --resource-soft: var(--color-success-soft); --resource-border: var(--color-success-soft); }
.generated-resource-card.tone-indigo { --resource-accent: var(--color-primary); --resource-soft: var(--color-primary-soft); --resource-border: var(--color-primary-border); }
.generated-resource-card.tone-slate { --resource-accent: var(--color-text-secondary); --resource-soft: var(--color-surface-hover); --resource-border: var(--color-border-hover); }
.generated-resource-card .resource-card-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-lg);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--resource-soft);
  border: none;
  color: var(--resource-accent);
  font-size: 1.25rem;
  flex-shrink: 0;
  box-shadow: 0 4px 12px var(--resource-soft);
}
.resource-card-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: var(--space-1);
}
.resource-card-meta-line {
  min-width: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.resource-card-meta-line span {
  color: var(--color-text-muted);
  font-size: 0.78rem;
  font-weight: var(--weight-semibold);
}
.resource-card-info h4 {
  margin: 0;
  color: var(--color-text);
  font-size: 1rem;
  line-height: 1.5;
  font-weight: var(--weight-bold);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
}
.resource-card-info p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.88rem;
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
}
.resource-card-action {
  grid-column: 1 / -1;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: var(--space-1);
  margin-top: var(--space-1);
  padding-top: var(--space-3);
  background: transparent;
  color: var(--color-text-faint);
  border: none;
  border-top: 1px solid rgba(15, 23, 42, 0.04);
  font-size: 0.82rem;
  font-weight: var(--weight-semibold);
  transition: all var(--transition-slow);
}
.generated-resource-card:hover .resource-card-action,
.generated-resource-card:focus-visible .resource-card-action {
  background: transparent;
  color: var(--resource-accent);
  border-color: rgba(15, 23, 42, 0.08);
}
.generated-resource-card:hover .resource-card-action .el-icon {
  transform: translateX(4px);
  transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.side-empty.compact { padding: var(--space-3); }

@media (max-width: 1200px) {
  .workbench-grid { grid-template-columns: 240px minmax(0, 1fr); }
  .resource-side-panel { grid-column: 1 / -1; position: static; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .generation-focus-grid { grid-template-columns: 1fr; }
  .agent-configs-grid { grid-template-columns: repeat(2, 1fr); }
  .workbench-hero { grid-template-columns: 1fr; }
  .bento-stats-row { grid-template-columns: repeat(2, 1fr); }
  .bento-resource-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); }
  .bento-res-card { grid-column: span 2 !important; }
  .resource-metric-stack { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .results-body-bento { padding: var(--space-6) var(--space-8); }
  .generated-resource-card { grid-column: span 4; }
  .interactive-resources-panel { min-height: 0; height: auto; }
}
@media (max-width: 768px) {
  .elegant-generator-layout { height: auto; min-height: calc(100vh - 64px); }
  .phase-view { position: relative; min-height: calc(100vh - 64px); }
  .input-view { padding: 1.4rem 1rem 1.8rem; }
  .welcome-header { margin-bottom: 1.8rem; }
  .sparkle-icon { width: 52px; height: 52px; border-radius: var(--radius-xl); margin-bottom: 1rem; font-size: 1.45rem; }
  .greeting-title { font-size: 2rem; margin-bottom: 0.75rem; }
  .greeting-subtitle { font-size: 0.96rem; line-height: 1.66; max-width: 100%; }
  .search-box-wrapper { border-radius: var(--radius-2xl); padding: var(--space-2); }
  .elegant-textarea :deep(.el-textarea__inner) { font-size: 1rem; padding: var(--space-4) var(--space-4); }
  .search-actions { flex-direction: column; align-items: stretch; gap: var(--space-3); padding: var(--space-1) var(--space-2) var(--space-2); }
  .generate-btn { width: 100%; justify-content: center; }
  .suggestion-area { margin-top: 1.25rem; gap: var(--space-3); }
  .suggestion-tags { justify-content: flex-start; }
  .agent-configs-grid { grid-template-columns: 1fr; }
  .scenario-selector-v2 { grid-template-columns: 1fr; }
  .generation-workbench { padding: var(--space-4); }
  .workbench-grid, .resource-side-panel { grid-template-columns: 1fr; }
  .progress-metrics { grid-template-columns: 1fr; }
  .flow-canvas { height: 720px; }
  .flow-node { width: 176px; min-height: 112px; font-size: 0.82rem; }
  .resource-status-item { grid-template-columns: 1fr; }
  .generated-resource-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .generated-resource-card { grid-column: span 1; grid-template-columns: auto minmax(0, 1fr); min-height: 0; }
  .interactive-resources-panel { min-height: 0; }
  .resource-card-action { grid-column: 1 / -1; width: 100%; }
  .workflow-timeline-panel, .resource-side-panel { position: static; }
  .event-log-row { grid-template-columns: 1fr; gap: var(--space-1); }
  .results-body-bento { padding: var(--space-4); }
  .result-hero-minimal { padding: var(--space-5); }
  .bento-stats-row { grid-template-columns: 1fr; }
  .bento-resource-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .bento-res-card { grid-column: span 1 !important; }
}
@media (max-width: 520px) {
  .sequence-track { display: flex; overflow-x: auto; padding-bottom: var(--space-1); }
  .sequence-node { min-width: 240px; }
  .resource-card-actions { flex-direction: column; }
  .resource-metric-stack { grid-template-columns: 1fr; }
  .generated-resource-grid { grid-template-columns: 1fr; }
  .bento-resource-grid { grid-template-columns: 1fr; }
  .bento-res-card { grid-column: span 1 !important; }
}

.elegant-dialog :deep(.el-dialog) { border-radius: var(--radius-2xl); overflow: hidden; box-shadow: var(--shadow-xl); }
.elegant-dialog :deep(.el-dialog__header) { padding: var(--space-6) var(--space-8) var(--space-5); margin-right: 0; border-bottom: 1px solid var(--color-surface-hover); }
.elegant-dialog :deep(.el-dialog__title) { font-weight: var(--weight-extrabold); font-size: 1.2rem; color: var(--color-text); }
.elegant-dialog :deep(.el-dialog__body) { padding: var(--space-8); background: var(--color-bg); }

/* ================= 极致明亮模式：排版微调 ================= */
h1, h2, h3, h4, .hero-title, .cc-title {
  letter-spacing: -0.025em;
  color: var(--color-text);
  font-weight: var(--weight-bold);
}

p, .card-summary, .s-desc, .greeting-subtitle {
  line-height: 1.65;
  letter-spacing: 0.01em;
  color: var(--color-text-secondary);
}

/* ================= 极致明亮模式：细节打磨与对齐 ================= */
.bento-res-card {
  display: flex;
  flex-direction: column;
  height: auto;
}
.card-body {
  display: flex;
  flex-direction: column;
  flex: 0 0 auto;
}

.card-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  margin-top: var(--space-2);
  padding-top: var(--space-4);
}
.metric-item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  background: var(--color-bg);
  border: 1px solid rgba(15, 23, 42, 0.04);
  border-radius: var(--radius-md);
  padding: var(--space-1) var(--space-3);
}
.m-l {
  font-size: 0.72rem;
  color: var(--color-text-muted);
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
}
.m-v {
  font-size: 0.8rem;
  color: var(--color-text);
  font-weight: var(--weight-extrabold);
}

.group-badge {
  background: var(--color-surface-hover);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  font-size: 0.75rem;
  font-weight: var(--weight-extrabold);
  letter-spacing: 0.05em;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-md);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

/* ================= 极致明亮模式：生成中 (Streaming) 面板重塑 ================= */
.workbench-hero {
  background: var(--color-surface);
  border: 1px solid rgba(15, 23, 42, 0.05);
  border-radius: var(--radius-2xl);
  padding: var(--space-8) var(--space-10);
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: var(--space-10);
  align-items: center;
  box-shadow: var(--shadow-sm);
}

.workbench-kicker {
  background: rgba(59, 130, 246, 0.08) !important;
  color: var(--color-info) !important;
  border: none !important;
  font-weight: var(--weight-extrabold);
  letter-spacing: 0.05em;
  padding: var(--space-1) var(--space-3);
}
.workbench-hero h2 {
  font-size: 2.2rem;
  letter-spacing: -0.03em;
  font-weight: var(--weight-extrabold);
  color: var(--color-text);
  margin-top: var(--space-4);
}

.progress-panel {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  box-shadow: none !important;
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.progress-number {
  font-size: 3.8rem;
  font-weight: var(--weight-extrabold);
  color: var(--color-text);
  letter-spacing: -0.04em;
  line-height: 1;
  font-family: var(--font-sans);
}

:deep(.progress-panel .el-progress-bar__outer) {
  background-color: rgba(15, 23, 42, 0.04) !important;
  border-radius: var(--radius-lg);
  height: 8px !important;
}
:deep(.progress-panel .el-progress-bar__inner) {
  background: linear-gradient(90deg, var(--color-info) 0%, var(--color-primary) 100%);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  position: relative;
  overflow: hidden;
}
:deep(.progress-panel .el-progress-bar__inner::after) {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
  animation: shimmer 1.5s infinite;
}
@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.progress-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-4);
  margin-top: var(--space-2);
}
.progress-metrics span {
  background: var(--color-bg);
  border: 1px solid rgba(15, 23, 42, 0.03);
  border-radius: var(--radius-xl);
  padding: var(--space-4) var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  color: var(--color-text);
  font-weight: var(--weight-bold);
  font-size: 0.95rem;
  transition: all var(--transition-slow);
}
.progress-metrics span:hover {
  transform: translateY(-2px);
  background: var(--color-surface);
  box-shadow: var(--shadow-md);
}
.progress-metrics b {
  color: var(--color-text-muted);
  font-size: 0.72rem;
  font-weight: var(--weight-bold);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 2px;
}

/* ================= 极致明亮模式：修复卡片撑破容器问题 ================= */
.generation-workbench {
  flex: 1 0 auto !important;
  min-height: min-content !important;
}

.resource-summary-card {
  flex-shrink: 0 !important;
  height: max-content !important;
  padding-bottom: var(--space-8) !important;
}

.generated-resource-card {
  height: auto !important;
}

/* ================= 极致明亮模式：面板标题区（已生成资源）重塑 ================= */
.interactive-resources-panel .panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid rgba(15, 23, 42, 0.04);
}

.interactive-resources-panel .panel-title > span {
  font-size: 1.15rem;
  font-weight: var(--weight-extrabold);
  color: var(--color-text);
  letter-spacing: -0.01em;
  position: relative;
  padding-left: var(--space-3);
  display: flex;
  align-items: center;
}

.interactive-resources-panel .panel-title > span::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 16px;
  border-radius: var(--radius-sm);
  background: var(--color-info);
}

.interactive-resources-panel .panel-title .el-tag {
  background: var(--color-bg) !important;
  border: 1px solid rgba(15, 23, 42, 0.05) !important;
  color: var(--color-text-muted) !important;
  font-weight: var(--weight-bold);
  font-size: 0.75rem;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  height: auto;
  box-shadow: var(--shadow-xs);
}

/* ================= 极简明亮模式：生成中顶部面板 ================= */
.compact-hero-bar { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: var(--radius-xl); padding: var(--space-4) var(--space-6); display: flex; justify-content: space-between; align-items: center; box-shadow: var(--shadow-sm); transition: all var(--transition-slow); }
.hero-bar-left { display: flex; align-items: center; gap: var(--space-5); }
.hero-kicker { display: flex; align-items: center; gap: var(--space-1); color: #0369A1 !important; border-color: #BAE6FD !important; background: #F0F9FF !important; font-weight: var(--weight-extrabold); padding: 0 var(--space-3); }
.ping-dot { width: 8px; height: 8px; border-radius: 50%; background-color: var(--color-success); animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite; }
@keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }
.hero-bar-title { margin: 0 0 var(--space-1); font-size: 1.25rem; font-weight: var(--weight-extrabold); color: var(--color-text); }
.hero-bar-message { margin: 0; color: var(--color-text-muted); font-size: 0.9rem; }
.hero-bar-right { display: flex; align-items: center; gap: var(--space-6); }
.progress-info-v2 { display: flex; gap: var(--space-5); text-align: right; }
.pi-item { display: flex; flex-direction: column; }
.pi-item span { font-size: 0.8rem; color: var(--color-text-faint); margin-bottom: 2px; }
.pi-item b { font-size: 1rem; color: var(--color-text); }
.mini-progress { position: relative; display: flex; justify-content: center; align-items: center; }
.mini-progress-text { position: absolute; font-size: 0.75rem; font-weight: var(--weight-extrabold); color: #0369A1; }

/* ================= 极简明亮模式：生成中底部面板重塑 ================= */
.bottom-panels { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-5); align-items: start; }
.compact-resource-panel { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: var(--radius-xl); padding: var(--space-5); box-shadow: var(--shadow-sm); }
.panel-header-minimal { display: flex; justify-content: space-between; margin-bottom: var(--space-4); }
.phm-left { display: flex; align-items: center; gap: var(--space-2); font-weight: var(--weight-extrabold); font-size: 1.05rem; color: var(--color-text); }
.phm-left .el-tag { margin-left: var(--space-1); }
.generated-resource-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: var(--space-3); }
.mini-resource-card { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3); background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-lg); cursor: pointer; transition: all var(--transition-base); }
.mini-resource-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-sm); background: var(--color-surface); border-color: var(--color-border-hover); }
.mrc-icon { width: 36px; height: 36px; border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; background: rgba(15, 23, 42, 0.03); }
.mrc-info { display: flex; flex-direction: column; min-width: 0; }
.mrc-info h4 { margin: 0; font-size: 0.9rem; font-weight: var(--weight-bold); color: var(--color-text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mrc-info span { font-size: 0.75rem; color: var(--color-text-muted); }

.live-event-timeline { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: var(--radius-xl); padding: var(--space-5); box-shadow: var(--shadow-sm); display: flex; flex-direction: column; height: 320px; }
.let-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-4); }
.let-title-group { display: flex; align-items: center; gap: var(--space-3); }
.let-title { font-weight: var(--weight-extrabold); font-size: 1.05rem; color: var(--color-text); }
.let-ping { width: 8px; height: 8px; background: var(--color-success); border-radius: 50%; position: relative; }
.let-ping::after { content: ''; position: absolute; inset: -4px; border-radius: 50%; border: 2px solid var(--color-success); animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite; }
@keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }
.let-count { font-size: 0.75rem; color: var(--color-text-muted); background: var(--color-surface-hover); padding: 2px var(--space-2); border-radius: var(--radius-pill); }
.let-body { flex: 1; overflow-y: auto; padding-right: var(--space-1); }
.let-body::-webkit-scrollbar { width: 4px; }
.let-body::-webkit-scrollbar-thumb { background: var(--color-border); border-radius: var(--radius-md); }
.let-list { display: flex; flex-direction: column; }
.let-row { display: flex; gap: var(--space-3); padding-bottom: var(--space-4); position: relative; }
.let-dot-col { display: flex; flex-direction: column; align-items: center; padding-top: var(--space-1); }
.let-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--color-border-hover); border: 2px solid var(--color-surface); box-shadow: 0 0 0 1px var(--color-border-hover); z-index: 1; }
.let-line { flex: 1; width: 1px; background: var(--color-border); margin: var(--space-1) 0 -16px; }
.let-row:last-child .let-line { display: none; }
.let-row.evt-running .let-dot { background: var(--color-info); box-shadow: 0 0 0 1px var(--color-info); }
.let-row.evt-success .let-dot { background: var(--color-success); box-shadow: 0 0 0 1px var(--color-success); }
.let-row.evt-failed .let-dot { background: var(--color-danger); box-shadow: 0 0 0 1px var(--color-danger); }
.let-content { flex: 1; min-width: 0; }
.let-top { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-1); }
.let-agent { font-size: 0.85rem; font-weight: var(--weight-bold); color: var(--color-text-strong); }
.let-type-tag { font-weight: var(--weight-bold); font-size: 0.7rem; height: 18px; padding: 0 6px; line-height: 16px; }
.let-time { font-size: 0.75rem; color: var(--color-text-faint); font-variant-numeric: tabular-nums; margin-left: auto; }
.let-msg { margin: 0; font-size: 0.8rem; color: var(--color-text-secondary); line-height: 1.5; word-break: break-all; }
.let-empty { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--color-text-faint); font-size: 0.9rem; }

.event-slide-enter-active, .event-slide-leave-active { transition: all var(--transition-slow); }
.event-slide-enter-from { opacity: 0; transform: translateX(-10px); }
.event-slide-leave-to { opacity: 0; transform: scale(0.95); }

.side-empty.minimal { display: flex; align-items: center; justify-content: center; height: 100px; color: var(--color-text-faint); font-size: 0.9rem; font-weight: var(--weight-semibold); }

@media (max-width: 1024px) {
  .bottom-panels { grid-template-columns: 1fr; }
  .compact-hero-bar { flex-direction: column; align-items: flex-start; gap: var(--space-4); }
}
</style>
