<template>
  <div class="elegant-generator-layout">
    <transition name="page-slide" mode="out-in">

      <div v-if="currentPhase === 'input'" class="phase-view omni-input-view" key="input">
        <!-- Soft Ambient Background (Not Flashy, Just Rich) -->
        <div class="omni-ambient-bg">
          <div class="ambient-glow glow-blue"></div>
          <div class="ambient-glow glow-indigo"></div>
          <div class="omni-pattern-bg"></div>
        </div>
        
        <div class="omni-container">
          <!-- Hero Header -->
          <div class="omni-hero-header">
            <h1 class="hero-title">AI 学习资源引擎</h1>
            <p class="hero-subtitle">输入你的学习目标，自动构建专属的知识图谱、测试与课件</p>
          </div>

          <!-- Spotlight Input Box -->
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
                  @click="goToPersonalize"
              >
                <el-icon><Top /></el-icon>
              </button>
            </div>
          </div>

          <!-- Rich Inspiration Grid -->
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
        <!-- Soft Ambient Background (Consistent with Phase 1) -->
        <div class="omni-ambient-bg">
          <div class="ambient-glow glow-blue"></div>
          <div class="ambient-glow glow-indigo"></div>
          <div class="omni-pattern-bg"></div>
        </div>
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
        <div class="stage-background-layer">
          <div class="stage-grid-bg"></div>
          <div class="stage-glow stage-glow-left"></div>
          <div class="stage-glow stage-glow-right"></div>
        </div>

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
                <h3>Plan 调度 Agent 执行全过程</h3>
              </div>
              <div class="stage-control-pills">
                <span class="control-pill active"><span class="live-dot"></span> 实时运行</span>
                <span class="control-pill">任务卡飞行动画</span>
                <span class="control-pill">结果回流</span>
              </div>
            </div>

            <div class="dispatch-stage">
              <div class="stage-orbit-ring ring-one"></div>
              <div class="stage-orbit-ring ring-two"></div>

              <div class="master-hub" :class="[`is-${dagNodeStates.planning?.status || 'waiting'}`]" @click="selectedDagNodeId = 'planning'">
                <div class="master-core">
                  <span class="master-icon">🎯</span>
                  <div class="master-pulse"></div>
                </div>
                <div class="master-info">
                  <span class="hub-kicker">MasterAgent / Plan</span>
                  <h4>调度中心</h4>
                  <p>{{ dagNodeStates.planning?.currentMessage || '解析需求、生成计划、分配任务' }}</p>
                </div>
                <div class="master-progress-line">
                  <span :style="{ width: `${dagNodeStates.planning?.progress || 0}%` }"></span>
                </div>
              </div>

              <div class="plan-card-stack">
                <div
                    v-for="(plan, index) in currentPlanSteps"
                    :key="plan.id"
                    class="plan-mini-card"
                    :style="{ animationDelay: `${index * 0.12}s` }"
                >
                  <span>{{ index + 1 }}</span>
                  <strong>{{ plan.title }}</strong>
                </div>
              </div>

              <article
                  v-for="node in stageAgentNodes"
                  :key="node.id"
                  class="agent-workstation"
                  :class="[`station-${node.id}`, `is-${node.status}`, { 'is-selected': selectedDagNodeId === node.id }]"
                  @click="selectedDagNodeId = node.id"
              >
                <div class="workstation-head">
                  <span class="workstation-icon">{{ node.icon }}</span>
                  <div class="workstation-title">
                    <strong>{{ node.label }}</strong>
                    <span>{{ getStatusText(node.status) }}</span>
                  </div>
                  <span class="workstation-status-dot"></span>
                </div>
                <div class="workstation-message-wrap">
                  <p v-if="node.status === 'failed'" class="error-text">哎呀，这部分大模型开小差了~</p>
                  <p v-else :key="node.currentMessage" class="typewriter-text">{{ node.currentMessage || getNodeFallbackMessage(node) }}</p>
                </div>
                <div class="workstation-progress" v-if="node.status !== 'failed'">
                  <span :style="{ width: `${node.progress}%` }"></span>
                </div>
                <div class="workstation-actions" v-if="node.status === 'failed'">
                  <button class="retry-btn" @click.stop="retryAgent(node.id)">
                    <el-icon><RefreshLeft /></el-icon> 重新为您准备
                  </button>
                </div>
                <div class="workstation-meta" v-else>
                  <span>{{ getAgentOutputFormat(node.id) }}</span>
                  <strong>{{ node.progress }}%</strong>
                </div>
              </article>

              <div class="dispatch-packets" aria-hidden="true">
                <span
                    v-for="node in stageAgentNodes"
                    :key="`packet-${node.id}`"
                    class="dispatch-packet"
                    :class="[`packet-${node.id}`, { active: isDispatchPacketActive(node.id) }]"
                >
                  <i></i>{{ getAgentShortName(node.id) }}任务
                </span>
              </div>

              <div class="review-assembly-lane">
                <article class="review-node lane-node" :class="`is-${dagNodeStates.review?.status || 'waiting'}`" @click="selectedDagNodeId = 'review'">
                  <span class="lane-icon">🔍</span>
                  <div class="lane-node-content">
                    <strong>质量把关助手</strong>
                    <div class="reviewer-checklist" v-if="dagNodeStates.review?.status === 'running'">
                       <div class="check-item" :class="{ 'passed': dagNodeStates.review.progress > 20 }">
                         <span class="check-box"><el-icon v-if="dagNodeStates.review.progress > 20"><Check /></el-icon></span> 知识点不超纲
                       </div>
                       <div class="check-item" :class="{ 'passed': dagNodeStates.review.progress > 60 }">
                         <span class="check-box"><el-icon v-if="dagNodeStates.review.progress > 60"><Check /></el-icon></span> 内容准确无误
                       </div>
                       <div class="check-item" :class="{ 'passed': dagNodeStates.review.progress > 90 }">
                         <span class="check-box"><el-icon v-if="dagNodeStates.review.progress > 90"><Check /></el-icon></span> 难度适中匹配
                       </div>
                       <div class="scanner-line"></div>
                    </div>
                    <p v-else>{{ dagNodeStates.review?.currentMessage || '等待资源生成后进行内容准确性与难度审核' }}</p>
                  </div>
                  <em>{{ dagNodeStates.review?.progress || 0 }}%</em>
                </article>
                <div class="lane-arrow"></div>
                <article class="bundle-node lane-node" :class="`is-${dagNodeStates.bundle?.status || 'waiting'}`" @click="selectedDagNodeId = 'bundle'">
                  <span class="lane-icon">📦</span>
                  <div class="lane-node-content">
                    <strong>资源打包助手</strong>
                    <p>{{ dagNodeStates.bundle?.currentMessage || '整理各类学习资料，为您生成最终专属学习包' }}</p>
                  </div>
                  <em>{{ dagNodeStates.bundle?.progress || 0 }}%</em>
                </article>
              </div>

              <div class="returning-resources" aria-hidden="true">
                <span
                    v-for="resource in sortedGeneratedResources.slice(0, 6)"
                    :key="`return-${resource.id || resource.type}`"
                    class="return-resource-card"
                    :class="`return-${resource.type}`"
                >
                  {{ getDagNodeIcon(resource.type) }} {{ getResourceTypeLabel(resource.type) }}
                </span>
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
                v-for="agentId in dagSelectedAgentIds"
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

    <el-dialog v-model="previewVisible" :title="previewData?.title || '资源预览'" width="78%" top="6vh" destroy-on-close :class="['elegant-dialog', { 'is-ppt-dialog': previewData?.agentId === 'ppt' }]">
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
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowRight, Cpu,
  CircleCheckFilled, RefreshLeft, Position,
  Document, Share, Edit, Collection,
  Clock, Odometer, DataBoard, Top, StarFilled, Check
} from '@element-plus/icons-vue'

import MindmapView from '@/components/resource/MindmapView.vue'
import MarkdownView from '@/components/resource/MarkdownView.vue'
import QuizView from '@/components/resource/QuizView.vue'
import CodeView from '@/components/resource/CodeView.vue'
import ReadingView from '@/components/resource/ReadingView.vue'
import PptView from '@/components/resource/PptView.vue'

import {
  startResourceGeneration,
  pollResourceStatus,
  getResourceBundle,
  streamResourceEvents,
  type LearningScenario,
  type ResourceAgentId,
  type ResourceTaskStatus,
} from '@/api/resource'

defineOptions({ name: 'ResourceGenerator' })

const route = useRoute()

type GeneratedResourceItem = Record<string, any> & {
  generatedAt?: string
  displayOrder?: number
}

// ===================== 场景默认参数字典 =====================
type QuizQuestionType = 'single' | 'multiple' | 'judge' | 'fill'
type AnyAgentConfigs = {
  content: { structure: string; include_common_mistakes: boolean; include_examples: boolean; focus_mode: string; depth_level: string }
  mindmap: { map_type: string; max_depth: number; highlight_weak: boolean; expand_weak_points: boolean; include_prerequisites: boolean }
  quiz: { question_count: number; difficulty_mode: string; weak_point_weight: number; exam_style: string; include_analysis: boolean; question_types?: QuizQuestionType[] }
  code: { programming_language: string; case_type: string; comment_level: string; include_test: boolean; difficulty: string }
  reading: { reading_depth: string; max_items: number; resource_quality: string; include_practice: boolean; language_preference: string }
  ppt: { template_id: string; page_count: number; difficulty: string; output_format: string }
}

