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
              placeholder="例如：我是软件工程大二学生，明天考《操作系统》。我搞不懂死锁的四个必要条件，我喜欢看图解，请帮我生成复习资料和几道自测题…"
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

                  <template v-if="agent.id === 'diagram'">
                    <div class="ctrl-group">
                      <label>图解渲染范式</label>
                      <el-select v-model="agentConfigs.diagram.diagram_type" size="default" class="w-full custom-select">
                        <el-option label="💡 智能自动判断 (Auto)" value="auto" />
                        <el-option-group label="通用基础图解">
                          <el-option label="层级结构图 (Hierarchy)" value="hierarchy" />
                          <el-option label="顺序流程图 (Flow)" value="flow" />
                          <el-option label="对比结构图 (Compare)" value="compare" />
                          <el-option label="关系网络图 (Relation)" value="relation" />
                        </el-option-group>
                        <el-option-group label="计算机学科图表">
                          <el-option label="类结构图 (Class)" value="class" />
                          <el-option label="实体关系图 (ER)" value="er" />
                          <el-option label="模块方块图 (Block)" value="block" />
                          <el-option label="协议包结构图 (Packet)" value="packet" />
                          <el-option label="Git 演进图 (Git)" value="git" />
                        </el-option-group>
                        <el-option-group label="软件工程图表">
                          <el-option label="交互时序图 (Sequence)" value="sequence" />
                          <el-option label="状态转移图 (State)" value="state" />
                          <el-option label="活动流程图 (Activity)" value="activity" />
                          <el-option label="用例关系图 (Usecase)" value="usecase" />
                          <el-option label="组件依赖图 (Component)" value="component" />
                          <el-option label="包依赖图 (Package)" value="package" />
                          <el-option label="部署拓扑图 (Deployment)" value="deployment" />
                          <el-option label="对象实例图 (Object)" value="object" />
                          <el-option label="通信协作图 (Communication)" value="communication" />
                        </el-option-group>
                      </el-select>
                    </div>
                    <div class="ctrl-group">
                      <label>视觉呈现风格</label>
                      <el-radio-group v-model="agentConfigs.diagram.visual_style" size="small" class="custom-radio-group">
                        <el-radio-button label="minimal">极简纯净</el-radio-button>
                        <el-radio-button label="exam">严肃应试</el-radio-button>
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
            <el-button type="primary" round class="action-btn-premium-mini glow-effect" @click="pushToLearningPath">
              启动学习路径 <el-icon class="el-icon--right"><Position /></el-icon>
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
        <DiagramView v-else-if="previewData.agentId === 'diagram'" :result-data="previewData.resultData" />
        <CodeView v-else-if="previewData.agentId === 'code'" :result-data="previewData.resultData" />
        <ReadingView v-else-if="previewData.agentId === 'reading'" :result-data="previewData.resultData" />
        <MarkdownView v-else :result-data="previewData.resultData" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  MagicStick, ArrowRight, Cpu,
  CircleCheckFilled, RefreshLeft, Position, VideoPlay,
  Document, Share, Monitor, Edit, Collection,
  Clock, Odometer
} from '@element-plus/icons-vue'

import MindmapView from '@/components/resource/MindmapView.vue'
import MarkdownView from '@/components/resource/MarkdownView.vue'
import QuizView from '@/components/resource/QuizView.vue'
import DiagramView from '@/components/resource/DiagramView.vue'
import CodeView from '@/components/resource/CodeView.vue'
import ReadingView from '@/components/resource/ReadingView.vue'

import { generateResources, type ResourceAgentId, type LearningScenario, type ResourceGenerateEvent } from '@/api/resource'

defineOptions({ name: 'ResourceGenerator' })

const router = useRouter()

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
type AnyAgentConfigs = {
  content: { structure: string; include_common_mistakes: boolean; include_examples: boolean; focus_mode: string; depth_level: string }
  mindmap: { map_type: string; max_depth: number; highlight_weak: boolean; expand_weak_points: boolean; include_prerequisites: boolean }
  diagram: { diagram_type: string; visual_style: string; highlight_mode: string; detail_level: string }
  quiz: { question_count: number; difficulty_mode: string; weak_point_weight: number; exam_style: string; include_analysis: boolean }
  code: { programming_language: string; case_type: string; comment_level: string; include_test: boolean; difficulty: string }
  reading: { reading_depth: string; max_items: number; resource_quality: string; include_practice: boolean; language_preference: string }
  video: { script_style: string; estimated_duration: number }
}

const SCENARIO_DEFAULTS: Record<string, Partial<AnyAgentConfigs>> = {
  exam_prep: { content: { structure: 'exam_points', include_common_mistakes: true, include_examples: true, focus_mode: 'weak_points', depth_level: 'standard' }, quiz: { question_count: 5, difficulty_mode: 'exam', weak_point_weight: 70, exam_style: '考研', include_analysis: true }, diagram: { diagram_type: 'auto', visual_style: 'exam', highlight_mode: 'weak_points', detail_level: 'standard' }, mindmap: { map_type: 'exam_map', max_depth: 3, highlight_weak: true, expand_weak_points: true, include_prerequisites: false }, code: { programming_language: 'python', case_type: 'algorithm_template', comment_level: 'standard', include_test: false, difficulty: 'intermediate' }, reading: { reading_depth: 'course_extended', max_items: 3, resource_quality: 'classic', include_practice: false, language_preference: 'chinese' } },
  daily_review: { content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'weak_points', depth_level: 'quick' }, quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 50, exam_style: 'school', include_analysis: true }, diagram: { diagram_type: 'auto', visual_style: 'minimal', highlight_mode: 'key_points', detail_level: 'concise' }, mindmap: { map_type: 'knowledge_tree', max_depth: 3, highlight_weak: true, expand_weak_points: true, include_prerequisites: false }, code: { programming_language: 'python', case_type: 'basic_demo', comment_level: 'standard', include_test: false, difficulty: 'beginner' }, reading: { reading_depth: 'course_extended', max_items: 3, resource_quality: 'balanced', include_practice: false, language_preference: 'chinese' } },
  project_practice: { content: { structure: 'case_driven', include_common_mistakes: true, include_examples: true, focus_mode: 'full_coverage', depth_level: 'deep' }, quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 30, exam_style: 'school', include_analysis: true }, diagram: { diagram_type: 'auto', visual_style: 'minimal', highlight_mode: 'all', detail_level: 'detailed' }, mindmap: { map_type: 'knowledge_tree', max_depth: 4, highlight_weak: false, expand_weak_points: false, include_prerequisites: true }, code: { programming_language: 'python', case_type: 'basic_demo', comment_level: 'standard', include_test: true, difficulty: 'intermediate' }, reading: { reading_depth: 'engineering', max_items: 5, resource_quality: 'latest', include_practice: true, language_preference: 'chinese' } },
  self_study: { content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'key_concepts', depth_level: 'deep' }, quiz: { question_count: 5, difficulty_mode: 'basic', weak_point_weight: 40, exam_style: 'school', include_analysis: true }, diagram: { diagram_type: 'auto', visual_style: 'minimal', highlight_mode: 'key_points', detail_level: 'standard' }, mindmap: { map_type: 'knowledge_tree', max_depth: 4, highlight_weak: false, expand_weak_points: false, include_prerequisites: true }, code: { programming_language: 'python', case_type: 'basic_demo', comment_level: 'verbose', include_test: false, difficulty: 'beginner' }, reading: { reading_depth: 'course_extended', max_items: 3, resource_quality: 'balanced', include_practice: false, language_preference: 'chinese' } },
}

// ===================== 1. 核心状态 =====================
type Phase = 'input' | 'personalize' | 'generating' | 'result'
const currentPhase = ref<Phase>('input')

const naturalInput = ref('')
const isInputFocused = ref(false)
const learningScenario = ref<LearningScenario>('daily_review')

const quickPrompts = [
  "复习《计算机网络》TCP三次握手，我喜欢看时序图，请多出几道难题",
  "零基础学习 Python 多线程，需要底层原理图解和带详细注释的代码",
  "考研冲刺《数据结构》二叉树，帮我精简思维导图，重点标注高频考点"
]

