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
              <div class="config-card-v2" :class="{ disabled: agent.disabled }" v-for="agent in personalizeAgents" :key="agent.id">
                <div class="cc-header-v2">
                  <div class="cc-icon-wrap" :class="agent.colorClass">
                    <el-icon><component :is="agent.icon" /></el-icon>
                  </div>
                  <span class="cc-title">{{ agent.name }}</span>
                </div>

                <div class="cc-body-v2">
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
            <el-button plain round size="large" @click="currentPhase = 'input'" class="footer-back-btn">返回修改需求</el-button>
            <el-button type="primary" round size="large" class="launch-btn-v2" @click="startGeneration">
              确认配置，启动多智能体加工 <el-icon class="el-icon--right"><VideoPlay /></el-icon>
            </el-button>
          </div>
        </div>
      </div>

      <div v-else-if="currentPhase === 'generating'" class="phase-view generating-view" key="generating">
        <div class="generation-workbench">
          <section class="workbench-hero" aria-live="polite">
            <div>
              <el-tag class="workbench-kicker" effect="plain" round>STREAMING WORKFLOW</el-tag>
              <h2>多智能体资源生成中</h2>
              <p>{{ currentMessage || '系统正在建立 SSE 流，准备展示每个子 Agent 的实时动作。' }}</p>
            </div>
            <div class="progress-panel">
              <div class="progress-number">{{ totalProgress }}%</div>
              <el-progress :percentage="totalProgress" :stroke-width="10" :show-text="false" />
              <div class="progress-metrics">
                <span><b>当前阶段</b>{{ currentStageLabel }}</span>
                <span><b>当前 Agent</b>{{ currentAgentLabel }}</span>
                <span><b>资源完成</b>{{ completedResourceCount }} / {{ expectedResourceCount }}</span>
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
                  <h3>分层资源生成流水线</h3>
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

          <section class="resource-summary-card interactive-resources-panel">
            <div class="panel-title">
              <span>已生成资源</span>
              <el-tag size="small" effect="plain" round v-if="generatedResources.length">{{ generatedResources.length }} 项可查看</el-tag>
            </div>
            <div v-if="generatedResources.length" class="generated-resource-grid">
              <article
                v-for="(resource, index) in sortedGeneratedResources"
                :key="resource.id || resource.type"
                class="generated-resource-card"
                :class="getResourceToneClass(resource.type)"
                :style="getGeneratedCardGridStyle(index, sortedGeneratedResources.length)"
                role="button"
                tabindex="0"
                @click="previewGeneratedResource(resource)"
                @keydown.enter.prevent="previewGeneratedResource(resource)"
                @keydown.space.prevent="previewGeneratedResource(resource)"
              >
                <div class="resource-card-icon" aria-hidden="true">
                  <el-icon><component :is="getAgentMeta(resource.type).icon" /></el-icon>
                </div>
                <div class="resource-card-info">
                  <div class="resource-card-meta-line">
                    <el-tag size="small" effect="plain" round>{{ getResourceTypeLabel(resource.type) }}</el-tag>
                    <span>{{ getResourceStageLabel(resource.type) }} · {{ getDefaultResourceFormat(resource.type) }}</span>
                  </div>
                  <h4>{{ resource.title || getResourceTypeLabel(resource.type) }}</h4>
                  <p>{{ stringifyCompact(resource.summary || getResourceUsageHint(resource.type), 84) }}</p>
                </div>
                <div class="resource-card-action">
                  <span>查看详情</span>
                  <el-icon><Position /></el-icon>
                </div>
              </article>
            </div>
            <div v-else class="side-empty compact">
              <el-icon class="empty-icon"><Collection /></el-icon>
              <span>资源会随着 Agent 完成而逐个出现，完成后可点击查看</span>
            </div>
          </section>

          <el-collapse class="workbench-collapse">
            <el-collapse-item title="MasterAgent 规划历史" name="planning">
              <div v-if="planningHistory.length" class="planning-history-list">
                <article v-for="plan in planningHistory" :key="`${plan.layer}-${plan.layer_name}`" class="planning-card">
                  <h4>{{ plan.layer_name || `Layer ${plan.layer}` }}</h4>
                  <p>{{ plan.reasoning || 'MasterAgent 已完成本层规划。' }}</p>
                  <div class="planning-agent-list">
                    <div v-for="agent in plan.agents || []" :key="agent.agent_id" class="planning-agent-item">
                      <strong>{{ agent.agent_role || getAgentMeta(agent.agent_id).name }}</strong>
                      <span>{{ agent.task_description }}</span>
                      <em>{{ agent.planning_reason }}</em>
                    </div>
                  </div>
                </article>
              </div>
              <div v-else class="side-empty">等待 MasterAgent 返回规划结果</div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>

      <div v-else-if="currentPhase === 'result'" class="phase-view results-view result-dashboard-view" key="result">
        <header class="result-hero-minimal">
          <div class="hero-content">
            <div class="hero-status-tag">
              <el-icon><CircleCheckFilled /></el-icon>
              <span>GEN_COMPLETE</span>
            </div>
            <h1 class="hero-title">{{ finalBundle?.title || '个性化学习资源已就绪' }}</h1>
          </div>
          <div class="hero-actions">
            <el-button plain round @click="resetGenerator" class="action-btn">
              <el-icon><RefreshLeft /></el-icon> 新建任务
            </el-button>
            <el-button type="primary" round @click="pushToLearningPath" class="action-btn-primary">
              规划路径 <el-icon class="el-icon--right"><Position /></el-icon>
            </el-button>
          </div>
        </header>

        <main class="results-body-bento">
          <section class="bento-stats-row">
            <div class="stat-pill">
              <span class="stat-v">{{ resultResources.length }}</span>
              <span class="stat-l">资源总数</span>
            </div>
            <div class="stat-pill">
              <span class="stat-v">{{ involvedAgentCount }}</span>
              <span class="stat-l">智能体参与</span>
            </div>
            <div class="stat-pill">
              <span class="stat-v">{{ learningSequenceResources.length }}</span>
              <span class="stat-l">推荐步骤</span>
            </div>
            <div class="stat-pill" v-if="reviewResult">
              <el-icon class="stat-icon-success"><CircleCheckFilled /></el-icon>
              <span class="stat-l">质量审查已通过</span>
            </div>
          </section>

          <section class="learning-path-timeline">
            <div class="timeline-header">
              <div class="timeline-kicker">LEARNING_PATH</div>
              <h2>智能循序学习路径</h2>
            </div>
            <div class="path-track-container">
              <div v-if="learningSequenceResources.length" class="path-track">
                <div
                  v-for="(res, index) in learningSequenceResources"
                  :key="res.id || `${res.type}-${index}`"
                  class="path-step"
                  :class="getResourceToneClass(res.type)"
                  @click="handlePreview({ agentId: res.type, resultData: res.content, title: res.title })"
                >
                  <div class="step-icon-wrap">
                    <el-icon><component :is="getAgentMeta(res.type).icon" /></el-icon>
                    <span class="step-number">{{ index + 1 }}</span>
                  </div>
                  <div class="step-info">
                    <span class="step-type">{{ getResourceTypeLabel(res.type) }}</span>
                    <span class="step-name">{{ stringifyCompact(res.title || getResourceUsageHint(res.type), 18) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <div class="bento-grid-container">
            <section v-for="group in groupedResultResources" :key="group.key" class="bento-group">
              <div class="group-header">
                <span class="group-badge">{{ group.badge }}</span>
                <h3>{{ group.label }}</h3>
              </div>

              <div class="bento-resource-grid">
                <article
                  v-for="(res, index) in group.resources"
                  :key="res.id || res.title"
                  class="bento-res-card"
                  :class="getResourceToneClass(res.type)"
                  :style="getBentoCardGridStyle(index, group.resources.length)"
                >
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
                    <h4 class="card-title">{{ res.title || getResourceTypeLabel(res.type) }}</h4>
                    <p class="card-summary">{{ stringifyCompact(res.summary || getResourceUsageHint(res.type), 100) }}</p>
                    
                    <div class="card-metrics">
                      <div class="metric-item">
                        <span class="m-l">难度</span>
                        <span class="m-v">{{ getDifficultyLabel(res.metadata?.difficulty) }}</span>
                      </div>
                      <div class="metric-item">
                        <span class="m-l">预计</span>
                        <span class="m-v">{{ res.metadata?.estimated_time || getEstimatedTime(res.type) }}</span>
                      </div>
                    </div>
                  </div>

                  <div class="card-footer">
                    <el-button type="primary" link @click="handlePreview({ agentId: res.type, resultData: res.content, title: res.title })">
                      查看详情 <el-icon class="el-icon--right"><Position /></el-icon>
                    </el-button>
                    <div class="card-actions-hover">
                      <el-button circle size="small" @click="pushToLearningPath"><el-icon><Position /></el-icon></el-button>
                    </div>
                  </div>
                </article>
              </div>
            </section>
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
        <MindmapResourceView v-if="previewData.agentId === 'mindmap'" :result-data="previewData.resultData" />
        <QuizResourceView v-else-if="previewData.agentId === 'quiz'" :result-data="previewData.resultData" />
        <DiagramResourceView v-else-if="previewData.agentId === 'diagram'" :result-data="previewData.resultData" />
        <CodeResourceView v-else-if="previewData.agentId === 'code'" :result-data="previewData.resultData" />
        <ReadingResourceView v-else-if="previewData.agentId === 'reading'" :result-data="previewData.resultData" />
        <MarkdownResourceView v-else :result-data="previewData.resultData" />
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
  Document, Share, Monitor, Edit, Collection
} from '@element-plus/icons-vue'

import MindmapResourceView from '@/components/resource/MindmapResourceView.vue'
import MarkdownResourceView from '@/components/resource/MarkdownResourceView.vue'
import QuizResourceView from '@/components/resource/QuizResourceView.vue'
import DiagramResourceView from '@/components/resource/DiagramResourceView.vue'
import CodeResourceView from '@/components/resource/CodeResourceView.vue'
import ReadingResourceView from '@/components/resource/ReadingResourceView.vue'

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
  { id: 'master', name: 'MasterAgent', icon: Cpu, colorClass: 'text-blue' },
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
const enabledAgentIds = computed<ResourceAgentId[]>(() => ['content', 'mindmap', 'diagram', 'code', 'quiz', 'reading'])

const personalizeAgents = computed(() => agentMetaList.filter(agent => enabledAgentIds.value.includes(agent.id as ResourceAgentId) || agent.id === 'video'))

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
  quiz: { question_count: 5, difficulty_mode: 'adaptive' as const, weak_point_weight: 50, exam_style: 'school' as const, include_analysis: true },
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
  { key: 'planning', label: 'MasterAgent 规划', status: 'pending' },
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

const currentAgentLabel = computed(() => {
  const agent = focusedAgent.value
  if (!agent) return '等待调度'
  return agent.agent_role || getAgentMeta(agent.id).name
})

const completedResourceCount = computed(() => generatedResources.value.length)
const expectedResourceCount = computed(() => Math.max(Object.keys(activeAgents).length, enabledAgentIds.value.length))

const DEFAULT_RESOURCE_SEQUENCE = ['content', 'mindmap', 'diagram', 'code', 'quiz', 'reading', 'video']

const flowAgentPhases = [
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

const fixedFlowNodes = [
  { id: 'master', label: 'MasterAgent', x: 8, y: 50, icon: Cpu },
]

const rawFlowEdges = [
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
  flowAgentPhases.forEach((phase) => {
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

const flowConnections = computed(() => rawFlowEdges.map(([from, to]) => {
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
  || stringifyCompact(naturalInput.value, 42)
  || '本次个性化学习任务'
))

const resultNeedSummary = computed(() => (
  finalBundle.value?.gap
  || finalBundle.value?.metadata?.gap
  || finalBundle.value?.metadata?.learning_need
  || finalBundle.value?.metadata?.weak_points
  || stringifyCompact(naturalInput.value, 86)
  || '系统已根据你的输入生成学习资源。'
))

const involvedAgentCount = computed(() => new Set(resultResources.value.map(resource => resource.type).filter(Boolean)).size)

const learningSequenceResources = computed(() => {
  const resourceMap = new Map<string, any>()
  resultResources.value.forEach((resource) => {
    if (resource?.type && !resourceMap.has(resource.type)) resourceMap.set(resource.type, resource)
  })
  return [...resourceMap.values()].sort((a, b) => getLearningResourceOrder(a) - getLearningResourceOrder(b))
})

const findGeneratedResourcePeer = (resource: any) => generatedResources.value.find(item => (
  item.id === resource?.id || (item.type === resource?.type && item.title === resource?.title)
))

const getLearningResourceOrder = (resource: any) => {
  const runtimeOrder = activeAgents[resource?.type]?.displayOrder
  if (typeof runtimeOrder === 'number') return runtimeOrder

  const generatedPeer = findGeneratedResourcePeer(resource)
  if (typeof generatedPeer?.displayOrder === 'number') return generatedPeer.displayOrder

  return 1000 + getDefaultResourceIndex(resource?.type)
}

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

const getGeneratedCardGridStyle = (index: number, total: number) => {
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

const groupedResultResources = computed(() => {
  const groups = [
    { key: 'basic', badge: 'FOUNDATION', label: '基础理解类', description: '用于快速建立概念理解、知识结构和核心关系。', types: ['content', 'mindmap', 'diagram'], resources: [] as any[] },
    { key: 'practice', badge: 'PRACTICE', label: '实践拓展类', description: '用于通过代码、案例和延伸阅读加深掌握。', types: ['code', 'reading', 'video'], resources: [] as any[] },
    { key: 'assessment', badge: 'ASSESSMENT', label: '检测巩固类', description: '用于检验掌握程度，发现仍然薄弱的知识点。', types: ['quiz'], resources: [] as any[] },
  ]
  resultResources.value.forEach((resource) => {
    const group = groups.find(item => item.types.includes(resource.type)) ?? groups[0]!
    group.resources.push(resource)
  })
  return groups
})

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
    diagram: agentConfigs.diagram,
    quiz: agentConfigs.quiz,
    code: agentConfigs.code,
    reading: agentConfigs.reading,
  }

  streamController.value = generateResources(
    {
      learning_need: naturalInput.value,
      learning_scenario: learningScenario.value,
      selected_agents: enabledAgentIds.value.map((id, index) => ({ agent_id: id, enabled: true, priority: index })),
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
  planningHistory.value = []
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
.elegant-generator-layout { width: 100%; height: calc(100vh - 64px); background: #FCFDFE; font-family: 'Plus Jakarta Sans', 'Inter', system-ui, -apple-system, sans-serif; overflow-x: hidden; position: relative; }
.phase-view { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; background: #FCFDFE; }
.page-slide-enter-active, .page-slide-leave-active { transition: opacity 0.4s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.page-slide-enter-from { opacity: 0; transform: translateY(30px) scale(0.98); }
.page-slide-leave-to { opacity: 0; transform: translateY(-30px) scale(1.02); }

/* ================= Phase 1: Input View ================= */
.input-view { align-items: center; justify-content: center; padding: 2rem; background-image: radial-gradient(circle at 50% 0%, rgba(59, 130, 246, 0.03) 0%, transparent 60%); }
.input-container { width: 100%; max-width: 800px; display: flex; flex-direction: column; align-items: center; margin-top: -8vh; }
.welcome-header { text-align: center; margin-bottom: 2.5rem; }
.sparkle-icon { display: inline-flex; justify-content: center; align-items: center; width: 56px; height: 56px; background: #EFF6FF; color: #3B82F6; font-size: 1.8rem; border-radius: 20px; margin-bottom: 1.5rem; box-shadow: 0 8px 20px rgba(59, 130, 246, 0.15); }
.greeting-title { font-size: 2.5rem; font-weight: 800; color: #0F172A; margin: 0 0 1rem; letter-spacing: -0.02em; }
.greeting-subtitle { font-size: 1.05rem; color: #64748B; line-height: 1.7; max-width: 660px; margin: 0 auto; }
.search-box-wrapper { width: 100%; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 28px; box-shadow: 0 10px 40px rgba(15, 23, 42, 0.05); padding: 8px; transition: border-color 0.3s ease, box-shadow 0.3s ease, transform 0.3s ease; }
.search-box-wrapper.is-focused { border-color: #3B82F6; box-shadow: 0 15px 50px rgba(59, 130, 246, 0.1); transform: translateY(-2px); }
.elegant-textarea :deep(.el-textarea__inner) { border: none; background: transparent; box-shadow: none !important; font-size: 1.15rem; color: #1E293B; padding: 20px 24px; line-height: 1.6; resize: none; }
.elegant-textarea :deep(.el-textarea__inner)::placeholder { color: #94A3B8; font-weight: 400; }
.search-actions { display: flex; justify-content: space-between; align-items: center; padding: 8px 16px 8px 24px; }
.ai-hint { font-size: 0.85rem; color: #94A3B8; display: flex; align-items: center; gap: 6px; }
.ai-hint .el-icon { color: #3B82F6; font-size: 1rem; }
.generate-btn { padding: 12px 28px; font-size: 1.05rem; font-weight: 700; border-radius: 999px; box-shadow: 0 8px 20px rgba(59, 130, 246, 0.25); transition: transform 0.2s ease; }
.generate-btn:hover:not(:disabled) { transform: scale(1.03); }
.suggestion-area { margin-top: 2.5rem; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.suggestion-label { font-size: 0.85rem; color: #94A3B8; font-weight: 600; }
.suggestion-tags { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; }
.s-tag { cursor: pointer; background: #F8FAFC !important; border-color: #E2E8F0 !important; color: #475569 !important; padding: 8px 16px; height: auto; font-size: 0.9rem; transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease; }
.s-tag:hover { background: #EFF6FF !important; border-color: #BFDBFE !important; color: #3B82F6 !important; }

/* ================= Phase 2: Personalize View ================= */
.personalize-view { background: #FCFDFE; align-items: center; overflow-y: auto; padding: 60px 20px; position: relative; }
.aurora-background { position: absolute; top: -20%; left: -10%; width: 120%; height: 140%; z-index: 0; background: radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.05) 0%, transparent 40%), radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.05) 0%, transparent 40%), radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.02) 0%, transparent 60%); filter: blur(80px); pointer-events: none; }
.personalize-container { width: 100%; max-width: 1160px; display: flex; flex-direction: column; gap: 48px; position: relative; z-index: 1; }
.view-header { text-align: center; margin-bottom: 0; }
.header-badge { margin-bottom: 16px; font-weight: 700; letter-spacing: 0.05em; background: #0F172A !important; border: none; }
.view-header h2 { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 2.5rem; font-weight: 800; color: #0F172A; margin: 0 0 16px; letter-spacing: -0.02em; }
.view-header p { font-size: 1.1rem; color: #64748B; margin: 0; max-width: 600px; margin: 0 auto; line-height: 1.6; }
.scenario-selector-v2 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
.scenario-card { background: rgba(255, 255, 255, 0.6); backdrop-filter: blur(10px); border: 1px solid #E2E8F0; border-radius: 20px; padding: 20px; display: flex; align-items: center; gap: 16px; cursor: pointer; transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), background-color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease; position: relative; }
.scenario-card:hover { transform: translateY(-4px); background: #FFFFFF; border-color: #3B82F6; box-shadow: 0 12px 24px -8px rgba(59, 130, 246, 0.15); }
.scenario-card.active { background: #FFFFFF; border-color: #3B82F6; box-shadow: 0 12px 30px -10px rgba(59, 130, 246, 0.25); border-width: 2px; }
.scenario-icon-box { width: 48px; height: 48px; background: #F8FAFC; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: 850; color: #0369A1; transition: background-color 0.3s ease, transform 0.3s ease; }
.scenario-card.active .scenario-icon-box { background: #EFF6FF; transform: scale(1.1); }
.scenario-info { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.s-name { font-weight: 700; font-size: 1rem; color: #0F172A; }
.s-desc { font-size: 0.75rem; color: #64748B; line-height: 1.4; }
.active-dot { position: absolute; top: 12px; right: 12px; width: 8px; height: 8px; background: #3B82F6; border-radius: 50%; box-shadow: 0 0 10px #3B82F6; }
.config-section-v2 { margin-top: 10px; }
.agent-configs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; }
.config-card-v2 { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 24px; overflow: hidden; display: flex; flex-direction: column; transition: transform 0.3s ease, box-shadow 0.3s ease, background-color 0.3s ease; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); }
.config-card-v2:hover { transform: translateY(-2px); box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04); }
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
:deep(.custom-radio-group .el-radio-button__inner) { width: 100%; border-radius: 10px !important; border: 1px solid #E2E8F0 !important; background: #F8FAFC; color: #64748B; font-weight: 600; transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease, box-shadow 0.2s ease; padding: 10px 0; }
:deep(.custom-radio-group .el-radio-button__original-radio:checked + .el-radio-button__inner) { background-color: #0F172A !important; color: #FFFFFF !important; border-color: #0F172A !important; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.2) !important; }
.slider-label-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: -4px; }
.slider-value { font-size: 0.9rem; color: #3B82F6; font-weight: 700; }
.custom-slider-v2 { padding: 0 8px; }
.personalize-footer-v2 { display: flex; justify-content: center; gap: 24px; margin-top: 16px; padding-bottom: 40px; }
.footer-back-btn { font-weight: 700; color: #64748B; border: 1px solid #E2E8F0; }
.launch-btn-v2 { font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 800; padding: 0 40px; background: #0369A1 !important; border: none; box-shadow: 0 10px 25px -5px rgba(3, 105, 161, 0.4); transition: transform 0.3s ease, box-shadow 0.3s ease; }
.launch-btn-v2:hover { transform: translateY(-3px); box-shadow: 0 15px 30px -5px rgba(3, 105, 161, 0.5); }

/* ================= Phase 3: Generating View ================= */
.generating-view { background: #F8FAFC; overflow-y: auto; }
.generation-workbench { width: 100%; max-width: 1760px; margin: 0 auto; padding: 28px; display: flex; flex-direction: column; gap: 20px; color: #0F172A; }
.workbench-hero { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 24px; padding: 24px 28px; display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 28px; align-items: center; box-shadow: 0 14px 34px rgba(15, 23, 42, 0.05); }
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
.runtime-agent-card { border: 1px solid #E2E8F0; border-radius: 18px; background: #FFFFFF; padding: 18px; display: flex; flex-direction: column; gap: 14px; min-width: 0; box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04); }
.runtime-agent-card.is-running { border-color: #93C5FD; box-shadow: 0 12px 28px rgba(37, 99, 235, 0.10); }
.runtime-agent-card.is-success { border-color: #A7F3D0; }
.runtime-agent-card.is-failed { border-color: #FCA5A5; }
.agent-card-header, .agent-title-wrap { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-width: 0; }
.agent-title-wrap { justify-content: flex-start; flex: 1; }
.agent-icon { width: 42px; height: 42px; border-radius: 14px; display: flex; align-items: center; justify-content: center; flex: 0 0 auto; background: #F8FAFC; }
.agent-icon.text-blue { background: #EFF6FF; color: #2563EB; }
.agent-icon.text-orange { background: #FFF7ED; color: #EA580C; }
.agent-icon.text-purple { background: #F5F3FF; color: #7C3AED; }
.agent-icon.text-red { background: #FEF2F2; color: #DC2626; }
.agent-icon.text-emerald { background: #ECFDF5; color: #059669; }
.agent-icon.text-indigo { background: #EEF2FF; color: #4F46E5; }
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
.kv-row { display: grid; grid-template-columns: minmax(72px, 0.7fr) minmax(0, 1.3fr); gap: 10px; align-items: start; padding: 8px 0; border-bottom: 1px solid #F1F5F9; }
.kv-row span { color: #64748B; font-size: 0.82rem; overflow-wrap: anywhere; }
.kv-row b { color: #1E293B; font-size: 0.82rem; font-weight: 650; overflow-wrap: anywhere; }
.output-preview { background: #F8FAFC; border-radius: 14px; padding: 12px; }
.output-preview strong { color: #0F172A; overflow-wrap: anywhere; }
.agent-progress { margin-top: auto; }
.empty-layer-state, .side-empty { border: 1px dashed #CBD5E1; border-radius: 16px; color: #94A3B8; background: #F8FAFC; padding: 22px; text-align: center; line-height: 1.5; }
.resource-side-panel { display: flex; flex-direction: column; gap: 20px; min-width: 0; position: sticky; top: 20px; }
.side-card { padding: 20px; }
.profile-summary-grid { display: flex; flex-direction: column; gap: 10px; }
.profile-summary-item { display: grid; grid-template-columns: 82px minmax(0, 1fr); gap: 10px; padding-bottom: 10px; border-bottom: 1px solid #F1F5F9; }
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
.flow-canvas { position: relative; height: 720px; margin-top: 18px; overflow: auto; border-radius: 22px; background: linear-gradient(135deg, #F8FAFC 0%, #FFFFFF 52%, #F0F9FF 100%); border: 1px solid #E2E8F0; }
.flow-canvas-inner { position: relative; min-width: 1320px; height: 680px; }
.flow-lines { position: absolute; inset: 0; z-index: 1; width: 100%; height: 100%; pointer-events: none; }
.flow-edge { stroke: #CBD5E1; stroke-width: 2.4; stroke-linecap: round; opacity: 0.72; }
.flow-edge.success { stroke: #10B981; opacity: 0.92; }
.flow-edge.failed { stroke: #EF4444; opacity: 0.9; }
.flow-edge.running, .flow-edge.active { stroke: #2563EB; stroke-dasharray: 10 10; animation: flowDash 1.2s linear infinite; opacity: 1; }
@keyframes flowDash { to { stroke-dashoffset: -20; } }
.flow-node { position: absolute; z-index: 5; transform: translate(-50%, -50%); width: 186px; min-height: 112px; border: 1px solid #CBD5E1; border-radius: 18px; background: rgba(255, 255, 255, 0.96); display: flex; flex-direction: column; align-items: stretch; justify-content: flex-start; gap: 8px; cursor: pointer; color: #475569; box-shadow: 0 10px 22px rgba(15, 23, 42, 0.07); padding: 12px; text-align: left; transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease; }
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
.flow-node.is-running { border-color: #60A5FA; box-shadow: 0 0 0 6px rgba(96, 165, 250, 0.14), 0 18px 32px rgba(37, 99, 235, 0.16); animation: nodePulse 1.4s ease-in-out infinite; }
.flow-node.is-running .node-icon { background: #DBEAFE; color: #2563EB; }
.flow-node.is-running .node-live-log { border-color: #BFDBFE; background: #EFF6FF; }
.flow-node.is-success { border-color: #86EFAC; }
.flow-node.is-success .node-icon { background: #DCFCE7; color: #16A34A; }
.flow-node.is-failed { border-color: #FCA5A5; }
.flow-node.is-failed .node-icon { background: #FEE2E2; color: #DC2626; }
.flow-node.is-skipped { opacity: 0.68; }
@keyframes nodePulse { 50% { box-shadow: 0 0 0 10px rgba(96, 165, 250, 0.08), 0 18px 32px rgba(37, 99, 235, 0.18); } }
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
.resource-summary-card { padding: 20px; }
.resource-status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
.resource-status-item { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 12px; align-items: start; border: 1px solid #E2E8F0; background: #FFFFFF; border-radius: 16px; padding: 14px; }
.resource-status-item h4 { margin: 0 0 4px; color: #0F172A; font-size: 0.96rem; line-height: 1.35; overflow-wrap: anywhere; }
.resource-status-item p { margin: 0; color: #64748B; line-height: 1.5; overflow-wrap: anywhere; }
.side-empty.compact { padding: 14px; }

/* ================= Phase 4: Results View (Bento Grid) ================= */
.results-view { background: #FCFDFE; overflow-y: auto; padding-bottom: 60px; }
.result-hero-minimal { padding: 32px 48px; background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(12px); border-bottom: 1px solid #E2E8F0; display: flex; justify-content: space-between; align-items: center; gap: 24px; }
.hero-content { display: flex; flex-direction: column; gap: 12px; }
.hero-status-tag { display: inline-flex; align-items: center; gap: 6px; background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; padding: 6px 12px; border-radius: 999px; font-size: 0.8rem; font-weight: 800; width: max-content; }
.hero-title { margin: 0; font-size: 2rem; font-weight: 850; color: #0F172A; letter-spacing: -0.02em; }
.hero-context-pills { display: flex; gap: 12px; flex-wrap: wrap; }
.context-pill { display: flex; align-items: center; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 6px 12px; font-size: 0.85rem; }
.pill-label { color: #64748B; font-weight: 800; margin-right: 8px; }
.pill-value { color: #0F172A; font-weight: 600; }
.hero-actions { display: flex; gap: 16px; align-items: center; }
.action-btn { font-weight: 700; }
.action-btn-primary { font-weight: 800; box-shadow: 0 8px 20px rgba(59, 130, 246, 0.2); }
.results-body-bento { max-width: 1440px; margin: 0 auto; padding: 32px 48px; display: flex; flex-direction: column; gap: 32px; }
.bento-stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.stat-pill { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 20px; padding: 24px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; box-shadow: 0 4px 6px rgba(15, 23, 42, 0.02); }
.stat-v { font-size: 2.5rem; font-weight: 850; color: #0F172A; line-height: 1.2; }
.stat-l { font-size: 0.9rem; font-weight: 700; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }
.stat-icon-success { font-size: 2.5rem; color: #10B981; margin-bottom: 8px; }
.learning-path-timeline { margin: 16px 0 28px; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 24px; padding: 32px; box-shadow: 0 4px 6px rgba(15, 23, 42, 0.02); }
.timeline-header { margin-bottom: 24px; }
.timeline-kicker { font-size: 0.8rem; font-weight: 850; color: #3B82F6; letter-spacing: 0.05em; margin-bottom: 8px; }
.timeline-header h2 { margin: 0; font-size: 1.5rem; font-weight: 800; color: #0F172A; }
.path-track-container { overflow-x: auto; overflow-y: visible; padding: 6px 0 10px; }
.path-track { display: flex; gap: 16px; min-width: max-content; padding-top: 4px; }
.path-step { display: flex; align-items: center; gap: 16px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 16px; padding: 16px 20px; cursor: pointer; transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease; min-width: 260px; }
.path-step:hover { transform: translateY(-2px); border-color: #3B82F6; box-shadow: 0 8px 24px rgba(59, 130, 246, 0.1); }
.step-icon-wrap { width: 48px; height: 48px; border-radius: 14px; background: #FFFFFF; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; position: relative; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
.step-number { position: absolute; top: -6px; right: -6px; width: 20px; height: 20px; background: #0F172A; color: #FFFFFF; font-size: 0.7rem; font-weight: 800; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid #FFFFFF; }
.step-info { display: flex; flex-direction: column; }
.step-type { font-size: 0.8rem; font-weight: 700; color: #64748B; }
.step-name { font-size: 1rem; font-weight: 800; color: #0F172A; }
.bento-grid-container { display: flex; flex-direction: column; gap: 32px; }
.bento-group { display: flex; flex-direction: column; gap: 16px; }
.group-header { display: flex; align-items: center; gap: 12px; }
.group-badge { background: #0F172A; color: #FFFFFF; font-size: 0.75rem; font-weight: 850; padding: 4px 10px; border-radius: 8px; }
.group-header h3 { margin: 0; font-size: 1.25rem; font-weight: 800; color: #0F172A; }
.bento-resource-grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 24px; align-items: stretch; }
.bento-res-card { grid-column: span 3; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 24px; padding: 24px; display: flex; flex-direction: column; gap: 16px; position: relative; overflow: hidden; transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease; box-shadow: 0 4px 6px rgba(15, 23, 42, 0.02); cursor: pointer; outline: none; }
.bento-res-card:hover, .bento-res-card:focus-visible { transform: translateY(-4px); box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08); }
.card-header { display: flex; align-items: center; gap: 12px; }
.type-icon-box { width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.4rem; }
.type-info { display: flex; flex-direction: column; }
.type-label { font-size: 0.9rem; font-weight: 800; color: #0F172A; }
.format-tag { font-size: 0.75rem; font-weight: 600; color: #64748B; }
.card-body { flex: 1; display: flex; flex-direction: column; gap: 8px; }
.card-title { margin: 0; font-size: 1.1rem; font-weight: 850; color: #0F172A; line-height: 1.4; }
.card-summary { margin: 0; font-size: 0.9rem; color: #64748B; line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.card-metrics { display: flex; gap: 16px; margin-top: 8px; }
.metric-item { background: #F8FAFC; border-radius: 8px; padding: 6px 10px; display: flex; flex-direction: column; }
.m-l { font-size: 0.7rem; color: #94A3B8; font-weight: 700; }
.m-v { font-size: 0.85rem; color: #0F172A; font-weight: 800; }
.card-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #F1F5F9; padding-top: 16px; }
.card-actions-hover { opacity: 0; transition: opacity 0.2s ease; }
.bento-res-card:hover .card-actions-hover, .bento-res-card:focus-visible .card-actions-hover { opacity: 1; }
.bento-res-card.tone-blue .type-icon-box { background: #EFF6FF; color: #3B82F6; }
.bento-res-card.tone-purple .type-icon-box { background: #F5F3FF; color: #8B5CF6; }
.bento-res-card.tone-amber .type-icon-box { background: #FFF7ED; color: #F59E0B; }
.bento-res-card.tone-rose .type-icon-box { background: #FFF1F2; color: #E11D48; }
.bento-res-card.tone-emerald .type-icon-box { background: #ECFDF5; color: #10B981; }
.bento-res-card.tone-indigo .type-icon-box { background: #EEF2FF; color: #6366F1; }
.bento-res-card.tone-slate .type-icon-box { background: #F1F5F9; color: #64748B; }
.bento-res-card.tone-blue:hover { border-color: #3B82F6; }
.bento-res-card.tone-purple:hover { border-color: #8B5CF6; }
.bento-res-card.tone-amber:hover { border-color: #F59E0B; }
.bento-res-card.tone-rose:hover { border-color: #E11D48; }
.bento-res-card.tone-emerald:hover { border-color: #10B981; }
.bento-res-card.tone-indigo:hover { border-color: #6366F1; }
.bento-res-card.tone-slate:hover { border-color: #64748B; }
.path-step.tone-blue .step-icon-wrap { color: #3B82F6; }
.path-step.tone-purple .step-icon-wrap { color: #8B5CF6; }
.path-step.tone-amber .step-icon-wrap { color: #F59E0B; }
.path-step.tone-rose .step-icon-wrap { color: #E11D48; }
.path-step.tone-emerald .step-icon-wrap { color: #10B981; }
.path-step.tone-indigo .step-icon-wrap { color: #6366F1; }
.path-step.tone-slate .step-icon-wrap { color: #64748B; }
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
  column-gap: 14px;
  row-gap: 20px;
  align-items: stretch;
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
  min-height: 196px;
  padding: 16px;
  border: 1px solid #E2E8F0;
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 250, 252, 0.92) 100%),
    var(--resource-soft);
  color: #0F172A;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.045);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}
.generated-resource-card::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  border-radius: 18px 0 0 18px;
  background: var(--resource-accent);
}
.generated-resource-card:hover,
.generated-resource-card:focus-visible {
  transform: translateY(-2px);
  border-color: var(--resource-border);
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.08);
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
  width: 46px;
  height: 46px;
  border-radius: 15px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--resource-soft);
  border: 1px solid var(--resource-border);
  color: var(--resource-accent);
  font-size: 1.18rem;
  flex-shrink: 0;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.78);
}
.resource-card-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 8px;
}
.resource-card-meta-line {
  min-width: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.resource-card-meta-line span {
  color: #94A3B8;
  font-size: 0.76rem;
  font-weight: 850;
}
.resource-card-info h4 {
  margin: 0;
  color: #0F172A;
  font-size: 1.02rem;
  line-height: 1.38;
  font-weight: 900;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
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
  justify-content: space-between;
  gap: 7px;
  margin-top: 8px;
  min-width: 0;
  width: 100%;
  padding: 10px 12px;
  box-sizing: border-box;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.02);
  color: #334155;
  border: 1px dashed #CBD5E1;
  font-size: 0.8rem;
  font-weight: 900;
  white-space: nowrap;
  transition: background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}
.generated-resource-card:hover .resource-card-action,
.generated-resource-card:focus-visible .resource-card-action {
  background: var(--resource-soft);
  color: var(--resource-accent);
  border-color: var(--resource-border);
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
}
@media (max-width: 768px) {
  .elegant-generator-layout { height: auto; min-height: calc(100vh - 64px); }
  .phase-view { position: relative; min-height: calc(100vh - 64px); }
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
  .resource-card-action { grid-column: 1 / -1; width: 100%; }
  .workflow-timeline-panel, .resource-side-panel { position: static; }
  .event-log-row { grid-template-columns: 1fr; gap: 6px; }
  .results-body-bento { padding: 16px; }
  .result-hero-minimal { padding: 20px; }
  .bento-stats-row { grid-template-columns: 1fr; }
  .bento-resource-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .bento-res-card { grid-column: span 1 !important; }
  .learning-path-timeline { margin: 12px 0 22px; padding: 20px; }
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
</style>