const SCENARIO_DEFAULTS: Record<string, Partial<AnyAgentConfigs>> = {
  exam_prep: { content: { structure: 'exam_points', include_common_mistakes: true, include_examples: true, focus_mode: 'weak_points', depth_level: 'standard' }, quiz: { question_count: 5, difficulty_mode: 'exam', weak_point_weight: 70, exam_style: '考研', include_analysis: true }, mindmap: { map_type: 'exam_map', max_depth: 3, highlight_weak: true, expand_weak_points: true, include_prerequisites: false }, code: { programming_language: 'python', case_type: 'algorithm_template', comment_level: 'standard', include_test: false, difficulty: 'intermediate' }, reading: { reading_depth: 'course_extended', max_items: 3, resource_quality: 'classic', include_practice: false, language_preference: 'chinese' }, ppt: { template_id: 'theme-logic-blue', page_count: 8, difficulty: 'advanced', output_format: 'preview' } },
  daily_review: { content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'weak_points', depth_level: 'quick' }, quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 50, exam_style: 'school', include_analysis: true }, mindmap: { map_type: 'knowledge_tree', max_depth: 3, highlight_weak: true, expand_weak_points: true, include_prerequisites: false }, code: { programming_language: 'python', case_type: 'basic_demo', comment_level: 'standard', include_test: false, difficulty: 'beginner' }, reading: { reading_depth: 'course_extended', max_items: 3, resource_quality: 'balanced', include_practice: false, language_preference: 'chinese' }, ppt: { template_id: 'theme-logic-blue', page_count: 5, difficulty: 'intermediate', output_format: 'preview' } },
  project_practice: { content: { structure: 'case_driven', include_common_mistakes: true, include_examples: true, focus_mode: 'full_coverage', depth_level: 'deep' }, quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 30, exam_style: 'school', include_analysis: true }, mindmap: { map_type: 'knowledge_tree', max_depth: 4, highlight_weak: false, expand_weak_points: false, include_prerequisites: true }, code: { programming_language: 'python', case_type: 'basic_demo', comment_level: 'standard', include_test: true, difficulty: 'intermediate' }, reading: { reading_depth: 'engineering', max_items: 5, resource_quality: 'latest', include_practice: true, language_preference: 'chinese' }, ppt: { template_id: 'theme-logic-blue', page_count: 10, difficulty: 'intermediate', output_format: 'preview' } },
  self_study: { content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'key_concepts', depth_level: 'deep' }, quiz: { question_count: 5, difficulty_mode: 'basic', weak_point_weight: 40, exam_style: 'school', include_analysis: true }, mindmap: { map_type: 'knowledge_tree', max_depth: 4, highlight_weak: false, expand_weak_points: false, include_prerequisites: true }, code: { programming_language: 'python', case_type: 'basic_demo', comment_level: 'verbose', include_test: false, difficulty: 'beginner' }, reading: { reading_depth: 'course_extended', max_items: 3, resource_quality: 'balanced', include_practice: false, language_preference: 'chinese' }, ppt: { template_id: 'theme-logic-blue', page_count: 6, difficulty: 'beginner', output_format: 'preview' } },
}

// ===================== 核心状态管理 =====================
type Phase = 'input' | 'personalize' | 'generating' | 'result'
const currentPhase = ref<Phase>('input')

const naturalInput = ref('')
const isInputFocused = ref(false)
const learningScenario = ref<LearningScenario>('daily_review')

const scenarioOptions: Array<{ icon: string; name: string; value: LearningScenario }> = [
  { icon: '备', name: '考试备考', value: 'exam_prep' },
  { icon: '学', name: '日常学习', value: 'daily_review' },
  { icon: '践', name: '项目实践', value: 'project_practice' },
  { icon: '预', name: '预习自学', value: 'self_study' }
]



const agentMetaList = [
  { id: 'master', name: '规划中枢', icon: Cpu, colorClass: 'text-blue' },
  { id: 'reviewer', name: '质量把关助手', icon: CircleCheckFilled, colorClass: 'text-emerald' },
  { id: 'assembler', name: '资源打包助手', icon: Position, colorClass: 'text-indigo' },
  { id: 'content', name: '讲义生成助手', icon: Document, colorClass: 'text-blue' },
  { id: 'mindmap', name: '导图绘制助手', icon: Share, colorClass: 'text-purple' },
  { id: 'code', name: '实战演练助手', icon: Cpu, colorClass: 'text-red' },
  { id: 'quiz', name: '自测题生成助手', icon: Edit, colorClass: 'text-emerald' },
  { id: 'reading', name: '拓展阅读助手', icon: Collection, colorClass: 'text-indigo' },
  { id: 'ppt', name: '演示文稿助手', icon: DataBoard, colorClass: 'text-pink' },
]

const getAgentMeta = (id: string) => agentMetaList.find(a => a.id === id) || { name: id, icon: Document, colorClass: 'text-blue' }
const enabledAgentIds = ref<ResourceAgentId[]>(['content', 'mindmap', 'code', 'quiz', 'reading', 'ppt'])

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