const agentMetaList = [
  { id: 'master', name: '多智能体调度', icon: Cpu, colorClass: 'text-blue' },
  { id: 'reviewer', name: '资源审查', icon: CircleCheckFilled, colorClass: 'text-emerald' },
  { id: 'assembler', name: '资源组装', icon: Position, colorClass: 'text-indigo' },
  { id: 'content', name: '核心知识讲解', icon: Document, colorClass: 'text-blue' },
  { id: 'diagram', name: '原理解析图解', icon: Monitor, colorClass: 'text-orange' },
  { id: 'mindmap', name: '知识结构图谱', icon: Share, colorClass: 'text-purple' },
  { id: 'code', name: '实战代码沙箱', icon: Cpu, colorClass: 'text-red' },
  { id: 'quiz', name: '自测题训练', icon: Edit, colorClass: 'text-emerald' },
  { id: 'reading', name: '拓展阅读推荐', icon: Collection, colorClass: 'text-indigo' },
  { id: 'video', name: '视频动画脚本', icon: VideoPlay, colorClass: 'text-slate', disabled: true }
]

const getAgentMeta = (id: string) => agentMetaList.find(a => a.id === id) || { name: id, icon: Document, colorClass: 'text-blue' }
const enabledAgentIds = ref<ResourceAgentId[]>(['content', 'mindmap', 'diagram', 'code', 'quiz', 'reading'])

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
  diagram: { diagram_type: 'auto' as const, visual_style: 'minimal' as const, highlight_mode: 'key_points' as const, detail_level: 'standard' as const },
  quiz: { question_count: 5, difficulty_mode: 'adaptive' as const, weak_point_weight: 50, exam_style: 'school' as const, include_analysis: true, question_types: ['single', 'multiple', 'judge'] as string[] },
  code: { programming_language: 'python' as const, case_type: 'basic_demo' as const, comment_level: 'standard' as const, include_test: false, difficulty: 'beginner' as const },
  reading: { reading_depth: 'course_extended' as const, max_items: 3, resource_quality: 'balanced' as const, include_practice: false, language_preference: 'chinese' as const },
  video: { script_style: 'concept_animation', estimated_duration: 3 },
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
const planningHistory = ref<any[]>([])
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
  { key: 'layer_0', label: '认知建构层', status: 'pending' },
  { key: 'layer_1', label: '实践拓展层', status: 'pending' },
  { key: 'layer_2', label: '检测巩固层', status: 'pending' },
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

const DEFAULT_RESOURCE_SEQUENCE = ['content', 'mindmap', 'diagram', 'code', 'quiz', 'reading', 'video']

// 每个 agent 属于哪个「阶段层」及在流图中的 x 坐标（固定）
const PHASE_LAYOUT: { x: number; agents: string[] }[] = [
  { x: 28, agents: ['content', 'mindmap'] },
  { x: 52, agents: ['diagram', 'code', 'quiz'] },
  { x: 72, agents: ['reading'] },
]

