<template>
  <div class="elegant-generator-layout">
    <div class="omni-ambient-bg">
      <div class="ambient-glow glow-blue"></div>
      <div class="ambient-glow glow-indigo"></div>
      <div class="omni-pattern-bg"></div>
    </div>
    
    <!-- Floating History Entry -->
    <div class="floating-history-btn" @click="router.push('/resource-history')">
      <el-icon><Timer /></el-icon>
      <span>历史记录</span>
    </div>

    <transition name="page-slide" mode="out-in">

      <div v-if="currentPhase === 'input'" class="phase-view omni-input-view" key="input">
        
        <div class="omni-container">
          <div class="omni-hero-header">
            <h1 class="hero-title">AI 学习资源引擎</h1>
            <p class="hero-subtitle">输入你的学习目标，自动构建专属的知识图谱、测试与课件</p>
          </div>

          <div class="omni-spotlight-wrapper" :class="{ 'is-focused': isInputFocused, 'has-content': naturalInput.trim().length > 0 }">
            <el-input
                v-model="naturalInput"
                type="textarea"
                :autosize="{ minRows: 1, maxRows: 10 }"
                placeholder="输入学习需求，唤醒多智能体..."
                class="omni-textarea"
                @focus="isInputFocused = true"
                @blur="isInputFocused = false"
                @keydown.enter.exact.prevent="goToPersonalize"
            />
            <div class="omni-actions">
              <span class="omni-hint" v-if="naturalInput.trim().length > 0">
                回车键进入参数配置 ⏎
              </span>
              <span class="omni-hint" v-else>
                描述考研、期末、或任意技术栈...
              </span>
              <button
                  class="omni-submit-btn"
                  :disabled="!naturalInput.trim()"
                  aria-label="进入参数配置"
                  @click="goToPersonalize"
              >
                <el-icon><Top /></el-icon>
              </button>
            </div>
          </div>

          <div class="omni-inspiration-grid">
            <div class="inspiration-card" @click="naturalInput = '复习《计算机网络》TCP三次握手，请多出几道难题'">
              <div class="ins-icon" style="background: #EFF6FF; color: #3B82F6;"><el-icon><StarFilled /></el-icon></div>
              <div class="ins-content">
                <h4>深度复习</h4>
                <p>复习《计算机网络》TCP三次握手...</p>
              </div>
            </div>
            <div class="inspiration-card" @click="naturalInput = '零基础学习 Python 多线程，需要底层原理和代码'">
              <div class="ins-icon" style="background: #F0FDF4; color: #22C55E;"><el-icon><Cpu /></el-icon></div>
              <div class="ins-content">
                <h4>零基础入门</h4>
                <p>零基础学习 Python 多线程原理...</p>
              </div>
            </div>
            <div class="inspiration-card" @click="naturalInput = '考研冲刺《数据结构》二叉树，帮我精简思维导图，重点标注高频考点'">
              <div class="ins-icon" style="background: #FEF2F2; color: #EF4444;"><el-icon><Odometer /></el-icon></div>
              <div class="ins-content">
                <h4>考研冲刺</h4>
                <p>《数据结构》二叉树，精简思维导图...</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="currentPhase === 'personalize'" class="phase-view personalize-view" key="personalize">
        <div class="personalize-container">
          <div class="view-header">
            <el-tag size="small" effect="dark" round class="header-badge">AI CONFIGURATION</el-tag>
            <h2>多智能体参数定制中心</h2>
            <p>请为即将出场的 AI 智能体配置加工参数，您的指令将作为最高优先级要求贯穿全局。</p>
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
              <div class="config-card-v2" :class="{ 'agent-off': !isAgentEnabled(agent.id) }" v-for="agent in personalizeAgents" :key="agent.id">
                <div class="cc-header-v2">
                  <div class="cc-icon-wrap" :class="agent.colorClass">
                    <el-icon><component :is="agent.icon" /></el-icon>
                  </div>
                  <span class="cc-title">{{ agent.name }}</span>
                  <div class="cc-header-switch">
                    <el-switch
                        :model-value="isAgentEnabled(agent.id)"
                        @change="toggleAgent(agent.id)"
                        active-color="#0369A1"
                    />
                  </div>
                </div>

                <div class="cc-body-v2" :class="{ 'body-disabled': !isAgentEnabled(agent.id) }">
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
                        <el-radio-button value="beginner">入门</el-radio-button>
                        <el-radio-button value="intermediate">进阶</el-radio-button>
                        <el-radio-button value="advanced">挑战</el-radio-button>
                      </el-radio-group>
                    </div>
                    <div class="ctrl-group">
                      <label>案例交付形态</label>
                      <el-radio-group v-model="agentConfigs.code.case_type" size="small" class="custom-radio-group">
                        <el-radio-button value="basic_demo">基础教学</el-radio-button>
                        <el-radio-button value="algorithm_template">算法模板</el-radio-button>
                      </el-radio-group>
                    </div>
                  </template>

                  <template v-if="agent.id === 'quiz'">
                    <div class="ctrl-group">
                      <label>测验难度引擎</label>
                      <el-radio-group v-model="agentConfigs.quiz.difficulty_mode" size="small" class="custom-radio-group">
                        <el-radio-button value="basic">基础巩固</el-radio-button>
                        <el-radio-button value="adaptive">动态自适应</el-radio-button>
                        <el-radio-button value="exam">硬核考研</el-radio-button>
                      </el-radio-group>
                    </div>
                    <div class="ctrl-group">
                      <label>题型偏好（可多选）</label>
                      <el-checkbox-group v-model="agentConfigs.quiz.question_types" class="question-type-group">
                        <el-checkbox value="single">单选题</el-checkbox>
                        <el-checkbox value="multiple">多选题</el-checkbox>
                        <el-checkbox value="judge">判断题</el-checkbox>
                        <el-checkbox value="fill">填空题</el-checkbox>
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
                        <el-radio-button value="chinese">中文优先</el-radio-button>
                        <el-radio-button value="both">中英双语</el-radio-button>
                        <el-radio-button value="english">英文原版</el-radio-button>
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
                      <label>交付方式</label>
                      <el-tag effect="plain" round>在线预览课件</el-tag>
                    </div>
                    <div class="ctrl-group">
                      <label>幻灯片主题风格</label>
                      <el-tag effect="plain" round type="primary">逻辑蓝 · 教学演示主题</el-tag>
                    </div>
                    <div class="ctrl-group">
                      <label>内容深度/难度</label>
                      <el-radio-group v-model="agentConfigs.ppt.difficulty" size="small" class="custom-radio-group">
                        <el-radio-button value="beginner">入门演示</el-radio-button>
                        <el-radio-button value="intermediate">进阶讲解</el-radio-button>
                        <el-radio-button value="advanced">硬核干货</el-radio-button>
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
                确认配置，启动多智能体加工 <el-icon class="el-icon--right"><Position /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="currentPhase === 'generating'" class="phase-view generating-view workflow-stage-page" key="generating">

        <header class="stage-topbar">
          <div class="stage-title-area">
            <div class="stage-route-progress">
              <span class="route-step done">1 需求输入</span>
              <span class="route-line done"></span>
              <span class="route-step done">2 个性化配置</span>
              <span class="route-line active"></span>
              <span class="route-step active">3 多智能体协作</span>
              <span class="route-line"></span>
              <span class="route-step">4 资源展示</span>
            </div>
            <h2>多智能体调度动画工作台</h2>
            <p>{{ dagHeroMessage }}</p>
          </div>

          <div class="stage-stat-group">
            <div class="stage-stat-card">
              <span>总进度</span>
              <strong>{{ overallProgress }}%</strong>
            </div>
            <div class="stage-stat-card">
              <span>活跃智能体</span>
              <strong>{{ runningAgentCount }}<small>/{{ dagSelectedAgentIds.length }}</small></strong>
            </div>
            <div class="stage-stat-card wide">
              <span>已接收资源</span>
              <strong>{{ generatedResources.length }}<small> 项</small></strong>
            </div>
            <el-button round class="stage-log-btn" @click="workflowLogDrawerVisible = true">
              查看调度日志
              <el-icon class="el-icon--right"><ArrowRight /></el-icon>
            </el-button>
          </div>
        </header>

        <el-alert v-if="generationError" class="stage-generation-error" type="error" :closable="false" show-icon :title="generationError" />

        <main class="agent-stage-layout">
          <section class="agent-stage-canvas">
            <div class="stage-canvas-header">
              <div>
                <span class="panel-eyebrow">MASTER PLAN DISPATCH</span>
                <h3>多智能体 OPRE 执行拓扑</h3>
              </div>
              <div class="stage-control-pills">
                <span class="control-pill active"><span class="live-dot"></span> SSE 实时流追踪</span>
              </div>
            </div>

            <div class="dispatch-stage dag-flow-wrapper">
              <div class="execution-stage-grid">
                <div class="execution-rail">
                  <article
                    v-for="node in leadingStageNodes"
                    :key="node.id"
                    class="dag-node-card stage-node-card"
                    :class="['status-' + node.status, { 'is-selected': selectedDagNodeId === node.id }]"
                    @click="selectedDagNodeId = node.id"
                  >
                    <div class="node-indicator"></div>
                    <div class="node-inner">
                      <div class="node-head">
                        <div class="node-icon"><span>{{ node.icon }}</span></div>
                        <div class="node-title-group">
                          <strong>{{ node.label }}</strong>
                          <span class="node-sub">{{ getNodeStageLabel(node) }}</span>
                        </div>
                        <div class="node-status-pill">{{ getNodeProgressLabel(node) }}</div>
                      </div>
                      <div class="node-divider"></div>
                      <div class="node-body">
                        <div class="meta-row">
                          <span class="meta-label">{{ getNodePhaseLabel(node) }}</span>
                          <span class="meta-time">{{ getNodeTimeLabel(node) }}</span>
                        </div>
                        <p class="node-message" :class="{ 'is-error': node.status === 'failed' }">
                          {{ getNodeDisplayMessage(node) }}
                        </p>
                      </div>
                    </div>
                  </article>

                  <section
                    class="parallel-pool-card"
                    :class="{ 'is-selected': selectedDagNodeId === COORDINATOR_AGENT_ID }"
                    @click="selectedDagNodeId = COORDINATOR_AGENT_ID"
                  >
                    <div class="pool-header">
                      <div>
                        <span class="panel-eyebrow">PARALLEL POOL</span>
                        <h4>并行资源生成池</h4>
                      </div>
                      <div class="pool-status">
                        <strong>{{ poolRunningCount }}</strong>
                        <span>运行 / {{ parallelPoolNodes.length }}</span>
                      </div>
                    </div>
                    <div class="pool-summary">
                      {{ parallelPoolSummary }}
                    </div>
                    <transition-group name="dag-node-anim" tag="div" class="parallel-agent-grid">
                      <article
                        v-for="node in parallelPoolNodes"
                        :key="node.id"
                        class="dag-node-card pool-agent-card"
                        :class="['status-' + node.status, { 'is-selected': selectedDagNodeId === node.id }]"
                        @click.stop="selectedDagNodeId = node.id"
                      >
                        <div class="node-indicator"></div>
                        <div class="node-inner">
                          <div class="node-head">
                            <div class="node-icon"><span>{{ node.icon }}</span></div>
                            <div class="node-title-group">
                              <strong>{{ node.label }}</strong>
                              <span class="node-sub">{{ getNodeStageLabel(node) }}</span>
                            </div>
                            <div class="node-status-pill">{{ getNodeProgressLabel(node) }}</div>
                          </div>
                          <div class="node-body compact">
                            <p class="node-message" :class="{ 'is-error': node.status === 'failed' }">
                              {{ getNodeDisplayMessage(node) }}
                            </p>
                          </div>
                        </div>
                      </article>
                    </transition-group>
                  </section>

                  <article
                    v-for="node in trailingStageNodes"
                    :key="node.id"
                    class="dag-node-card stage-node-card"
                    :class="['status-' + node.status, { 'is-selected': selectedDagNodeId === node.id }]"
                    @click="selectedDagNodeId = node.id"
                  >
                    <div class="node-indicator"></div>
                    <div class="node-inner">
                      <div class="node-head">
                        <div class="node-icon"><span>{{ node.icon }}</span></div>
                        <div class="node-title-group">
                          <strong>{{ node.label }}</strong>
                          <span class="node-sub">{{ getNodeStageLabel(node) }}</span>
                        </div>
                        <div class="node-status-pill">{{ getNodeProgressLabel(node) }}</div>
                      </div>
                      <div class="node-divider"></div>
                      <div class="node-body">
                        <div class="meta-row">
                          <span class="meta-label">{{ getNodePhaseLabel(node) }}</span>
                          <span class="meta-time">{{ getNodeTimeLabel(node) }}</span>
                        </div>
                        <p class="node-message" :class="{ 'is-error': node.status === 'failed' }">
                          {{ getNodeDisplayMessage(node) }}
                        </p>
                      </div>
                    </div>
                  </article>
                </div>

                <aside class="agent-focus-panel" v-if="selectedDagNode">
                  <div class="focus-panel-header">
                    <div class="focus-agent-icon">{{ selectedDagNode.icon }}</div>
                    <div>
                      <span class="panel-eyebrow">FOCUS AGENT</span>
                      <h4>{{ selectedDagNode.label }}</h4>
                    </div>
                  </div>
                  <div class="focus-status-line" :class="'status-' + selectedDagNode.status">
                    <span>{{ getNodeStageLabel(selectedDagNode) }}</span>
                    <strong>{{ getNodeProgressLabel(selectedDagNode) }}</strong>
                  </div>
                  <div class="focus-progress-track">
                    <span :style="{ width: `${Math.min(100, Math.max(0, selectedDagNode.progress))}%` }"></span>
                  </div>
                  <dl class="focus-metrics">
                    <div>
                      <dt>当前阶段</dt>
                      <dd>{{ getNodePhaseLabel(selectedDagNode) }}</dd>
                    </div>
                    <div>
                      <dt>运行耗时</dt>
                      <dd>{{ formatElapsed(selectedDagNode.elapsedMs) }}</dd>
                    </div>
                    <div>
                      <dt>最近更新</dt>
                      <dd>{{ getNodeTimeLabel(selectedDagNode) }}</dd>
                    </div>
                    <div>
                      <dt>产物状态</dt>
                      <dd>{{ hasGeneratedResource(selectedDagNode.id) ? '已进入产物坞' : '等待生成' }}</dd>
                    </div>
                  </dl>
                  <div class="focus-message">
                    {{ getNodeDisplayMessage(selectedDagNode) }}
                  </div>
                  <div class="focus-metric-chips" v-if="getMetricChips(selectedDagNode).length">
                    <span v-for="chip in getMetricChips(selectedDagNode)" :key="chip">{{ chip }}</span>
                  </div>
                  <div class="focus-history">
                    <span class="panel-eyebrow">RECENT STEPS</span>
                    <p v-for="step in selectedDagNode.stepHistory.slice(-4)" :key="step">{{ step }}</p>
                    <p v-if="!selectedDagNode.stepHistory.length">等待该智能体上报执行步骤</p>
                  </div>
                </aside>
              </div>
            </div>
          </section>
        </main>

        <section class="output-dock-section">
          <div class="output-dock-heading">
            <div>
              <span class="panel-eyebrow">OUTPUT DOCK</span>
              <strong>资源产出独立展示区</strong>
            </div>
            <p>资源卡片只展示产出状态，不再覆盖多智能体调度舞台</p>
          </div>
          <div class="output-dock-list">
            <article
                v-for="agentId in visibleOutputAgentIds"
                :key="agentId"
                class="output-dock-item"
                :class="{ ready: hasGeneratedResource(agentId) }"
                @click="openResourceByType(agentId)"
            >
              <span>{{ getDagNodeIcon(agentId) }}</span>
              <div>
                <strong>{{ getResourceTypeLabel(agentId) }}</strong>
                <p>{{ hasGeneratedResource(agentId) ? '已生成，可预览' : getAgentOutputFormat(agentId) }}</p>
              </div>
            </article>
            <div v-if="visibleOutputAgentIds.length === 0" class="output-dock-empty">
              等待第一个智能体完成调用
            </div>
          </div>
        </section>

        <el-drawer v-model="workflowLogDrawerVisible" title="实时调度日志" direction="rtl" size="420px" class="workflow-log-drawer">
          <div class="drawer-log-list">
            <div v-for="item in workflowLogItems" :key="item.id" class="drawer-log-item" :class="`is-${item.status}`">
              <span class="drawer-log-dot"></span>
              <div>
                <strong>{{ item.title }}</strong>
                <p>{{ item.message }}</p>
              </div>
            </div>
          </div>
        </el-drawer>
      </div>

      <div v-else-if="currentPhase === 'result'" class="phase-view results-view result-dashboard-view" key="result">
        <header class="result-hero-compact">
          <div class="hero-content-left">
            <div class="hero-status-tag-mini success-glow">
              <el-icon><CircleCheckFilled /></el-icon>
              <span>{{ resultWarning ? '部分完成' : '已完成' }}</span>
            </div>
            <h1 class="hero-title-compact">{{ finalBundle?.title || '个性化学习资源已就绪' }}</h1>
            <p class="hero-subtitle-compact">多智能体协同加工完成，已为您生成专属学习资源包</p>
          </div>
          <div class="hero-actions-right">
            <el-button round size="small" @click="resetGenerator">
              <el-icon><RefreshLeft /></el-icon> 新建任务
            </el-button>
          </div>
        </header>
        <el-alert
            v-if="resultWarning"
            class="result-warning"
            type="warning"
            :closable="false"
            show-icon
            :title="resultWarning"
        />

        <main class="results-body-bento">
          <div class="bento-grid-container">
            <div class="premium-resource-grid">
              <article
                  v-for="(res, index) in resultResources"
                  :key="res.id || res.title"
                  class="premium-res-card"
                  :class="getResourceToneClass(res.type)"
                  :style="{...getBentoCardGridStyle(index, resultResources.length), animationDelay: `${index * 0.08}s`}"
                  role="button"
                  tabindex="0"
                  :aria-label="`预览 ${formatBentoTitle(res.title, res.type)}`"
                  @click="handlePreview({ agentId: res.type, resultData: res.content, title: res.title })"
                  @keydown.enter.prevent="handlePreview({ agentId: res.type, resultData: res.content, title: res.title })"
                  @keydown.space.prevent="handlePreview({ agentId: res.type, resultData: res.content, title: res.title })"
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

    <el-dialog v-model="previewVisible" :title="previewData ? getResourceTypeLabel(previewData.agentId) : '资源预览'" width="78%" top="6vh" destroy-on-close :class="['elegant-dialog', { 'is-ppt-dialog': previewData?.agentId === 'ppt' }]">
      <div v-if="previewData" class="preview-dialog-body" :class="{ 'is-ppt-preview': previewData.agentId === 'ppt' }">
        <MindmapView v-if="previewData.agentId === 'mindmap'" :result-data="previewData.resultData" />
        <QuizView v-else-if="previewData.agentId === 'quiz'" :result-data="previewData.resultData" />
        <CodeView v-else-if="previewData.agentId === 'code'" :result-data="previewData.resultData" />
        <ReadingView v-else-if="previewData.agentId === 'reading'" :result-data="previewData.resultData" />
        <PptView v-else-if="previewData.agentId === 'ppt'" :result-data="previewData.resultData" />
        <MarkdownView v-else :result-data="previewData.resultData" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, reactive, computed, onMounted, onBeforeUnmount, onActivated, onDeactivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowRight, RefreshLeft, Cpu, Position, CircleCheckFilled,
  Clock, Odometer, Top, StarFilled, Timer
} from '@element-plus/icons-vue'

