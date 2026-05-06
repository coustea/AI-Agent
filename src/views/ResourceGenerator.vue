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
                        </el-option-group>
                        <el-option-group label="软件工程图表">
                          <el-option label="交互时序图 (Sequence)" value="sequence" />
                          <el-option label="状态转移图 (State)" value="state" />
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

                    <div class="node-stage">
                      {{ getNodeCurrentStage(node.id, node.status) }}
                    </div>

                    <div v-if="getNodeBubbles(node.id, 2).length" class="node-inline-logs">
                      <p
                        v-for="bubble in getNodeBubbles(node.id, 2)"
                        :key="bubble.id"
                      >
                        {{ formatFlowLogMessage(bubble) }}
                      </p>
                    </div>

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

          <section class="resource-summary-card">
            <div class="panel-title">已生成资源轻量摘要</div>
            <div v-if="resourceStatusSummary.length" class="resource-status-grid">
              <article v-for="resource in resourceStatusSummary" :key="resource.key" class="resource-status-item">
                <el-tag size="small" effect="plain">{{ resource.type }}</el-tag>
                <div>
                  <h4>{{ resource.title }}</h4>
                  <p>{{ resource.summary }}</p>
                </div>
                <el-tag size="small" type="success" effect="light">{{ resource.status }}</el-tag>
              </article>
            </div>
            <div v-else class="side-empty compact">资源会随着 WorkerAgent 完成而流式出现</div>
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
            <el-collapse-item title="调试信息：SSE 原始事件日志" name="events">
              <div class="event-log-list">
                <div v-for="log in visibleEventLogs" :key="log.event_id" class="event-log-row">
                  <span>{{ formatEventTime(log.timestamp) }}</span>
                  <el-tag size="small" effect="plain">{{ log.event_type }}</el-tag>
                  <b>{{ log.agent || '-' }}</b>
                  <el-tag size="small" :type="getStatusTagType(log.status)" effect="light">{{ getStatusLabel(log.status) }}</el-tag>
                  <p>{{ log.message }}</p>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>

      <div v-else-if="currentPhase === 'result'" class="phase-view results-view" key="result">
        <header class="results-header glass-nav">
          <div class="nav-brand">
            <el-icon class="success-icon"><CircleCheckFilled /></el-icon>
            <div class="nav-titles">
              <h2>{{ finalBundle?.title || '个性化学习资源包已就绪' }}</h2>
              <p>生成状态：{{ finalBundle?.status || 'success' }} · 共 {{ resultResources.length }} 项定制资料</p>
            </div>
          </div>
          <div class="nav-actions">
            <el-button plain round @click="resetGenerator" class="back-btn">
              <el-icon><RefreshLeft /></el-icon> 新建任务
            </el-button>
            <el-button type="primary" round @click="pushToLearningPath" class="path-btn">
              基于本次资源规划学习路径 <el-icon class="el-icon--right"><Position /></el-icon>
            </el-button>
          </div>
        </header>

        <div class="results-body">
          <section class="review-summary-card" v-if="reviewResult">
            <div class="panel-title">ReviewerAgent 审查结果</div>
            <p>{{ reviewResult.summary || reviewResult.message || '资源质量审查已完成。' }}</p>
          </section>

          <div class="result-resource-groups">
            <section v-for="group in groupedResultResources" :key="group.key" class="result-group-section">
              <header class="result-group-header">
                <div>
                  <span class="layer-index">{{ group.badge }}</span>
                  <h3>{{ group.label }}</h3>
                </div>
                <el-tag effect="plain">{{ group.resources.length }} 项</el-tag>
              </header>

              <div v-if="group.resources.length" class="result-resource-grid">
                <article v-for="res in group.resources" :key="res.id || res.title" class="result-resource-card">
                  <div class="result-card-header">
                    <div>
                      <el-tag effect="plain">{{ res.type }}</el-tag>
                      <h3>{{ res.title || '未命名资源' }}</h3>
                    </div>
                    <span>{{ res.format || 'json' }}</span>
                  </div>
                  <p>{{ res.summary || '暂无摘要' }}</p>
                  <div class="result-meta-grid">
                    <span><b>Agent</b>{{ res.metadata?.agent_role || getAgentMeta(res.type).name }}</span>
                    <span><b>难度</b>{{ res.metadata?.difficulty || 'basic' }}</span>
                    <span><b>阶段</b>{{ res.metadata?.suitable_stage || 'resource_generation' }}</span>
                    <span><b>时长</b>{{ res.metadata?.estimated_time || '待评估' }}</span>
                  </div>
                  <div class="tag-row" v-if="normalizeList(res.metadata?.knowledge_points).length">
                    <el-tag
                      v-for="point in normalizeList(res.metadata?.knowledge_points)"
                      :key="point"
                      size="small"
                      effect="plain"
                    >
                      {{ point }}
                    </el-tag>
                  </div>
                  <div class="personalized-reason" v-if="res.metadata?.personalized_reason">
                    {{ res.metadata.personalized_reason }}
                  </div>
                  <el-button plain round @click="handlePreview({ agentId: res.type, resultData: res.content, title: res.title })">
                    查看详情
                  </el-button>
                </article>
              </div>
              <div v-else class="side-empty compact">本组暂无资源</div>
            </section>
          </div>
        </div>
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
            <p>{{ getStatusLabel(focusedAgent.status) }} · {{ focusedAgent.layer_name || '多智能体工作流' }}</p>
          </div>
        </div>

        <section class="drawer-section">
          <h4>当前动作</h4>
          <p>{{ focusedAgent.current_action || focusedAgent.step_label || focusedAgent.message || '暂无当前动作' }}</p>
        </section>

        <section class="drawer-section" v-if="focusedAgent.current_step || focusedAgent.total_steps || (focusedAgent.progress !== null && focusedAgent.progress !== undefined)">
          <h4>步骤进度</h4>
          <div class="drawer-progress-row">
            <span>{{ focusedAgent.current_step || 0 }} / {{ focusedAgent.total_steps || '-' }}</span>
            <el-progress :percentage="getAgentProgress(focusedAgent.status)" :stroke-width="8" :show-text="false" />
          </div>
        </section>

        <section class="drawer-section" v-if="focusedAgent.task_description">
          <h4>任务描述</h4>
          <p>{{ focusedAgent.task_description }}</p>
        </section>

        <section class="drawer-section" v-if="focusedAgent.planning_reason">
          <h4>规划理由</h4>
          <p>{{ focusedAgent.planning_reason }}</p>
        </section>

        <section class="drawer-section" v-if="normalizeList(focusedAgent.depends_on || focusedAgent.upstream_agents).length">
          <h4>依赖关系</h4>
          <div class="drawer-tags">
            <el-tag
              v-for="dependency in normalizeList(focusedAgent.depends_on || focusedAgent.upstream_agents)"
              :key="dependency"
              size="small"
              effect="plain"
            >
              {{ getAgentMeta(dependency).name }}
            </el-tag>
          </div>
        </section>

        <section class="drawer-section" v-if="normalizeList(focusedAgent.personalized_constraints).length">
          <h4>个性化约束</h4>
          <ul>
            <li v-for="item in normalizeList(focusedAgent.personalized_constraints)" :key="item">{{ item }}</li>
          </ul>
        </section>

        <section class="drawer-section" v-if="hasEntries(focusedAgent.input_params)">
          <h4>输入参数</h4>
          <div class="drawer-kv-list">
            <div v-for="item in kvEntries(focusedAgent.input_params)" :key="item.key">
              <span>{{ item.key }}</span>
              <b>{{ item.value }}</b>
            </div>
          </div>
        </section>

        <section class="drawer-section" v-if="hasEntries(focusedAgent.output_requirements)">
          <h4>输出要求</h4>
          <div class="drawer-kv-list">
            <div v-for="item in kvEntries(focusedAgent.output_requirements)" :key="item.key">
              <span>{{ item.key }}</span>
              <b>{{ item.value }}</b>
            </div>
          </div>
        </section>

        <section class="drawer-section" v-if="focusedAgent.output_preview || focusedAgent.summary">
          <h4>输出预览</h4>
          <p>{{ focusedAgent.output_preview || focusedAgent.summary }}</p>
        </section>

        <section class="drawer-section" v-if="getNodeBubbles(focusedAgent.id, 8).length">
          <h4>最近执行日志</h4>
          <div class="drawer-log-list">
            <div
              v-for="log in getNodeBubbles(focusedAgent.id, 8)"
              :key="log.id"
              class="drawer-log-item"
            >
              <span></span>
              <p>{{ formatFlowLogMessage(log) }}</p>
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
import { ref, reactive, computed } from 'vue'
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