const flowAgentMeta: Record<string, { label: string; icon: any }> = {
  content: { label: '课程讲解', icon: Document },
  mindmap: { label: '思维导图', icon: Share },
  diagram: { label: '知识图解', icon: Monitor },
  code: { label: '代码案例', icon: Cpu },
  quiz: { label: '练习题', icon: Edit },
  reading: { label: '拓展阅读', icon: Collection },
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
  ['content', 'diagram'],
  ['mindmap', 'diagram'],
  ['content', 'code'],
  ['content', 'quiz'],
  ['diagram', 'reading'],
  ['code', 'reading'],
  ['quiz', 'reading'],
  ['content', 'reviewer'],
  ['mindmap', 'reviewer'],
  ['diagram', 'reviewer'],
  ['code', 'reviewer'],
  ['reading', 'reviewer'],
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

const resultTopicSummary = computed(() => (
  finalBundle.value?.topic
  || finalBundle.value?.metadata?.topic
  || finalBundle.value?.metadata?.course
  || finalBundle.value?.learning_need
  || stringifyCompact(naturalInput.value, 42)
  || '本次个性化学习任务'
))

const resultNeedSummary = computed(() => (
  finalBundle.value?.gap
  || finalBundle.value?.metadata?.gap
  || finalBundle.value?.metadata?.learning_need
  || finalBundle.value?.metadata?.weak_points
  || finalBundle.value?.learning_need
  || stringifyCompact(naturalInput.value, 86)
  || '系统已根据你的输入生成学习资源。'
))



const getResourceTypeLabel = (type: string) => {
  const labelMap: Record<string, string> = {
    content: '专业讲解',
    mindmap: '知识导图',
    diagram: '知识图解',
    code: '代码案例',
    quiz: '自测题',
    reading: '拓展阅读',
    video: '视频脚本',
    reviewer: '质量审查',
  }
  return labelMap[type] || getAgentMeta(type).name || type
}

const getResourceUsageHint = (type: string) => {
  const hintMap: Record<string, string> = {
    content: '先阅读讲解，建立基础概念和关键术语理解。',
    mindmap: '用于梳理知识层级、概念关系和复习框架。',
    diagram: '用图解理解流程、结构、状态变化或核心机制。',
    code: '通过代码案例把知识点落到实践，适合边运行边理解。',
    quiz: '完成自测题，检查掌握情况并定位仍然薄弱的知识点。',
    reading: '用于课后拓展和深入理解，适合完成基础资源后阅读。',
    video: '可作为后续视频或动画讲解的脚本基础。',
  }
  return hintMap[type] || '建议结合本次学习目标使用该资源。'
}

const getResourceStageLabel = (type: string) => {
  const stageMap: Record<string, string> = {
    content: '概念理解',
    mindmap: '结构梳理',
    diagram: '原理可视化',
    code: '实践验证',
    quiz: '检测巩固',
    reading: '拓展提升',
    video: '讲解呈现',
  }
  return stageMap[type] || '资源学习'
}

const getDefaultResourceFormat = (type: string) => {
  const formatMap: Record<string, string> = {
    content: 'Markdown',
    mindmap: 'Markdown / Tree',
    diagram: 'Diagram Source',
    code: 'Code',
    quiz: 'Quiz JSON',
    reading: 'Reading List',
    video: 'Script',
  }
  return formatMap[type] || 'Resource'
}

const getEstimatedTime = (type: string) => {
  const timeMap: Record<string, string> = {
    content: '10-15 分钟',
    mindmap: '5-8 分钟',
    diagram: '6-10 分钟',
    code: '15-25 分钟',
    quiz: '10-20 分钟',
    reading: '20-30 分钟',
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
    diagram: 'tone-amber',
    code: 'tone-rose',
    quiz: 'tone-emerald',
    reading: 'tone-indigo',
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

  // 仅发送后端 schema 中允许的字段（question_types 是纯前端 UI 状态，不传后端）
  const { question_types: _qt, ...quizConfig } = agentConfigs.quiz
  const requestAgentConfigs = {
    content: agentConfigs.content,
    mindmap: agentConfigs.mindmap,
    diagram: agentConfigs.diagram,
    quiz: quizConfig,
    code: agentConfigs.code,
    reading: agentConfigs.reading,
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
      id: 'mock-diagram-tcp-sequence',
      type: 'diagram',
      title: 'TCP三次握手时序图（含异常分支）',
      summary: '主干流程 + 丢包重传 + SYN Flood 防护标注，适合按时序线复盘每个状态迁移。',
      format: 'Diagram Source',
      metadata: { difficulty: 'advanced', estimated_time: '10-15 分钟' },
      content: {
        title: 'TCP三次握手时序图',
        diagram_type: 'sequence',
        mermaid: `sequenceDiagram
participant C as Client
participant S as Server
C->>S: SYN(seq=x)
S->>C: SYN+ACK(seq=y, ack=x+1)
C->>S: ACK(ack=y+1)
Note over C,S: Connection Established`,
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
      planningHistory.value.push(event.payload)
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
  const suffixPattern = /\s*[-－—]\s*(内容讲解|思维导图|知识图解|代码实操案例|拓展阅读|自测题)\s*$/
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

const pushToLearningPath = () => {
  const resourceId = finalBundle.value?.resource_id || finalBundle.value?.id
  const taskId = finalBundle.value?.task_id || resourceId
  router.push({
    path: '/path-planner',
    query: {
      ...(resourceId ? { resource_id: String(resourceId) } : {}),
      ...(taskId ? { task_id: String(taskId) } : {}),
    },
  })
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
.elegant-generator-layout { width: 100%; height: calc(100vh - 64px); background: #FAFAFA; font-family: 'Plus Jakarta Sans', 'Inter', system-ui, -apple-system, sans-serif; overflow-x: hidden; position: relative; padding-top: 20px; }
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
  color: #4F46E5;
  font-size: 1.9rem;
  border-radius: 22px;
  margin-bottom: 1.35rem;
  box-shadow: 0 8px 24px rgba(79, 70, 229, 0.12);
}
.greeting-title { font-size: clamp(2.1rem, 4.2vw, 3.15rem); font-weight: 850; color: #0B1B3A; margin: 0 0 0.9rem; letter-spacing: -0.03em; }
.greeting-subtitle { font-size: 1.08rem; color: #5A6E8C; line-height: 1.75; max-width: 680px; margin: 0 auto; }
.search-box-wrapper {
  width: 100%;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(203, 213, 225, 0.6);
  border-radius: 30px;
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.04);
  backdrop-filter: blur(12px);
  padding: 10px;
  transition: border-color 0.28s ease, box-shadow 0.28s ease, transform 0.28s ease;
}
.search-box-wrapper.is-focused {
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 16px 48px rgba(59, 130, 246, 0.08);
  transform: translateY(-4px) scale(1.005);
}
.elegant-textarea :deep(.el-textarea__inner) {
  border: none;
  background: transparent;
  box-shadow: none !important;
  font-size: 1.13rem;
  color: #0F2549;
  padding: 22px 26px;
  line-height: 1.68;
  resize: none;
}
.elegant-textarea :deep(.el-textarea__inner)::placeholder { color: #9AAACA; font-weight: 500; }
.search-actions { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px 10px 24px; gap: 12px; }
.ai-hint { font-size: 0.92rem; color: #62748F; display: flex; align-items: center; gap: 8px; font-weight: 600; }
.ai-hint .el-icon { color: #3B82F6; font-size: 1rem; }
.generate-btn {
  padding: 12px 28px;
  font-size: 1.02rem;
  font-weight: 800;
  border-radius: 999px;
  background: #0F172A !important;
  border-color: transparent !important;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
  transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
}
.generate-btn:hover:not(:disabled) { transform: translateY(-1px); background: #1E293B !important; box-shadow: 0 8px 20px rgba(15, 23, 42, 0.2); filter: none; }
.suggestion-area { margin-top: 2.25rem; display: flex; flex-direction: column; align-items: center; gap: 14px; }
.suggestion-label { font-size: 0.84rem; color: #8397B7; font-weight: 700; letter-spacing: 0.04em; }
.suggestion-tags { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
.s-tag {
  cursor: pointer;
  background: #FFFFFF !important;
  border-color: #D8E5FA !important;
  color: #4A607F !important;
  padding: 8px 16px;
  height: auto;
  font-size: 0.9rem;
  font-weight: 600;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
  transition: transform 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}
.s-tag:hover { transform: translateY(-1px); background: #EFF6FF !important; border-color: #93C5FD !important; color: #1D4ED8 !important; }

/* ================= Phase 2: Personalize View ================= */
.personalize-view { background: #FCFDFE; align-items: center; overflow-y: auto; padding: 60px 20px; position: relative; }
.aurora-background { position: absolute; top: -20%; left: -10%; width: 120%; height: 140%; z-index: 0; background: radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.05) 0%, transparent 40%), radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.05) 0%, transparent 40%), radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.02) 0%, transparent 60%); filter: blur(80px); pointer-events: none; }
.personalize-container { width: 100%; max-width: 1160px; display: flex; flex-direction: column; gap: 48px; position: relative; z-index: 1; }
.view-header { text-align: center; margin-bottom: 0; }
.header-badge { margin-bottom: 16px; font-weight: 700; letter-spacing: 0.05em; background: #0F172A !important; border: none; }
.view-header h2 { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 2.5rem; font-weight: 800; color: #0F172A; margin: 0 0 16px; letter-spacing: -0.02em; }
.view-header p { font-size: 1.1rem; color: #64748B; margin: 0; max-width: 600px; margin: 0 auto; line-height: 1.6; }
.scenario-selector-v2 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
.scenario-card { background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: 20px; padding: 20px; display: flex; align-items: center; gap: 16px; cursor: pointer; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); position: relative; box-shadow: 0 4px 20px -4px rgba(15, 23, 42, 0.03), 0 2px 8px -2px rgba(15, 23, 42, 0.02); }
.scenario-card:hover { transform: translateY(-3px); background: rgba(255, 255, 255, 0.75); border-color: rgba(148, 163, 184, 0.4); box-shadow: 0 12px 32px -8px rgba(15, 23, 42, 0.08), 0 4px 12px -4px rgba(15, 23, 42, 0.04); }
.scenario-card.active { background: #FFFFFF; border-color: #0F172A; box-shadow: 0 8px 24px -8px rgba(15, 23, 42, 0.12); border-width: 1.5px; }
.scenario-icon-box { width: 48px; height: 48px; background: #F8FAFC; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: 850; color: #0369A1; transition: background-color 0.3s ease, transform 0.3s ease; }
.scenario-card.active .scenario-icon-box { background: #EFF6FF; transform: scale(1.1); }
.scenario-info { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.s-name { font-weight: 700; font-size: 1rem; color: #0F172A; }
.s-desc { font-size: 0.75rem; color: #64748B; line-height: 1.4; }
.active-dot { position: absolute; top: 12px; right: 12px; width: 8px; height: 8px; background: #0F172A; border-radius: 50%; box-shadow: none; }
.config-section-v2 { margin-top: 10px; }
.agent-configs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; }
.config-card-v2 { background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: 24px; overflow: hidden; display: flex; flex-direction: column; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); box-shadow: 0 4px 20px -4px rgba(15, 23, 42, 0.03), 0 2px 8px -2px rgba(15, 23, 42, 0.02); }
.config-card-v2:hover { transform: translateY(-3px); border-color: rgba(148, 163, 184, 0.4); box-shadow: 0 12px 32px -8px rgba(15, 23, 42, 0.08), 0 4px 12px -4px rgba(15, 23, 42, 0.04); }
.cc-header-v2 { padding: 24px 24px 16px; display: flex; align-items: center; gap: 12px; }
.cc-icon-wrap { width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; background: #F8FAFC; }
.cc-icon-wrap.text-blue { background: #EFF6FF; color: #3B82F6; }
.cc-icon-wrap.text-orange { background: #FFF7ED; color: #F59E0B; }
.cc-icon-wrap.text-purple { background: #F5F3FF; color: #8B5CF6; }
.cc-icon-wrap.text-red { background: #FEF2F2; color: #EF4444; }
.cc-icon-wrap.text-emerald { background: #ECFDF5; color: #10B981; }
.cc-icon-wrap.text-indigo { background: #EEF2FF; color: #6366F1; }
.cc-icon-wrap.text-slate { background: #F1F5F9; color: #475569; }
.config-card-v2.disabled { opacity: 0.74; background: #F8FAFC; }
.config-card-v2.agent-off { border-color: #E2E8F0; opacity: 0.85; }
.cc-header-v2 { padding: 24px 24px 16px; display: flex; align-items: center; gap: 12px; }
.cc-header-switch { margin-left: auto; flex-shrink: 0; }
.cc-body-v2.body-disabled { opacity: 0.38; pointer-events: none; filter: grayscale(60%); }
.question-type-group { display: flex; gap: 10px; flex-wrap: wrap; }
.question-type-group :deep(.el-checkbox) { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 6px 12px; margin: 0; transition: all 0.2s ease; }
.question-type-group :deep(.el-checkbox.is-checked) { background: #EFF6FF; border-color: #93C5FD; }
.question-type-group :deep(.el-checkbox__label) { font-size: 0.88rem; font-weight: 600; color: #334155; }
.question-type-group :deep(.el-checkbox.is-checked .el-checkbox__label) { color: #1D4ED8; }
.coming-soon-panel { min-height: 128px; border: 1px dashed #CBD5E1; border-radius: 16px; background: #FFFFFF; display: flex; align-items: center; gap: 14px; padding: 20px; color: #475569; }
.coming-soon-panel .el-icon { width: 42px; height: 42px; border-radius: 14px; background: #F1F5F9; color: #334155; font-size: 1.3rem; flex: 0 0 auto; }
.coming-soon-panel div { display: flex; flex-direction: column; gap: 6px; }
.coming-soon-panel strong { color: #0F172A; font-size: 0.98rem; }
.coming-soon-panel span { color: #64748B; font-size: 0.82rem; line-height: 1.55; }
.cc-title { font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 700; font-size: 1.1rem; color: #0F172A; }
.cc-body-v2 { padding: 0 24px 24px; display: flex; flex-direction: column; gap: 24px; flex: 1; }
.ctrl-group { display: flex; flex-direction: column; gap: 12px; }
.ctrl-group label { font-size: 0.85rem; color: #64748B; font-weight: 700; text-transform: uppercase; letter-spacing: 0.02em; }
:deep(.custom-select .el-input__wrapper) { background-color: #F8FAFC; border-radius: 12px; padding: 4px 12px; box-shadow: 0 0 0 1px #E2E8F0 inset !important; transition: background-color 0.2s ease, box-shadow 0.2s ease; }
:deep(.custom-select .el-input__wrapper:hover) { background-color: #F1F5F9; box-shadow: 0 0 0 1px #CBD5E1 inset !important; }
:deep(.custom-select .el-input__wrapper.is-focus) { background-color: #FFFFFF; box-shadow: 0 0 0 2px #3B82F6 inset !important; }
.ctrl-switch-group-v2 { display: flex; flex-direction: column; gap: 20px; }
.ctrl-switch-v2 { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.sw-info { display: flex; flex-direction: column; gap: 2px; }
.sw-label { font-size: 0.9rem; font-weight: 600; color: #1E293B; }
.sw-desc { font-size: 0.75rem; color: #94A3B8; line-height: 1.4; }
.custom-radio-group { display: flex; gap: 8px; width: 100%; }
:deep(.custom-radio-group .el-radio-button) { flex: 1; }
:deep(.custom-radio-group .el-radio-button__inner) { width: 100%; border-radius: 10px !important; border: 1px solid transparent !important; background: rgba(241, 245, 249, 0.6); color: #64748B; font-weight: 600; transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease; padding: 10px 0; }
:deep(.custom-radio-group .el-radio-button__original-radio:checked + .el-radio-button__inner) { background-color: #FFFFFF !important; color: #0F172A !important; border-color: rgba(226, 232, 240, 0.8) !important; box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06) !important; }
.slider-label-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: -4px; }
.slider-value { font-size: 0.9rem; color: #3B82F6; font-weight: 700; }
.custom-slider-v2 { padding: 0 8px; }
.personalize-footer-v2 { display: flex; flex-direction: column; align-items: center; gap: 20px; margin-top: 16px; padding-bottom: 40px; }
.footer-btns { display: flex; justify-content: center; gap: 24px; }
.selected-agents-bar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: center; background: rgba(255,255,255,0.75); backdrop-filter: blur(12px); border: 1px solid #E2E8F0; border-radius: 16px; padding: 12px 20px; max-width: 860px; }
.sab-label { font-size: 0.85rem; color: #64748B; font-weight: 700; white-space: nowrap; }
.sab-pills { display: flex; gap: 8px; flex-wrap: wrap; }
.sab-pill { display: inline-flex; align-items: center; gap: 5px; font-size: 0.82rem; font-weight: 600; cursor: default; }
.sab-hint { font-size: 0.78rem; color: #D97706; font-weight: 700; }
.footer-back-btn { font-weight: 700; color: #64748B; border: 1px solid #E2E8F0; }
.launch-btn-v2 { font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 800; padding: 0 40px; background: #0369A1 !important; border: none; box-shadow: 0 10px 25px -5px rgba(3, 105, 161, 0.4); transition: transform 0.3s ease, box-shadow 0.3s ease; }
.launch-btn-v2:hover { transform: translateY(-3px); box-shadow: 0 15px 30px -5px rgba(3, 105, 161, 0.5); }

/* ================= Phase 3: Generating View ================= */
.generating-view { background: #F8FAFC; overflow-y: auto; }
.generation-workbench { width: 100%; max-width: 1760px; margin: 0 auto; padding: 28px; display: flex; flex-direction: column; gap: 20px; color: #0F172A; }
.workbench-hero { background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: 24px; padding: 24px 28px; display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 28px; align-items: center; box-shadow: 0 4px 20px -4px rgba(15, 23, 42, 0.03), 0 2px 8px -2px rgba(15, 23, 42, 0.02); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.workbench-kicker { margin-bottom: 12px; color: #0369A1 !important; border-color: #BAE6FD !important; background: #F0F9FF !important; font-weight: 800; letter-spacing: 0.05em; }
.workbench-hero h2 { margin: 0 0 10px; font-size: 2rem; line-height: 1.2; font-weight: 850; color: #0F172A; text-wrap: balance; }
.workbench-hero p { margin: 0; max-width: 760px; color: #64748B; line-height: 1.65; }
.progress-panel { grid-column: 1 / -1; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 18px; padding: 18px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.progress-number { font-size: 2.1rem; font-weight: 850; color: #0369A1; font-variant-numeric: tabular-nums; }
.current-message { color: #475569; line-height: 1.5; word-break: break-word; }
.generation-error { border-radius: 16px; }
.workbench-grid { display: grid; grid-template-columns: 260px minmax(0, 1fr) 340px; gap: 20px; align-items: start; }
.workflow-timeline-panel, .side-card, .agent-layer-section, .workbench-collapse, .review-summary-card, .result-resource-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 20px; box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04); }
.workflow-timeline-panel { padding: 20px; position: sticky; top: 20px; }
.panel-title { font-size: 0.92rem; font-weight: 850; color: #0F172A; margin-bottom: 16px; }
.workflow-stage-list { display: flex; flex-direction: column; gap: 12px; }
.workflow-stage-item { min-height: 42px; display: grid; grid-template-columns: 14px minmax(0, 1fr) auto; gap: 10px; align-items: center; color: #64748B; }
.stage-dot { width: 10px; height: 10px; border-radius: 999px; background: #CBD5E1; box-shadow: 0 0 0 4px #F1F5F9; }
.workflow-stage-item.is-running .stage-dot { background: #2563EB; box-shadow: 0 0 0 4px #DBEAFE; }
.workflow-stage-item.is-success .stage-dot { background: #059669; box-shadow: 0 0 0 4px #D1FAE5; }
.workflow-stage-item.is-failed .stage-dot { background: #DC2626; box-shadow: 0 0 0 4px #FEE2E2; }
.workflow-stage-item.is-skipped .stage-dot { background: #D97706; box-shadow: 0 0 0 4px #FEF3C7; }
.stage-label { min-width: 0; font-weight: 700; color: #334155; }
.agent-live-panel { display: flex; flex-direction: column; gap: 20px; min-width: 0; }
.agent-layer-section { padding: 22px; }
.layer-header { display: flex; justify-content: space-between; gap: 20px; align-items: flex-start; margin-bottom: 18px; }
.layer-index { display: inline-flex; color: #0369A1; font-size: 0.78rem; font-weight: 850; letter-spacing: 0.04em; margin-bottom: 6px; }
.layer-header h3 { margin: 0 0 6px; font-size: 1.2rem; font-weight: 850; color: #0F172A; }
.layer-header p { margin: 0; color: #64748B; line-height: 1.5; }
.agent-card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.runtime-agent-card { border: 1px solid rgba(226, 232, 240, 0.8); border-radius: 18px; background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); padding: 18px; display: flex; flex-direction: column; gap: 14px; min-width: 0; box-shadow: 0 4px 20px -4px rgba(15, 23, 42, 0.03), 0 2px 8px -2px rgba(15, 23, 42, 0.02); transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.runtime-agent-card.is-running { border-color: #93C5FD; box-shadow: 0 12px 28px rgba(37, 99, 235, 0.10); }
.runtime-agent-card.is-success { border-color: #A7F3D0; }
.runtime-agent-card.is-failed { border-color: #FCA5A5; }
.agent-card-header, .agent-title-wrap { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-width: 0; }
.agent-title-wrap { justify-content: flex-start; flex: 1; }
.agent-icon { width: 42px; height: 42px; border-radius: 14px; display: flex; align-items: center; justify-content: center; flex: 0 0 auto; background: rgba(15, 23, 42, 0.03); border: 1px solid rgba(15, 23, 42, 0.04); }
.agent-icon.text-blue { color: #2563EB; }
.agent-icon.text-orange { color: #EA580C; }
.agent-icon.text-purple { color: #7C3AED; }
.agent-icon.text-red { color: #DC2626; }
.agent-icon.text-emerald { color: #059669; }
.agent-icon.text-indigo { color: #4F46E5; }
.agent-title-wrap h4 { margin: 0 0 4px; color: #0F172A; font-size: 1rem; font-weight: 850; overflow-wrap: anywhere; }
.agent-title-wrap span { color: #64748B; font-size: 0.82rem; }
.agent-current-action { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 14px; padding: 12px; display: flex; flex-direction: column; gap: 6px; }
.agent-current-action strong { color: #0F172A; line-height: 1.45; overflow-wrap: anywhere; }
.agent-current-action span, .agent-info-block p, .output-preview p, .planning-card p, .live-resource-card p, .result-resource-card p { color: #64748B; line-height: 1.58; margin: 0; overflow-wrap: anywhere; }
.agent-info-block { display: flex; flex-direction: column; gap: 10px; }
.agent-info-block b { display: inline-flex; margin-right: 8px; color: #0369A1; }
.tag-field, .kv-grid, .output-preview { display: flex; flex-direction: column; gap: 8px; }
.field-label { font-size: 0.76rem; color: #64748B; font-weight: 850; text-transform: uppercase; letter-spacing: 0.03em; }
.tag-row { display: flex; gap: 8px; flex-wrap: wrap; min-width: 0; }
.kv-row { display: grid; grid-template-columns: minmax(72px, 0.7fr) minmax(0, 1.3fr); gap: 10px; align-items: start; padding: 8px 0; border-bottom: 1px solid rgba(15, 23, 42, 0.04); }
.kv-row span { color: #64748B; font-size: 0.82rem; overflow-wrap: anywhere; }
.kv-row b { color: #1E293B; font-size: 0.82rem; font-weight: 650; overflow-wrap: anywhere; }
.output-preview { background: #F8FAFC; border-radius: 14px; padding: 12px; }
.output-preview strong { color: #0F172A; overflow-wrap: anywhere; }
.agent-progress { margin-top: auto; }
.empty-layer-state, .side-empty { border: 1px dashed #CBD5E1; border-radius: 16px; color: #94A3B8; background: #F8FAFC; padding: 22px; text-align: center; line-height: 1.5; }
.resource-side-panel { display: flex; flex-direction: column; gap: 20px; min-width: 0; position: sticky; top: 20px; }
.side-card { padding: 20px; }
.profile-summary-grid { display: flex; flex-direction: column; gap: 10px; }
.profile-summary-item { display: grid; grid-template-columns: 82px minmax(0, 1fr); gap: 10px; padding-bottom: 10px; border-bottom: 1px solid rgba(15, 23, 42, 0.04); }
.profile-summary-item span { color: #64748B; font-size: 0.82rem; }
.profile-summary-item b { color: #1E293B; font-size: 0.86rem; line-height: 1.45; overflow-wrap: anywhere; }
.live-resource-list { display: flex; flex-direction: column; gap: 12px; }
.live-resource-card { border: 1px solid #E2E8F0; border-radius: 16px; padding: 14px; display: flex; flex-direction: column; gap: 10px; background: #FFFFFF; }
.live-resource-card h4 { margin: 8px 0 0; color: #0F172A; font-size: 0.98rem; line-height: 1.35; overflow-wrap: anywhere; }
.resource-meta-line { display: flex; flex-wrap: wrap; gap: 8px; color: #64748B; font-size: 0.78rem; }
.workbench-collapse { padding: 4px 18px; }
.planning-history-list { display: grid; gap: 14px; }
.planning-card { border: 1px solid #E2E8F0; border-radius: 16px; padding: 16px; }
.planning-card h4 { margin: 0 0 8px; color: #0F172A; }
.planning-agent-list { display: grid; gap: 10px; margin-top: 14px; }
.planning-agent-item { background: #F8FAFC; border-radius: 12px; padding: 12px; display: grid; gap: 6px; }
.planning-agent-item strong { color: #0369A1; }
.planning-agent-item span { color: #334155; line-height: 1.5; overflow-wrap: anywhere; }
.planning-agent-item em { color: #64748B; font-style: normal; line-height: 1.5; overflow-wrap: anywhere; }
.event-log-list { display: flex; flex-direction: column; gap: 8px; max-height: 360px; overflow-y: auto; }
.event-log-row { display: grid; grid-template-columns: 78px 86px 80px 72px minmax(0, 1fr); gap: 10px; align-items: center; padding: 10px 0; border-bottom: 1px solid #F1F5F9; }
.event-log-row span, .event-log-row b { color: #64748B; font-size: 0.82rem; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.event-log-row p { margin: 0; color: #334155; line-height: 1.45; overflow-wrap: anywhere; }

.progress-metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.progress-metrics span { min-width: 0; padding: 10px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; color: #334155; line-height: 1.35; overflow-wrap: anywhere; }
.progress-metrics b { display: block; color: #94A3B8; font-size: 0.72rem; margin-bottom: 4px; }
.generation-focus-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 20px; align-items: stretch; }
.flow-canvas-card, .resource-summary-card, .result-group-section { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 20px; box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04); }
.flow-canvas-card { padding: 22px; min-width: 0; }
.flow-card-header, .result-group-header { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.flow-card-header h3, .result-group-header h3 { margin: 4px 0 0; color: #0F172A; font-size: 1.18rem; font-weight: 850; }
.flow-canvas { position: relative; height: 720px; margin-top: 18px; overflow: auto; border-radius: 22px; background: #FCFCFD; border: 1px solid rgba(226, 232, 240, 0.6); }
.flow-canvas-inner { position: relative; min-width: 1320px; height: 680px; }
.flow-lines { position: absolute; inset: 0; z-index: 1; width: 100%; height: 100%; pointer-events: none; }
.flow-edge { stroke: #CBD5E1; stroke-width: 2.4; stroke-linecap: round; opacity: 0.72; }
.flow-edge.success { stroke: #10B981; opacity: 0.92; }
.flow-edge.failed { stroke: #EF4444; opacity: 0.9; }
.flow-edge.running, .flow-edge.active { stroke: #4F46E5; stroke-dasharray: 10 10; animation: flowDash 1.2s linear infinite; opacity: 1; }
@keyframes flowDash { to { stroke-dashoffset: -20; } }
.flow-node { position: absolute; z-index: 5; transform: translate(-50%, -50%); width: 186px; min-height: 112px; border: 1px solid rgba(203, 213, 225, 0.6); border-radius: 18px; background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(12px); display: flex; flex-direction: column; align-items: stretch; justify-content: flex-start; gap: 8px; cursor: pointer; color: #475569; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04); padding: 12px; text-align: left; transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease; }
.flow-node:hover, .flow-node.focused { transform: translate(-50%, -50%) translateY(-3px); border-color: #2563EB; box-shadow: 0 16px 30px rgba(37, 99, 235, 0.16); }
.node-head { display: flex; align-items: center; gap: 10px; min-width: 0; }
.flow-node .node-icon { width: 34px; height: 34px; border-radius: 12px; display: flex; align-items: center; justify-content: center; background: #F1F5F9; color: #64748B; flex: 0 0 auto; }
.node-title-group { min-width: 0; flex: 1; }
.flow-node .node-label { display: block; font-weight: 850; color: #1E293B; font-size: 0.9rem; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.flow-node small { display: block; margin-top: 2px; color: #94A3B8; font-weight: 700; font-size: 0.72rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.node-live-log { border: 1px solid #E2E8F0; background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%); border-radius: 14px; padding: 9px 10px; min-height: 64px; box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8); }
.node-live-log-meta { display: flex; justify-content: space-between; gap: 8px; align-items: center; margin-bottom: 4px; }
.node-live-log-meta span { color: #2563EB; font-size: 0.66rem; font-weight: 850; letter-spacing: 0.05em; }
.node-live-log-meta em { color: #94A3B8; font-size: 0.66rem; font-style: normal; font-variant-numeric: tabular-nums; }
.node-live-log p { margin: 0; color: #475569; font-size: 0.72rem; line-height: 1.35; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.log-fade-enter-active, .log-fade-leave-active { transition: opacity 0.22s ease, transform 0.22s ease; }
.log-fade-enter-from { opacity: 0; transform: translateY(6px); }
.log-fade-leave-to { opacity: 0; transform: translateY(-6px); }
.node-progress { position: relative; height: 3px; margin-top: auto; overflow: hidden; border-radius: 999px; background: #E2E8F0; }
.node-progress span { position: absolute; inset: 0 auto 0 0; width: 45%; border-radius: inherit; background: #2563EB; animation: nodeProgressMove 1.35s ease-in-out infinite; }
.flow-node.is-running { border-color: #A5B4FC; box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.08), 0 8px 24px rgba(15, 23, 42, 0.06); animation: nodePulse 2s ease-in-out infinite; }
.flow-node.is-running .node-icon { background: #DBEAFE; color: #2563EB; }
.flow-node.is-running .node-live-log { border-color: #BFDBFE; background: #EFF6FF; }
.flow-node.is-success { border-color: #86EFAC; }
.flow-node.is-success .node-icon { background: #DCFCE7; color: #16A34A; }
.flow-node.is-failed { border-color: #FCA5A5; }
.flow-node.is-failed .node-icon { background: #FEE2E2; color: #DC2626; }
.flow-node.is-skipped { opacity: 0.68; }
@keyframes nodePulse { 50% { box-shadow: 0 0 0 6px rgba(99, 102, 241, 0.06), 0 10px 26px rgba(15, 23, 42, 0.08); } }
@keyframes nodeProgressMove { 0% { transform: translateX(-120%); } 100% { transform: translateX(260%); } }
.workflow-stage-strip { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }
.stage-chip { border: 1px solid #E2E8F0; background: #FFFFFF; border-radius: 999px; padding: 8px 12px; color: #64748B; font-weight: 750; display: inline-flex; align-items: center; gap: 7px; cursor: pointer; }
.stage-chip span { width: 8px; height: 8px; border-radius: 999px; background: #CBD5E1; }
.stage-chip.is-running { color: #1D4ED8; border-color: #BFDBFE; background: #EFF6FF; }
.stage-chip.is-running span { background: #2563EB; }
.stage-chip.is-success { color: #047857; border-color: #A7F3D0; background: #ECFDF5; }
.stage-chip.is-success span { background: #10B981; }
.stage-chip.is-failed { color: #B91C1C; border-color: #FCA5A5; background: #FEF2F2; }
.stage-chip.is-failed span { background: #EF4444; }
.resource-summary-card { padding: 24px; }
.interactive-resources-panel {
  min-height: 0;
  height: auto;
  padding-top: 4px;
  padding-bottom: 6px;
}
.resource-status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
.resource-status-item { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 12px; align-items: start; border: 1px solid #E2E8F0; background: #FFFFFF; border-radius: 16px; padding: 14px; }
.resource-status-item h4 { margin: 0 0 4px; color: #0F172A; font-size: 0.96rem; line-height: 1.35; overflow-wrap: anywhere; }
.resource-status-item p { margin: 0; color: #64748B; line-height: 1.5; overflow-wrap: anywhere; }
.side-empty.compact { padding: 14px; }

/* ================= Phase 4: Premium Results View ================= */
.results-view {
  background: #F4F7FB;
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

.result-hero-premium {
  position: relative;
  padding: 48px 60px;
  background: #FFFFFF;
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 32px;
  z-index: 1;
  box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.05);
  overflow: hidden;
  flex-shrink: 0;
}
.hero-bg-pattern {
  position: absolute;
  top: 0; right: 0; bottom: 0; left: 0;
  background-image: radial-gradient(rgba(15, 23, 42, 0.03) 1px, transparent 1px);
  background-size: 24px 24px;
  pointer-events: none;
}
.hero-content {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 16px;
  z-index: 1;
}
.hero-status-tag.success-glow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
  border: 1px solid rgba(16, 185, 129, 0.2);
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 0.85rem;
  font-weight: 800;
  width: max-content;
  box-shadow: 0 0 20px rgba(16, 185, 129, 0.15);
  animation: pulse-glow 2s infinite alternate;
}
@keyframes pulse-glow {
  0% { box-shadow: 0 0 10px rgba(16, 185, 129, 0.1); }
  100% { box-shadow: 0 0 25px rgba(16, 185, 129, 0.3); }
}
.hero-title.gradient-text {
  margin: 0;
  font-size: 2.6rem;
  font-weight: 900;
  letter-spacing: -0.03em;
  background: linear-gradient(135deg, #0F172A 0%, #334155 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1.2;
}
.hero-subtitle {
  font-size: 1.1rem;
  color: #64748B;
  margin: 0 0 8px 0;
}
.hero-context-pills {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.glass-pill {
  display: flex;
  align-items: center;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  padding: 8px 16px;
  font-size: 0.9rem;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.02);
}
.hero-actions {
  position: relative;
  display: flex;
  gap: 20px;
  align-items: center;
  z-index: 1;
}
.action-btn-ghost {
  border: 1px solid #CBD5E1;
  color: #475569;
  font-weight: 700;
  padding: 12px 24px;
  height: auto;
  transition: all 0.3s ease;
}
.action-btn-ghost:hover {
  background: #F1F5F9;
  color: #0F172A;
  border-color: #94A3B8;
}
.action-btn-premium {
  background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%) !important;
  border: none !important;
  font-weight: 800;
  font-size: 1.05rem;
  padding: 14px 32px;
  height: auto;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
  color: #FFF !important;
}
.action-btn-premium.glow-effect {
  box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.4);
}
.action-btn-premium:hover {
  transform: translateY(-2px);
  box-shadow: 0 15px 30px -5px rgba(79, 70, 229, 0.5);
}
.action-btn-premium::after {
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
  padding: 40px 60px;
  display: flex;
  flex-direction: column;
  gap: 40px;
  position: relative;
  z-index: 1;
}

.premium-stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}
.premium-stat-card {
  background: #FFFFFF;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 24px;
  padding: 24px 32px;
  display: flex;
  align-items: center;
  gap: 24px;
  box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.05);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.premium-stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 40px -10px rgba(15, 23, 42, 0.08);
}
.stat-icon-wrapper {
  width: 64px; height: 64px;
  border-radius: 18px;
  display: flex; align-items: center; justify-content: center;
  font-size: 2rem;
  background: #F8FAFC;
}
.stat-icon-wrapper.text-blue { background: #EFF6FF; color: #3B82F6; }
.stat-icon-wrapper.text-purple { background: #F5F3FF; color: #8B5CF6; }
.stat-icon-wrapper.text-emerald { background: #ECFDF5; color: #10B981; }

.stat-info { display: flex; flex-direction: column; gap: 4px; }
.premium-stat-card .stat-v { font-size: 2.2rem; font-weight: 900; color: #0F172A; line-height: 1; font-family: 'Plus Jakarta Sans', -apple-system, sans-serif; }
.premium-stat-card .stat-l { font-size: 0.9rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.04em; }

.premium-resource-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 28px;
  align-items: stretch;
}
.premium-res-card {
  grid-column: span 3;
  background: #FFFFFF;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 24px;
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
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
  box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.1);
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
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.5rem;
  background: rgba(15, 23, 42, 0.03); border: 1px solid rgba(15, 23, 42, 0.04);
}
.premium-res-card.tone-blue .type-icon-box { color: #2563EB; }
.premium-res-card.tone-purple .type-icon-box { color: #7C3AED; }
.premium-res-card.tone-amber .type-icon-box { color: #D97706; }
.premium-res-card.tone-rose .type-icon-box { color: #E11D48; }
.premium-res-card.tone-emerald .type-icon-box { color: #059669; }
.premium-res-card.tone-indigo .type-icon-box { color: #6366F1; }
.premium-res-card.tone-slate .type-icon-box { color: #475569; }

.premium-res-card .card-title {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
  color: #0F172A;
  line-height: 1.45;
  white-space: pre-line; display: -webkit-box; -webkit-line-clamp: 3; line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere;
}
.premium-res-card .card-summary {
  margin: 0;
  font-size: 0.95rem;
  color: #475569;
  line-height: 1.6;
  display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.card-metrics-modern {
  display: flex;
  gap: 12px;
  margin-top: auto;
  padding-top: 12px;
}
.metric-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #F8FAFC;
  color: #475569;
  padding: 6px 12px;
  border: 1px solid rgba(15, 23, 42, 0.04);
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 700;
}
.premium-res-card .card-footer {
  border-top: 1px solid rgba(226, 232, 240, 0.6);
  padding-top: 20px;
  margin-top: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modern-text-btn {
  background: transparent;
  border: none;
  color: #0F172A;
  font-weight: 800;
  font-size: 0.95rem;
  padding: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: color 0.2s ease;
}
.modern-text-btn span {
  transition: transform 0.3s ease;
}
.premium-res-card:hover .modern-text-btn {
  color: #2563EB;
}
.premium-res-card:hover .modern-text-btn span {
  transform: translateX(4px);
}
.interactive-resources-panel .panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.interactive-resources-panel .panel-title > span {
  display: inline-flex;
  align-items: center;
  color: #0F172A;
  font-size: 1rem;
  font-weight: 900;
}
.generated-resource-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  column-gap: 20px;
  row-gap: 44px;
  align-items: stretch;
  margin-top: 12px;
  padding-bottom: 16px;
}
.generated-resource-card {
  --resource-accent: #2563EB;
  --resource-soft: #EFF6FF;
  --resource-border: #BFDBFE;
  
  position: relative;
  min-width: 0;
  grid-column: span 3;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  height: 100%;
  min-height: 142px;
  padding: 20px 18px 16px;
  border: 1px solid rgba(15, 23, 42, 0.05);
  border-radius: 16px;
  background: #FFFFFF;
  color: #0F172A;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.02);
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.generated-resource-card::before {
  display: none;
}
.generated-resource-card:hover,
.generated-resource-card:focus-visible {
  transform: translateY(-4px);
  border-color: rgba(15, 23, 42, 0.12);
  box-shadow: 0 16px 32px -8px rgba(15, 23, 42, 0.08);
  outline: none;
}
.generated-resource-card.tone-blue { --resource-accent: #2563EB; --resource-soft: #EFF6FF; --resource-border: #BFDBFE; }
.generated-resource-card.tone-purple { --resource-accent: #7C3AED; --resource-soft: #F5F3FF; --resource-border: #DDD6FE; }
.generated-resource-card.tone-amber { --resource-accent: #D97706; --resource-soft: #FFFBEB; --resource-border: #FDE68A; }
.generated-resource-card.tone-rose { --resource-accent: #E11D48; --resource-soft: #FFF1F2; --resource-border: #FFE4E6; }
.generated-resource-card.tone-emerald { --resource-accent: #059669; --resource-soft: #ECFDF5; --resource-border: #A7F3D0; }
.generated-resource-card.tone-indigo { --resource-accent: #4F46E5; --resource-soft: #EEF2FF; --resource-border: #C7D2FE; }
.generated-resource-card.tone-slate { --resource-accent: #475569; --resource-soft: #F1F5F9; --resource-border: #CBD5E1; }
.generated-resource-card .resource-card-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
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
  gap: 6px;
}
.resource-card-meta-line {
  min-width: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.resource-card-meta-line span {
  color: #64748B;
  font-size: 0.78rem;
  font-weight: 600;
}
.resource-card-info h4 {
  margin: 0;
  color: #0F172A;
  font-size: 1rem;
  line-height: 1.5;
  font-weight: 700;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
}
.resource-card-info p {
  margin: 0;
  color: #64748B;
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
  gap: 6px;
  margin-top: 6px;
  padding-top: 12px;
  background: transparent;
  color: #94A3B8;
  border: none;
  border-top: 1px solid rgba(15, 23, 42, 0.04);
  font-size: 0.82rem;
  font-weight: 600;
  transition: all 0.3s ease;
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
.side-empty.compact { padding: 14px; }

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
  .results-body-bento { padding: 24px 28px; }
  .generated-resource-card { grid-column: span 4; }
  .interactive-resources-panel { min-height: 0; height: auto; }
}
@media (max-width: 768px) {
  .elegant-generator-layout { height: auto; min-height: calc(100vh - 64px); }
  .phase-view { position: relative; min-height: calc(100vh - 64px); }
  .input-view { padding: 1.4rem 1rem 1.8rem; }
  .welcome-header { margin-bottom: 1.8rem; }
  .sparkle-icon { width: 52px; height: 52px; border-radius: 16px; margin-bottom: 1rem; font-size: 1.45rem; }
  .greeting-title { font-size: 2rem; margin-bottom: 0.75rem; }
  .greeting-subtitle { font-size: 0.96rem; line-height: 1.66; max-width: 100%; }
  .search-box-wrapper { border-radius: 22px; padding: 8px; }
  .elegant-textarea :deep(.el-textarea__inner) { font-size: 1rem; padding: 16px 16px; }
  .search-actions { flex-direction: column; align-items: stretch; gap: 10px; padding: 6px 8px 8px; }
  .generate-btn { width: 100%; justify-content: center; }
  .suggestion-area { margin-top: 1.25rem; gap: 10px; }
  .suggestion-tags { justify-content: flex-start; }
  .agent-configs-grid { grid-template-columns: 1fr; }
  .scenario-selector-v2 { grid-template-columns: 1fr; }
  .generation-workbench { padding: 16px; }
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
  .event-log-row { grid-template-columns: 1fr; gap: 6px; }
  .results-body-bento { padding: 16px; }
  .result-hero-minimal { padding: 20px; }
  .bento-stats-row { grid-template-columns: 1fr; }
  .bento-resource-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .bento-res-card { grid-column: span 1 !important; }
}
@media (max-width: 520px) {
  .sequence-track { display: flex; overflow-x: auto; padding-bottom: 4px; }
  .sequence-node { min-width: 240px; }
  .resource-card-actions { flex-direction: column; }
  .resource-metric-stack { grid-template-columns: 1fr; }
  .generated-resource-grid { grid-template-columns: 1fr; }
  .bento-resource-grid { grid-template-columns: 1fr; }
  .bento-res-card { grid-column: span 1 !important; }
}

.elegant-dialog :deep(.el-dialog) { border-radius: 24px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); }
.elegant-dialog :deep(.el-dialog__header) { padding: 24px 32px 20px; margin-right: 0; border-bottom: 1px solid #F1F5F9; }
.elegant-dialog :deep(.el-dialog__title) { font-weight: 800; font-size: 1.2rem; color: #0F172A; }
.elegant-dialog :deep(.el-dialog__body) { padding: 32px; background: #F8FAFC; }

/* ================= 极致明亮模式：排版微调 ================= */
h1, h2, h3, h4, .hero-title, .cc-title {
  letter-spacing: -0.025em;
  color: #0F172A;
  font-weight: 700;
}

p, .card-summary, .s-desc, .greeting-subtitle {
  line-height: 1.65;
  letter-spacing: 0.01em;
  color: #475569;
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
  gap: 10px;
  margin-top: 10px;
  padding-top: 16px;
}
.metric-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #F8FAFC;
  border: 1px solid rgba(15, 23, 42, 0.04);
  border-radius: 8px;
  padding: 6px 12px;
}
.m-l {
  font-size: 0.72rem;
  color: #64748B;
  font-weight: 600;
  text-transform: uppercase;
}
.m-v {
  font-size: 0.8rem;
  color: #0F172A;
  font-weight: 800;
}

.group-badge {
  background: #F1F5F9;
  color: #475569;
  border: 1px solid #E2E8F0;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  padding: 4px 10px;
  border-radius: 8px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

/* ================= 极致明亮模式：生成中 (Streaming) 面板重塑 ================= */
.workbench-hero {
  background: #FFFFFF;
  border: 1px solid rgba(15, 23, 42, 0.05);
  border-radius: 24px;
  padding: 32px 40px;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 40px;
  align-items: center;
  box-shadow: 0 10px 40px -10px rgba(15, 23, 42, 0.04);
}

.workbench-kicker {
  background: rgba(59, 130, 246, 0.08) !important;
  color: #2563EB !important;
  border: none !important;
  font-weight: 800;
  letter-spacing: 0.05em;
  padding: 6px 14px;
}
.workbench-hero h2 {
  font-size: 2.2rem;
  letter-spacing: -0.03em;
  font-weight: 800;
  color: #0F172A;
  margin-top: 16px;
}

.progress-panel {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  box-shadow: none !important;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.progress-number {
  font-size: 3.8rem;
  font-weight: 800;
  color: #0F172A;
  letter-spacing: -0.04em;
  line-height: 1;
  font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
}

:deep(.progress-panel .el-progress-bar__outer) {
  background-color: rgba(15, 23, 42, 0.04) !important;
  border-radius: 12px;
  height: 8px !important;
}
:deep(.progress-panel .el-progress-bar__inner) {
  background: linear-gradient(90deg, #3B82F6 0%, #6366F1 100%);
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(59, 130, 246, 0.3);
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
  gap: 16px;
  margin-top: 8px;
}
.progress-metrics span {
  background: #FAFAFA;
  border: 1px solid rgba(15, 23, 42, 0.03);
  border-radius: 16px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #0F172A;
  font-weight: 700;
  font-size: 0.95rem;
  transition: all 0.3s ease;
}
.progress-metrics span:hover {
  transform: translateY(-2px);
  background: #FFFFFF;
  box-shadow: 0 8px 24px -6px rgba(15, 23, 42, 0.06);
}
.progress-metrics b {
  color: #64748B;
  font-size: 0.72rem;
  font-weight: 700;
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
  padding-bottom: 32px !important;
}

.generated-resource-card {
  height: auto !important;
}

/* ================= 极致明亮模式：面板标题区（已生成资源）重塑 ================= */
.interactive-resources-panel .panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.04);
}

.interactive-resources-panel .panel-title > span {
  font-size: 1.15rem;
  font-weight: 800;
  color: #0F172A;
  letter-spacing: -0.01em;
  position: relative;
  padding-left: 14px;
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
  border-radius: 4px;
  background: #3B82F6;
}

.interactive-resources-panel .panel-title .el-tag {
  background: #F8FAFC !important;
  border: 1px solid rgba(15, 23, 42, 0.05) !important;
  color: #64748B !important;
  font-weight: 700;
  font-size: 0.75rem;
  padding: 4px 12px;
  border-radius: 999px;
  height: auto;
  box-shadow: 0 2px 4px rgba(15, 23, 42, 0.01);
}

/* ================= 极简明亮模式：生成中顶部面板 ================= */
.compact-hero-bar { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: 16px; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 4px 20px -4px rgba(15, 23, 42, 0.03); transition: all 0.3s ease; }
.hero-bar-left { display: flex; align-items: center; gap: 20px; }
.hero-kicker { display: flex; align-items: center; gap: 6px; color: #0369A1 !important; border-color: #BAE6FD !important; background: #F0F9FF !important; font-weight: 800; padding: 0 12px; }
.ping-dot { width: 8px; height: 8px; border-radius: 50%; background-color: #10B981; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite; }
@keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }
.hero-bar-title { margin: 0 0 4px; font-size: 1.25rem; font-weight: 800; color: #0F172A; }
.hero-bar-message { margin: 0; color: #64748B; font-size: 0.9rem; }
.hero-bar-right { display: flex; align-items: center; gap: 24px; }
.progress-info-v2 { display: flex; gap: 20px; text-align: right; }
.pi-item { display: flex; flex-direction: column; }
.pi-item span { font-size: 0.8rem; color: #94A3B8; margin-bottom: 2px; }
.pi-item b { font-size: 1rem; color: #0F172A; }
.mini-progress { position: relative; display: flex; justify-content: center; align-items: center; }
.mini-progress-text { position: absolute; font-size: 0.75rem; font-weight: 800; color: #0369A1; }

/* ================= 极简明亮模式：生成中底部面板重塑 ================= */
.bottom-panels { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start; }
.compact-resource-panel { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px -4px rgba(15, 23, 42, 0.03); }
.panel-header-minimal { display: flex; justify-content: space-between; margin-bottom: 16px; }
.phm-left { display: flex; align-items: center; gap: 8px; font-weight: 800; font-size: 1.05rem; color: #0F172A; }
.phm-left .el-tag { margin-left: 6px; }
.generated-resource-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.mini-resource-card { display: flex; align-items: center; gap: 12px; padding: 12px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; cursor: pointer; transition: all 0.2s ease; }
.mini-resource-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05); background: #FFFFFF; border-color: #CBD5E1; }
.mrc-icon { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; background: rgba(15, 23, 42, 0.03); }
.mrc-info { display: flex; flex-direction: column; min-width: 0; }
.mrc-info h4 { margin: 0; font-size: 0.9rem; font-weight: 700; color: #0F172A; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mrc-info span { font-size: 0.75rem; color: #64748B; }

.live-event-timeline { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px -4px rgba(15, 23, 42, 0.03); display: flex; flex-direction: column; height: 320px; }
.let-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.let-title-group { display: flex; align-items: center; gap: 10px; }
.let-title { font-weight: 800; font-size: 1.05rem; color: #0F172A; }
.let-ping { width: 8px; height: 8px; background: #10B981; border-radius: 50%; position: relative; }
.let-ping::after { content: ''; position: absolute; inset: -4px; border-radius: 50%; border: 2px solid #10B981; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite; }
@keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }
.let-count { font-size: 0.75rem; color: #64748B; background: #F1F5F9; padding: 2px 8px; border-radius: 999px; }
.let-body { flex: 1; overflow-y: auto; padding-right: 4px; }
.let-body::-webkit-scrollbar { width: 4px; }
.let-body::-webkit-scrollbar-thumb { background: #E2E8F0; border-radius: 10px; }
.let-list { display: flex; flex-direction: column; }
.let-row { display: flex; gap: 12px; padding-bottom: 16px; position: relative; }
.let-dot-col { display: flex; flex-direction: column; align-items: center; padding-top: 6px; }
.let-dot { width: 8px; height: 8px; border-radius: 50%; background: #CBD5E1; border: 2px solid #FFF; box-shadow: 0 0 0 1px #CBD5E1; z-index: 1; }
.let-line { flex: 1; width: 1px; background: #E2E8F0; margin: 4px 0 -16px; }
.let-row:last-child .let-line { display: none; }
.let-row.evt-running .let-dot { background: #3B82F6; box-shadow: 0 0 0 1px #3B82F6; }
.let-row.evt-success .let-dot { background: #10B981; box-shadow: 0 0 0 1px #10B981; }
.let-row.evt-failed .let-dot { background: #EF4444; box-shadow: 0 0 0 1px #EF4444; }
.let-content { flex: 1; min-width: 0; }
.let-top { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.let-agent { font-size: 0.85rem; font-weight: 700; color: #1E293B; }
.let-type-tag { font-weight: 700; font-size: 0.7rem; height: 18px; padding: 0 6px; line-height: 16px; }
.let-time { font-size: 0.75rem; color: #94A3B8; font-variant-numeric: tabular-nums; margin-left: auto; }
.let-msg { margin: 0; font-size: 0.8rem; color: #475569; line-height: 1.5; word-break: break-all; }
.let-empty { flex: 1; display: flex; align-items: center; justify-content: center; color: #94A3B8; font-size: 0.9rem; }

.event-slide-enter-active, .event-slide-leave-active { transition: all 0.3s ease; }
.event-slide-enter-from { opacity: 0; transform: translateX(-10px); }
.event-slide-leave-to { opacity: 0; transform: scale(0.95); }

.side-empty.minimal { display: flex; align-items: center; justify-content: center; height: 100px; color: #94A3B8; font-size: 0.9rem; font-weight: 600; }

@media (max-width: 1024px) {
  .bottom-panels { grid-template-columns: 1fr; }
  .compact-hero-bar { flex-direction: column; align-items: flex-start; gap: 16px; }
}
</style>