import MindmapView from '@/resource/components/MindmapView.vue'
import MarkdownView from '@/resource/components/MarkdownView.vue'
import QuizView from '@/resource/components/QuizView.vue'
import CodeView from '@/resource/components/CodeView.vue'
import ReadingView from '@/resource/components/ReadingView.vue'
import PptView from '@/resource/components/PptView.vue'

import {
  startResourceGeneration,
  pollResourceStatus,
  getResourceBundle,
  streamResourceEvents,
} from '@/resource/api/resource'

import type {
  LearningScenario,
  ResourceAgentId,
  ResourceTaskStatus,
  ResourceGenerationRequest,
  ResourceStreamEvent,
} from '@/resource/types/resource'

import {
  PPT_AGENT_ID,
  PRE_REVIEW_AGENT_ID,
  PPT_REVIEW_AGENT_ID,
  COORDINATOR_AGENT_ID,
  BUNDLE_AGENT_ID,
  SYSTEM_AGENT_IDS,
  MIN_AGENTS,
  AGENT_DISPLAY,
  agentMetaList,
  getAgentMeta,
  SCENARIO_DEFAULTS,
  scenarioOptions,
  getScenarioDesc,
  getResourceTypeLabel,
  getResourceUsageHint,
  getDefaultResourceFormat,
  getEstimatedTime,
  getDifficultyLabel,
  getResourceToneClass,
  getAgentOutputFormat,
  createDagNode,
  getNodeFallbackMessage,
  getDagNodeIcon,
  getBentoCardGridStyle,
  stringifyCompact,
  formatBentoTitle,
  type QuizQuestionType,
  type DagNodeState,
} from './ResourceGeneratorConstants'