import { generateResources, type ResourceAgentId, type LearningScenario } from '@/api/resource'

const router = useRouter()

type WorkflowStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped'

type ResourceGenerateEvent = {
  event_id: string
  task_id: string
  event_type: 'workflow' | 'planning' | 'agent' | 'resource' | 'review' | 'bundle' | 'error' | 'done'
  stage: string
  agent?: string | null
  status: WorkflowStatus
  message: string
  progress?: number | null
  payload: Record<string, any>
  timestamp: string
}

type AgentStepRecord = {
  action?: string
  step_label?: string
  current_step?: number
  total_steps?: number
  message?: string
  output_preview?: string
  timestamp?: string
}

type AgentRuntimeState = {
  id: string
  agent_role?: string
  status: WorkflowStatus
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
  output_preview?: string
  resource_id?: string
  title?: string
  summary?: string
  progress?: number | null
  updated_at?: string
  step_history?: AgentStepRecord[]
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
const eventLogs = ref<ResourceGenerateEvent[]>([])
const activeAgents = reactive<Record<string, AgentRuntimeState>>({})
const generatedResources = ref<any[]>([])
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

const focusedAgent = computed<AgentRuntimeState | null>(() => {
  if (focusedAgentId.value && activeAgents[focusedAgentId.value]) {
    return activeAgents[focusedAgentId.value]
  }
  if (focusedAgentId.value) {
    const node = flowNodes.value.find(item => item.id === focusedAgentId.value)
    if (node) {
      return {
        id: node.id,
        agent_role: node.label,
        status: node.status,
        current_action: getNodeCurrentStage(node.id, node.status),
        message: getNodeCurrentStage(node.id, node.status),
        layer_name: '多智能体流程节点',
        updated_at: new Date().toISOString(),
      }
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

const flowNodeDefinitions = [
  { id: 'master', label: 'MasterAgent', x: 8, y: 50, icon: Cpu },
  { id: 'content', label: '课程讲解', x: 28, y: 24, icon: Document },
  { id: 'mindmap', label: '思维导图', x: 28, y: 50, icon: Share },
  { id: 'diagram', label: '知识图解', x: 28, y: 76, icon: Monitor },
  { id: 'code', label: '代码案例', x: 50, y: 30, icon: Cpu },
  { id: 'reading', label: '拓展阅读', x: 50, y: 62, icon: Collection },
  { id: 'quiz', label: '练习题', x: 68, y: 46, icon: Edit },
  { id: 'reviewer', label: '资源审查', x: 84, y: 38, icon: CircleCheckFilled },
  { id: 'assembler', label: '资源组装', x: 92, y: 66, icon: Position },
]

const rawFlowEdges = [
  ['master', 'content'],
  ['master', 'mindmap'],
  ['master', 'diagram'],
  ['content', 'code'],
  ['diagram', 'code'],
  ['content', 'reading'],
  ['content', 'quiz'],
  ['code', 'quiz'],
  ['content', 'reviewer'],
  ['mindmap', 'reviewer'],
  ['diagram', 'reviewer'],
  ['code', 'reviewer'],
  ['reading', 'reviewer'],
  ['quiz', 'reviewer'],
  ['reviewer', 'assembler'],
]

const flowNodes = computed(() => flowNodeDefinitions.map(node => ({
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

const visibleEventLogs = computed(() => eventLogs.value.slice(-80).reverse())

const resultResources = computed(() => {
  const resources = finalBundle.value?.resources
  return Array.isArray(resources) && resources.length ? resources : generatedResources.value
})

const resourceStatusSummary = computed(() => generatedResources.value.map((resource, index) => ({
  key: resource.id || `${resource.type}-${index}`,
  type: resource.type || 'resource',
  status: '已生成',
  title: resource.title || '未命名资源',
  summary: stringifyCompact(resource.summary || resource.metadata?.summary || '资源已生成，等待摘要写入。', 96),
})))

const groupedResultResources = computed(() => {
  const groups = [
    { key: 'basic', badge: 'FOUNDATION', label: '基础理解类', types: ['content', 'mindmap', 'diagram'], resources: [] as any[] },
    { key: 'practice', badge: 'PRACTICE', label: '实践拓展类', types: ['code', 'reading', 'video'], resources: [] as any[] },
    { key: 'assessment', badge: 'ASSESSMENT', label: '检测巩固类', types: ['quiz'], resources: [] as any[] },
  ]
  resultResources.value.forEach((resource) => {
    const group = groups.find(item => item.types.includes(resource.type)) ?? groups[0]!
    group.resources.push(resource)
  })
  return groups
})

const startGeneration = async () => {
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

const resetGenerationState = () => {
  totalProgress.value = 0
  currentMessage.value = ''
  eventLogs.value = []
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
  isGenerating.value = false
  workflowStages.splice(0, workflowStages.length, ...createWorkflowStages())
}

const handleSseEvent = (event: ResourceGenerateEvent) => {
  if (!event?.event_type) return

  eventLogs.value.push(event)
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
        const previous = activeAgents[agent.agent_id] || { id: agent.agent_id, status: 'pending' as WorkflowStatus }
        activeAgents[agent.agent_id] = {
          ...previous,
          id: agent.agent_id,
          status: previous.status,
          layer: event.payload.layer,
          layer_name: event.payload.layer_name,
          agent_role: agent.agent_role || getAgentMeta(agent.agent_id).name,
          task_description: agent.task_description,
          planning_reason: agent.planning_reason,
          depends_on: agent.depends_on || [],
          resource_type: agent.resource_type,
          input_params: agent.input_params || {},
          output_requirements: agent.output_requirements || {},
          personalized_constraints: agent.personalized_constraints || [],
          updated_at: event.timestamp,
        }
      })
    }
  }

  if (event.event_type === 'agent' && event.agent) {
    const payload = event.payload || {}
    const previous = activeAgents[event.agent] || { id: event.agent, status: 'pending' as WorkflowStatus }
    const stepHistory = [...(previous.step_history || [])]
    if (payload.current_step !== undefined || payload.step_label) {
      stepHistory.push({
        action: payload.action,
        step_label: payload.step_label,
        current_step: payload.current_step,
        total_steps: payload.total_steps,
        message: event.message,
        output_preview: payload.output_preview,
        timestamp: event.timestamp,
      })
    }
    activeAgents[event.agent] = {
      ...previous,
      ...pickDefined({
        id: event.agent,
        status: event.status,
        message: event.message,
        action: payload.action,
        progress: event.progress,
        layer: payload.layer,
        layer_name: payload.layer_name,
        agent_role: payload.agent_role,
        current_action: payload.current_action,
        current_step: payload.current_step,
        total_steps: payload.total_steps,
        step_label: payload.step_label,
        task_description: payload.task_description,
        planning_reason: payload.planning_reason,
        depends_on: payload.depends_on,
        upstream_agents: payload.upstream_agents,
        has_profile: payload.has_profile,
        input_params: payload.input_params,
        output_requirements: payload.output_requirements,
        personalized_constraints: payload.personalized_constraints,
        output_preview: payload.output_preview,
        resource_id: payload.resource_id,
        resource_type: payload.resource_type,
        title: payload.title,
        summary: payload.summary,
        updated_at: event.timestamp,
      }),
      step_history: stepHistory,
    }
    if (event.status === 'running') {
      focusedAgentId.value = event.agent
    }
  }

  if (event.event_type === 'resource') {
    const resource = event.payload?.resource
    if (resource) {
      upsertResource(resource)
      if (event.agent && activeAgents[event.agent]) {
        const existingAgent = activeAgents[event.agent]!
        activeAgents[event.agent] = {
          ...existingAgent,
          id: event.agent,
          status: 'success',
          resource_id: resource.id,
          title: resource.title,
          summary: resource.summary,
          output_preview: resource.summary || existingAgent.output_preview,
          updated_at: event.timestamp,
        }
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

const upsertResource = (resource: any) => {
  const index = generatedResources.value.findIndex(item => item.id === resource.id || (item.type === resource.type && item.title === resource.title))
  if (index >= 0) {
    generatedResources.value[index] = { ...generatedResources.value[index], ...resource }
    return
  }
  generatedResources.value.push(resource)
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

  const next = [...flowEventBubbles.value, bubble]
  const perNodeCount = new Map<string, number>()
  flowEventBubbles.value = next
    .reverse()
    .filter((item) => {
      const count = perNodeCount.get(item.nodeId) || 0
      if (count >= 2) return false
      perNodeCount.set(item.nodeId, count + 1)
      return true
    })
    .reverse()
    .slice(-12)
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

  const latestBubble = getNodeBubbles(nodeId).at(-1)
  if (latestBubble?.message) return latestBubble.message

  if (status === 'success') return '已完成当前阶段'
  if (status === 'running') return '正在执行当前任务'
  if (status === 'failed') return '执行失败，请查看日志'
  if (status === 'skipped') return '已跳过当前任务'
  return '等待上游任务完成'
}

const formatFlowLogMessage = (log: FlowEventBubble) => {
  return stringifyCompact(log.message || getStatusLabel(log.status) || '正在处理任务', 54)
}

const pickDefined = <T extends Record<string, any>>(value: T): Partial<T> => {
  return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== undefined)) as Partial<T>
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

const hasEntries = (value?: Record<string, any>) => Boolean(value && Object.keys(value).length)

const kvEntries = (value?: Record<string, any>) => {
  if (!value) return []
  return Object.entries(value).map(([key, item]) => ({ key, value: stringifyCompact(item, 72) }))
}

const normalizeList = (value: any): string[] => {
  if (!value) return []
  if (Array.isArray(value)) return value.map(item => String(item)).filter(Boolean)
  return [String(value)]
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

const getStatusTagType = (status: WorkflowStatus) => {
  const types: Record<WorkflowStatus, 'primary' | 'success' | 'info' | 'warning' | 'danger'> = {
    pending: 'info',
    running: 'primary',
    success: 'success',
    failed: 'danger',
    skipped: 'warning',
  }
  return types[status]
}

const getAgentProgress = (status: WorkflowStatus) => {
  if (status === 'success') return 100
  if (status === 'running') return 58
  if (status === 'failed') return 100
  return 0
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
  return activeAgents[nodeId]?.status || 'pending'
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
.progress-panel { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 18px; padding: 18px; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
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
.flow-node { position: absolute; z-index: 5; transform: translate(-50%, -50%); width: 186px; min-height: 132px; border: 1px solid #CBD5E1; border-radius: 18px; background: rgba(255, 255, 255, 0.96); display: flex; flex-direction: column; align-items: stretch; justify-content: flex-start; gap: 8px; cursor: pointer; color: #475569; box-shadow: 0 10px 22px rgba(15, 23, 42, 0.07); padding: 12px; text-align: left; transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease; }
.flow-node:hover, .flow-node.focused { transform: translate(-50%, -50%) translateY(-3px); border-color: #2563EB; box-shadow: 0 16px 30px rgba(37, 99, 235, 0.16); }
.node-head { display: flex; align-items: center; gap: 10px; min-width: 0; }
.flow-node .node-icon { width: 34px; height: 34px; border-radius: 12px; display: flex; align-items: center; justify-content: center; background: #F1F5F9; color: #64748B; flex: 0 0 auto; }
.node-title-group { min-width: 0; flex: 1; }
.flow-node .node-label { display: block; font-weight: 850; color: #1E293B; font-size: 0.9rem; line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.flow-node small { display: block; margin-top: 2px; color: #94A3B8; font-weight: 700; font-size: 0.72rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.node-stage { min-height: 38px; border-radius: 12px; background: #F8FAFC; border: 1px solid #E2E8F0; color: #334155; font-size: 0.76rem; font-weight: 760; line-height: 1.35; padding: 8px 10px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.node-inline-logs { display: grid; gap: 4px; }
.node-inline-logs p { position: relative; margin: 0; padding-left: 12px; color: #64748B; font-size: 0.7rem; line-height: 1.35; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.node-inline-logs p::before { content: ''; position: absolute; left: 2px; top: 0.55em; width: 5px; height: 5px; border-radius: 999px; background: #94A3B8; }
.node-progress { position: relative; height: 3px; margin-top: auto; overflow: hidden; border-radius: 999px; background: #E2E8F0; }
.node-progress span { position: absolute; inset: 0 auto 0 0; width: 45%; border-radius: inherit; background: #2563EB; animation: nodeProgressMove 1.35s ease-in-out infinite; }
.flow-node.is-running { border-color: #60A5FA; box-shadow: 0 0 0 6px rgba(96, 165, 250, 0.14), 0 18px 32px rgba(37, 99, 235, 0.16); animation: nodePulse 1.4s ease-in-out infinite; }
.flow-node.is-running .node-icon { background: #DBEAFE; color: #2563EB; }
.flow-node.is-running .node-inline-logs p::before { background: #2563EB; }
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

/* ================= Phase 4: Results View ================= */
.results-view { background: #F8FAFC; overflow-y: auto; }
.results-header { position: sticky; top: 0; z-index: 50; padding: 20px 40px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(226, 232, 240, 0.6); }
.glass-nav { background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(16px); }
.nav-brand { display: flex; align-items: center; gap: 16px; }
.success-icon { font-size: 2.2rem; color: #10B981; }
.nav-titles h2 { margin: 0 0 4px; font-size: 1.25rem; font-weight: 800; color: #0F172A; }
.nav-titles p { margin: 0; font-size: 0.9rem; color: #64748B; }
.nav-actions { display: flex; gap: 12px; }
.back-btn { border: none !important; background: #F1F5F9 !important; color: #475569 !important; font-weight: 600; }
.back-btn:hover { background: #E2E8F0 !important; color: #0F172A !important; }
.path-btn { font-weight: 700; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }

.results-body { padding: 40px; max-width: 1500px; width: 100%; margin: 0 auto; display: flex; flex-direction: column; gap: 24px; }
.review-summary-card { padding: 22px; }
.review-summary-card p { margin: 0; color: #475569; line-height: 1.65; }
.result-resource-groups { display: flex; flex-direction: column; gap: 24px; }
.result-group-section { padding: 22px; }
.result-group-header { margin-bottom: 18px; }
.result-resource-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 22px; }
.result-resource-card { padding: 22px; display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.result-card-header { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.result-card-header h3 { margin: 10px 0 0; font-size: 1.12rem; line-height: 1.35; color: #0F172A; overflow-wrap: anywhere; }
.result-card-header > span { color: #64748B; font-size: 0.82rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.04em; }
.result-meta-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.result-meta-grid span { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 10px; color: #475569; line-height: 1.4; overflow-wrap: anywhere; }
.result-meta-grid b { display: block; color: #94A3B8; font-size: 0.76rem; margin-bottom: 4px; }
.personalized-reason { background: #F0F9FF; border: 1px solid #BAE6FD; border-radius: 14px; padding: 12px; color: #075985; line-height: 1.55; overflow-wrap: anywhere; }

@media (max-width: 1200px) {
  .workbench-grid { grid-template-columns: 240px minmax(0, 1fr); }
  .resource-side-panel { grid-column: 1 / -1; position: static; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .generation-focus-grid { grid-template-columns: 1fr; }
  .agent-configs-grid { grid-template-columns: repeat(2, 1fr); }
  .workbench-hero { grid-template-columns: 1fr; }
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
  .flow-node { width: 176px; min-height: 126px; font-size: 0.82rem; }
  .resource-status-item { grid-template-columns: 1fr; }
  .workflow-timeline-panel, .resource-side-panel { position: static; }
  .event-log-row { grid-template-columns: 1fr; gap: 6px; }
  .result-meta-grid { grid-template-columns: 1fr; }
  .results-header { align-items: flex-start; flex-direction: column; gap: 16px; padding: 18px; }
  .results-body { padding: 18px; }
}

.elegant-dialog :deep(.el-dialog) { border-radius: 24px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); }
.elegant-dialog :deep(.el-dialog__header) { padding: 24px 32px 20px; margin-right: 0; border-bottom: 1px solid #F1F5F9; }
.elegant-dialog :deep(.el-dialog__title) { font-weight: 800; font-size: 1.2rem; color: #0F172A; }
.elegant-dialog :deep(.el-dialog__body) { padding: 32px; background: #F8FAFC; }
</style>