// ===================== 参数表单状态 =====================
const agentConfigs = reactive({
  content: { structure: 'progressive' as const, include_common_mistakes: true, include_examples: true, focus_mode: 'full_coverage' as const, depth_level: 'standard' as const },
  mindmap: { map_type: 'knowledge_tree' as const, max_depth: 3, highlight_weak: true, expand_weak_points: false, include_prerequisites: false },
  quiz: { question_count: 5, difficulty_mode: 'adaptive' as const, weak_point_weight: 50, exam_style: 'school' as const, include_analysis: true, question_types: ['single', 'multiple', 'judge'] as QuizQuestionType[] },
  code: { programming_language: 'python' as const, case_type: 'basic_demo' as const, comment_level: 'standard' as const, include_test: false, difficulty: 'beginner' as const },
  reading: { reading_depth: 'course_extended' as const, max_items: 3, resource_quality: 'balanced' as const, include_practice: false, language_preference: 'chinese' as const },
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

const selectScenario = (scenario: LearningScenario) => {
  learningScenario.value = scenario
  applyScenarioDefaults(scenario)
}

const goToPersonalize = () => {
  if (!naturalInput.value.trim()) return
  currentPhase.value = 'personalize'
}

// ===================== 异步工作流大盘画布引擎 =====================
const generatedResources = ref<GeneratedResourceItem[]>([])
const finalBundle = ref<any | null>(null)
const isGenerating = ref(false)
const generationError = ref<string | null>(null)
const resultWarning = ref('')
const overallProgress = ref(0)
const latestWorkflowMessage = ref('')
const pollingInterval = ref<ReturnType<typeof setInterval> | null>(null)
const resourceStreamController = ref<AbortController | null>(null)
const generationFinalized = ref(false)

const RESOURCE_TYPE_ORDER = ['content', 'mindmap', 'code', 'quiz', 'reading', 'ppt']

const AGENT_DISPLAY: Record<string, { label: string; icon: string }> = {
  planning: { label: '规划任务', icon: '🎯' },
  content: { label: '讲义生成助手', icon: '📝' },
  mindmap: { label: '导图绘制助手', icon: '🧠' },
  quiz: { label: '自测题生成助手', icon: '📋' },
  code: { label: '实战演练助手', icon: '💻' },
  reading: { label: '拓展阅读助手', icon: '📚' },
  ppt: { label: '演示文稿助手', icon: '📊' },
  review: { label: '质量把关助手', icon: '🔍' },
  bundle: { label: '资源打包助手', icon: '📦' },
}

interface DagNodeState {
  id: string
  label: string
  icon: string
  status: 'waiting' | 'running' | 'success' | 'failed' | 'skipped'
  progress: number
  currentMessage: string
  stepHistory: string[]
  isSystem: boolean
}

const dagNodeStates = ref<Record<string, DagNodeState>>({})
const selectedDagNodeId = ref('planning')

const dagSelectedAgentIds = computed(() => {
  return enabledAgentIds.value.filter(id => !['master', 'reviewer', 'assembler'].includes(id))
})

const dagNodesV2 = computed<DagNodeState[]>(() => {
  const selected = dagSelectedAgentIds.value
  const nodes: DagNodeState[] = []

  // 1. 顶层规划节点
  nodes.push(dagNodeStates.value['planning'] || {
    id: 'planning', label: '规划任务', icon: '🎯',
    status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: true,
  })

  // 2. 选中的业务子智能体群组
  for (const agentId of selected) {
    const display = AGENT_DISPLAY[agentId]
    if (!display) continue
    nodes.push(dagNodeStates.value[agentId] || {
      id: agentId, label: display.label, icon: display.icon,
      status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: false,
    })
  }

  // 3. 质量审查节点
  nodes.push(dagNodeStates.value['review'] || {
    id: 'review', label: '质量审查', icon: '🔍',
    status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: true,
  })

  // 4. 打包输出节点
  nodes.push(dagNodeStates.value['bundle'] || {
    id: 'bundle', label: '资源组装', icon: '📦',
    status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: true,
  })

  return nodes
})



// const dagCanvasWidthV2 = 1160
// const dagCanvasHeightV2 = 620
// const dagLayerY: [number, number, number, number, number] = [72, 212, 332, 486, 560]

// const dagNodePositionsV2 = computed<Record<string, { x: number; y: number }>>(() => {
//   const positions: Record<string, { x: number; y: number }> = {}
//   const selected = dagSelectedAgentIds.value
//   const cx = dagCanvasWidthV2 / 2

//   positions['planning'] = { x: cx, y: dagLayerY[0] }

//   if (selected.length > 0) {
//     const firstRowCount = selected.length <= 3 ? selected.length : Math.ceil(selected.length / 2)
//     const secondRowCount = Math.max(0, selected.length - firstRowCount)
//     const firstRow = selected.slice(0, firstRowCount)
//     const secondRow = selected.slice(firstRowCount)

//     const placeRow = (row: string[], y: number) => {
//       const rowWidth = row.length <= 1 ? 0 : Math.min(820, (row.length - 1) * 285)
//       const startX = cx - rowWidth / 2
//       row.forEach((id, i) => {
//         positions[id] = { x: row.length === 1 ? cx : startX + i * (rowWidth / (row.length - 1)), y }
//       })
//     }

//     placeRow(firstRow, dagLayerY[1])
//     if (secondRowCount > 0) placeRow(secondRow, dagLayerY[2])
//   }

//   positions['review'] = { x: cx, y: dagLayerY[3] }
//   positions['bundle'] = { x: cx, y: dagLayerY[4] }

//   return positions
// })


const dagHeroMessage = computed(() => {
  const running = Object.values(dagNodeStates.value).find(n => n.status === 'running')
  if (running) return running.currentMessage || `${running.label}处理中...`
  const allDone = Object.values(dagNodeStates.value).every(n => n.status === 'success')
  if (allDone) return '所有资源生成完成'
  return latestWorkflowMessage.value || '多智能体协同生成中'
})


function getStatusText(status: DagNodeState['status']) {
  const statusMap: Record<DagNodeState['status'], string> = {
    waiting: '等待中',
    running: '运行中',
    success: '已完成',
    failed: '失败',
    skipped: '已跳过',
  }
  return statusMap[status]
}

function getNodeFallbackMessage(node: DagNodeState) {
  if (node.status === 'waiting') return '等待 MasterAgent 调度'
  if (node.status === 'success') return '该节点已完成处理'
  if (node.status === 'failed') return '该节点执行失败，请查看日志'
  if (node.status === 'skipped') return '本次任务未启用该节点'
  return '正在处理任务'
}

function getDagNodeIcon(type: string): string {
  return AGENT_DISPLAY[type]?.icon || '📄'
}

const workflowLogDrawerVisible = ref(false)

const stageAgentNodes = computed(() => {
  return dagSelectedAgentIds.value
    .map(id => dagNodeStates.value[id] || createDagNode(id, false))
    .filter(Boolean)
})

const runningAgentCount = computed(() => {
  return stageAgentNodes.value.filter(node => node.status === 'running').length
})

const currentPlanSteps = computed(() => {
  return dagSelectedAgentIds.value.map((id) => ({
    id,
    title: `${AGENT_DISPLAY[id]?.label || getResourceTypeLabel(id)}任务`,
  }))
})

const workflowLogItems = computed(() => {
  const items: Array<{ id: string; title: string; message: string; status: DagNodeState['status'] }> = []
  dagNodesV2.value.forEach((node) => {
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

function getAgentShortName(agentId: string) {
  const shortMap: Record<string, string> = {
    content: '讲解',
    mindmap: '导图',
    code: '代码',
    quiz: '题库',
    reading: '阅读',
    ppt: 'PPT',
  }
  return shortMap[agentId] || getResourceTypeLabel(agentId)
}

function getAgentOutputFormat(agentId: string) {
  const formatMap: Record<string, string> = {
    content: 'Markdown 讲解',
    mindmap: '知识结构图',
    code: 'Code 示例',
    quiz: 'Quiz 题库',
    reading: 'Reading List',
    ppt: 'PPT 页面',
  }
  return formatMap[agentId] || '学习资源'
}

function isDispatchPacketActive(agentId: string) {
  const planStatus = dagNodeStates.value.planning?.status
  const agentStatus = dagNodeStates.value[agentId]?.status
  return planStatus === 'success' && ['waiting', 'running', 'success'].includes(agentStatus || 'waiting')
}

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

const getResourceTypeLabel = (type: string) => {
  const labelMap: Record<string, string> = {
    content: '专业讲解',
    mindmap: '知识导图',
    code: '代码案例',
    quiz: '自测题',
    reading: '拓展阅读',
    ppt: '演示文稿',
    reviewer: '质量审查',
  }
  return labelMap[type] || getAgentMeta(type).name || type
}

const getResourceUsageHint = (type: string) => {
  const hintMap: Record<string, string> = {
    content: '先阅读讲解，建立基础概念和关键术语理解。',
    mindmap: '用于梳理知识层级、概念关系和复习框架。',
    code: '通过代码案例把知识点落到实践，适合边运行边理解。',
    quiz: '完成自测题，检查掌握情况并定位仍然薄弱的知识点。',
    reading: '用于课后拓展和深入理解，适合完成基础资源后阅读。',
    ppt: '精美的自动生成幻灯片，可用于直接演示或快速概览。',
  }
  return hintMap[type] || '建议结合本次学习目标使用该资源。'
}

const getDefaultResourceFormat = (type: string) => {
  const formatMap: Record<string, string> = {
    content: 'Markdown',
    mindmap: 'Markdown / Tree',
    code: 'Code',
    quiz: 'Quiz JSON',
    reading: 'Reading List',
    ppt: 'PPT JSON',
  }
  return formatMap[type] || 'Resource'
}

const getEstimatedTime = (type: string) => {
  const timeMap: Record<string, string> = {
    content: '10-15 分钟',
    mindmap: '5-8 分钟',
    code: '15-25 分钟',
    quiz: '10-20 分钟',
    reading: '20-30 分钟',
    ppt: '5-10 分钟',
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
    code: 'tone-rose',
    quiz: 'tone-emerald',
    reading: 'tone-indigo',
    ppt: 'tone-pink',
  }
  return toneMap[type] || 'tone-blue'
}

const sortedGeneratedResources = computed(() => {
  return [...generatedResources.value].sort((a, b) => {
    const aOrder = typeof a.displayOrder === 'number' ? a.displayOrder : -1
    const bOrder = typeof b.displayOrder === 'number' ? b.displayOrder : -1
    if (aOrder !== bOrder) return bOrder - aOrder
    const aIdx = RESOURCE_TYPE_ORDER.indexOf(a.type)
    const bIdx = RESOURCE_TYPE_ORDER.indexOf(b.type)
    return (aIdx === -1 ? 999 : aIdx) - (bIdx === -1 ? 999 : bIdx)
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

const previewGeneratedResource = (resource: any) => {
  handlePreview({
    agentId: resource.type,
    resultData: resource.content,
    title: resource.title || getResourceTypeLabel(resource.type)
  })
}

function createDagNode(id: string, isSystem: boolean): DagNodeState {
  const display = AGENT_DISPLAY[id] || { label: getResourceTypeLabel(id), icon: getDagNodeIcon(id) }
  return {
    id,
    label: display.label,
    icon: display.icon,
    status: 'waiting',
    progress: 0,
    currentMessage: '',
    stepHistory: [],
    isSystem,
  }
}

function initializeWaitingNodes() {
  const nodes: Record<string, DagNodeState> = {
    planning: createDagNode('planning', true),
    review: createDagNode('review', true),
    bundle: createDagNode('bundle', true),
  }
  enabledAgentIds.value.forEach((agentId) => {
    nodes[agentId] = createDagNode(agentId, false)
  })
  dagNodeStates.value = nodes
  selectedDagNodeId.value = 'planning'
}

function applyProgressSnapshot(progress: ResourceTaskStatus['progress']) {
  overallProgress.value = progress.progress
  latestWorkflowMessage.value = progress.latest_message
  Object.entries(progress.agents).forEach(([agentId, snapshot]) => {
    const node = dagNodeStates.value[agentId] || createDagNode(
        agentId,
        ['planning', 'review', 'bundle'].includes(agentId),
    )
    node.status = snapshot.status
    node.progress = snapshot.progress
    node.currentMessage = snapshot.message
    node.stepHistory = snapshot.steps || []
    dagNodeStates.value[agentId] = node
  })

  const runningNode = Object.values(dagNodeStates.value).find(node => node.status === 'running')
  if (runningNode) selectedDagNodeId.value = runningNode.id
}

function applyTaskStatus(taskStatus: ResourceTaskStatus) {
  applyProgressSnapshot(taskStatus.progress)
  if (Array.isArray(taskStatus.resources)) {
    generatedResources.value = taskStatus.resources
  }
}

async function completeGeneration(resourceId: number, taskStatus: ResourceTaskStatus) {
  if (generationFinalized.value) return
  generationFinalized.value = true
  stopPolling()
  stopResourceStream()

  if (taskStatus.status === 'completed' || taskStatus.status === 'partial_completed') {
    const bundle = await getResourceBundle(resourceId)
    finalBundle.value = bundle
    generatedResources.value = bundle.resources || taskStatus.resources || []
    resultWarning.value = taskStatus.status === 'partial_completed'
        ? '部分资源生成失败或质量审查未通过，以下已完成内容仍可查看。'
        : ''
    isGenerating.value = false
    currentPhase.value = 'result'
    return
  }

  generationError.value = taskStatus.progress.latest_message || '资源生成失败，暂无可展示内容'
  isGenerating.value = false
  ElMessage.error(generationError.value || '资源生成失败，暂无可展示内容')
}

async function checkStatusOnce(resourceId: number) {
  const taskStatus = await pollResourceStatus(resourceId)
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

function startResourceStream(resourceId: number) {
  stopResourceStream()
  resourceStreamController.value = streamResourceEvents(
    resourceId,
    ({ event, data }) => {
      if ((event === 'snapshot' || event === 'done') && data && typeof data === 'object') {
        const taskStatus = data as ResourceTaskStatus
        applyTaskStatus(taskStatus)
        if (['completed', 'partial_completed', 'failed'].includes(taskStatus.status)) {
          void completeGeneration(resourceId, taskStatus)
        }
      }
    },
    () => {
      if (isGenerating.value && !generationFinalized.value) {
        startPollingFallback(resourceId)
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
    const { resource_id } = await startResourceGeneration({
      learning_need: naturalInput.value,
      learning_scenario: learningScenario.value,
      selected_agents: enabledAgentIds.value.map((id, index) => ({ agent_id: id, enabled: true, priority: index })).filter(a => a.enabled),
      agent_configs: requestAgentConfigs,
      output_options: { output_format: 'json' }
    })

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
    resourceStreamController.value.abort()
    resourceStreamController.value = null
  }
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
  const suffixPattern = /\s*[-－—]\s*(内容讲解|思维导图|代码实操案例|拓展阅读|自测题)\s*$/
  const matched = raw.match(suffixPattern)
  if (!matched) return raw
  const suffix = matched[1] || ''
  const prefix = raw.replace(suffixPattern, '').trim()
  return prefix ? `${prefix}\n- ${suffix}` : suffix
}

const retryAgent = (agentId: string) => {
  const node = dagNodeStates.value[agentId]
  if (!node) return
  node.status = 'running'
  node.progress = 10
  node.currentMessage = '正在为您重新梳理内容逻辑...'
  // Simulate API retry logic
  setTimeout(() => {
    node.progress = 60
    node.currentMessage = '内容重新生成中，请稍候...'
    setTimeout(() => {
      node.status = 'success'
      node.progress = 100
      node.currentMessage = '已为您重新准备完毕！'
    }, 2000)
  }, 1500)
}

onMounted(() => {
  const prompt = route.query.prompt
  if (prompt) {
    naturalInput.value = String(prompt)
  }
})

onBeforeUnmount(() => {
  stopPolling()
  stopResourceStream()
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
.elegant-generator-layout { width: 100%; min-height: calc(100vh - 64px); background: #FAFAFA; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif; overflow-x: hidden; position: relative; padding-top: var(--space-5); }
.phase-view { position: relative; width: 100%; min-height: calc(100vh - 64px); display: flex; flex-direction: column; background: transparent; backdrop-filter: blur(20px); }
.page-slide-enter-active, .page-slide-leave-active { transition: opacity 0.4s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.page-slide-enter-from { opacity: 0; transform: translateY(30px) scale(0.98); }
.page-slide-leave-to { opacity: 0; transform: translateY(-30px) scale(1.02); }

/* ================= Phase 1: Omni Spotlight 输入舱 ================= */
.omni-input-view {
  align-items: center;
  justify-content: center;
  position: relative;
  background: #F8FAFC;
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
  background-image: radial-gradient(circle, #CBD5E1 1px, transparent 1px);
  background-size: 24px 24px;
  opacity: 0.6;
  z-index: 1;
  pointer-events: none;
}
.omni-pattern-bg::after {
  content: '';
  position: absolute;
  top: 0; left: 0; width: 100%; height: 100%;
  background: radial-gradient(circle at center, transparent 0%, #F8FAFC 90%);
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
  color: #0F172A;
  letter-spacing: -0.03em;
  margin: 0 0 12px 0;
  background: linear-gradient(135deg, #1E293B, #3B82F6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hero-subtitle {
  font-size: 1.1rem;
  color: #64748B;
  font-weight: 500;
  margin: 0;
}

.omni-spotlight-wrapper {
  width: 100%;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
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
  color: #1E293B;
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
  color: #94A3B8;
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
  color: #64748B;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}
.omni-submit-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #F1F5F9;
  color: #94A3B8;
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
  color: #FFFFFF;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}
.omni-spotlight-wrapper.has-content .omni-submit-btn:hover {
  transform: translateY(-2px) scale(1.05);
  background: #2563EB;
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
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
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
  border-color: #CBD5E1;
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
  color: #1E293B;
}
.ins-content p {
  margin: 0;
  font-size: 0.85rem;
  color: #64748B;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* ================= Phase 2: 参数定制配置 ================= */
.personalize-view { background: #F8FAFC; align-items: center; overflow-y: auto; padding: 60px var(--space-5); position: relative; }
.personalize-container { width: 100%; max-width: 1160px; display: flex; flex-direction: column; gap: var(--space-12); position: relative; z-index: 10; }
.view-header { text-align: center; margin-bottom: 0; }
.header-badge { margin-bottom: var(--space-4); font-weight: 700; letter-spacing: 0.05em; background: #E2E8F0 !important; color: #475569 !important; border: none; padding: 0 12px; }
.view-header h2 { 
  font-size: 2.5rem; 
  font-weight: 800; 
  margin: 0 0 12px 0; 
  letter-spacing: -0.02em; 
  background: linear-gradient(135deg, #1E293B, #3B82F6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.view-header p { font-size: 1.1rem; color: #64748B; margin: 0; max-width: 600px; margin: 0 auto; line-height: 1.6; }
.scenario-selector-v2 { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-5); }
.scenario-card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px; padding: var(--space-5); display: flex; align-items: center; gap: var(--space-4); cursor: pointer; transition: all 0.2s ease; position: relative; box-shadow: 0 2px 8px rgba(148, 163, 184, 0.04); }
.scenario-card:hover { transform: translateY(-2px); border-color: #CBD5E1; box-shadow: 0 8px 16px rgba(148, 163, 184, 0.08); }
.scenario-card.active { border-color: #3B82F6; box-shadow: 0 8px 24px rgba(59, 130, 246, 0.12); border-width: 1px; }
.scenario-icon-box { width: 44px; height: 44px; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; color: #475569; transition: background-color 0.2s, transform 0.2s; }
.scenario-card.active .scenario-icon-box { background: #3B82F6; color: #FFFFFF; border-color: #3B82F6; }
.scenario-info { display: flex; flex-direction: column; gap: var(--space-1); flex: 1; }
.s-name { font-weight: 700; font-size: 1rem; color: #1E293B; }
.s-desc { font-size: 0.75rem; color: #64748B; line-height: 1.4; }
.active-dot { position: absolute; top: 12px; right: 12px; width: 8px; height: 8px; background: #3B82F6; border-radius: 50%; }
.config-section-v2 { margin-top: var(--space-2); }
.agent-configs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-6); }
.config-card-v2 { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 24px; overflow: hidden; display: flex; flex-direction: column; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); box-shadow: 0 4px 24px rgba(148, 163, 184, 0.06); }
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
.slider-value { font-size: 0.9rem; color: #3B82F6; font-weight: 700; }
.custom-slider-v2 { padding: 0 var(--space-2); }
.personalize-footer-v2 { display: flex; flex-direction: column; align-items: center; gap: 24px; margin-top: 16px; padding-bottom: 60px; }
.footer-btns { display: flex; justify-content: center; gap: 20px; }
.selected-agents-bar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; justify-content: center; background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(12px); border: 1px solid #E2E8F0; border-radius: 24px; padding: 16px 24px; max-width: 860px; box-shadow: 0 4px 24px rgba(148, 163, 184, 0.08); }
.sab-label { font-size: 0.9rem; color: #64748B; font-weight: 700; white-space: nowrap; }
.sab-pills { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
.sab-pills :deep(.el-tag.sab-pill) { background: #F8FAFC !important; border: 1px solid #E2E8F0 !important; color: #475569 !important; border-radius: 99px !important; padding: 0 16px !important; height: 32px !important; font-size: 0.85rem; display: inline-flex; align-items: center; gap: 6px; }
.sab-pills :deep(.el-tag.sab-pill) .el-icon { color: #3B82F6; font-size: 1rem; }
.sab-hint { font-size: 0.8rem; color: #64748B; font-weight: 600; margin-left: 8px; }
.footer-back-btn { font-weight: 600; color: #64748B; border: 1px solid #E2E8F0; background: #FFFFFF; }
.footer-back-btn:hover { color: #1E293B; border-color: #CBD5E1; background: #F8FAFC; }
.launch-btn-v2 { font-weight: 700; padding: 0 32px; background: #3B82F6 !important; color: #FFFFFF !important; border: none; box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3); transition: transform 0.2s, box-shadow 0.2s; }
.launch-btn-v2:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(59, 130, 246, 0.4); background: #2563EB !important; }

/* ==================== 第三部分：多智能体工作流控制台 ==================== */
.generating-view {
  background:
    radial-gradient(ellipse at 0% 0%, rgba(79, 70, 229, 0.12) 0%, transparent 40%),
    radial-gradient(ellipse at 100% 100%, rgba(99, 102, 241, 0.1) 0%, transparent 40%),
    linear-gradient(180deg, #F5F4FF 0%, #F0F4FF 40%, #F8FAFC 100%);
  overflow-y: auto;
}
.workflow-shell {
  width: 100%;
  max-width: 1540px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-8) var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.workflow-card {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.workflow-topbar {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-5) var(--space-6);
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.workflow-topbar-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-5);
}
.workflow-title-block { display: flex; flex-direction: column; gap: var(--space-2); min-width: 0; }
.workflow-kicker {
  width: fit-content;
  color: #374151 !important;
  border-color: #D1D5DB !important;
  background: #F3F4F6 !important;
  font-weight: var(--weight-extrabold);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
}
.ping-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  background-color: #10B981;
  border-radius: 999px;
  margin-right: 6px;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.35);
  animation: ssePingPulse 1.6s infinite;
}
@keyframes ssePingPulse {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.35); }
  70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}
.workflow-title-block h2 {
  margin: 0;
  font-size: 1.3rem;
  font-weight: var(--weight-extrabold);
  color: #111827;
}
.workflow-title-block p { margin: 0; font-size: 0.9rem; color: #6B7280; }
.workflow-summary-panel {
  min-width: 320px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  grid-template-rows: auto auto;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-4);
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 18px;
}
.summary-item { display: flex; flex-direction: column; gap: 2px; }
.summary-item span { font-size: 0.76rem; color: #64748B; font-weight: var(--weight-bold); }
.summary-item strong { font-size: 1.35rem; color: #0F172A; font-weight: var(--weight-extrabold); }
.summary-item small { font-size: 0.82rem; color: #94A3B8; margin-left: 2px; }
.summary-divider { width: 1px; height: 36px; background: #E2E8F0; }
.workflow-total-progress { grid-column: 1 / -1; }
.workflow-total-progress :deep(.el-progress-bar__outer) { background: #E5E7EB; }
.workflow-total-progress :deep(.el-progress-bar__inner) { background: #374151; }
.generation-error { border-radius: var(--radius-xl); }

/* Stage Steps Strip */
.stage-steps-strip {
  display: flex;
  align-items: center;
  gap: 0;
  padding: var(--space-3) var(--space-4);
  background: #F9FAFB;
  border: 1px solid #E5E7EB;
  border-radius: 12px;
  overflow-x: auto;
}
.stage-step {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  position: relative;
}
.step-dot {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #F3F4F6;
  border: 1.5px solid #D1D5DB;
  color: #6B7280;
  font-size: 0.75rem;
  font-weight: var(--weight-extrabold);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.25s ease;
}
.stage-step.is-running .step-dot {
  background: #111827;
  border-color: #111827;
  color: #fff;
  box-shadow: 0 0 0 3px rgba(17, 24, 39, 0.12);
  animation: stepPulse 1.8s ease-in-out infinite;
}
.stage-step.is-success .step-dot {
  background: #059669;
  border-color: #059669;
  color: #fff;
}
.stage-step.is-failed .step-dot { background: #FEF2F2; border-color: #FECACA; color: #EF4444; }
@keyframes stepPulse { 0%, 100% { box-shadow: 0 0 0 3px rgba(17, 24, 39, 0.12); } 50% { box-shadow: 0 0 0 6px rgba(17, 24, 39, 0.06); } }
.step-label strong { font-size: 0.79rem; color: #6B7280; font-weight: var(--weight-medium); white-space: nowrap; }
.stage-step.is-running .step-label strong { color: #111827; font-weight: var(--weight-semibold); }
.stage-step.is-success .step-label strong { color: #059669; }
.step-connector {
  width: 28px;
  height: 1px;
  background: #D1D5DB;
  margin: 0 var(--space-2);
}
.workflow-main-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-5);
}
.panel-header { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); }
.panel-header.compact { align-items: flex-start; flex-direction: column; gap: 3px; }
.panel-header h3, .resource-strip-header h3 { margin: 0; font-size: 1rem; color: #0F172A; font-weight: var(--weight-extrabold); }
.panel-eyebrow { font-size: 0.7rem; letter-spacing: 0.12em; color: #94A3B8; font-weight: var(--weight-extrabold); }

.workflow-canvas-panel {
  padding: var(--space-5);
  overflow-x: auto;
  overflow-y: hidden;
}
.canvas-header {
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid #F1F5F9;
}
.workflow-canvas {
  position: relative;
  width: 1160px;
  max-width: none;
  height: 620px;
  margin: 0 auto;
  background:
    radial-gradient(circle at 50% 5%, rgba(37, 99, 235, 0.08), transparent 34%),
    linear-gradient(180deg, rgba(248, 250, 252, 0.96), #FFFFFF 62%);
  border: 1px solid #E2E8F0;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8), 0 18px 45px rgba(15, 23, 42, 0.06);
}
.workflow-canvas::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.12) 1px, transparent 1px);
  background-size: 32px 32px;
  mask-image: radial-gradient(circle at center, black 0%, black 62%, transparent 100%);
  pointer-events: none;
  z-index: 0;
}
.parallel-layer-label {
  position: absolute;
  left: 48px;
  right: 48px;
  top: 144px;
  height: 258px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 13px;
  background: rgba(248, 250, 252, 0.56);
  border: 1px dashed rgba(59, 130, 246, 0.25);
  border-radius: 24px;
  color: #64748B;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  pointer-events: none;
  z-index: 1;
}
.parallel-layer-label::before,
.parallel-layer-label::after {
  content: '';
  position: absolute;
  left: 28px;
  right: 28px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(148, 163, 184, 0.35), transparent);
}
.parallel-layer-label::before { top: 86px; }
.parallel-layer-label::after { bottom: 86px; }
.workflow-lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 2;
}
.workflow-edge-base {
  stroke: #CBD5E1;
  stroke-width: 1.4;
  stroke-dasharray: 7 7;
  opacity: 0.68;
  transition: stroke 0.3s ease, opacity 0.3s ease;
  fill: none;
}
.workflow-edge-base.completed {
  stroke: #10B981;
  stroke-width: 1.8;
  opacity: 0.7;
  stroke-dasharray: none;
}
.workflow-edge-base.active {
  stroke: #60A5FA;
  stroke-width: 1.8;
  stroke-dasharray: none;
  opacity: 0.8;
}
.workflow-edge-flow {
  stroke: url(#flow-particle);
  stroke-width: 4;
  stroke-linecap: round;
  stroke-dasharray: 26 130;
  animation: dagFlowMoving 1.45s linear infinite;
  filter: drop-shadow(0 0 6px rgba(59, 130, 246, 0.45));
  fill: none;
}
@keyframes dagFlowMoving { from { stroke-dashoffset: 156; } to { stroke-dashoffset: 0; } }
.workflow-agent-node {
  position: absolute;
  z-index: 5;
  appearance: none;
  border: 1px solid rgba(226, 232, 240, 0.95);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(16px);
  border-radius: 18px;
  padding: 12px;
  text-align: left;
  cursor: pointer;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.07);
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease, background 0.25s ease;
}
.workflow-agent-node::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: #CBD5E1;
}
.workflow-agent-node:hover,
.workflow-agent-node.is-selected {
  transform: translateY(-5px);
  border-color: #93C5FD;
  box-shadow: 0 22px 44px rgba(37, 99, 235, 0.13);
}
.workflow-agent-node.is-waiting { opacity: 0.72; }
.workflow-agent-node.is-running {
  border-color: #60A5FA;
  background: #FFFFFF;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12), 0 22px 50px rgba(37, 99, 235, 0.18);
  animation: workflowNodePulse 2.2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}
.workflow-agent-node.is-running::before { background: #3B82F6; }
.workflow-agent-node.is-success {
  border-color: #A7F3D0;
  background: #FBFFFD;
  box-shadow: 0 16px 34px rgba(16, 185, 129, 0.10);
}
.workflow-agent-node.is-success::before { background: #10B981; }
.workflow-agent-node.is-failed {
  border-color: #FECACA;
  background: #FFFBFB;
}
.workflow-agent-node.is-failed::before { background: #EF4444; }
.workflow-agent-node.is-system-node {
  border-color: rgba(191, 219, 254, 0.95);
  background: rgba(255, 255, 255, 0.98);
}
.workflow-agent-node.is-system-node::before { background: #2563EB; }
@keyframes workflowNodePulse {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-3px); }
}
.agent-node-topline {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.agent-icon-bubble {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: #F1F5F9;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 1rem;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.12);
}
.workflow-agent-node.is-system-node .agent-icon-bubble { background: #EFF6FF; }
.agent-node-name {
  font-size: 0.88rem;
  color: #0F172A;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.agent-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #CBD5E1;
  margin-left: auto;
  flex-shrink: 0;
}
.workflow-agent-node.is-running .agent-status-dot { background: #3B82F6; box-shadow: 0 0 0 5px rgba(59, 130, 246, 0.14); }
.workflow-agent-node.is-success .agent-status-dot { background: #10B981; }
.workflow-agent-node.is-failed .agent-status-dot { background: #EF4444; }
.agent-node-message {
  margin: 0;
  min-height: 34px;
  font-size: 0.74rem;
  line-height: 1.55;
  color: #64748B;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.agent-node-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #94A3B8;
  font-size: 0.72rem;
  font-weight: 700;
}
.agent-node-footer strong { color: #334155; font-family: var(--font-mono); }
.agent-mini-progress { height: 4px; border-radius: 999px; overflow: hidden; background: #EEF2F7; }
.agent-mini-progress span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #2563EB, #06B6D4); transition: width 0.35s ease; }
.workflow-canvas::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 426px;
  width: 1px;
  height: 94px;
  transform: translateX(-50%);
  background: linear-gradient(180deg, rgba(148, 163, 184, 0.1), rgba(37, 99, 235, 0.45), rgba(148, 163, 184, 0.1));
  z-index: 1;
}
/* Inline Agent Detail Panel */
.inline-agent-detail {
  margin-top: var(--space-4);
  border: 1px solid #E5E7EB;
  border-radius: 14px;
  background: #FAFAFA;
  overflow: hidden;
}
.iad-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  background: #FFFFFF;
  border-bottom: 1px solid #F3F4F6;
}
.iad-agent-info { display: flex; align-items: center; gap: var(--space-3); min-width: 0; }
.iad-icon { width: 38px; height: 38px; border-radius: 10px; background: #F3F4F6; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; flex-shrink: 0; border: 1px solid #E5E7EB; }
.iad-agent-info h4 { margin: 0 0 3px; font-size: 0.95rem; font-weight: var(--weight-bold); color: #111827; }
.iad-progress-wrap { flex-shrink: 0; }
.iad-action { flex: 1; min-width: 0; }
.iad-action-text { font-size: 0.82rem; color: #6B7280; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 1; line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }
.iad-close {
  margin-left: auto;
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid #E5E7EB;
  background: #F9FAFB;
  color: #6B7280;
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}
.iad-close:hover { background: #F3F4F6; color: #111827; }
.iad-logs { display: flex; flex-direction: column; gap: 6px; padding: var(--space-4) var(--space-5); max-height: 160px; overflow-y: auto; }
.iad-logs-empty { padding: var(--space-4) var(--space-5); color: #9CA3AF; font-size: 0.82rem; }
.detail-slide-enter-active, .detail-slide-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.detail-slide-enter-from, .detail-slide-leave-to { opacity: 0; transform: translateY(-6px); }

.workflow-detail-panel { display: flex; flex-direction: column; gap: var(--space-5); }
.agent-detail-card { display: flex; flex-direction: column; gap: var(--space-5); }
.detail-agent-head { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-4); background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 18px; }
.detail-agent-icon { width: 44px; height: 44px; border-radius: 16px; background: #FFFFFF; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; box-shadow: var(--shadow-xs); }
.detail-agent-head h4 { margin: 0 0 5px; color: #0F172A; font-size: 1rem; font-weight: var(--weight-extrabold); }
.detail-status-pill { display: inline-flex; align-items: center; padding: 3px 9px; border-radius: 999px; background: #F1F5F9; color: #64748B; font-size: 0.68rem; font-weight: var(--weight-bold); }
.detail-status-pill.is-running { background: #EFF6FF; color: #2563EB; }
.detail-status-pill.is-success { background: #ECFDF5; color: #10B981; }
.detail-status-pill.is-failed { background: #FEF2F2; color: #EF4444; }
.detail-section { display: flex; flex-direction: column; gap: var(--space-2); }
.detail-label { font-size: 0.68rem; color: #94A3B8; font-weight: var(--weight-extrabold); letter-spacing: 0.08em; }
.detail-section p { margin: 0; color: #334155; font-size: 0.88rem; line-height: 1.65; }
.agent-log-list { display: flex; flex-direction: column; gap: 8px; max-height: 260px; overflow-y: auto; padding-right: 4px; }
.agent-log-item { display: flex; align-items: flex-start; gap: 8px; padding: 9px 10px; background: #F8FAFC; border: 1px solid #EEF2F7; border-radius: 12px; color: #475569; font-size: 0.78rem; line-height: 1.45; }
.agent-log-item.active { background: #EFF6FF; border-color: #BFDBFE; color: #1D4ED8; font-weight: var(--weight-semibold); }
.log-dot { width: 7px; height: 7px; margin-top: 6px; border-radius: 999px; background: #CBD5E1; flex-shrink: 0; }
.agent-log-item.active .log-dot { background: #2563EB; animation: stepBulletBlink 0.9s infinite alternate; }
@keyframes stepBulletBlink { from { opacity: 0.3; } to { opacity: 1; } }
.agent-log-empty { padding: var(--space-4); border-radius: 14px; border: 1px dashed #CBD5E1; background: #F8FAFC; color: #94A3B8; font-size: 0.82rem; text-align: center; }
.workflow-resource-strip { padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-4); }
.resource-strip-header { display: flex; justify-content: space-between; align-items: center; gap: var(--space-4); }
.res-count-badge { background: #ECFDF5 !important; color: #10B981 !important; border-color: rgba(16, 185, 129, 0.18) !important; font-weight: var(--weight-bold); }
.resource-strip-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-3); }
.resource-chip-card { display: flex; align-items: center; gap: var(--space-3); padding: var(--space-3); background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 16px; cursor: pointer; transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease, background 0.2s ease; }
.resource-chip-card:hover { transform: translateY(-2px); background: #FFFFFF; border-color: #BFDBFE; box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06); }
.resource-chip-icon { width: 34px; height: 34px; border-radius: 12px; background: #FFFFFF; display: flex; align-items: center; justify-content: center; box-shadow: var(--shadow-xs); flex-shrink: 0; }
.resource-chip-meta { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.resource-chip-meta span { font-size: 0.68rem; color: #94A3B8; font-weight: var(--weight-bold); }
.resource-chip-meta strong { font-size: 0.8rem; color: #0F172A; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.resource-chip-card .el-icon { color: #94A3B8; }
.resource-empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; padding: var(--space-8); color: #64748B; font-size: 0.9rem; }
.empty-wave-loader { display: flex; gap: 4px; align-items: center; height: 12px; }
.empty-wave-loader span { width: 4px; height: 7px; background-color: #CBD5E1; border-radius: 2px; animation: emptyWavePluse 1.2s infinite ease-in-out alternate; }
.empty-wave-loader span:nth-child(2) { animation-delay: 0.2s; }
.empty-wave-loader span:nth-child(3) { animation-delay: 0.4s; }
@keyframes emptyWavePluse { from { transform: scaleY(0.6); background-color: #E2E8F0; } to { transform: scaleY(1.8); background-color: #94A3B8; } }
.scale-fade-enter-active, .scale-fade-leave-active { transition: all 0.2s ease; }
.scale-fade-enter-from, .scale-fade-leave-to { transform: scale(0.85); opacity: 0; }

/* ================= Phase 4: 交付中心看板 (Bento Layout) ================= */
.results-view { background: #F9FAFB; overflow-y: auto; padding-bottom: 80px; position: relative; }
.result-hero-compact { display: flex; justify-content: space-between; align-items: center; padding: var(--space-4) var(--space-8); background: #FFFFFF; border-bottom: 1px solid #E5E7EB; margin-bottom: var(--space-6); border-radius: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); position: sticky; top: 0; z-index: 100; }
.hero-content-left { display: flex; flex-direction: column; gap: var(--space-1); }
.hero-status-tag-mini { display: inline-flex; align-items: center; gap: var(--space-1); color: var(--color-success); font-size: 0.75rem; font-weight: var(--weight-extrabold); }
.hero-title-compact { margin: 0; font-size: 1.25rem; font-weight: var(--weight-extrabold); color: var(--color-text-strong); }
.hero-subtitle-compact { margin: 0; font-size: 0.85rem; color: var(--color-text-muted); }
.hero-actions-right { display: flex; gap: var(--space-3); align-items: center; }
.results-body-bento { max-width: 1440px; margin: 0 auto; padding: var(--space-10) 60px; display: flex; flex-direction: column; gap: var(--space-10); position: relative; z-index: 1; }
.premium-resource-grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: var(--space-8); align-items: stretch; }
.premium-res-card { grid-column: span 3; background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 16px; padding: var(--space-8); display: flex; flex-direction: column; gap: var(--space-5); position: relative; overflow: hidden; transition: all 0.2s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.04); cursor: pointer; animation: fadeSlideUp 0.6s ease-out backwards; }
@keyframes fadeSlideUp { 0% { opacity: 0; transform: translateY(20px); } 100% { opacity: 1; transform: translateY(0); } }
.premium-res-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.06); border-color: #D1D5DB; }
.card-bg-glow { display: none; }

.premium-res-card .card-header, .premium-res-card .card-body, .premium-res-card .card-footer { position: relative; z-index: 1; }
.premium-res-card .type-icon-box { width: 48px; height: 48px; border-radius: var(--radius-lg); display: flex; align-items: center; justify-content: center; font-size: 1.5rem; background: rgba(15, 23, 42, 0.03); border: 1px solid rgba(15, 23, 42, 0.04); }
.premium-res-card.tone-blue .type-icon-box { color: var(--color-info); }
.premium-res-card.tone-purple .type-icon-box { color: #7C3AED; }
.premium-res-card.tone-rose .type-icon-box { color: #E11D48; }
.premium-res-card.tone-emerald .type-icon-box { color: var(--tone-emerald); }
.premium-res-card.tone-indigo .type-icon-box { color: var(--color-primary); }
.premium-res-card.tone-pink .type-icon-box { color: #DB2777; }

.premium-res-card .card-title { margin: 0; font-size: 1.15rem; font-weight: var(--weight-extrabold); color: var(--color-text); line-height: 1.45; white-space: pre-line; display: -webkit-box; -webkit-line-clamp: 3; line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: anywhere; }
.premium-res-card .card-summary { margin: 0; font-size: 0.95rem; color: var(--color-text-secondary); line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.card-metrics-modern { display: flex; gap: var(--space-3); margin-top: auto; padding-top: var(--space-3); }
.metric-badge { display: inline-flex; align-items: center; gap: var(--space-1); background: var(--color-bg); color: var(--color-text-secondary); padding: var(--space-1) var(--space-3); border: 1px solid rgba(15, 23, 42, 0.04); border-radius: var(--radius-md); font-size: 0.8rem; font-weight: var(--weight-bold); }
.premium-res-card .card-footer { border-top: 1px solid rgba(226, 232, 240, 0.6); padding-top: var(--space-5); margin-top: var(--space-1); display: flex; justify-content: space-between; align-items: center; }
.modern-text-btn { background: transparent; border: none; color: var(--color-text); font-weight: var(--weight-extrabold); font-size: 0.95rem; padding: 0; cursor: pointer; display: flex; align-items: center; gap: var(--space-2); transition: color var(--transition-base); }
.modern-text-btn span { transition: transform var(--transition-slow); }
.premium-res-card:hover .modern-text-btn { color: var(--color-info); }
.premium-res-card:hover .modern-text-btn span { transform: translateX(4px); }

/* ================= 媒体查询与响应式适配 ================= */
@media (max-width: 1200px) {
  .agent-configs-grid { grid-template-columns: repeat(2, 1fr); }
  .premium-resource-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); }
  .premium-res-card { grid-column: span 2 !important; }
  .results-body-bento { padding: var(--space-6) var(--space-8); }
  .dag-canvas { min-height: 380px; }
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
  .results-body-bento { padding: var(--space-4); }
  .premium-resource-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .premium-res-card { grid-column: span 1 !important; }
  .dag-canvas { min-height: 360px; }
}
@media (max-width: 520px) {
  .premium-resource-grid { grid-template-columns: 1fr; }
  .premium-res-card { grid-column: span 1 !important; }
}

/* Element Plus 弹窗深度订制 */
.elegant-dialog :deep(.el-dialog) { border-radius: var(--radius-2xl); overflow: hidden; box-shadow: var(--shadow-xl); }
.elegant-dialog :deep(.el-dialog__header) { padding: var(--space-6) var(--space-8) var(--space-5); margin-right: 0; border-bottom: 1px solid var(--color-surface-hover); }
.elegant-dialog :deep(.el-dialog__title) { font-weight: var(--weight-extrabold); font-size: 1.2rem; color: var(--color-text); }
.elegant-dialog :deep(.el-dialog__body) { padding: var(--space-8); background: var(--color-bg); }

/* PPT 预览弹窗专属沉浸式样式 */
.is-ppt-dialog :deep(.el-dialog__body) {
  padding: 0 !important;
  background: #F8FAFC !important;
}

.preview-dialog-body.is-ppt-preview {
  padding: 0 !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.preview-dialog-body.is-ppt-preview :deep(.player-wrapper) {
  margin-top: 0 !important;
  border: none !important;
  border-radius: 0 !important;
}

h1, h2, h3, h4, .greeting-title, .cc-title { letter-spacing: -0.025em; color: var(--color-text); font-weight: var(--weight-bold); }
p, .card-summary, .s-desc, .greeting-subtitle { line-height: 1.65; letter-spacing: 0.01em; color: var(--color-text-secondary); }
@media (max-width: 1280px) {
  .workflow-shell { padding-left: var(--space-4); padding-right: var(--space-4); }
  .workflow-canvas { width: 1160px; max-width: none; height: 620px; }
}


/* ================= Phase 3: 独立多智能体调度动画舞台 ================= */
.workflow-stage-page {
  background: #F8FAFC;
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
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 22px;
  padding: 14px 18px;
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.055);
  backdrop-filter: blur(18px);
}
.stage-title-area { display: flex; flex-direction: column; gap: 7px; min-width: 0; }
.stage-title-area h2 { margin: 0; font-size: 1.24rem; font-weight: 900; color: #0F172A; }
.stage-title-area p { margin: 0; color: #64748B; font-size: 0.9rem; }
.stage-route-progress { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.route-step {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: #F1F5F9;
  color: #94A3B8;
  font-size: 0.72rem;
  font-weight: 800;
}
.route-step.done { background: #ECFDF5; color: #059669; }
.route-step.active { background: #EFF6FF; color: #2563EB; box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.16); }
.route-line { width: 28px; height: 2px; border-radius: 99px; background: #CBD5E1; }
.route-line.done { background: #34D399; }
.route-line.active { background: linear-gradient(90deg, #34D399, #2563EB); }
.stage-stat-group { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.stage-stat-card {
  min-width: 92px;
  padding: 10px 14px;
  border-radius: 18px;
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stage-stat-card.wide { min-width: 110px; }
.stage-stat-card span { color: #64748B; font-size: 0.72rem; font-weight: 700; }
.stage-stat-card strong { color: #0F172A; font-size: 1.22rem; line-height: 1; font-weight: 900; }
.stage-stat-card small { color: #94A3B8; font-size: 0.78rem; margin-left: 2px; }
.stage-log-btn { height: 42px; border-color: #BFDBFE !important; color: #2563EB !important; font-weight: 800; background: #FFFFFF !important; }
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
.agent-stage-canvas,
.agent-detail-panel,
.output-dock-bar {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(18px);
}
.agent-stage-canvas {
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
.panel-eyebrow { display: inline-block; font-size: 0.68rem; font-weight: 900; color: #2563EB; letter-spacing: 0.08em; text-transform: uppercase; }
.stage-canvas-header h3 { margin: 4px 0 0; font-size: 1.05rem; font-weight: 900; color: #0F172A; }
.stage-control-pills { display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.control-pill { display: inline-flex; align-items: center; gap: 7px; height: 28px; padding: 0 10px; border-radius: 999px; background: #F8FAFC; color: #64748B; border: 1px solid #E2E8F0; font-size: 0.72rem; font-weight: 800; }
.control-pill.active { background: #EFF6FF; color: #2563EB; border-color: #BFDBFE; }
.live-dot { width: 7px; height: 7px; border-radius: 999px; background: #22C55E; box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.14); }
.dispatch-stage { position: relative; height: clamp(680px, calc(100vh - 220px), 860px); margin-top: 4px; overflow: hidden; border-radius: 26px; background: linear-gradient(180deg, rgba(248, 250, 252, 0.72), rgba(255, 255, 255, 0.96)); }
.stage-orbit-ring { position: absolute; left: 50%; top: 49%; transform: translate(-50%, -50%); border-radius: 999px; border: 1px dashed rgba(148, 163, 184, 0.35); pointer-events: none; }
.ring-one { width: 560px; height: 380px; }
.ring-two { width: min(1080px, 82%); height: 580px; opacity: 0.62; }
.master-hub {
  position: absolute;
  left: 50%;
  top: 45%;
  width: 250px;
  transform: translate(-50%, -50%);
  background: linear-gradient(180deg, #FFFFFF, #F8FAFC);
  border: 1px solid #BFDBFE;
  border-radius: 28px;
  padding: 16px;
  box-shadow: 0 28px 70px rgba(37, 99, 235, 0.16);
  z-index: 5;
  cursor: pointer;
}
.master-hub.is-running { animation: hubBreathing 1.8s ease-in-out infinite; }
@keyframes hubBreathing { 0%, 100% { box-shadow: 0 28px 70px rgba(37, 99, 235, 0.16); } 50% { box-shadow: 0 32px 86px rgba(37, 99, 235, 0.28); } }
.master-core { position: relative; width: 64px; height: 64px; margin: 0 auto 12px; display: grid; place-items: center; }
.master-icon { position: relative; z-index: 2; width: 54px; height: 54px; border-radius: 18px; background: linear-gradient(135deg, #2563EB, #06B6D4); display: grid; place-items: center; font-size: 1.6rem; box-shadow: 0 14px 32px rgba(37, 99, 235, 0.28); }
.master-pulse { position: absolute; inset: 0; border-radius: 24px; background: rgba(37, 99, 235, 0.14); animation: masterPulse 1.6s ease-out infinite; }
@keyframes masterPulse { from { transform: scale(0.82); opacity: 0.9; } to { transform: scale(1.38); opacity: 0; } }
.master-info { text-align: center; }
.hub-kicker { color: #2563EB; font-size: 0.68rem; font-weight: 900; letter-spacing: 0.08em; }
.master-info h4 { margin: 4px 0 5px; font-size: 1.12rem; font-weight: 900; color: #0F172A; }
.master-info p { margin: 0; color: #64748B; font-size: 0.78rem; line-height: 1.45; min-height: 34px; }
.master-progress-line { height: 6px; border-radius: 999px; background: #E2E8F0; overflow: hidden; margin-top: 12px; }
.master-progress-line span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #2563EB, #06B6D4); transition: width 0.3s ease; }
.plan-card-stack { position: absolute; left: 50%; top: 10px; transform: translateX(-50%); display: flex; gap: 8px; z-index: 6; max-width: 74%; flex-wrap: wrap; justify-content: center; }
.plan-mini-card { display: inline-flex; align-items: center; gap: 6px; height: 30px; padding: 0 10px; border-radius: 999px; background: #FFFFFF; border: 1px solid #E2E8F0; box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05); animation: planDrop 0.5s ease both; }
@keyframes planDrop { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }
.plan-mini-card span { width: 17px; height: 17px; border-radius: 999px; background: #EFF6FF; color: #2563EB; display: grid; place-items: center; font-size: 0.68rem; font-weight: 900; }
.plan-mini-card strong { color: #334155; font-size: 0.72rem; white-space: nowrap; }
.agent-workstation {
  position: absolute;
  width: 210px;
  min-height: 112px;
  border-radius: 22px;
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  padding: 12px;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.055);
  z-index: 4;
  cursor: pointer;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease, opacity 0.25s ease;
}
.agent-workstation:hover,
.agent-workstation.is-selected { transform: translateY(-4px); box-shadow: 0 24px 48px rgba(37, 99, 235, 0.14); border-color: #93C5FD; }
.agent-workstation.is-waiting { opacity: 0.72; }
.agent-workstation.is-running { border-color: #FDBA74; animation: stationRunning 1.8s ease-in-out infinite; }
@keyframes stationRunning { 0%, 100% { box-shadow: 0 16px 34px rgba(251, 146, 60, 0.08); } 50% { box-shadow: 0 22px 54px rgba(251, 146, 60, 0.22); } }
.agent-workstation.is-success { border-color: #A7F3D0; background: linear-gradient(180deg, #FFFFFF, #F0FDF4); }
.agent-workstation.is-failed { border-color: #FECACA; background: linear-gradient(180deg, #FFFFFF, #FEF2F2); }
.station-content { left: 4%; top: 42%; }
.station-mindmap { left: 16%; top: 12%; }
.station-code { right: 16%; top: 12%; }
.station-quiz { right: 4%; top: 42%; }
.station-reading { left: 17%; bottom: 26%; }
.station-ppt { right: 17%; bottom: 26%; }
.workstation-head { display: flex; align-items: center; gap: 10px; }
.workstation-icon { width: 34px; height: 34px; border-radius: 13px; background: #F8FAFC; display: grid; place-items: center; font-size: 1.12rem; flex-shrink: 0; }
.workstation-title { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1; }
.workstation-title strong { color: #0F172A; font-size: 0.88rem; font-weight: 900; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.workstation-title span { color: #64748B; font-size: 0.7rem; font-weight: 800; }
.workstation-status-dot { width: 9px; height: 9px; border-radius: 999px; background: #CBD5E1; flex-shrink: 0; }
.agent-workstation.is-running .workstation-status-dot { background: #F97316; box-shadow: 0 0 0 5px rgba(249, 115, 22, 0.14); }
.agent-workstation.is-success .workstation-status-dot { background: #10B981; }
.agent-workstation p { margin: 8px 0 9px; color: #64748B; font-size: 0.72rem; line-height: 1.38; min-height: 30px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.workstation-message-wrap { min-height: 38px; }
.error-text { color: #F97316 !important; font-weight: 600; }
.typewriter-text { display: inline-block; animation: textReveal 0.5s ease-out forwards; }
@keyframes textReveal { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: translateY(0); } }
.workstation-actions { margin-top: 8px; display: flex; justify-content: center; }
.retry-btn { background: #FFF7ED; color: #EA580C; border: 1px solid #FFEDD5; border-radius: 99px; padding: 4px 12px; font-size: 0.7rem; font-weight: 800; display: inline-flex; align-items: center; gap: 4px; cursor: pointer; transition: all 0.2s; }
.retry-btn:hover { background: #FFEDD5; transform: scale(1.02); }
.workstation-progress { height: 6px; border-radius: 999px; background: #E2E8F0; overflow: hidden; }
.workstation-progress span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #2563EB, #06B6D4); transition: width 0.35s ease; }
.agent-workstation.is-success .workstation-progress span { background: #10B981; }
.agent-workstation.is-running .workstation-progress span { background: linear-gradient(90deg, #F97316, #FBBF24); }
.workstation-meta { display: flex; align-items: center; justify-content: space-between; margin-top: 9px; color: #94A3B8; font-size: 0.7rem; font-weight: 800; }
.workstation-meta strong { color: #334155; }
.dispatch-packet,
.return-resource-card {
  position: absolute;
  z-index: 3;
  height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: #FFFFFF;
  border: 1px solid #BFDBFE;
  color: #2563EB;
  box-shadow: 0 12px 26px rgba(37, 99, 235, 0.12);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.7rem;
  font-weight: 900;
  opacity: 0;
}
.dispatch-packet i { width: 7px; height: 7px; border-radius: 999px; background: #2563EB; }
.dispatch-packet.active { opacity: 1; }
.packet-content { left: 48%; top: 42%; animation: flyContent 2.8s ease-in-out infinite; }
.packet-mindmap { left: 48%; top: 42%; animation: flyMindmap 3.1s ease-in-out infinite; }
.packet-code { left: 48%; top: 42%; animation: flyCode 3s ease-in-out infinite; }
.packet-quiz { left: 48%; top: 42%; animation: flyQuiz 3.2s ease-in-out infinite; }
.packet-reading { left: 48%; top: 42%; animation: flyReading 3.1s ease-in-out infinite; }
.packet-ppt { left: 48%; top: 42%; animation: flyPpt 3.3s ease-in-out infinite; }
@keyframes flyContent { 0% { transform: translate(0,0) scale(.9); opacity:0; } 15%,70% { opacity:1; } 100% { transform: translate(-410px,-92px) scale(1); opacity:0; } }
@keyframes flyMindmap { 0% { transform: translate(0,0) scale(.9); opacity:0; } 15%,70% { opacity:1; } 100% { transform: translate(-260px,-205px) scale(1); opacity:0; } }
@keyframes flyCode { 0% { transform: translate(0,0) scale(.9); opacity:0; } 15%,70% { opacity:1; } 100% { transform: translate(250px,-205px) scale(1); opacity:0; } }
@keyframes flyQuiz { 0% { transform: translate(0,0) scale(.9); opacity:0; } 15%,70% { opacity:1; } 100% { transform: translate(390px,-92px) scale(1); opacity:0; } }
@keyframes flyReading { 0% { transform: translate(0,0) scale(.9); opacity:0; } 15%,70% { opacity:1; } 100% { transform: translate(-350px,160px) scale(1); opacity:0; } }
@keyframes flyPpt { 0% { transform: translate(0,0) scale(.9); opacity:0; } 15%,70% { opacity:1; } 100% { transform: translate(330px,160px) scale(1); opacity:0; } }
.review-assembly-lane { position: absolute; left: 50%; bottom: 22px; transform: translateX(-50%); display: flex; align-items: center; gap: 14px; z-index: 5; }
.lane-node { width: 250px; min-height: 66px; display: flex; align-items: center; gap: 10px; padding: 11px 12px; border-radius: 20px; background: #FFFFFF; border: 1px solid #E2E8F0; box-shadow: 0 14px 30px rgba(15, 23, 42, 0.055); cursor: pointer; }
.lane-node.is-running { border-color: #A78BFA; box-shadow: 0 18px 42px rgba(124, 58, 237, 0.16); }
.lane-node.is-success { border-color: #A7F3D0; background: #F0FDF4; }
.lane-icon { width: 42px; height: 42px; border-radius: 15px; background: #F8FAFC; display: grid; place-items: center; font-size: 1.25rem; flex-shrink: 0; }
.lane-node strong { color: #0F172A; font-size: 0.86rem; font-weight: 900; }
.lane-node p { margin: 3px 0 0; color: #64748B; font-size: 0.72rem; line-height: 1.35; }
.lane-node-content { flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: center; position: relative; }
.lane-node em { margin-left: auto; font-style: normal; color: #334155; font-weight: 900; font-size: 0.8rem; }
.reviewer-checklist { display: flex; flex-direction: column; gap: 4px; margin-top: 6px; position: relative; overflow: hidden; padding-bottom: 2px; }
.check-item { display: flex; align-items: center; gap: 6px; font-size: 0.7rem; color: #94A3B8; transition: color 0.3s; }
.check-item.passed { color: #10B981; font-weight: 800; }
.check-box { width: 12px; height: 12px; border-radius: 3px; border: 1px solid #CBD5E1; display: grid; place-items: center; font-size: 0.6rem; transition: all 0.3s; }
.check-item.passed .check-box { background: #10B981; border-color: #10B981; color: #FFFFFF; }
.scanner-line { position: absolute; left: 0; right: 0; height: 20px; background: linear-gradient(180deg, rgba(16, 185, 129, 0) 0%, rgba(16, 185, 129, 0.15) 100%); border-bottom: 1px solid rgba(16, 185, 129, 0.5); animation: scanSweep 2s linear infinite; pointer-events: none; }
@keyframes scanSweep { 0% { top: -20px; opacity: 0; } 10% { opacity: 1; } 90% { opacity: 1; } 100% { top: 100%; opacity: 0; } }
.lane-arrow { width: 42px; height: 2px; background: linear-gradient(90deg, #CBD5E1, #2563EB); position: relative; }
.lane-arrow::after { content: ''; position: absolute; right: -2px; top: 50%; width: 8px; height: 8px; border-top: 2px solid #2563EB; border-right: 2px solid #2563EB; transform: translateY(-50%) rotate(45deg); }
.return-resource-card { border-color: #A7F3D0; color: #059669; }
.return-content { left: 18%; bottom: 125px; animation: returnFloat 2.3s ease-in-out infinite; opacity: 1; }
.return-mindmap { left: 31%; bottom: 128px; animation: returnFloat 2.5s ease-in-out infinite; opacity: 1; }
.return-code { right: 31%; bottom: 128px; animation: returnFloat 2.4s ease-in-out infinite; opacity: 1; }
.return-quiz { right: 18%; bottom: 125px; animation: returnFloat 2.6s ease-in-out infinite; opacity: 1; }
.return-reading { left: 23%; bottom: 92px; animation: returnFloat 2.6s ease-in-out infinite; opacity: 1; }
.return-ppt { right: 23%; bottom: 92px; animation: returnFloat 2.5s ease-in-out infinite; opacity: 1; }
@keyframes returnFloat { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
.agent-detail-panel { border-radius: 28px; padding: 18px; display: flex; flex-direction: column; gap: 14px; overflow-y: auto; }
.detail-panel-header h3 { margin: 4px 0 0; font-size: 1.05rem; font-weight: 900; color: #0F172A; }
.detail-agent-card { border: 1px solid #E2E8F0; border-radius: 22px; background: #F8FAFC; padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.detail-agent-card.is-running { border-color: #FDBA74; background: #FFF7ED; }
.detail-agent-card.is-success { border-color: #A7F3D0; background: #F0FDF4; }
.detail-agent-top { display: flex; gap: 12px; align-items: flex-start; }
.detail-agent-icon { width: 46px; height: 46px; border-radius: 16px; background: #FFFFFF; display: grid; place-items: center; font-size: 1.35rem; flex-shrink: 0; box-shadow: 0 8px 18px rgba(15, 23, 42, 0.05); }
.detail-agent-top strong { color: #0F172A; font-size: 0.92rem; font-weight: 900; }
.detail-agent-top p { margin: 4px 0 0; color: #64748B; font-size: 0.78rem; line-height: 1.45; }
.detail-section-card { border: 1px solid #E2E8F0; border-radius: 22px; background: #FFFFFF; padding: 16px; }
.detail-section-card h4 { margin: 0 0 12px; color: #0F172A; font-size: 0.92rem; font-weight: 900; }
.compact-log-list { display: flex; flex-direction: column; gap: 10px; }
.compact-log-item { display: flex; gap: 9px; align-items: flex-start; }
.compact-log-item span { width: 8px; height: 8px; margin-top: 6px; border-radius: 999px; background: #2563EB; flex-shrink: 0; }
.compact-log-item p { margin: 0; color: #475569; font-size: 0.78rem; line-height: 1.45; }
.compact-empty { color: #94A3B8; font-size: 0.82rem; padding: 12px; text-align: center; border-radius: 14px; background: #F8FAFC; }
.mini-stage-list { display: flex; flex-direction: column; gap: 12px; }
.mini-stage-item { display: flex; gap: 10px; align-items: flex-start; }
.mini-stage-item > span { width: 10px; height: 10px; border-radius: 999px; background: #CBD5E1; margin-top: 5px; flex-shrink: 0; }
.mini-stage-item.is-running > span { background: #F97316; box-shadow: 0 0 0 5px rgba(249, 115, 22, 0.12); }
.mini-stage-item.is-success > span { background: #10B981; }
.mini-stage-item.is-failed > span { background: #EF4444; }
.mini-stage-item strong { color: #0F172A; font-size: 0.78rem; font-weight: 900; }
.mini-stage-item p { margin: 2px 0 0; color: #64748B; font-size: 0.72rem; line-height: 1.35; }
.output-dock-bar { position: relative; z-index: 2; border-radius: 22px; padding: 10px 12px; display: flex; align-items: center; gap: 12px; }
.output-dock-title { width: 130px; flex-shrink: 0; display: flex; flex-direction: column; gap: 2px; }
.output-dock-title strong { color: #0F172A; font-size: 0.92rem; font-weight: 900; }
.output-dock-list { display: grid; grid-template-columns: repeat(6, minmax(110px, 1fr)); gap: 8px; flex: 1; }
.output-dock-item { display: flex; gap: 8px; align-items: center; padding: 8px 10px; border: 1px solid #E2E8F0; border-radius: 16px; background: #F8FAFC; opacity: 0.72; transition: all 0.2s ease; cursor: default; }
.output-dock-item.ready { opacity: 1; background: #F0FDF4; border-color: #A7F3D0; cursor: pointer; }
.output-dock-item.ready:hover { transform: translateY(-2px); box-shadow: 0 14px 28px rgba(16, 185, 129, 0.10); }
.output-dock-item > span { width: 26px; height: 26px; border-radius: 8px; background: #FFFFFF; display: grid; place-items: center; flex-shrink: 0; font-size: 0.9rem; }
.output-dock-item strong { display: block; color: #0F172A; font-size: 0.72rem; font-weight: 900; white-space: nowrap; }
.output-dock-item p { margin: 1px 0 0; color: #64748B; font-size: 0.65rem; white-space: nowrap; }
.workflow-log-drawer :deep(.el-drawer__header) { margin-bottom: 0; padding: 20px 22px; border-bottom: 1px solid #E2E8F0; font-weight: 900; color: #0F172A; }
.drawer-log-list { display: flex; flex-direction: column; gap: 14px; padding: 4px; }
.drawer-log-item { display: flex; gap: 12px; align-items: flex-start; padding: 12px; border-radius: 16px; background: #F8FAFC; border: 1px solid #E2E8F0; }
.drawer-log-dot { width: 10px; height: 10px; border-radius: 999px; background: #CBD5E1; margin-top: 5px; flex-shrink: 0; }
.drawer-log-item.is-running .drawer-log-dot { background: #F97316; box-shadow: 0 0 0 5px rgba(249, 115, 22, 0.12); }
.drawer-log-item.is-success .drawer-log-dot { background: #10B981; }
.drawer-log-item.is-failed .drawer-log-dot { background: #EF4444; }
.drawer-log-item strong { color: #0F172A; font-size: 0.86rem; font-weight: 900; }
.drawer-log-item p { margin: 4px 0 0; color: #64748B; font-size: 0.78rem; line-height: 1.45; }

/* Stage spacious redesign: keep the workflow page focused on the animated collaboration stage. */
.agent-detail-panel { display: none !important; }
.stage-route-progress { row-gap: 6px; }
.stage-canvas-header .panel-eyebrow { letter-spacing: 0.12em; }
@media (min-width: 1500px) {
  .agent-workstation { width: 222px; min-height: 118px; }
  .station-content { left: 5%; }
  .station-quiz { right: 5%; }
  .station-mindmap { left: 18%; }
  .station-code { right: 18%; }
}
@media (max-width: 1320px) {
  .agent-stage-layout { grid-template-columns: 1fr; }
  .agent-detail-panel { display: none; }
  .stage-stat-group { flex-wrap: wrap; justify-content: flex-end; }
  .output-dock-list { grid-template-columns: repeat(3, minmax(140px, 1fr)); }
}
@media (max-width: 980px) {
  .workflow-stage-page { overflow-y: auto; }
  .stage-topbar { align-items: flex-start; flex-direction: column; }
  .agent-stage-canvas { min-height: 780px; }
  .dispatch-stage { height: 700px; }
  .master-hub { top: 35%; }
  .station-content, .station-mindmap, .station-code, .station-quiz, .station-reading, .station-ppt { left: 50%; right: auto; transform: translateX(-50%); }
  .station-content { top: 10%; }
  .station-mindmap { top: 25%; }
  .station-code { top: 50%; }
  .station-quiz { top: 65%; }
  .station-reading { top: 80%; bottom: auto; }
  .station-ppt { top: 95%; bottom: auto; }
  .review-assembly-lane { position: relative; left: auto; bottom: auto; transform: none; flex-direction: column; margin-top: 660px; }
  .lane-arrow { width: 2px; height: 34px; }
  .output-dock-bar { flex-direction: column; align-items: stretch; }
  .output-dock-title { width: auto; }
  .output-dock-list { grid-template-columns: 1fr; }
}



/* ================= Phase 3 output dock separation fix =================
   资源产出区独立成底部模块，避免遮挡主体多智能体动画舞台。 */
.workflow-stage-page {
  overflow-y: auto;
  overflow-x: hidden;
  padding: 10px 18px 14px;
  gap: 10px;
}

.workflow-stage-page .stage-topbar {
  flex-shrink: 0;
}

.workflow-stage-page .agent-stage-layout {
  flex: 1 1 auto;
}

.workflow-stage-page .agent-stage-canvas {
  padding: 14px;
  display: flex;
  flex-direction: column;
}

.workflow-stage-page .stage-canvas-header {
  flex-shrink: 0;
}

.workflow-stage-page .dispatch-stage {
  flex: 1 1 auto;
  margin-top: 4px;
}

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
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.96);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(18px);
}

.output-dock-heading {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.output-dock-heading > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.output-dock-heading strong {
  color: #0F172A;
  font-size: 0.98rem;
  font-weight: 900;
  line-height: 1.2;
}

.output-dock-heading p {
  margin: 0;
  color: #64748B;
  font-size: 0.74rem;
  line-height: 1.5;
}

.output-dock-section .output-dock-list {
  display: grid;
  grid-template-columns: repeat(6, minmax(130px, 1fr));
  gap: 10px;
  min-width: 0;
}

.output-dock-section .output-dock-item {
  min-width: 0;
  min-height: 40px;
  padding: 4px 8px;
  border-radius: 10px;
  background: #F8FAFC;
}

.output-dock-section .output-dock-item > div {
  min-width: 0;
}

.output-dock-section .output-dock-item strong,
.output-dock-section .output-dock-item p {
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 1440px) {
  .output-dock-section {
    grid-template-columns: 1fr;
    gap: 10px;
    min-height: 0;
  }

  .output-dock-heading {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .output-dock-heading p {
    max-width: 360px;
    text-align: right;
  }

  .output-dock-section .output-dock-list {
    grid-template-columns: repeat(3, minmax(150px, 1fr));
  }
}

@media (max-width: 900px) {
  .workflow-stage-page {
    overflow: auto;
  }

  .output-dock-heading {
    flex-direction: column;
    align-items: flex-start;
  }

  .output-dock-heading p {
    text-align: left;
    max-width: none;
  }

  .output-dock-section .output-dock-list {
    grid-template-columns: 1fr;
  }
}

</style>