defineOptions({ name: 'ResourceGenerator' })

const route = useRoute()

type GeneratedResourceItem = Record<string, any> & {
  generatedAt?: string
  displayOrder?: number
}

// ===================== 核心状态管理 =====================
type Phase = 'input' | 'personalize' | 'generating' | 'result'
const currentPhase = ref<Phase>('input')

const router = useRouter()

const naturalInput = ref('')
const isInputFocused = ref(false)
const learningScenario = ref<LearningScenario>('daily_review')

const enabledAgentIds = ref<ResourceAgentId[]>(['content', 'mindmap', 'code', 'quiz', 'reading', 'ppt'])

const isAgentEnabled = (id: string) => enabledAgentIds.value.includes(id as ResourceAgentId)

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

// ===================== 参数表单状态 =====================
const agentConfigs = reactive({
  content: { structure: 'progressive' as const, include_common_mistakes: true, include_examples: true, focus_mode: 'full_coverage' as const, depth_level: 'standard' as const },
  mindmap: { map_type: 'knowledge_tree' as const, max_depth: 3, highlight_weak: true, expand_weak_points: false, include_prerequisites: false },
  quiz: { question_count: 5, difficulty_mode: 'adaptive' as const, weak_point_weight: 50, exam_style: 'school' as const, include_analysis: true, question_types: ['single', 'multiple', 'judge'] as QuizQuestionType[] },
  code: { programming_language: 'python' as const, case_type: 'basic_demo' as const, difficulty: 'beginner' as const },
  reading: { reading_depth: 'course_extended' as const, max_items: 3, language_preference: 'chinese' as const },
  ppt: { page_count: 6, difficulty: 'intermediate' as const, output_format: 'preview' as const },
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

const selectScenario = (scenario: LearningScenario) => {
  learningScenario.value = scenario
  applyScenarioDefaults(scenario)
}

const goToPersonalize = () => {
  if (!naturalInput.value.trim()) return
  currentPhase.value = 'personalize'
}

// ===================== 异步工作流大盘画布引擎 =====================
const generatedResources = shallowRef<GeneratedResourceItem[]>([])
const finalBundle = shallowRef<any | null>(null)
const isGenerating = ref(false)
const generationError = ref<string | null>(null)
const resultWarning = ref('')
const overallProgress = ref(0)
const latestWorkflowMessage = ref('')
const pollingInterval = ref<ReturnType<typeof setInterval> | null>(null)
const resourceStreamController = ref<EventSource | null>(null)
const generationFinalized = ref(false)
const activeResourceId = ref<number | null>(null)

const dagNodeStates = ref<Record<string, DagNodeState>>({})
const selectedDagNodeId = ref('planning')

const dagSelectedAgentIds = computed(() => {
  return enabledAgentIds.value.filter(id => !['master', 'reviewer', 'assembler'].includes(id))
})

const baseGenerationAgentIds = computed(() => {
  return dagSelectedAgentIds.value.filter(id => id !== PPT_AGENT_ID)
})

const dagNodesV2 = computed<DagNodeState[]>(() => {
  const selected = dagSelectedAgentIds.value
  const nodes: DagNodeState[] = []

  // 1. 顶层规划节点
  nodes.push(dagNodeStates.value['planning'] || {
    id: 'planning', label: '规划任务', icon: '🎯',
    status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: true,
  })

  nodes.push(dagNodeStates.value[COORDINATOR_AGENT_ID] || {
    id: COORDINATOR_AGENT_ID, label: '并行调度中枢', icon: '⚙️',
    status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: true,
  })

  // 2. 基础资源子智能体群组
  for (const agentId of baseGenerationAgentIds.value) {
    const display = AGENT_DISPLAY[agentId]
    if (!display) continue
    nodes.push(dagNodeStates.value[agentId] || {
      id: agentId, label: display.label, icon: display.icon,
      status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: false,
    })
  }

  // 3. 前置审核节点
  nodes.push(dagNodeStates.value[PRE_REVIEW_AGENT_ID] || {
    id: PRE_REVIEW_AGENT_ID, label: '前置安全审核', icon: '🛡️',
    status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: true,
  })

  if (selected.includes(PPT_AGENT_ID)) {
    nodes.push(dagNodeStates.value[PPT_AGENT_ID] || {
      id: PPT_AGENT_ID, label: '演示文稿助手', icon: '📊',
      status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: false,
    })
    nodes.push(dagNodeStates.value[PPT_REVIEW_AGENT_ID] || {
      id: PPT_REVIEW_AGENT_ID, label: 'PPT 安全审核', icon: '🔍',
      status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: true,
    })
  }

  // 4. 打包输出节点
  nodes.push(dagNodeStates.value[BUNDLE_AGENT_ID] || {
    id: BUNDLE_AGENT_ID, label: '资源组装', icon: '📦',
    status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: true,
  })

  return nodes
})

function hasNodeEntered(node?: DagNodeState) {
  if (!node) return false
  if (node.id === 'planning') return true
  return node.status !== 'waiting'
      || node.progress > 0
      || Boolean(node.currentMessage)
      || (node.stepHistory?.length || 0) > 0
      || hasGeneratedResource(node.id)
}

const visibleWorkflowNodes = computed(() => {
  return dagNodesV2.value.filter(node => hasNodeEntered(node))
})

function getStageNode(id: string) {
  return dagNodeStates.value[id] || createDagNode(id, SYSTEM_AGENT_IDS.includes(id))
}

const leadingStageNodes = computed(() => [getStageNode('planning')])

const trailingStageNodes = computed(() => {
  const nodes = [getStageNode(PRE_REVIEW_AGENT_ID)]
  if (dagSelectedAgentIds.value.includes(PPT_AGENT_ID as ResourceAgentId)) {
    nodes.push(getStageNode(PPT_AGENT_ID), getStageNode(PPT_REVIEW_AGENT_ID))
  }
  nodes.push(getStageNode(BUNDLE_AGENT_ID))
  return nodes
})

const agentStatusRank: Record<DagNodeState['status'], number> = {
  failed: 0,
  running: 1,
  success: 2,
  waiting: 3,
  skipped: 4,
}

const parallelPoolNodes = computed(() => {
  return baseGenerationAgentIds.value
    .map(agentId => getStageNode(agentId))
    .sort((a, b) => {
      const rankDiff = agentStatusRank[a.status] - agentStatusRank[b.status]
      if (rankDiff !== 0) return rankDiff
      return b.progress - a.progress
    })
})

const selectedDagNode = computed(() => {
  if (selectedDagNodeId.value === COORDINATOR_AGENT_ID) return getStageNode(COORDINATOR_AGENT_ID)
  return dagNodeStates.value[selectedDagNodeId.value] || getStageNode(selectedDagNodeId.value)
})

const poolRunningCount = computed(() => parallelPoolNodes.value.filter(node => node.status === 'running').length)

const parallelPoolSummary = computed(() => {
  const failed = parallelPoolNodes.value.filter(node => node.status === 'failed').length
  const finished = parallelPoolNodes.value.filter(node => node.status === 'success').length
  if (failed) return `${failed} 个资源智能体需要关注，${finished} 个已完成`
  if (poolRunningCount.value) return `${poolRunningCount.value} 个智能体正在并行生成，${finished} 个资源已就绪`
  if (finished) return `${finished} 个基础资源已生成，等待进入审核阶段`
  return '规划完成后，基础资源智能体会在这里并行展开'
})

function getNodeProgressLabel(node: DagNodeState) {
  if (node.status === 'failed') return '失败'
  if (node.status === 'skipped') return '跳过'
  return `${node.progress}%`
}

function getNodeStageLabel(node: DagNodeState) {
  if (node.status === 'success') return '已就绪'
  if (node.status === 'failed') return '执行失败'
  if (node.status === 'skipped') return '已跳过'
  if (node.status === 'running') {
    if (node.phase === 'llm_generating') return '模型生成中'
    if (node.phase === 'validating') return '解析校验中'
    if (node.phase === 'artifact_saved') return '产物已保存'
    if (node.phase === 'bundling') return '资源打包中'
    return '执行中'
  }
  return '等待依赖'
}

function getNodePhaseLabel(node: DagNodeState) {
  const phaseMap: Record<string, string> = {
    planning_blueprint: '规划蓝图',
    llm_generating: '模型调用',
    validating: '解析校验',
    reviewing_sources: '前置审核',
    reviewing_ppt: 'PPT 审核',
    ppt_waiting_sources: '等待事实来源',
    pre_review_waiting_sources: '等待基础资源',
    artifact_saved: '产物保存',
    bundling: '资源组装',
    finished: '完成',
    failed: '失败',
  }
  if (node.phase && phaseMap[node.phase]) return phaseMap[node.phase]
  if (node.status === 'waiting') return '等待上游'
  if (node.status === 'success') return '完成'
  if (node.status === 'failed') return '失败'
  return '执行阶段'
}

function getNodeDisplayMessage(node: DagNodeState) {
  if (node.status === 'failed') return node.currentMessage || '执行失败，请检查该智能体输出'
  if (node.currentMessage) return node.currentMessage
  if (node.id === PPT_AGENT_ID) return '等待前置审核通过后生成演示文稿'
  if (node.id === PRE_REVIEW_AGENT_ID) return '等待基础资源完成后进行事实性与安全审核'
  if (node.id === PPT_REVIEW_AGENT_ID) return '等待 PPT 生成后进行专项审核'
  if (node.id === BUNDLE_AGENT_ID) return '等待资源和审核结果完成后组装资源包'
  return getNodeFallbackMessage(node)
}

function formatElapsed(ms?: number | null) {
  if (!ms || ms < 0) return '未开始'
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${minutes}m ${rest}s`
}

function getNodeTimeLabel(node: DagNodeState) {
  if (node.status === 'waiting') return '等待上游'
  if (!node.lastUpdatedAt) return formatElapsed(node.elapsedMs)
  const seconds = Math.max(0, Math.floor((Date.now() - node.lastUpdatedAt) / 1000))
  if (seconds < 3) return '刚刚更新'
  if (seconds < 60) return `${seconds}s 前更新`
  return `${Math.floor(seconds / 60)}m 前更新`
}

function getMetricChips(node: DagNodeState) {
  const metrics = node.metrics || {}
  return Object.entries(metrics)
    .filter(([, value]) => value !== null && value !== undefined && value !== '')
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${String(value)}`)
}

function updateOverallProgressFromDag() {
  const stages = [
    { weight: 15, progress: getStageNode('planning').progress },
    {
      weight: 45,
      progress: parallelPoolNodes.value.length
        ? parallelPoolNodes.value.reduce((sum, node) => sum + node.progress, 0) / parallelPoolNodes.value.length
        : 0,
    },
    { weight: 10, progress: getStageNode(PRE_REVIEW_AGENT_ID).progress },
    ...(dagSelectedAgentIds.value.includes(PPT_AGENT_ID as ResourceAgentId)
      ? [
          { weight: 15, progress: getStageNode(PPT_AGENT_ID).progress },
          { weight: 5, progress: getStageNode(PPT_REVIEW_AGENT_ID).progress },
        ]
      : []),
    { weight: 10, progress: getStageNode(BUNDLE_AGENT_ID).progress },
  ]
  const weightTotal = stages.reduce((sum, item) => sum + item.weight, 0)
  const weighted = stages.reduce((sum, item) => sum + item.progress * item.weight, 0)
  overallProgress.value = Math.round(weighted / weightTotal)
}

const dagHeroMessage = computed(() => {
  const running = Object.values(dagNodeStates.value).find(n => n.status === 'running')
  if (running) return running.currentMessage || `${running.label}处理中...`
  const allDone = Object.values(dagNodeStates.value).every(n => n.status === 'success')
  if (allDone) return '所有资源生成完成'
  return latestWorkflowMessage.value || '多智能体协同生成中'
})





const workflowLogDrawerVisible = ref(false)

const runningAgentCount = computed(() => {
  return visibleWorkflowNodes.value.filter(node => node.status === 'running').length
})

const workflowLogItems = computed(() => {
  const items: Array<{ id: string; title: string; message: string; status: DagNodeState['status'] }> = []
  visibleWorkflowNodes.value.forEach((node) => {
    if (node.stepHistory?.length) {
      node.stepHistory.slice(-3).forEach((step, index) => {
        items.push({
          id: `${node.id}-${index}-${step}`,
          title: node.label,
          message: step,
          status: node.status,
        })
      })
    } else {
      items.push({
        id: `${node.id}-fallback`,
        title: node.label,
        message: node.currentMessage || getNodeFallbackMessage(node),
        status: node.status,
      })
    }
  })
  return items
})

const visibleOutputAgentIds = computed(() => {
  return dagSelectedAgentIds.value.filter((agentId) => {
    const node = dagNodeStates.value[agentId]
    return hasGeneratedResource(agentId) || hasNodeEntered(node)
  })
})




function hasGeneratedResource(type: string) {
  return generatedResources.value.some(resource => resource.type === type)
}

function openResourceByType(type: string) {
  const resource = generatedResources.value.find(item => item.type === type)
  if (resource) previewGeneratedResource(resource)
}

const resultResources = computed(() => {
  const resources = finalBundle.value?.resources
  return Array.isArray(resources) && resources.length ? resources : generatedResources.value
})




const previewGeneratedResource = (resource: any) => {
  handlePreview({
    agentId: resource.type,
    resultData: resource.content,
    title: resource.title || getResourceTypeLabel(resource.type)
  })
}

function initializeWaitingNodes() {
  const nodes: Record<string, DagNodeState> = {
    planning: createDagNode('planning', true),
    [COORDINATOR_AGENT_ID]: createDagNode(COORDINATOR_AGENT_ID, true),
    [PRE_REVIEW_AGENT_ID]: createDagNode(PRE_REVIEW_AGENT_ID, true),
    [BUNDLE_AGENT_ID]: createDagNode(BUNDLE_AGENT_ID, true),
  }
  if (enabledAgentIds.value.includes(PPT_AGENT_ID as ResourceAgentId)) {
    nodes[PPT_REVIEW_AGENT_ID] = createDagNode(PPT_REVIEW_AGENT_ID, true)
  }
  enabledAgentIds.value.forEach((agentId) => {
    nodes[agentId] = createDagNode(agentId, false)
  })
  dagNodeStates.value = nodes
  selectedDagNodeId.value = 'planning'
  updateOverallProgressFromDag()
}

function applyAgentEvent(event: ResourceStreamEvent) {
  if (!event.agent_id) return
  const node = dagNodeStates.value[event.agent_id] || createDagNode(
    event.agent_id,
    SYSTEM_AGENT_IDS.includes(event.agent_id),
  )
  if (event.status) {
    node.status = event.status === 'finished' ? 'success' : event.status
  }
  if (event.progress != null) {
    node.progress = Math.max(node.progress, event.progress)
  }
  if (event.phase) node.phase = event.phase
  if (event.elapsed_ms != null) node.elapsedMs = event.elapsed_ms
  if (event.metrics) node.metrics = { ...(node.metrics || {}), ...event.metrics }
  if (event.artifact_id) node.artifactId = event.artifact_id
  node.lastUpdatedAt = Date.now()
  if (event.message) {
    node.currentMessage = event.message
    if (node.stepHistory[node.stepHistory.length - 1] !== event.message) {
      node.stepHistory = [...node.stepHistory.slice(-7), event.message]
    }
  }
  dagNodeStates.value[event.agent_id] = node
  updateOverallProgressFromDag()

  if (event.status === 'running' || event.event_type === 'agent.heartbeat' || event.event_type === 'agent.step') {
    selectedDagNodeId.value = event.agent_id
  }
}

function applyTaskStatus(taskStatus: ResourceTaskStatus) {
  if (Array.isArray(taskStatus.resources)) {
    generatedResources.value = taskStatus.resources
  }
  updateOverallProgressFromDag()
}

async function completeGeneration(resourceId: number, taskStatus: ResourceTaskStatus) {
  if (generationFinalized.value) return
  generationFinalized.value = true
  stopPolling()
  stopResourceStream()

  if (taskStatus.status === 'completed' || taskStatus.status === 'partial_completed') {
    const bundle = (await getResourceBundle(resourceId)).data.data
    finalBundle.value = bundle
    generatedResources.value = bundle.resources || taskStatus.resources || []
    resultWarning.value = taskStatus.status === 'partial_completed'
        ? '部分资源生成失败或质量审查未通过，以下已完成内容仍可查看。'
        : ''
    isGenerating.value = false
    currentPhase.value = 'result'
    return
  }

  generationError.value = '资源生成失败，暂无可展示内容'
  isGenerating.value = false
  ElMessage.error(generationError.value || '资源生成失败，暂无可展示内容')
}

async function checkStatusOnce(resourceId: number) {
  const taskStatus = (await pollResourceStatus(resourceId)).data.data
  applyTaskStatus(taskStatus)
  if (['completed', 'partial_completed', 'failed'].includes(taskStatus.status)) {
    await completeGeneration(resourceId, taskStatus)
  }
}

function startPollingFallback(resourceId: number) {
  if (pollingInterval.value) return
  void checkStatusOnce(resourceId)
  pollingInterval.value = setInterval(() => {
    void checkStatusOnce(resourceId).catch((err: any) => {
      stopPolling()
      generationError.value = err.message || '生成中断，请稍后重试'
      isGenerating.value = false
      ElMessage.error(generationError.value || '生成中断，请稍后重试')
    })
  }, 1500)
}

function syncStatusSoon(resourceId: number) {
  void checkStatusOnce(resourceId).catch((err: any) => {
    console.warn('[ResourceGenerator] 状态同步失败:', err)
  })
}

function startResourceStream(resourceId: number) {
  stopResourceStream()
  startPollingFallback(resourceId)
  resourceStreamController.value = streamResourceEvents(
    resourceId,
    (event) => {
      applyAgentEvent(event)
      if (event.message) {
        latestWorkflowMessage.value = event.message
      }
      if (event.status === 'finished') {
        syncStatusSoon(resourceId)
      }
    },
    (event) => {
      if (isGenerating.value && !generationFinalized.value) {
        void checkStatusOnce(resourceId).catch((err: any) => {
          console.warn('[ResourceGenerator] 完成态同步失败:', err)
          void completeGeneration(resourceId, { resource_id: resourceId, status: event.success ? 'completed' : 'failed' })
        })
      }
    },
    (err) => {
      if (!isGenerating.value || generationFinalized.value) return
      console.warn('[ResourceGenerator] SSE 连接失败，切换到轮询兜底:', err)
      latestWorkflowMessage.value = '实时连接中断，已切换到状态同步模式'
      startPollingFallback(resourceId)
    },
  )
}

const startGeneration = async () => {
  currentPhase.value = 'generating'
  resetGenerationState()
  initializeWaitingNodes()
  isGenerating.value = true

  const requestAgentConfigs = {
    content: agentConfigs.content,
    mindmap: agentConfigs.mindmap,
    quiz: agentConfigs.quiz,
    code: agentConfigs.code,
    reading: agentConfigs.reading,
    ppt: agentConfigs.ppt,
  }

  try {
    const requestParams: ResourceGenerationRequest = {
      learning_need: naturalInput.value,
      learning_scenario: learningScenario.value,
      selected_agents: enabledAgentIds.value.map((id, index) => ({ agent_id: id, enabled: true, priority: index })).filter(a => a.enabled),
      agent_configs: requestAgentConfigs,
    }
    const { resource_id } = (await startResourceGeneration(requestParams)).data.data
    activeResourceId.value = resource_id

    startResourceStream(resource_id)
  } catch (err: any) {
    generationError.value = err.message || '生成请求失败'
    isGenerating.value = false
    ElMessage.error(generationError.value || '生成请求失败')
  }
}

const resetGenerationState = () => {
  generatedResources.value = []
  finalBundle.value = null
  generationError.value = null
  resultWarning.value = ''
  overallProgress.value = 0
  latestWorkflowMessage.value = ''
  isGenerating.value = false
  generationFinalized.value = false
  activeResourceId.value = null
  dagNodeStates.value = {}
  selectedDagNodeId.value = 'planning'
}

const stopPolling = () => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
    pollingInterval.value = null
  }
}

const stopResourceStream = () => {
  if (resourceStreamController.value) {
    resourceStreamController.value.close()
    resourceStreamController.value = null
  }
}

const pauseLiveGenerationUpdates = () => {
  stopPolling()
  stopResourceStream()
}

const resumeLiveGenerationUpdates = async () => {
  const resourceId = activeResourceId.value
  if (!resourceId || !isGenerating.value || generationFinalized.value) return

  try {
    await checkStatusOnce(resourceId)
  } catch (err: any) {
    latestWorkflowMessage.value = '状态同步失败，正在重试实时连接'
    console.warn('[ResourceGenerator] 恢复任务状态失败:', err)
  }

  if (activeResourceId.value === resourceId && isGenerating.value && !generationFinalized.value) {
    startResourceStream(resourceId)
  }
}




onMounted(() => {
  const prompt = route.query.prompt
  if (prompt) {
    naturalInput.value = String(prompt)
  }
})

onActivated(() => {
  void resumeLiveGenerationUpdates()
})

onDeactivated(() => {
  pauseLiveGenerationUpdates()
})

onBeforeUnmount(() => {
  pauseLiveGenerationUpdates()
})

const resetGenerator = () => {
  stopPolling()
  stopResourceStream()
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
/* ================= 全局基础排版与转场 ================= */
.elegant-generator-layout {
  min-height: calc(100vh - 64px);
  position: relative;
  background: var(--color-bg);
  overflow-x: hidden;
  font-family: var(--font-sans);
}

.floating-history-btn {
  position: absolute;
  top: 24px;
  right: 24px;
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 20px;
  color: var(--color-primary);
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.floating-history-btn:hover {
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}
.phase-view { position: relative; width: 100%; min-height: calc(100vh - 64px); display: flex; flex-direction: column; background: transparent; backdrop-filter: blur(20px); }
.page-slide-enter-active, .page-slide-leave-active { transition: opacity 0.4s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.page-slide-enter-from { opacity: 0; transform: translateY(30px) scale(0.98); }
.page-slide-leave-to { opacity: 0; transform: translateY(-30px) scale(1.02); }

/* ================= Phase 1: Omni Spotlight 输入舱 ================= */
.omni-input-view {
  align-items: center;
  justify-content: center;
  position: relative;
  background: transparent;
}

/* Ambient Background */
.omni-ambient-bg {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%; overflow: hidden; z-index: 0;
}
.ambient-glow {
  position: absolute; border-radius: 50%; filter: blur(120px); opacity: 0.5;
}
.glow-blue { width: 600px; height: 600px; background: #DBEAFE; top: -100px; left: -100px; }
.glow-indigo { width: 500px; height: 500px; background: #E0E7FF; bottom: -10vh; right: 10%; }

/* 学术网格背景 (Subtle dot pattern) */
.omni-pattern-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: radial-gradient(circle, var(--color-border-hover) 1px, transparent 1px);
  background-size: 24px 24px;
  opacity: 0.6;
  z-index: 1;
  pointer-events: none;
}
.omni-pattern-bg::after {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background: radial-gradient(circle at center, transparent 0%, var(--color-bg) 90%);
}

.omni-container {
  width: 100%;
  max-width: 820px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2.5rem;
  margin-top: -6vh;
  position: relative;
  z-index: 10;
}

/* Hero Header */
.omni-hero-header {
  text-align: center;
  margin-bottom: 0.5rem;
  animation: fadeDown 0.8s ease-out forwards;
}
@keyframes fadeDown {
  0% { opacity: 0; transform: translateY(-20px); }
  100% { opacity: 1; transform: translateY(0); }
}
.hero-title {
  font-size: 2.8rem;
  font-weight: 800;
  color: var(--color-text);
  letter-spacing: -0.03em;
  margin: 0 0 12px 0;
  background: linear-gradient(135deg, var(--color-text-strong), #3B82F6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hero-subtitle {
  font-size: 1.1rem;
  color: var(--color-text-muted);
  font-weight: 500;
  margin: 0;
}

.omni-spotlight-wrapper {
  width: 100%;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 20px;
  box-shadow: 
    0 4px 6px -1px rgba(0, 0, 0, 0.05),
    0 10px 15px -3px rgba(0, 0, 0, 0.03),
    0 25px 50px -12px rgba(0, 0, 0, 0.05);
  padding: 8px;
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  animation: scaleUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both;
}
@keyframes scaleUp {
  0% { opacity: 0; transform: scale(0.95); }
  100% { opacity: 1; transform: scale(1); }
}
.omni-spotlight-wrapper.is-focused, .omni-spotlight-wrapper.has-content {
  border-color: rgba(59, 130, 246, 0.4);
  box-shadow: 
    0 8px 30px rgba(59, 130, 246, 0.08),
    0 0 0 4px rgba(59, 130, 246, 0.1);
  transform: translateY(-2px);
}
.omni-textarea :deep(.el-textarea__inner) {
  border: none;
  background: transparent;
  box-shadow: none !important;
  font-size: 1.15rem;
  color: var(--color-text-strong);
  padding: 18px 20px 8px;
  line-height: 1.6;
  resize: none;
  font-weight: 500;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.omni-textarea :deep(.el-textarea__inner)::-webkit-scrollbar {
  display: none;
  width: 0;
  height: 0;
}
.omni-textarea :deep(.el-textarea__inner)::placeholder {
  color: var(--color-text-faint);
  font-weight: 400;
}
.omni-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 12px 10px 20px;
}
.omni-hint {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}
.omni-submit-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-surface-hover);
  color: var(--color-text-faint);
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.omni-spotlight-wrapper.has-content .omni-submit-btn {
  background: #3B82F6;
  color: var(--color-surface);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}
.omni-spotlight-wrapper.has-content .omni-submit-btn:hover {
  transform: translateY(-2px) scale(1.05);
  background: var(--color-info);
}

/* Rich Inspiration Grid */
.omni-inspiration-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  width: 100%;
  animation: fadeUp 0.6s ease-out 0.2s both;
}
@keyframes fadeUp {
  0% { opacity: 0; transform: translateY(20px); }
  100% { opacity: 1; transform: translateY(0); }
}
.inspiration-card {
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(148, 163, 184, 0.04);
}
.inspiration-card:hover {
  border-color: var(--color-border-hover);
  transform: translateY(-3px);
  box-shadow: 0 10px 20px rgba(148, 163, 184, 0.08);
}
.ins-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
}
.ins-content h4 {
  margin: 0 0 6px 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text-strong);
}
.ins-content p {
  margin: 0;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* ================= Phase 2: 参数定制配置 ================= */
.personalize-view { background: transparent; align-items: center; overflow-y: auto; padding: 60px var(--space-5); position: relative; }
.personalize-container { width: 100%; max-width: 1160px; display: flex; flex-direction: column; gap: var(--space-12); position: relative; z-index: 10; }
.view-header { text-align: center; margin-bottom: 0; }
.header-badge { margin-bottom: var(--space-4); font-weight: 700; letter-spacing: 0.05em; background: var(--color-border) !important; color: var(--color-text-secondary) !important; border: none; padding: 0 12px; }
.view-header h2 { 
  font-size: 2.5rem; 
  font-weight: 800; 
  margin: 0 0 12px 0; 
  letter-spacing: -0.02em; 
  background: linear-gradient(135deg, var(--color-text-strong), #3B82F6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.view-header p { font-size: 1.1rem; color: var(--color-text-muted); margin: 0; max-width: 600px; margin: 0 auto; line-height: 1.6; }
.scenario-selector-v2 { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-5); }
.scenario-card { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.8); border-radius: 16px; padding: var(--space-5); display: flex; align-items: center; gap: var(--space-4); cursor: pointer; transition: all 0.2s ease; position: relative; box-shadow: 0 2px 8px rgba(148, 163, 184, 0.04); }
.scenario-card:hover { transform: translateY(-2px); border-color: var(--color-border-hover); box-shadow: 0 8px 16px rgba(148, 163, 184, 0.08); }
.scenario-card.active { border-color: #3B82F6; box-shadow: 0 8px 24px rgba(59, 130, 246, 0.12); border-width: 1px; }
.scenario-icon-box { width: 44px; height: 44px; background: var(--color-bg); border: 1px solid var(--color-border); border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; color: var(--color-text-secondary); transition: background-color 0.2s, transform 0.2s; }
.scenario-card.active .scenario-icon-box { background: #3B82F6; color: var(--color-surface); border-color: #3B82F6; }
.scenario-info { display: flex; flex-direction: column; gap: var(--space-1); flex: 1; }
.s-name { font-weight: 700; font-size: 1rem; color: var(--color-text-strong); }
.s-desc { font-size: 0.75rem; color: var(--color-text-muted); line-height: 1.4; }
.active-dot { position: absolute; top: 12px; right: 12px; width: 8px; height: 8px; background: #3B82F6; border-radius: 50%; }
.config-section-v2 { margin-top: var(--space-2); }
.agent-configs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-6); }
.config-card-v2 { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.8); border-radius: 24px; overflow: hidden; display: flex; flex-direction: column; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); box-shadow: 0 4px 24px rgba(148, 163, 184, 0.06); }
.config-card-v2:hover { transform: translateY(-4px); box-shadow: 0 16px 40px rgba(148, 163, 184, 0.12); }
.cc-header-v2 { padding: var(--space-5) var(--space-5) 12px; display: flex; align-items: center; gap: var(--space-3); }
.cc-icon-wrap { width: 38px; height: 38px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.15rem; background: #F3F4F6; border: 1px solid #E5E7EB; color: #4B5563; }
.cc-icon-wrap.text-blue, .cc-icon-wrap.text-orange, .cc-icon-wrap.text-purple, .cc-icon-wrap.text-red, .cc-icon-wrap.text-emerald, .cc-icon-wrap.text-indigo, .cc-icon-wrap.text-slate { background: #F3F4F6; color: #374151; }
.config-card-v2.disabled { opacity: 0.7; background: #F9FAFB; }
.config-card-v2.agent-off { border-color: #E5E7EB; opacity: 0.85; }
.cc-header-switch { margin-left: auto; flex-shrink: 0; }
.cc-body-v2.body-disabled { opacity: 0.38; pointer-events: none; filter: grayscale(60%); }
.question-type-group { display: flex; gap: var(--space-3); flex-wrap: wrap; }
.question-type-group :deep(.el-checkbox) { background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--space-1) var(--space-3); margin: 0; transition: all var(--transition-base); }
.question-type-group :deep(.el-checkbox.is-checked) { background: var(--color-info-soft); border-color: #93C5FD; }
.question-type-group :deep(.el-checkbox__label) { font-size: 0.88rem; font-weight: var(--weight-semibold); color: var(--color-text-strong); }
.question-type-group :deep(.el-checkbox.is-checked .el-checkbox__label) { color: #1D4ED8; }
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
.slider-value { font-size: 0.9rem; color: #3B82F6; font-weight: 700; }
.custom-slider-v2 { padding: 0 var(--space-2); }
.personalize-footer-v2 { display: flex; flex-direction: column; align-items: center; gap: 24px; margin-top: 16px; padding-bottom: 60px; }
.footer-btns { display: flex; justify-content: center; gap: 20px; }
.selected-agents-bar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; justify-content: center; background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(12px); border: 1px solid var(--color-border); border-radius: 24px; padding: 16px 24px; max-width: 860px; box-shadow: 0 4px 24px rgba(148, 163, 184, 0.08); }
.sab-label { font-size: 0.9rem; color: var(--color-text-muted); font-weight: 700; white-space: nowrap; }
.sab-pills { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
.sab-pills :deep(.el-tag.sab-pill) { background: var(--color-bg) !important; border: 1px solid var(--color-border) !important; color: var(--color-text-secondary) !important; border-radius: 99px !important; padding: 0 16px !important; height: 32px !important; font-size: 0.85rem; display: inline-flex; align-items: center; gap: 6px; }
.sab-pills :deep(.el-tag.sab-pill) .el-icon { color: #3B82F6; font-size: 1rem; }
.sab-hint { font-size: 0.8rem; color: var(--color-text-muted); font-weight: 600; margin-left: 8px; }
.footer-back-btn { font-weight: 600; color: var(--color-text-muted); border: 1px solid var(--color-border); background: var(--color-surface); }
.footer-back-btn:hover { color: var(--color-text-strong); border-color: var(--color-border-hover); background: var(--color-bg); }
.launch-btn-v2 { font-weight: 700; padding: 0 32px; background: #3B82F6 !important; color: var(--color-surface) !important; border: none; box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3); transition: transform 0.2s, box-shadow 0.2s; }
.launch-btn-v2:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(59, 130, 246, 0.4); background: var(--color-info) !important; }

/* ==================== 第三部分：多智能体工作流控制台 ==================== */
.generating-view {
  background: transparent;
  overflow-y: auto;
}
.workflow-stage-page {
  background: transparent;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 18px 16px;
  gap: 12px;
}
.stage-background-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 0;
}
.stage-grid-bg {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.10) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.10) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: radial-gradient(circle at 50% 40%, #000 0%, transparent 78%);
}
.stage-glow {
  position: absolute;
  width: 420px;
  height: 420px;
  border-radius: 999px;
  filter: blur(120px);
  opacity: 0.55;
}
.stage-glow-left { left: -80px; top: 80px; background: #DBEAFE; }
.stage-glow-right { right: -100px; top: 260px; background: #E0E7FF; }
.stage-topbar {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 22px;
  padding: 14px 18px;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.055);
}
.stage-title-area { display: flex; flex-direction: column; gap: 7px; min-width: 0; }
.stage-title-area h2 { margin: 0; font-size: 1.24rem; font-weight: 900; color: var(--color-text); }
.stage-title-area p { margin: 0; color: var(--color-text-muted); font-size: 0.9rem; }
.stage-route-progress { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.route-step {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--color-surface-hover);
  color: var(--color-text-faint);
  font-size: 0.72rem;
  font-weight: 800;
}
.route-step.done { background: #ECFDF5; color: #059669; }
.route-step.active { background: #EFF6FF; color: var(--color-info); box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.16); }
.route-line { width: 28px; height: 2px; border-radius: 99px; background: var(--color-border-hover); }
.route-line.done { background: #34D399; }
.route-line.active { background: linear-gradient(90deg, #34D399, var(--color-info)); }
.stage-stat-group { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.stage-stat-card {
  min-width: 92px;
  padding: 10px 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.8);
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stage-stat-card.wide { min-width: 110px; }
.stage-stat-card span { color: var(--color-text-muted); font-size: 0.72rem; font-weight: 700; }
.stage-stat-card strong { color: var(--color-text); font-size: 1.22rem; line-height: 1; font-weight: 900; }
.stage-stat-card small { color: var(--color-text-faint); font-size: 0.78rem; margin-left: 2px; }
.stage-log-btn { height: 42px; border-color: #BFDBFE !important; color: var(--color-info) !important; font-weight: 800; background: var(--color-surface) !important; }
.stage-generation-error { position: relative; z-index: 2; border-radius: 16px; }
.agent-stage-layout {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
  min-height: 0;
  flex: 1;
}
.agent-stage-canvas {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
  position: relative;
  border-radius: 28px;
  padding: 16px;
  overflow: hidden;
  min-height: 740px;
}
.stage-canvas-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
  z-index: 8;
  padding: 0 2px 8px;
}
.panel-eyebrow { display: inline-block; font-size: 0.68rem; font-weight: 900; color: var(--color-info); letter-spacing: 0.08em; text-transform: uppercase; }
.stage-canvas-header h3 { margin: 4px 0 0; font-size: 1.05rem; font-weight: 900; color: var(--color-text); }
.stage-control-pills { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.control-pill { display: inline-flex; align-items: center; gap: 7px; height: 28px; padding: 0 10px; border-radius: 999px; background: var(--color-bg); color: var(--color-text-muted); border: 1px solid var(--color-border); font-size: 0.72rem; font-weight: 800; }
.control-pill.active { background: #EFF6FF; color: var(--color-info); border-color: #BFDBFE; }
.live-dot { width: 7px; height: 7px; border-radius: 999px; background: #22C55E; box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.14); }

/* ================= 严格后面对齐的 DAG 画布样式 ================= */
.dag-flow-wrapper {
  position: relative;
  min-height: 580px;
  background: transparent;
  border-radius: 16px;
  overflow: hidden;
  padding: 18px;
  /* 科技感背景暗网格 */
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.1) 1px, transparent 1px);
  background-size: 24px 24px;
}

.execution-stage-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 16px;
  align-items: stretch;
}

.execution-rail {
  display: flex;
  align-items: center;
  gap: 18px;
  min-width: 0;
  overflow-x: auto;
  padding: 16px 4px 18px;
  scrollbar-width: thin;
}

.execution-rail > .stage-node-card,
.execution-rail > .parallel-pool-card {
  flex: 0 0 auto;
}

.stage-node-card {
  width: 238px;
}

.stage-node-card::after,
.parallel-pool-card::after {
  content: '';
  position: absolute;
  right: -18px;
  top: 50%;
  width: 18px;
  height: 2px;
  background-image: linear-gradient(90deg, #3B82F6 50%, transparent 50%);
  background-size: 12px 2px;
  animation: dagDashMove 0.7s linear infinite;
  opacity: 0.55;
}

.execution-rail > :last-child::after {
  display: none;
}

.parallel-pool-card {
  position: relative;
  width: min(520px, 46vw);
  min-width: 380px;
  border-radius: 20px;
  padding: 16px;
  background: rgba(248, 250, 252, 0.82);
  border: 1px solid rgba(191, 219, 254, 0.9);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.7), 0 16px 34px rgba(15, 23, 42, 0.055);
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.parallel-pool-card:hover,
.parallel-pool-card.is-selected {
  border-color: #93C5FD;
  box-shadow: 0 18px 36px rgba(37, 99, 235, 0.10);
  transform: translateY(-2px);
}

.pool-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.pool-header h4 {
  margin: 3px 0 0;
  color: var(--color-text);
  font-size: 1rem;
  font-weight: 900;
}

.pool-status {
  min-width: 74px;
  border-radius: 14px;
  padding: 8px 10px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  text-align: right;
}

.pool-status strong {
  display: block;
  color: var(--color-info);
  font-size: 1.1rem;
  font-weight: 950;
  line-height: 1;
}

.pool-status span {
  display: block;
  color: var(--color-text-muted);
  font-size: 0.66rem;
  font-weight: 800;
  margin-top: 3px;
}

.pool-summary {
  min-height: 20px;
  color: var(--color-text-muted);
  font-size: 0.76rem;
  font-weight: 700;
  margin-bottom: 12px;
}

.parallel-agent-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.pool-agent-card {
  width: auto;
  min-width: 0;
  border-radius: 14px;
}

.pool-agent-card .node-inner {
  padding: 11px 12px 11px 16px;
}

.pool-agent-card .node-icon {
  width: 32px;
  height: 32px;
  font-size: 1rem;
}

.pool-agent-card .node-title-group strong {
  font-size: 0.8rem;
}

.pool-agent-card .node-status-pill {
  font-size: 0.66rem;
  padding: 2px 6px;
}

.node-body.compact {
  margin-top: 8px;
}

.node-body.compact .node-message {
  height: 31px;
  font-size: 0.7rem;
}

.agent-focus-panel {
  border-radius: 22px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.07);
  min-width: 0;
}

.focus-panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}

.focus-agent-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  font-size: 1.25rem;
}

.focus-panel-header h4 {
  margin: 3px 0 0;
  color: var(--color-text);
  font-size: 1rem;
  font-weight: 950;
}

.focus-status-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 16px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
  font-weight: 900;
}

.focus-status-line.status-running {
  color: var(--color-info);
  background: #EFF6FF;
  border-color: #BFDBFE;
}

.focus-status-line.status-success {
  color: var(--color-success);
  background: #ECFDF5;
  border-color: #A7F3D0;
}

.focus-status-line.status-failed {
  color: var(--color-danger);
  background: #FEF2F2;
  border-color: #FECACA;
}

.focus-progress-track {
  height: 8px;
  border-radius: 999px;
  background: var(--color-border);
  overflow: hidden;
  margin: 14px 0;
}

.focus-progress-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #3B82F6, #10B981);
  transition: width 0.35s ease;
}

.focus-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0 0 12px;
}

.focus-metrics div {
  padding: 9px 10px;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.84);
  border: 1px solid var(--color-border);
}

.focus-metrics dt {
  color: var(--color-text-muted);
  font-size: 0.66rem;
  font-weight: 850;
}

.focus-metrics dd {
  margin: 4px 0 0;
  color: var(--color-text);
  font-size: 0.78rem;
  font-weight: 900;
}

.focus-message {
  padding: 12px;
  border-radius: 16px;
  background: var(--color-bg);
  color: var(--color-text-secondary);
  font-size: 0.78rem;
  line-height: 1.55;
  border: 1px solid var(--color-border);
}

.focus-metric-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.focus-metric-chips span {
  padding: 5px 8px;
  border-radius: 999px;
  color: var(--color-text-secondary);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  font-size: 0.68rem;
  font-weight: 800;
}

.focus-history {
  margin-top: 14px;
}

.focus-history p {
  margin: 8px 0 0;
  padding-left: 10px;
  border-left: 2px solid #BFDBFE;
  color: var(--color-text-muted);
  font-size: 0.74rem;
  line-height: 1.45;
}

.dag-flow-container {
  display: flex;
  gap: 75px; /* 每一列之间的虚线连线跨度 */
  align-items: center; /* 纵向居中对齐所有列 */
  min-width: max-content;
  height: 100%;
}

.dag-col {
  display: flex;
  flex-direction: column;
  gap: 24px; /* 同一列中并行卡片的上下间距 */
  position: relative;
  z-index: 2;
}

.dag-col-inner {
  display: flex;
  flex-direction: column;
  gap: 24px;
  position: relative;
}

/* ================= 动画过渡部分 ================= */
/* 1. 列的出场/进场动画 (横向推入) */
.dag-col-anim-enter-active,
.dag-col-anim-leave-active {
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}
.dag-col-anim-enter-from {
  opacity: 0;
  transform: translateX(40px);
}
.dag-col-anim-leave-to {
  opacity: 0;
  transform: translateX(-40px);
  position: absolute;
}

/* 2. 节点卡片的出场/进场动画 (带弹性的缩放弹出) */
.dag-node-anim-enter-active {
  transition: all 0.65s cubic-bezier(0.34, 1.56, 0.64, 1); 
}
.dag-node-anim-leave-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  position: absolute; 
}
.dag-node-anim-enter-from {
  opacity: 0;
  transform: translateY(25px) scale(0.85);
}
.dag-node-anim-leave-to {
  opacity: 0;
  transform: translateY(-20px) scale(0.9);
}

.dag-node-anim-move {
  transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

/* 3. 数据流连线的渐显动画 */
.fade-edge-enter-active {
  transition: opacity 0.5s ease 0.3s; 
}
.fade-edge-leave-active {
  transition: opacity 0.3s ease;
}
.fade-edge-enter-from, .fade-edge-leave-to {
  opacity: 0;
}

/* --- 智能体卡片核心设计 --- */
.dag-node-card {
  width: 270px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(16px);
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
  position: relative;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.dag-node-card:hover, .dag-node-card.is-selected {
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.12);
  border-color: #93C5FD;
  transform: translateY(-3px);
}

/* 侧边状态边界柱 */
.node-indicator {
  position: absolute;
  left: -1px; top: -1px; bottom: -1px; width: 4px;
  border-top-left-radius: 14px;
  border-bottom-left-radius: 14px;
  background: var(--color-border-hover); 
}
.status-success .node-indicator { background: var(--color-success); }
.status-running .node-indicator { background: #3B82F6; box-shadow: 0 0 8px rgba(59, 130, 246, 0.6); }
.status-failed .node-indicator { background: var(--color-danger); }

.node-inner { padding: 14px 16px 14px 20px; }

/* 头部排版 */
.node-head { display: flex; align-items: center; gap: 12px; }
.node-icon {
  width: 38px; height: 38px; border-radius: 10px;
  background: var(--color-surface-hover); color: var(--color-text-muted);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.15rem; border: 1px solid rgba(0,0,0,0.03);
}
.status-success .node-icon { background: #D1FAE5; color: var(--color-success); }
.status-running .node-icon { background: #DBEAFE; color: #3B82F6; }
.status-failed .node-icon { background: #FEE2E2; color: var(--color-danger); }

.node-title-group { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.node-title-group strong { color: var(--color-text); font-size: 0.92rem; font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.node-title-group .node-sub { color: var(--color-text-faint); font-size: 0.72rem; }

.node-status-pill {
  font-family: var(--font-mono, monospace);
  font-size: 0.72rem; font-weight: 800;
  background: var(--color-bg); padding: 3px 8px; border-radius: 6px;
  color: var(--color-text-muted);
}
.status-running .node-status-pill { background: #EFF6FF; color: var(--color-info); }
.status-success .node-status-pill { background: #ECFDF5; color: var(--color-success); }

.node-divider { margin: 12px 0; border-top: 1px dashed var(--color-border); }

/* 底部状态消息区 */
.meta-row { display: flex; justify-content: space-between; margin-bottom: 6px; }
.meta-label { font-size: 0.75rem; font-weight: 700; color: #3B82F6; }
.status-waiting .meta-label { color: var(--color-text-faint); }
.status-success .meta-label { color: var(--color-success); }
.meta-time { font-size: 0.75rem; color: var(--color-text-faint); font-family: var(--font-mono, monospace); }

.node-message {
  margin: 0; font-size: 0.78rem; color: var(--color-text-secondary);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; height: 34px; line-height: 1.45;
}
.status-running .node-message { color: var(--color-text-strong); }
.node-message.is-error { color: var(--color-danger); font-weight: 600; }

/* --- 核心动画：数据流转虚线 --- */
.dag-edge-out {
  position: absolute;
  right: -75px; /* 完全跨越 gap */
  top: 50%;
  width: 75px;
  height: 2px;
  background-image: linear-gradient(90deg, #3B82F6 50%, transparent 50%);
  background-size: 12px 2px;
  z-index: -1;
  opacity: 0.7;
  animation: dagDashMove 0.7s linear infinite;
}
/* 等待态：虚线静止并变灰 */
.status-waiting .dag-edge-out { background-image: linear-gradient(90deg, var(--color-border-hover) 50%, transparent 50%); animation: none; }
/* 成功态：虚线静止并变绿 */
.status-success .dag-edge-out { background-image: linear-gradient(90deg, var(--color-success) 50%, transparent 50%); animation: none; }
/* 失败态：虚线静止并变红 */
.status-failed .dag-edge-out { background-image: linear-gradient(90deg, var(--color-danger) 50%, transparent 50%); animation: none; }

@keyframes dagDashMove {
  from { background-position: 0 0; }
  to { background-position: 24px 0; } 
}


/* ================= Output Dock ================= */
.output-dock-section {
  position: relative;
  z-index: 4;
  flex-shrink: 0;
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);
  gap: 16px;
  align-items: center;
  min-height: 56px;
  padding: 8px 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}
.output-dock-heading { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.output-dock-heading > div { display: flex; flex-direction: column; gap: 4px; }
.output-dock-heading strong { color: var(--color-text); font-size: 0.98rem; font-weight: 900; line-height: 1.2; }
.output-dock-heading p { margin: 0; color: var(--color-text-muted); font-size: 0.74rem; line-height: 1.5; }
.output-dock-list { display: grid; grid-template-columns: repeat(6, minmax(130px, 1fr)); gap: 10px; min-width: 0; }
.output-dock-item { display: flex; gap: 8px; align-items: center; padding: 8px 10px; border: 1px solid var(--color-border); border-radius: 16px; background: var(--color-bg); opacity: 0.72; transition: opacity 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease; cursor: default; }
.output-dock-item.ready { opacity: 1; background: #F0FDF4; border-color: #A7F3D0; cursor: pointer; }
.output-dock-item.ready:hover { transform: translateY(-2px); box-shadow: 0 14px 28px rgba(16, 185, 129, 0.10); }
.output-dock-item > span { width: 26px; height: 26px; border-radius: 8px; background: var(--color-surface); display: grid; place-items: center; flex-shrink: 0; font-size: 0.9rem; }
.output-dock-item strong { display: block; color: var(--color-text); font-size: 0.72rem; font-weight: 900; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.output-dock-item p { margin: 1px 0 0; color: var(--color-text-muted); font-size: 0.65rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.output-dock-empty { min-height: 40px; display: flex; align-items: center; justify-content: center; border: 1px dashed var(--color-border-hover); border-radius: 12px; color: var(--color-text-muted); background: var(--color-bg); font-size: 0.78rem; font-weight: 800; }

.workflow-log-drawer :deep(.el-drawer__header) { margin-bottom: 0; padding: 20px 22px; border-bottom: 1px solid var(--color-border); font-weight: 900; color: var(--color-text); }
.drawer-log-list { display: flex; flex-direction: column; gap: 14px; padding: 4px; }
.drawer-log-item { display: flex; gap: 12px; align-items: flex-start; padding: 12px; border-radius: 16px; background: var(--color-bg); border: 1px solid var(--color-border); }
.drawer-log-dot { width: 10px; height: 10px; border-radius: 999px; background: var(--color-border-hover); margin-top: 5px; flex-shrink: 0; }
.drawer-log-item.is-running .drawer-log-dot { background: #F97316; box-shadow: 0 0 0 5px rgba(249, 115, 22, 0.12); }
.drawer-log-item.is-success .drawer-log-dot { background: var(--color-success); }
.drawer-log-item.is-failed .drawer-log-dot { background: var(--color-danger); }
.drawer-log-item strong { color: var(--color-text); font-size: 0.86rem; font-weight: 900; }
.drawer-log-item p { margin: 4px 0 0; color: var(--color-text-muted); font-size: 0.78rem; line-height: 1.45; }


/* ================= Phase 4: 交付中心看板 (Bento Layout) ================= */
.results-view { background: transparent; overflow-y: auto; padding-bottom: 80px; position: relative; }
.result-hero-compact { display: flex; justify-content: space-between; align-items: center; padding: var(--space-4) var(--space-8); background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.8); margin-bottom: var(--space-6); border-radius: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); position: sticky; top: 0; z-index: 100; }
.hero-content-left { display: flex; flex-direction: column; gap: var(--space-1); }
.hero-status-tag-mini { display: inline-flex; align-items: center; gap: var(--space-1); color: var(--color-success); font-size: 0.75rem; font-weight: var(--weight-extrabold); }
.hero-title-compact { margin: 0; font-size: 1.25rem; font-weight: var(--weight-extrabold); color: var(--color-text-strong); }
.hero-subtitle-compact { margin: 0; font-size: 0.85rem; color: var(--color-text-muted); }
.hero-actions-right { display: flex; gap: var(--space-3); align-items: center; }
.results-body-bento { max-width: 1440px; margin: 0 auto; padding: var(--space-10) 60px; display: flex; flex-direction: column; gap: var(--space-10); position: relative; z-index: 1; }
.premium-resource-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; align-items: stretch; }
.premium-res-card { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.8); border-radius: 16px; padding: 24px; display: flex; flex-direction: column; gap: 20px; position: relative; overflow: hidden; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03); cursor: pointer; animation: fadeSlideUp 0.6s ease-out backwards; }
@keyframes fadeSlideUp { 0% { opacity: 0; transform: translateY(20px); } 100% { opacity: 1; transform: translateY(0); } }
.premium-res-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.06); border-color: #D1D5DB; }
.premium-res-card:focus-visible { outline: 2px solid var(--color-info); outline-offset: 2px; }
.card-bg-glow { display: none; }

.premium-res-card .card-header, .premium-res-card .card-body, .premium-res-card .card-footer { position: relative; z-index: 1; }
.premium-res-card .type-icon-box { width: 48px; height: 48px; border-radius: var(--radius-lg); display: flex; align-items: center; justify-content: center; font-size: 1.5rem; background: rgba(15, 23, 42, 0.03); border: 1px solid rgba(15, 23, 42, 0.04); }
.premium-res-card.tone-blue .type-icon-box { color: var(--color-info); }
.premium-res-card.tone-purple .type-icon-box { color: #7C3AED; }
.premium-res-card.tone-rose .type-icon-box { color: #E11D48; }
.premium-res-card.tone-emerald .type-icon-box { color: var(--tone-emerald); }
.premium-res-card.tone-indigo .type-icon-box { color: var(--color-primary); }
.premium-res-card.tone-pink .type-icon-box { color: #DB2777; }

.premium-res-card .card-title { margin: 0; font-size: 1.15rem; font-weight: var(--weight-extrabold); color: var(--color-text); line-height: 1.45; text-wrap: balance; white-space: pre-line; display: -webkit-box; -webkit-line-clamp: 3; line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere; }
.premium-res-card .card-summary { margin: 0; font-size: 0.95rem; color: var(--color-text-secondary); line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.card-metrics-modern { display: flex; gap: var(--space-3); margin-top: auto; padding-top: var(--space-3); }
.metric-badge { display: inline-flex; align-items: center; gap: var(--space-1); background: var(--color-bg); color: var(--color-text-secondary); padding: var(--space-1) var(--space-3); border: 1px solid rgba(15, 23, 42, 0.04); border-radius: var(--radius-md); font-size: 0.8rem; font-weight: var(--weight-bold); }
.premium-res-card .card-footer { border-top: 1px solid rgba(226, 232, 240, 0.6); padding-top: var(--space-5); margin-top: var(--space-1); display: flex; justify-content: space-between; align-items: center; }
.modern-text-btn { background: transparent; border: none; color: var(--color-text); font-weight: var(--weight-extrabold); font-size: 0.95rem; padding: 0; cursor: pointer; display: flex; align-items: center; gap: var(--space-2); transition: color var(--transition-base); pointer-events: none; tabindex: -1; }
.modern-text-btn span { transition: transform var(--transition-slow); }
.premium-res-card:hover .modern-text-btn { color: var(--color-info); }
.premium-res-card:hover .modern-text-btn span { transform: translateX(4px); }

/* ================= 媒体查询与响应式适配 ================= */
@media (max-width: 1440px) {
  .output-dock-section { grid-template-columns: 1fr; gap: 10px; min-height: 0; }
  .output-dock-heading { flex-direction: row; align-items: center; justify-content: space-between; gap: 12px; }
  .output-dock-heading p { max-width: 360px; text-align: right; }
  .output-dock-section .output-dock-list { grid-template-columns: repeat(3, minmax(150px, 1fr)); }
}
@media (max-width: 1200px) {
  .agent-configs-grid { grid-template-columns: repeat(2, 1fr); }
  .premium-resource-grid { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
  .results-body-bento { padding: var(--space-6) var(--space-8); }
  .execution-stage-grid { grid-template-columns: 1fr; }
  .agent-focus-panel { order: 2; }
  .parallel-pool-card { width: min(560px, 58vw); }
}
@media (max-width: 900px) {
  .workflow-stage-page { overflow: auto; }
  .stage-topbar { flex-direction: column; align-items: stretch; }
  .stage-stat-group { flex-wrap: wrap; }
  .agent-stage-canvas { min-height: 0; }
  .dag-flow-wrapper { overflow: visible; }
  .execution-rail {
    flex-direction: column;
    align-items: stretch;
    overflow: visible;
    padding: 10px 0;
  }
  .stage-node-card,
  .parallel-pool-card {
    width: 100%;
    min-width: 0;
  }
  .stage-node-card::after,
  .parallel-pool-card::after {
    right: auto;
    left: 28px;
    top: auto;
    bottom: -18px;
    width: 2px;
    height: 18px;
    background-image: linear-gradient(180deg, #3B82F6 50%, transparent 50%);
    background-size: 2px 12px;
  }
  .parallel-agent-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .output-dock-heading { flex-direction: column; align-items: flex-start; }
  .output-dock-heading p { text-align: left; max-width: none; }
  .output-dock-section .output-dock-list { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .elegant-generator-layout { height: auto; min-height: calc(100vh - 64px); }
  .phase-view { position: relative; min-height: calc(100vh - 64px); }
  .agent-configs-grid { grid-template-columns: 1fr; }
  .scenario-selector-v2 { grid-template-columns: 1fr; }
  .results-body-bento { padding: var(--space-4); }
  .premium-resource-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .premium-res-card { grid-column: span 1 !important; }
  .parallel-agent-grid { grid-template-columns: 1fr; }
  .focus-metrics { grid-template-columns: 1fr; }
}
@media (max-width: 520px) {
  .premium-resource-grid { grid-template-columns: 1fr; }
  .premium-res-card { grid-column: span 1 !important; }
}

/* Element Plus 弹窗深度订制 */
.elegant-dialog :deep(.el-dialog) { 
  border-radius: var(--radius-2xl); 
  overflow: hidden; 
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.08);
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.5);
}
.elegant-dialog :deep(.el-dialog__header) { padding: var(--space-6) var(--space-8) var(--space-5); margin-right: 0; border-bottom: 1px solid rgba(0, 0, 0, 0.05); }
.elegant-dialog :deep(.el-dialog__title) { font-weight: var(--weight-extrabold); font-size: 1.2rem; color: var(--color-text); }
.elegant-dialog :deep(.el-dialog__body) { padding: var(--space-8); background: transparent; }

/* 彻底解决三层嵌套问题：在弹窗内部署的资源卡片必须完全融入，去除独立边框与背景 */
.elegant-dialog :deep(.resource-card-wrapper) {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  border-radius: 0 !important;
}
.elegant-dialog :deep(.resource-card-wrapper:hover) {
  background: transparent !important;
  box-shadow: none !important;
  border: none !important;
}

/* PPT 预览弹窗专属沉浸式样式 */
.is-ppt-dialog :deep(.el-dialog__body) { padding: 0 !important; background: transparent !important; }
.preview-dialog-body.is-ppt-preview { padding: 0 !important; background: transparent !important; border: none !important; box-shadow: none !important; }
.preview-dialog-body.is-ppt-preview :deep(.player-wrapper) { margin-top: 0 !important; border: none !important; border-radius: 0 !important; }

h1, h2, h3, h4, .cc-title { letter-spacing: -0.025em; color: var(--color-text); font-weight: var(--weight-bold); }
p, .card-summary, .s-desc { line-height: 1.65; letter-spacing: 0.01em; color: var(--color-text-secondary); }

</style>
