<template>
  <div class="phase-view generating-view workflow-page">
    <!-- 顶部状态摘要 -->
    <header class="workflow-summary">
      <div class="summary-main">
        <div class="summary-title">
          <span class="summary-eyebrow">MULTI-AGENT WORKFLOW</span>
          <h2>资源生成工作流</h2>
          <p>{{ dagHeroMessage }}</p>
        </div>

        <div class="route-progress" aria-label="资源生成阶段">
          <template v-for="(step, index) in routeSteps" :key="step.key">
            <div class="route-step" :class="step.state">
              <span>{{ index + 1 }}</span>
              <strong>{{ step.label }}</strong>
            </div>

            <i
                v-if="index < routeSteps.length - 1"
                class="route-connector"
                :class="step.lineState"
            ></i>
          </template>
        </div>
      </div>

      <div class="summary-metrics">
        <div class="summary-progress">
          <span>总体进度</span>
          <strong>{{ overallProgress }}%</strong>

          <div class="summary-progress-track">
            <i :style="{ transform: `scaleX(${overallProgress / 100})` }"></i>
          </div>
        </div>

        <div class="summary-metric">
          <span>活跃智能体</span>
          <strong>
            {{ runningAgentCount }}
            <small>/{{ workflowAgentTotal }}</small>
          </strong>
        </div>

        <div class="summary-metric">
          <span>已交付资源</span>
          <strong>
            {{ generatedResources.length }}
            <small>项</small>
          </strong>
        </div>

        <button
            class="summary-log-button"
            type="button"
            @click="workflowLogDrawerVisible = true"
        >
          查看日志
          <ArrowRight class="h-4 w-4" />
        </button>
      </div>
    </header>

    <main class="workflow-main">
      <section class="workflow-workbench">
        <header class="workbench-header">
          <div>
            <span class="panel-eyebrow">实时协同视图</span>
            <h3>多智能体调用链</h3>
            <p>展示任务拆分、并行执行、结果回传、上下文交接与多模态资源生成过程。</p>
          </div>

          <div class="workbench-controls">
            <button
                v-if="generationError"
                class="workflow-error-status"
                type="button"
                :title="generationError"
                @click="workflowLogDrawerVisible = true"
            >
              <span></span>
              <strong>生成中断</strong>
              <em>查看详情</em>
              <ArrowRight class="h-4 w-4" />
            </button>

            <span v-else class="live-control">
              <i></i>
              SSE 实时追踪
            </span>

            <span class="plan-control">
              计划 {{ planReady ? '已就绪' : '生成中' }}
            </span>
          </div>
        </header>

        <div
            ref="flowCanvasRef"
            class="workflow-canvas"
            :class="{
            'has-measured-links': agentLinkPaths.length > 0,
            'is-running': runningAgentCount > 0,
          }"
        >
          <div class="canvas-grid"></div>
          <div class="canvas-glow canvas-glow-one"></div>
          <div class="canvas-glow canvas-glow-two"></div>

          <!-- 第一阶段：规划调度 -->
          <section class="workflow-stage planning-stage">
            <div class="stage-heading">
              <span class="stage-index">01</span>

              <div>
                <strong>任务规划与调度</strong>
                <p>解析学习需求，制定教学计划，并拆分多个资源生成任务。</p>
              </div>

              <em :class="`status-${planningNode.status}`">
                {{ getNodeStatusLabel(planningNode) }}
              </em>
            </div>

            <article
                ref="planningNodeRef"
                class="agent-card planning-agent-card"
                :class="[
                getAgentToneClass(planningNode.id),
                `status-${planningNode.status}`,
                {
                  'is-selected': selectedDagNodeId === planningNode.id,
                },
              ]"
                @click="handleAgentClick(planningNode.id)"
            >
              <div class="agent-card-running-line"></div>

              <header class="agent-card-header">
                <div class="agent-icon">
                  <component
                      :is="getWorkflowIcon(planningNode.id)"
                      class="h-4 w-4"
                  />
                </div>

                <div class="agent-identity">
                  <strong>{{ getWorkflowTitle(planningNode.id) }}</strong>
                  <span>{{ getAgentRoleName(planningNode.id) }}</span>
                </div>

                <span
                    class="node-status-badge compact"
                    :class="`status-${planningNode.status}`"
                >
                  <i></i>
                  {{ getNodeStatusLabel(planningNode) }}
                </span>
              </header>

              <div class="agent-current-task">
                <span>{{ getNodePhaseLabel(planningNode) }}</span>
                <p>{{ getNodeMessage(planningNode) }}</p>
              </div>

              <div
                  class="agent-execution-chain"
                  aria-label="智能体执行步骤"
              >
                <template
                    v-for="(step, index) in getAgentExecutionSteps(planningNode)"
                    :key="step.label"
                >
                  <div
                      class="execution-step"
                      :class="step.state"
                  >
                    <i></i>
                    <span>{{ step.label }}</span>
                  </div>

                  <b
                      v-if="index < getAgentExecutionSteps(planningNode).length - 1"
                  ></b>
                </template>
              </div>

              <div class="agent-event-preview">
                <span>最新事件</span>
                <p>{{ getLatestNodeEvent(planningNode) }}</p>
                <em>{{ getNodeEventCount(planningNode) }} 条事件</em>
              </div>

              <footer class="agent-card-footer">
                <span>{{ getNodeStageLabel(planningNode) }}</span>

                <div class="node-progress-track">
                  <i
                      :style="{
                      transform: `scaleX(${getNodeProgress(planningNode) / 100})`,
                    }"
                  ></i>
                </div>

                <b>{{ getNodeProgress(planningNode) }}%</b>
              </footer>
            </article>

            <div class="dispatch-bus" aria-hidden="true">
              <div class="dispatch-command">
                <span></span>
                <strong>任务分发</strong>
                <em>{{ parallelDispatchLabel }}</em>
              </div>
            </div>
          </section>

          <!-- Planning Agent 到基础资源 Agent 的动态连接线 -->
          <svg
              class="agent-link-svg"
              :viewBox="`0 0 ${linkCanvasSize.width} ${linkCanvasSize.height}`"
              preserveAspectRatio="none"
              aria-hidden="true"
          >
            <defs>
              <linearGradient
                  id="agentLinkGradient"
                  x1="0"
                  x2="1"
                  y1="0"
                  y2="1"
              >
                <stop
                    offset="0%"
                    stop-color="#5b7cfa"
                    stop-opacity="0.2"
                />
                <stop
                    offset="48%"
                    stop-color="#4f73e8"
                    stop-opacity="0.92"
                />
                <stop
                    offset="100%"
                    stop-color="#33b7a4"
                    stop-opacity="0.32"
                />
              </linearGradient>

              <filter
                  id="agentPacketGlow"
                  x="-100%"
                  y="-100%"
                  width="300%"
                  height="300%"
              >
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <path
                v-for="link in agentLinkPaths"
                :key="link.id"
                class="agent-link-path"
                :class="`status-${link.status}`"
                :d="link.d"
            />

            <g
                v-for="link in runningAgentLinkPaths"
                :key="`${link.id}-packets`"
                class="agent-packet-group"
            >
              <circle class="agent-data-packet" r="4">
                <animateMotion
                    :path="link.d"
                    dur="1.7s"
                    repeatCount="indefinite"
                />
              </circle>

              <circle
                  class="agent-data-packet packet-secondary"
                  r="3"
              >
                <animateMotion
                    :path="link.d"
                    dur="1.7s"
                    begin="0.65s"
                    repeatCount="indefinite"
                />
              </circle>
            </g>

            <circle
                v-for="link in agentLinkPaths"
                :key="`${link.id}-terminal`"
                class="agent-link-terminal"
                :class="`status-${link.status}`"
                :cx="link.x"
                :cy="link.y"
                r="4"
            />
          </svg>

          <!-- 第二阶段：基础资源并行执行 -->
          <section class="workflow-stage parallel-stage">
            <div class="stage-heading">
              <span class="stage-index">02</span>

              <div>
                <strong>基础资源并行执行层</strong>
                <p>多个专业智能体并发生成讲解、导图、题目、代码和阅读资源。</p>
              </div>

              <div class="stage-live-summary">
                <span>
                  <i class="running-dot"></i>
                  {{ activeBaseCount }} 执行中
                </span>

                <span>
                  {{ completedBaseCount }}/{{ parallelPoolNodes.length }} 已返回
                </span>
              </div>
            </div>

            <transition-group
                name="agent-station"
                tag="div"
                class="parallel-agent-grid"
            >
              <article
                  v-for="node in parallelPoolNodes"
                  :key="node.id"
                  :ref="el => setStationCardRef(node.id, el)"
                  class="agent-card"
                  :class="[
                  getAgentToneClass(node.id),
                  `status-${node.status}`,
                  {
                    'is-selected': selectedDagNodeId === node.id,
                    'has-artifact': hasGeneratedResource(node.id),
                  },
                ]"
                  @click="handleAgentClick(node.id)"
              >
                <div class="agent-card-running-line"></div>

                <header class="agent-card-header">
                  <div class="agent-icon">
                    <component
                        :is="getWorkflowIcon(node.id)"
                        class="h-4 w-4"
                    />
                  </div>

                  <div class="agent-identity">
                    <strong>{{ getWorkflowTitle(node.id) }}</strong>
                    <span>{{ getAgentRoleName(node.id) }}</span>
                  </div>

                  <span
                      class="node-status-badge compact"
                      :class="`status-${node.status}`"
                  >
                    <i></i>
                    {{ getNodeStatusLabel(node) }}
                  </span>
                </header>

                <div class="agent-current-task">
                  <span>{{ getNodePhaseLabel(node) }}</span>
                  <p>{{ getNodeMessage(node) }}</p>
                </div>

                <div
                    class="agent-execution-chain"
                    aria-label="智能体执行步骤"
                >
                  <template
                      v-for="(step, index) in getAgentExecutionSteps(node)"
                      :key="step.label"
                  >
                    <div
                        class="execution-step"
                        :class="step.state"
                    >
                      <i></i>
                      <span>{{ step.label }}</span>
                    </div>

                    <b
                        v-if="index < getAgentExecutionSteps(node).length - 1"
                    ></b>
                  </template>
                </div>

                <div class="agent-event-preview">
                  <span>最新事件</span>
                  <p>{{ getLatestNodeEvent(node) }}</p>
                  <em>{{ getNodeEventCount(node) }} 条事件</em>
                </div>

                <footer class="agent-card-footer">
                  <span>{{ getNodeStageLabel(node) }}</span>

                  <div class="node-progress-track">
                    <i
                        :style="{
                        transform: `scaleX(${getNodeProgress(node) / 100})`,
                      }"
                    ></i>
                  </div>

                  <b>{{ getNodeProgress(node) }}%</b>
                </footer>
              </article>
            </transition-group>
          </section>

          <!-- 并行资源回传 -->
          <div class="handoff-rail handoff-return-rail">
            <div class="handoff-packet packet-one">
              <i></i>
              <span>资源结果</span>
            </div>

            <div class="handoff-packet packet-two">
              <i></i>
              <span>运行快照</span>
            </div>

            <div class="handoff-packet packet-three">
              <i></i>
              <span>质量指标</span>
            </div>

            <strong>并行结果回传</strong>
          </div>

          <!-- 第三阶段：轻量协同交接，保留流程语义但不再使用外层卡片 -->
          <section class="workflow-stage coordination-stage">
            <div class="stage-heading">
              <span class="stage-index">03</span>

              <div>
                <strong>协同汇总与上下文交接</strong>
                <p>系统自动收集执行结果，完成结构检查，并组装下游生成上下文。</p>
              </div>

              <em :class="`status-${coordinatorNode.status}`">
                {{ getNodeStatusLabel(coordinatorNode) }}
              </em>
            </div>

            <div
                class="coordination-flow"
                :class="`status-${coordinatorNode.status}`"
            >
              <div class="coordination-flow-header">
                <div>
                  <strong>{{ getNodeMessage(coordinatorNode) }}</strong>
                </div>

                <div class="coordination-progress-copy">
                  <span>{{ getNodeStageLabel(coordinatorNode) }}</span>
                  <b>{{ getNodeProgress(coordinatorNode) }}%</b>
                </div>
              </div>

              <div class="coordination-steps">
                <template
                    v-for="(step, index) in coordinationSteps"
                    :key="step.label"
                >
                  <div
                      class="coordination-step"
                      :class="step.state"
                  >
                    <span>{{ index + 1 }}</span>

                    <div>
                      <strong>{{ step.label }}</strong>
                      <p>{{ step.description }}</p>
                    </div>

                    <em>{{ getStepStateLabel(step.state) }}</em>
                  </div>

                  <i
                      v-if="index < coordinationSteps.length - 1"
                      class="coordination-step-line"
                      :class="step.state"
                  ></i>
                </template>
              </div>

              <div class="coordination-progress-track">
                <i
                    :style="{
                    transform: `scaleX(${getNodeProgress(coordinatorNode) / 100})`,
                  }"
                ></i>
              </div>
            </div>
          </section>

          <!-- 上下文传递 -->
          <div
              v-if="showAggregationStage"
              class="context-handoff-line"
          >
            <span></span>

            <div>
              <i></i>

              <p>
                <strong>上下文 Handoff</strong>
                <em>教学计划 · 基础资源 · 用户画像 · 生成参数</em>
              </p>
            </div>
          </div>

          <!-- 第四阶段：多模态资源合成 -->
          <section
              v-if="showAggregationStage"
              class="workflow-stage aggregation-stage"
          >
            <div class="stage-heading">
              <span class="stage-index">04</span>

              <div>
                <strong>多模态资源合成层</strong>
                <p>基于基础资源结果生成教学课件与动画讲解。</p>
              </div>

              <div class="stage-live-summary">
                <span>
                  <i class="running-dot"></i>
                  {{ activeAggregationCount }} 执行中
                </span>

                <span>
                  {{ completedAggregationCount }}/{{ aggregationNodes.length }} 已完成
                </span>
              </div>
            </div>

            <div class="aggregation-agent-grid">
              <article
                  v-for="node in aggregationNodes"
                  :key="node.id"
                  class="agent-card aggregation-agent-card"
                  :class="[
                  getAgentToneClass(node.id),
                  `status-${node.status}`,
                  {
                    'is-selected': selectedDagNodeId === node.id,
                    'has-artifact': hasGeneratedResource(node.id),
                  },
                ]"
                  @click="handleAgentClick(node.id)"
              >
                <div class="agent-card-running-line"></div>

                <header class="agent-card-header">
                  <div class="agent-icon">
                    <component
                        :is="getWorkflowIcon(node.id)"
                        class="h-4 w-4"
                    />
                  </div>

                  <div class="agent-identity">
                    <strong>{{ getWorkflowTitle(node.id) }}</strong>
                    <span>{{ getAgentRoleName(node.id) }}</span>
                  </div>

                  <span
                      class="node-status-badge compact"
                      :class="`status-${node.status}`"
                  >
                    <i></i>
                    {{ getNodeStatusLabel(node) }}
                  </span>
                </header>

                <div class="agent-current-task">
                  <span>{{ getNodePhaseLabel(node) }}</span>
                  <p>{{ getNodeMessage(node) }}</p>
                </div>

                <div class="agent-execution-chain">
                  <template
                      v-for="(step, index) in getAgentExecutionSteps(node)"
                      :key="step.label"
                  >
                    <div
                        class="execution-step"
                        :class="step.state"
                    >
                      <i></i>
                      <span>{{ step.label }}</span>
                    </div>

                    <b
                        v-if="index < getAgentExecutionSteps(node).length - 1"
                    ></b>
                  </template>
                </div>

                <div class="agent-event-preview">
                  <span>最新事件</span>
                  <p>{{ getLatestNodeEvent(node) }}</p>
                  <em>{{ getNodeEventCount(node) }} 条事件</em>
                </div>

                <footer class="agent-card-footer">
                  <span>{{ getNodeStageLabel(node) }}</span>

                  <div class="node-progress-track">
                    <i
                        :style="{
                        transform: `scaleX(${getNodeProgress(node) / 100})`,
                      }"
                    ></i>
                  </div>

                  <b>{{ getNodeProgress(node) }}%</b>
                </footer>
              </article>
            </div>
          </section>

          <!-- 产物进入最终交付 -->
          <div class="delivery-merge-line" aria-hidden="true">
            <span></span>

            <div>
              <i></i>

              <p>
                <strong>产物合并</strong>
                <em>统一保存资源索引与生成结果</em>
              </p>
            </div>
          </div>

          <!-- 最终资源交付摘要，不再作为 Agent 卡片 -->
          <section class="workflow-stage delivery-stage">
            <div class="stage-heading">
              <span class="stage-index">
                {{ showAggregationStage ? '05' : '04' }}
              </span>

              <div>
                <strong>资源整合与交付</strong>
                <p>汇总生成结果、保存资源索引并构建最终学习资源包。</p>
              </div>

              <em :class="`status-${bundleNode.status}`">
                {{ getNodeStatusLabel(bundleNode) }}
              </em>
            </div>

            <div
                class="delivery-summary"
                :class="`status-${bundleNode.status}`"
            >
              <div class="delivery-icon">
                <component
                    :is="getWorkflowIcon(bundleNode.id)"
                    class="h-5 w-5"
                />
              </div>

              <div class="delivery-copy">
                <span>FINAL DELIVERY</span>
                <strong>个性化学习资源包</strong>
                <p>{{ getNodeMessage(bundleNode) }}</p>
              </div>

              <div class="delivery-count">
                <span>已接收产物</span>
                <strong>{{ generatedResources.length }}</strong>
              </div>

              <div class="delivery-progress">
                <div class="node-progress-track">
                  <i
                      :style="{
                      transform: `scaleX(${getNodeProgress(bundleNode) / 100})`,
                    }"
                  ></i>
                </div>

                <span>{{ getNodeStageLabel(bundleNode) }}</span>
                <b>{{ getNodeProgress(bundleNode) }}%</b>
              </div>

              <span
                  class="node-status-badge"
                  :class="`status-${bundleNode.status}`"
              >
                <i></i>
                {{ getNodeStatusLabel(bundleNode) }}
              </span>
            </div>
          </section>
        </div>
      </section>

      <!-- Agent 完整执行流程弹窗 -->
      <Teleport to="body">
        <transition name="detail-fade">
          <div
              v-if="detailPanelVisible && selectedDagNode"
              class="detail-overlay"
              @click="closeAgentDetail"
          >
            <aside
                class="agent-detail-panel"
                :class="getAgentToneClass(selectedDagNode.id)"
                role="dialog"
                aria-modal="true"
                aria-label="智能体完整执行流程"
                @click.stop
            >
              <header class="detail-header">
                <div class="detail-agent-icon">
                  <component
                      :is="getWorkflowIcon(selectedDagNode.id)"
                      class="h-5 w-5"
                  />
                </div>

                <div class="detail-agent-title">
                  <span>AGENT EXECUTION WORKFLOW</span>
                  <h3>{{ getWorkflowTitle(selectedDagNode.id) }}</h3>
                  <p>{{ getAgentRoleName(selectedDagNode.id) }}</p>
                </div>

                <span
                    class="detail-status"
                    :class="`status-${selectedDagNode.status}`"
                >
                  <i></i>
                  {{ getNodeStatusLabel(selectedDagNode) }}
                </span>

                <button
                    type="button"
                    aria-label="关闭详情"
                    @click="closeAgentDetail"
                >
                  ×
                </button>
              </header>

              <div class="detail-body">
                <!-- 左侧：Agent 执行概览 -->
                <div class="detail-overview">
                  <section class="detail-current-task">
                    <div class="detail-section-heading">
                      <div>
                        <span>当前运行任务</span>
                        <strong>{{ getNodePhaseLabel(selectedDagNode) }}</strong>
                      </div>

                      <b>{{ getNodeProgress(selectedDagNode) }}%</b>
                    </div>

                    <p>{{ getNodeDisplayMessage(selectedDagNode) }}</p>

                    <div class="detail-progress-row">
                      <div class="node-progress-track">
                        <i
                            :style="{
                            transform: `scaleX(${getNodeProgress(selectedDagNode) / 100})`,
                          }"
                        ></i>
                      </div>
                    </div>
                  </section>

                  <dl class="detail-metrics">
                    <div>
                      <dt>当前阶段</dt>
                      <dd>{{ getNodePhaseLabel(selectedDagNode) }}</dd>
                    </div>

                    <div>
                      <dt>运行耗时</dt>
                      <dd>{{ getNodeElapsedLabel(selectedDagNode) }}</dd>
                    </div>

                    <div>
                      <dt>最近更新</dt>
                      <dd>{{ getNodeTimeLabel(selectedDagNode) }}</dd>
                    </div>

                    <div>
                      <dt>成果状态</dt>
                      <dd>{{ getNodeArtifactStatus(selectedDagNode) }}</dd>
                    </div>
                  </dl>

                  <section class="detail-full-process">
                    <header class="detail-section-title">
                      <div>
                        <span>完整执行流程</span>
                        <p>展示该智能体从接收任务到成果交付的全部阶段。</p>
                      </div>

                      <em>
                        {{ completedExecutionStepCount(selectedDagNode) }}
                        /
                        {{ getAgentExecutionSteps(selectedDagNode).length }}
                      </em>
                    </header>

                    <div class="detail-process-list">
                      <article
                          v-for="(step, index) in getAgentExecutionSteps(selectedDagNode)"
                          :key="step.label"
                          class="detail-process-step"
                          :class="step.state"
                      >
                        <div class="detail-process-index">
                          <span>{{ index + 1 }}</span>
                          <i></i>
                        </div>

                        <div class="detail-process-copy">
                          <div>
                            <strong>{{ step.label }}</strong>
                            <em>{{ getStepStateLabel(step.state) }}</em>
                          </div>

                          <p>
                            {{ getExecutionStepDescription(selectedDagNode, index) }}
                          </p>
                        </div>
                      </article>
                    </div>
                  </section>

                  <section class="detail-io-grid">
                    <article>
                      <span>输入上下文</span>
                      <p>
                        {{ getNodeExecutionInputSummary(selectedDagNode) }}
                      </p>
                    </article>

                    <article>
                      <span>输出结果</span>
                      <p>
                        {{ getNodeOutputSummary(selectedDagNode) }}
                      </p>
                    </article>
                  </section>

                  <section
                      v-if="getMetricChips(selectedDagNode).length"
                      class="detail-metric-section"
                  >
                    <span>运行指标</span>

                    <div class="detail-metric-chips">
                      <em
                          v-for="chip in getMetricChips(selectedDagNode)"
                          :key="chip"
                      >
                        {{ chip }}
                      </em>
                    </div>
                  </section>
                </div>

                <!-- 右侧：完整事件时间线 -->
                <section class="detail-history">
                  <header class="detail-history-header">
                    <div>
                      <span>完整事件流</span>
                      <h4>Agent 运行记录</h4>
                      <p>按执行顺序展示该智能体收到的状态、阶段和结果事件。</p>
                    </div>

                    <em>{{ selectedNodeTimeline.length }} 条记录</em>
                  </header>

                  <div
                      v-if="selectedNodeTimeline.length"
                      class="timeline-stream"
                  >
                    <article
                        v-for="(item, index) in selectedNodeTimeline"
                        :key="item.id"
                        class="timeline-item"
                        :class="`is-${item.status}`"
                    >
                      <div class="timeline-axis">
                        <span>{{ index + 1 }}</span>
                        <i></i>
                      </div>

                      <div class="timeline-card">
                        <header>
                          <div>
                            <strong>{{ item.phaseLabel }}</strong>
                            <span>{{ getLogStatusLabel(item.status) }}</span>
                          </div>

                          <em>{{ formatEventTime(item.timestamp) }}</em>
                        </header>

                        <p>{{ item.message }}</p>
                      </div>
                    </article>
                  </div>

                  <div v-else class="timeline-empty">
                    <span></span>
                    <strong>等待运行事件</strong>
                    <p>该智能体尚未上报详细执行记录。</p>
                  </div>
                </section>
              </div>
            </aside>
          </div>
        </transition>
      </Teleport>
    </main>

    <!-- 日志抽屉 -->
    <Teleport to="body">
      <transition name="slide-over">
        <div
            v-if="workflowLogDrawerVisible"
            class="drawer-overlay"
            @click="workflowLogDrawerVisible = false"
        >
          <aside
              class="log-drawer"
              aria-label="实时调度日志"
              @click.stop
          >
            <header>
              <div>
                <span>WORKFLOW LOGS</span>
                <h3>实时调度日志</h3>
              </div>

              <button
                  type="button"
                  aria-label="关闭日志"
                  @click="workflowLogDrawerVisible = false"
              >
                ×
              </button>
            </header>

            <div class="drawer-log-list">
              <article
                  v-for="item in workflowLogItems"
                  :key="item.id"
                  class="drawer-log-item"
                  :class="`is-${item.status}`"
              >
                <span class="drawer-log-dot"></span>

                <div>
                  <strong>{{ item.title }}</strong>
                  <p>{{ item.message }}</p>
                </div>
              </article>

              <p
                  v-if="!workflowLogItems.length"
                  class="empty-log"
              >
                等待智能体上报运行日志
              </p>
            </div>
          </aside>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import {
  computed,
  ref,
  type Component,
} from 'vue'

import {
  PhTarget as Aim,
  PhArrowRight as ArrowRight,
  PhArchive as Box,
  PhCpu as Cpu,
  PhChartBar as DataBoard,
  PhFileText as Document,
  PhNotePencil as EditPen,
  PhBookOpen as Reading,
  PhShareNetwork as Share,
  PhFilmStrip as VideoIcon,
} from '@phosphor-icons/vue'

import type {
  ResourceAgentId,
} from '@/features/resource/model/resource'

import {
  useFlow,
} from '../composables/useFlow'

import {
  COORDINATOR_AGENT_ID,
  CARTOON_AGENT_ID,
  PPT_AGENT_ID,
  BUNDLE_AGENT_ID,
  SYSTEM_AGENT_IDS,
  AGENT_DISPLAY,
  type DagNodeState,
} from '../model/catalog'

type GeneratedResourceItem = Record<string, any> & {
  generatedAt?: string
  displayOrder?: number
}

type ExecutionStepState = 'waiting' | 'running' | 'success' | 'failed'

type ExecutionStep = {
  label: string
  state: ExecutionStepState
}

type CoordinationStep = ExecutionStep & {
  description: string
}

type DetailTimelineItem = {
  id: string
  phaseLabel: string
  message: string
  status: DagNodeState['status']
  timestamp?: number
}

const props = defineProps<{
  naturalInput: string
  dagNodeStates: Record<string, DagNodeState>
  selectedDagNodeId: string | null
  overallProgress: number
  latestWorkflowMessage: string
  generatedResources: GeneratedResourceItem[]
  dagSelectedAgentIds: ResourceAgentId[]
  generationError: string | null
  planReady: boolean
  visibleWorkflowNodes: DagNodeState[]
}>()

const emit = defineEmits<{
  selectNode: [id: string]
}>()

const workflowLogDrawerVisible = ref(false)
const detailPanelVisible = ref(false)

const workflowIconMap: Record<string, Component> = {
  planning: Aim,
  coordinator: Share,
  content: Document,
  mindmap: Share,
  quiz: EditPen,
  code: Cpu,
  reading: Reading,
  ppt: DataBoard,
  cartoon: VideoIcon,
  bundle: Box,
}

const workflowTitleMap: Record<string, string> = {
  planning: '教学计划',
  coordinator: '协同汇总',
  content: '课程讲解',
  mindmap: '思维导图',
  quiz: '练习题',
  code: '代码示例',
  reading: '拓展阅读',
  ppt: '教学课件',
  cartoon: '动画讲解',
  bundle: '资源包交付',
}

const agentRoleMap: Record<string, string> = {
  planning: 'Planning Agent',
  coordinator: 'Coordination Pipeline',
  content: 'Content Agent',
  mindmap: 'Mindmap Agent',
  quiz: 'Quiz Agent',
  code: 'Code Agent',
  reading: 'Reading Agent',
  ppt: 'PPT Agent',
  cartoon: 'Cartoon Agent',
  bundle: 'Delivery Pipeline',
}

const agentToneMap: Record<string, string> = {
  planning: 'tone-indigo',
  coordinator: 'tone-cyan',
  content: 'tone-blue',
  mindmap: 'tone-violet',
  quiz: 'tone-rose',
  code: 'tone-amber',
  reading: 'tone-emerald',
  ppt: 'tone-indigo',
  cartoon: 'tone-pink',
  bundle: 'tone-cyan',
}

function getWorkflowIcon(id: string) {
  return workflowIconMap[id] || Document
}

function getWorkflowTitle(id: string) {
  return workflowTitleMap[id] || AGENT_DISPLAY[id]?.label || id
}

function getAgentRoleName(id: string) {
  return agentRoleMap[id] || `${id} Agent`
}

function getAgentToneClass(id: string) {
  return agentToneMap[id] || 'tone-blue'
}

function handleAgentClick(id: string) {
  detailPanelVisible.value = true
  emit('selectNode', id)
}

function closeAgentDetail() {
  detailPanelVisible.value = false
}

const baseGenerationAgentIds = computed(() => {
  return props.dagSelectedAgentIds.filter(
      id => ![
        PPT_AGENT_ID,
        CARTOON_AGENT_ID,
      ].includes(id),
  )
})

const parallelPoolNodes = computed(() => {
  return baseGenerationAgentIds.value.map(agentId => {
    return getStageNode(agentId)
  })
})

const {
  canvasRef: flowCanvasRef,
  sourceRef: planningNodeRef,
  canvasSize: linkCanvasSize,
  links: agentLinkPaths,
  setCardRef: setStationCardRef,
} = useFlow(parallelPoolNodes)

void flowCanvasRef
void planningNodeRef

const aggregationNodes = computed(() => {
  const nodes: DagNodeState[] = []

  if (
      props.dagSelectedAgentIds.includes(
          PPT_AGENT_ID as ResourceAgentId,
      )
  ) {
    nodes.push(getStageNode(PPT_AGENT_ID))
  }

  if (
      props.dagSelectedAgentIds.includes(
          CARTOON_AGENT_ID as ResourceAgentId,
      )
  ) {
    nodes.push(getStageNode(CARTOON_AGENT_ID))
  }

  return nodes
})

const showAggregationStage = computed(() => {
  return aggregationNodes.value.length > 0
})

const planningNode = computed(() => {
  return getStageNode('planning')
})

const coordinatorNode = computed(() => {
  return getStageNode(COORDINATOR_AGENT_ID)
})

const bundleNode = computed(() => {
  return getStageNode(BUNDLE_AGENT_ID)
})

const selectedDagNode = computed(() => {
  if (!props.selectedDagNodeId) {
    return null
  }

  return (
      props.dagNodeStates[props.selectedDagNodeId]
      || getStageNode(props.selectedDagNodeId)
  )
})

const selectedNodeTimeline = computed<DetailTimelineItem[]>(() => {
  if (!selectedDagNode.value) {
    return []
  }

  return getNodeFullTimeline(selectedDagNode.value)
})

const runningAgentCount = computed(() => {
  return props.visibleWorkflowNodes.filter(node => {
    return (
        node.id !== COORDINATOR_AGENT_ID
        && node.id !== BUNDLE_AGENT_ID
        && node.status === 'running'
    )
  }).length
})

const workflowAgentTotal = computed(() => {
  return props.dagSelectedAgentIds.length + 1
})

const activeBaseCount = computed(() => {
  return parallelPoolNodes.value.filter(node => {
    return node.status === 'running'
  }).length
})

const completedBaseCount = computed(() => {
  return parallelPoolNodes.value.filter(node => {
    return ['success', 'skipped'].includes(node.status)
  }).length
})

const activeAggregationCount = computed(() => {
  return aggregationNodes.value.filter(node => {
    return node.status === 'running'
  }).length
})

const completedAggregationCount = computed(() => {
  return aggregationNodes.value.filter(node => {
    return ['success', 'skipped'].includes(node.status)
  }).length
})

const runningAgentLinkPaths = computed(() => {
  return agentLinkPaths.value.filter(link => {
    return link.status === 'running'
  })
})

const parallelDispatchLabel = computed(() => {
  if (planningNode.value.status === 'running') {
    return '正在拆分任务'
  }

  if (planningNode.value.status === 'success') {
    if (activeBaseCount.value > 0) {
      return `${activeBaseCount.value} 个 Agent 已启动`
    }

    if (
        parallelPoolNodes.value.length > 0
        && completedBaseCount.value === parallelPoolNodes.value.length
    ) {
      return '基础任务已全部返回'
    }

    return '任务已分发'
  }

  if (planningNode.value.status === 'failed') {
    return '任务分发中断'
  }

  return '等待教学计划'
})

const coordinationSteps = computed<CoordinationStep[]>(() => {
  const node = coordinatorNode.value
  const progress = getNodeProgress(node)

  const labels = [
    {
      label: '收集执行结果',
      description: `${completedBaseCount.value}/${parallelPoolNodes.value.length} 个基础资源已返回`,
    },
    {
      label: '检查资源结构',
      description: '检查资源完整性、格式和下游依赖',
    },
    {
      label: '组装生成上下文',
      description: '构建课件与动画智能体所需输入',
    },
  ]

  return labels.map((item, index) => {
    let state: ExecutionStepState = 'waiting'

    if (node.status === 'success') {
      state = 'success'
    } else if (node.status === 'failed') {
      const currentIndex = Math.min(
          labels.length - 1,
          Math.floor(progress / (100 / labels.length)),
      )

      if (index < currentIndex) {
        state = 'success'
      } else if (index === currentIndex) {
        state = 'failed'
      }
    } else if (node.status === 'running') {
      const currentIndex = Math.min(
          labels.length - 1,
          Math.floor(progress / (100 / labels.length)),
      )

      if (index < currentIndex) {
        state = 'success'
      } else if (index === currentIndex) {
        state = 'running'
      }
    }

    return {
      ...item,
      state,
    }
  })
})

const dagHeroMessage = computed(() => {
  const runningNode = Object.values(props.dagNodeStates).find(node => {
    return (
        node.id !== COORDINATOR_AGENT_ID
        && node.id !== BUNDLE_AGENT_ID
        && node.status === 'running'
    )
  })

  if (runningNode) {
    return (
        runningNode.currentMessage
        || `${getWorkflowTitle(runningNode.id)}正在执行`
    )
  }

  if (coordinatorNode.value.status === 'running') {
    return '正在汇总基础资源并构建下游智能体上下文'
  }

  if (bundleNode.value.status === 'running') {
    return '正在整合并打包个性化学习资源'
  }

  const allCompleted = props.visibleWorkflowNodes.length > 0
      && props.visibleWorkflowNodes.every(node => {
        return ['success', 'skipped'].includes(node.status)
      })

  if (allCompleted) {
    return '所有智能体任务已完成，资源包已准备就绪'
  }

  return (
      props.latestWorkflowMessage
      || '多智能体正在协同生成个性化学习资源'
  )
})

const routeSteps = computed(() => {
  const planning = planningNode.value
  const coordinator = coordinatorNode.value
  const bundle = bundleNode.value

  const baseRunning = parallelPoolNodes.value.some(node => {
    return node.status === 'running'
  })

  const baseDone = parallelPoolNodes.value.length > 0
      && parallelPoolNodes.value.every(node => {
        return ['success', 'failed', 'skipped'].includes(node.status)
      })

  const aggregationRunning = aggregationNodes.value.some(node => {
    return node.status === 'running'
  })

  const aggregationDone = aggregationNodes.value.length === 0
      || aggregationNodes.value.every(node => {
        return ['success', 'failed', 'skipped'].includes(node.status)
      })

  const steps = [
    {
      key: 'planning',
      label: '任务规划',
      state: getRouteNodeState(planning),
      lineState: planning.status === 'success'
          ? 'done'
          : planning.status === 'running'
              ? 'active'
              : '',
    },
    {
      key: 'parallel',
      label: '并行生成',
      state: baseDone
          ? 'done'
          : baseRunning
              ? 'active'
              : '',
      lineState: baseDone || coordinator.status === 'running'
          ? 'done'
          : baseRunning
              ? 'active'
              : '',
    },
    {
      key: 'coordination',
      label: '协同交接',
      state: getRouteNodeState(coordinator),
      lineState: coordinator.status === 'success'
          ? 'done'
          : coordinator.status === 'running'
              ? 'active'
              : '',
    },
  ]

  if (showAggregationStage.value) {
    steps.push({
      key: 'aggregation',
      label: '多模态合成',
      state: aggregationDone
          ? 'done'
          : aggregationRunning
              ? 'active'
              : '',
      lineState: aggregationDone || bundle.status === 'running'
          ? 'done'
          : aggregationRunning
              ? 'active'
              : '',
    })
  }

  steps.push({
    key: 'bundle',
    label: '资源交付',
    state: getRouteNodeState(bundle),
    lineState: '',
  })

  return steps
})

const workflowLogItems = computed(() => {
  const items: Array<{
    id: string
    title: string
    message: string
    status: DagNodeState['status']
  }> = []

  if (props.generationError) {
    items.push({
      id: 'global-generation-error',
      title: '资源生成任务',
      message: props.generationError,
      status: 'failed',
    })
  }

  props.visibleWorkflowNodes.forEach(node => {
    const eventLogs = node.eventLogs || []

    if (eventLogs.length) {
      eventLogs.slice(-5).forEach(log => {
        items.push({
          id: log.id,
          title: `${getWorkflowTitle(node.id)} · ${getLogPhaseLabel(log.phase)}`,
          message: log.message,
          status: log.status || node.status,
        })
      })

      return
    }

    if (node.stepHistory?.length) {
      node.stepHistory.slice(-3).forEach((step, index) => {
        items.push({
          id: `${node.id}-${index}-${step}`,
          title: getWorkflowTitle(node.id),
          message: step,
          status: node.status,
        })
      })
    }
  })

  return items
})

function getRouteNodeState(node: DagNodeState) {
  if (node.status === 'success') {
    return 'done'
  }

  if (node.status === 'running') {
    return 'active'
  }

  if (node.status === 'failed') {
    return 'failed'
  }

  return ''
}

function getStageNode(id: string): DagNodeState {
  return props.dagNodeStates[id] || {
    id,
    label: AGENT_DISPLAY[id]?.label || id,
    icon: AGENT_DISPLAY[id]?.icon || '✨',
    status: 'waiting',
    progress: 0,
    currentMessage: '',
    stepHistory: [],
    eventLogs: [],
    isSystem: SYSTEM_AGENT_IDS.includes(id),
  }
}

function hasGeneratedResource(type: string) {
  const resourceReady = props.generatedResources.some(resource => {
    return resource.type === type
  })

  const nodeReady = props.dagNodeStates[type]?.status === 'success'

  return resourceReady || nodeReady
}

function getNodeStatusLabel(node: DagNodeState) {
  if (node.status === 'failed') {
    return '执行失败'
  }

  if (node.status === 'skipped') {
    return '已跳过'
  }

  if (node.status === 'success') {
    return '已完成'
  }

  if (node.status === 'running') {
    return '执行中'
  }

  return '等待调度'
}

function getNodeProgress(node: DagNodeState) {
  if (node.status === 'success') {
    return 100
  }

  if (
      node.status === 'waiting'
      || node.status === 'skipped'
  ) {
    return 0
  }

  return Math.max(
      0,
      Math.min(
          100,
          Math.round(node.progress || 0),
      ),
  )
}

function getNodeMessage(node: DagNodeState) {
  if (node.status === 'success') {
    return getNodeSuccessMessage(node)
  }

  if (node.status === 'failed') {
    return node.currentMessage?.trim() || '智能体执行失败'
  }

  if (node.status === 'skipped') {
    return '该智能体已跳过'
  }

  if (node.status === 'running') {
    const message = node.currentMessage?.trim()

    if (
        message
        && /^(planning|content|mindmap|quiz|code|reading|ppt|cartoon|bundle|coordinator)\s+(completed|finished|done)/i.test(message)
    ) {
      return getNodeRunningFallback(node)
    }

    return message || getNodeRunningFallback(node)
  }

  return getNodeWaitingMessage(node)
}

function getNodeSuccessMessage(node: DagNodeState) {
  if (node.id === 'planning') {
    return '教学计划已完成，任务已分发'
  }

  if (node.id === COORDINATOR_AGENT_ID) {
    return '资源检查完成，下游上下文已准备'
  }

  if (node.id === BUNDLE_AGENT_ID) {
    return '个性化学习资源包已生成'
  }

  if (node.id === PPT_AGENT_ID) {
    return '教学课件已生成'
  }

  if (node.id === CARTOON_AGENT_ID) {
    return '动画讲解已生成'
  }

  return '资源已生成并返回'
}

function getNodeRunningFallback(node: DagNodeState) {
  if (node.id === 'planning') {
    return '正在分析需求并拆分资源任务'
  }

  if (node.id === COORDINATOR_AGENT_ID) {
    return '正在检查资源并组装下游上下文'
  }

  if (node.id === BUNDLE_AGENT_ID) {
    return '正在汇总并打包学习资源'
  }

  if (node.id === PPT_AGENT_ID) {
    return '正在生成教学课件'
  }

  if (node.id === CARTOON_AGENT_ID) {
    return '正在生成动画讲解'
  }

  return '正在生成个性化学习资源'
}

function getNodeWaitingMessage(node: DagNodeState) {
  if (node.id === 'planning') {
    return '等待启动任务规划'
  }

  if (node.id === COORDINATOR_AGENT_ID) {
    return '等待基础资源返回'
  }

  if (node.id === BUNDLE_AGENT_ID) {
    return '等待上游资源全部就绪'
  }

  if (
      node.id === PPT_AGENT_ID
      || node.id === CARTOON_AGENT_ID
  ) {
    return '等待基础资源与教学计划'
  }

  return '等待 Planning Agent 分发任务'
}

function getNodeStageLabel(node: DagNodeState) {
  if (node.status === 'success') {
    if (node.id === BUNDLE_AGENT_ID) {
      return '资源交付完成'
    }

    return '任务已完成'
  }

  if (node.status === 'failed') {
    return '协同执行中断'
  }

  if (node.status === 'skipped') {
    return '该任务已跳过'
  }

  if (node.status === 'running') {
    if (node.id === 'planning') {
      return '正在规划与分发'
    }

    if (node.id === COORDINATOR_AGENT_ID) {
      return '正在汇总与交接'
    }

    if (node.id === BUNDLE_AGENT_ID) {
      return '正在整合资源'
    }

    if (
        node.id === PPT_AGENT_ID
        || node.id === CARTOON_AGENT_ID
    ) {
      return '正在合成多模态资源'
    }

    return '正在执行资源任务'
  }

  if (node.id === BUNDLE_AGENT_ID) {
    return '等待所有产物'
  }

  if (
      node.id === PPT_AGENT_ID
      || node.id === CARTOON_AGENT_ID
  ) {
    return '等待上游上下文'
  }

  return '等待任务调度'
}

function getNodePhaseLabel(node: DagNodeState): string {
  const phaseMap: Record<string, string> = {
    queued: '等待调度',
    planning: '任务规划',
    planning_research: '规划资料核验',
    plan_ready: '计划就绪',
    generation_started: '任务已启动',
    working: '内容生成',
    heartbeat: '持续生成',
    reading_research: '资料检索',
    validation: '结构校验',
    persistence: '成果保存',
    artifact_saved: '成果已交付',
    coordination: '结果汇总',
    aggregation_ready: '聚合准备',
    aggregation: '资源聚合',
    generation: '任务完成',
    timeout: '执行超时',
    failed: '执行失败',
  }

  if (node.phase && node.phase in phaseMap) {
    return phaseMap[node.phase]!
  }

  if (node.status === 'waiting') {
    return '等待上游'
  }

  if (node.status === 'success') {
    return '执行完成'
  }

  if (node.status === 'failed') {
    return '执行异常'
  }

  if (node.id === 'planning') {
    return '计划编排'
  }

  if (node.id === COORDINATOR_AGENT_ID) {
    return '协同汇总'
  }

  if (node.id === BUNDLE_AGENT_ID) {
    return '资源打包'
  }

  return '资源生成'
}

function getNodeDisplayMessage(node: DagNodeState) {
  return node.currentMessage?.trim() || getNodeMessage(node)
}

function getNodeArtifactStatus(node: DagNodeState) {
  if (node.status === 'failed') {
    return '未交付成果'
  }

  if (node.status === 'skipped') {
    return '已跳过'
  }

  if (node.id === 'planning') {
    return node.status === 'success'
        ? '教学计划已生成'
        : '计划生成中'
  }

  if (node.id === COORDINATOR_AGENT_ID) {
    return node.status === 'success'
        ? '上下文交接已完成'
        : '等待结果汇总'
  }

  if (node.id === BUNDLE_AGENT_ID) {
    return node.status === 'success'
        ? '最终资源包已交付'
        : '资源包尚未完成'
  }

  if (hasGeneratedResource(node.id)) {
    return '资源已交付'
  }

  if (node.status === 'running') {
    return '成果生成中'
  }

  return '等待生成'
}

function getNodeExecutionInputSummary(node: DagNodeState) {
  if (node.id === 'planning') {
    return '学习需求、用户画像、课程范围、资源偏好与已选智能体'
  }

  if (node.id === COORDINATOR_AGENT_ID) {
    return '教学计划、基础资源执行结果、Agent 状态和质量指标'
  }

  if (node.id === BUNDLE_AGENT_ID) {
    return '基础资源、多模态资源、持久化结果和资源元数据'
  }

  if (node.id === PPT_AGENT_ID) {
    return '教学计划、课程讲解、思维导图、练习题与个性化参数'
  }

  if (node.id === CARTOON_AGENT_ID) {
    return '教学计划、基础资源、动画参数、讲解风格与用户画像'
  }

  return '学习需求、用户画像、教学计划与知识库检索上下文'
}

function getNodeOutputSummary(node: DagNodeState) {
  if (node.id === 'planning') {
    return '教学大纲、任务拆分结果、Agent 分工与依赖关系'
  }

  if (node.id === COORDINATOR_AGENT_ID) {
    return '基础资源摘要、质量检查结果和下游生成上下文'
  }

  if (node.id === BUNDLE_AGENT_ID) {
    return node.status === 'success'
        ? '最终资源包、资源索引和可预览结果'
        : '等待上游资源后构建最终资源包'
  }

  if (node.id === PPT_AGENT_ID) {
    return hasGeneratedResource(node.id)
        ? '教学课件已生成'
        : '教学课件生成中'
  }

  if (node.id === CARTOON_AGENT_ID) {
    return hasGeneratedResource(node.id)
        ? '动画视频已生成'
        : '动画讲解生成中'
  }

  return hasGeneratedResource(node.id)
      ? '基础资源已生成并保存'
      : '基础资源生成中'
}

function formatElapsed(ms?: number | null) {
  if (ms == null || ms < 0) {
    return '未开始'
  }

  const seconds = Math.floor(ms / 1000)

  if (seconds < 60) {
    return `${seconds}s`
  }

  const minutes = Math.floor(seconds / 60)
  const restSeconds = seconds % 60

  return `${minutes}m ${restSeconds}s`
}

function getNodeElapsedLabel(node: DagNodeState) {
  if (node.elapsedMs != null) {
    return formatElapsed(node.elapsedMs)
  }

  if (node.status === 'running') {
    return '进行中'
  }

  return '未开始'
}

function getNodeTimeLabel(node: DagNodeState) {
  if (node.status === 'waiting') {
    return '等待上游'
  }

  if (!node.lastUpdatedAt) {
    return node.status === 'running'
        ? '刚刚更新'
        : formatElapsed(node.elapsedMs)
  }

  const seconds = Math.max(
      0,
      Math.floor(
          (Date.now() - node.lastUpdatedAt) / 1000,
      ),
  )

  if (seconds < 3) {
    return '刚刚更新'
  }

  if (seconds < 60) {
    return `${seconds}s 前`
  }

  return `${Math.floor(seconds / 60)}m 前`
}

function getMetricChips(node: DagNodeState) {
  const metrics = node.metrics || {}

  return Object.entries(metrics)
      .filter(([, value]) => {
        return (
            value !== null
            && value !== undefined
            && value !== ''
        )
      })
      .slice(0, 8)
      .map(([key, value]) => {
        return `${key}: ${String(value)}`
      })
}

function getNodeEventCount(node: DagNodeState) {
  if (node.eventLogs?.length) {
    return node.eventLogs.length
  }

  return node.stepHistory?.length || 0
}

function getLatestNodeEvent(node: DagNodeState) {
  const eventLogs = node.eventLogs || []

  if (eventLogs.length) {
    const latestEvent = eventLogs[eventLogs.length - 1]
    return latestEvent?.message || getNodeMessage(node)
  }

  const stepHistory = node.stepHistory || []

  if (stepHistory.length) {
    return stepHistory[stepHistory.length - 1]
  }

  return getNodeMessage(node)
}

function getLogPhaseLabel(phase?: string): string {
  const phaseMap: Record<string, string> = {
    queued: '等待调度',
    planning: '任务规划',
    planning_research: '资料核验',
    plan_ready: '计划就绪',
    generation_started: '启动任务',
    working: '资源生成',
    heartbeat: '生成心跳',
    reading_research: '资料检索',
    validation: '结构校验',
    persistence: '成果保存',
    artifact_saved: '成果交付',
    coordination: '结果汇总',
    aggregation_ready: '聚合就绪',
    aggregation: '资源聚合',
    generation: '任务完成',
    timeout: '执行超时',
    failed: '执行失败',
  }

  return phase
      ? phaseMap[phase] || phase
      : '运行状态'
}

function getLogStatusLabel(
    status?: DagNodeState['status'],
) {
  if (status === 'success') {
    return '已完成'
  }

  if (status === 'failed') {
    return '执行失败'
  }

  if (status === 'skipped') {
    return '已跳过'
  }

  if (status === 'running') {
    return '进行中'
  }

  return '等待中'
}

function formatEventTime(timestamp?: number) {
  if (!timestamp) {
    return '阶段记录'
  }

  const date = new Date(timestamp)

  if (Number.isNaN(date.getTime())) {
    return '阶段记录'
  }

  return date.toLocaleTimeString('zh-CN', {
    hour12: false,
  })
}

function getAgentExecutionSteps(
    node: DagNodeState,
): ExecutionStep[] {
  const labels = getExecutionStepLabels(node)

  return labels.map((label, index) => {
    return {
      label,
      state: getExecutionStepState(
          node,
          index,
          labels.length,
      ),
    }
  })
}

function getExecutionStepLabels(node: DagNodeState) {
  if (node.id === 'planning') {
    return [
      '理解学习需求',
      '构建教学计划',
      '拆分资源任务',
      '分发智能体任务',
    ]
  }

  if (node.id === COORDINATOR_AGENT_ID) {
    return [
      '收集执行结果',
      '检查资源结构',
      '组装生成上下文',
      '完成上下文交接',
    ]
  }

  if (node.id === BUNDLE_AGENT_ID) {
    return [
      '收集生成产物',
      '建立资源索引',
      '统一打包资源',
      '完成资源交付',
    ]
  }

  if (node.id === PPT_AGENT_ID) {
    return [
      '接收上游上下文',
      '设计课件大纲',
      '生成课件页面',
      '渲染教学课件',
    ]
  }

  if (node.id === CARTOON_AGENT_ID) {
    return [
      '接收上游上下文',
      '设计动画分镜',
      '生成动画内容',
      '渲染教学视频',
    ]
  }

  return [
    '接收生成任务',
    '生成资源内容',
    '校验资源结果',
    '保存并回传成果',
  ]
}

function getExecutionStepState(
    node: DagNodeState,
    index: number,
    total: number,
): ExecutionStepState {
  if (node.status === 'success') {
    return 'success'
  }

  if (node.status === 'failed') {
    const failedIndex = Math.min(
        total - 1,
        Math.floor(
            getNodeProgress(node) / (100 / total),
        ),
    )

    if (index < failedIndex) {
      return 'success'
    }

    if (index === failedIndex) {
      return 'failed'
    }

    return 'waiting'
  }

  if (
      node.status === 'waiting'
      || node.status === 'skipped'
  ) {
    return 'waiting'
  }

  const progress = getNodeProgress(node)
  const stepSize = 100 / total
  const currentIndex = Math.min(
      total - 1,
      Math.floor(progress / stepSize),
  )

  if (index < currentIndex) {
    return 'success'
  }

  if (index === currentIndex) {
    return 'running'
  }

  return 'waiting'
}

function completedExecutionStepCount(node: DagNodeState) {
  return getAgentExecutionSteps(node).filter(step => {
    return step.state === 'success'
  }).length
}

function getStepStateLabel(state: ExecutionStepState) {
  if (state === 'success') {
    return '已完成'
  }

  if (state === 'running') {
    return '执行中'
  }

  if (state === 'failed') {
    return '失败'
  }

  return '等待中'
}

function getExecutionStepDescription(
    node: DagNodeState,
    index: number,
) {
  if (node.id === 'planning') {
    return [
      '解析学习目标、课程主题、用户画像和资源偏好。',
      '规划知识结构、教学顺序和资源覆盖范围。',
      '将教学计划拆分为多个可以并行执行的资源任务。',
      '向已启用的资源智能体发送任务和执行上下文。',
    ][index] || ''
  }

  if (node.id === PPT_AGENT_ID) {
    return [
      '读取教学计划、基础资源和个性化学习参数。',
      '设计章节结构、页面顺序和每页教学重点。',
      '生成标题、正文、图示和教学内容布局。',
      '完成课件文件渲染、保存和资源回传。',
    ][index] || ''
  }

  if (node.id === CARTOON_AGENT_ID) {
    return [
      '读取教学目标、基础内容和动画生成配置。',
      '规划场景顺序、动画过程、旁白和重点展示。',
      '生成动画页面、时间线和动态教学内容。',
      '完成视频渲染、文件保存和资源回传。',
    ][index] || ''
  }

  return [
    '接收 Planning Agent 分发的任务和教学上下文。',
    '根据资源类型生成符合用户画像的学习内容。',
    '检查资源结构、内容完整性和格式正确性。',
    '保存最终成果，并向工作流返回资源信息。',
  ][index] || ''
}

function getNodeFullTimeline(
    node: DagNodeState,
): DetailTimelineItem[] {
  const eventLogs = node.eventLogs || []

  if (eventLogs.length) {
    return eventLogs.map((log, index) => ({
      id: log.id || `${node.id}-event-${index}`,
      phaseLabel: getLogPhaseLabel(log.phase),
      message: log.message,
      status: log.status || node.status,
      timestamp: log.timestamp,
    }))
  }

  const stepHistory = node.stepHistory || []

  if (stepHistory.length) {
    return stepHistory.map((step, index) => ({
      id: `${node.id}-history-${index}`,
      phaseLabel: `执行阶段 ${index + 1}`,
      message: step,
      status: index === stepHistory.length - 1
          ? node.status
          : 'success',
    }))
  }

  return [
    {
      id: `${node.id}-current`,
      phaseLabel: getNodePhaseLabel(node),
      message: getNodeMessage(node),
      status: node.status,
      timestamp: node.lastUpdatedAt,
    },
  ]
}
</script>

<style scoped>
.workflow-page,
.workflow-page * {
  box-sizing: border-box;
}

.workflow-page {
  --workflow-text: #142033;
  --workflow-text-secondary: #475569;
  --workflow-muted: #718096;
  --workflow-faint: #94a3b8;
  --workflow-border: #dfe6ef;
  --workflow-border-strong: #cbd6e4;
  --workflow-surface: #ffffff;
  --workflow-surface-soft: #f7f9fc;

  width: 100%;
  max-width: 100%;
  min-width: 0;
  padding: 18px 22px 60px;
  overflow-x: hidden;
  color: var(--workflow-text);
  background: transparent;
}

.workflow-summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: center;
  padding: 5px 0 16px;
  border-bottom: 1px solid var(--workflow-border);
}

.summary-main {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 34px;
}

.summary-title {
  min-width: 260px;
}

.summary-eyebrow,
.panel-eyebrow {
  display: block;
  color: #718096;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.1em;
}

.summary-title h2 {
  margin: 5px 0 0;
  color: var(--workflow-text);
  font-size: 21px;
  font-weight: 800;
  line-height: 1.25;
  letter-spacing: -0.02em;
}

.summary-title p {
  max-width: 430px;
  margin: 5px 0 0;
  overflow: hidden;
  color: var(--workflow-muted);
  font-size: 13px;
  line-height: 1.5;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.route-progress {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
}

.route-step {
  display: inline-flex;
  height: 31px;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  border: 1px solid #e3e8ef;
  border-radius: 8px;
  color: #7e8a9b;
  background: #f8fafc;
  white-space: nowrap;
  transition:
      border-color 180ms ease,
      color 180ms ease,
      background-color 180ms ease;
}

.route-step > span {
  display: grid;
  width: 18px;
  height: 18px;
  place-items: center;
  border-radius: 50%;
  color: #7f8b9d;
  background: #e7ecf2;
  font-size: 10px;
  font-weight: 800;
}

.route-step strong {
  font-size: 11px;
  font-weight: 750;
}

.route-step.active {
  border-color: #b9cdfc;
  color: #3158aa;
  background: #f4f7ff;
}

.route-step.active > span {
  color: #ffffff;
  background: #4f73e8;
  box-shadow: 0 0 0 4px rgba(79, 115, 232, 0.11);
}

.route-step.done {
  border-color: #b8dfd1;
  color: #16745c;
  background: #f2fbf7;
}

.route-step.done > span {
  color: #ffffff;
  background: #22a47c;
}

.route-step.failed {
  border-color: #f0bebe;
  color: #af4040;
  background: #fff5f5;
}

.route-step.failed > span {
  color: #ffffff;
  background: #d65353;
}

.route-connector {
  width: clamp(14px, 1.8vw, 32px);
  height: 2px;
  border-radius: 99px;
  background: #dce3eb;
}

.route-connector.active {
  background: linear-gradient(
      90deg,
      #4f73e8,
      #90a9ec
  );
}

.route-connector.done {
  background: #48b38d;
}

.summary-metrics {
  display: flex;
  min-width: 0;
  align-items: center;
}

.summary-progress,
.summary-metric {
  display: grid;
  grid-template-columns: auto auto;
  align-items: baseline;
  gap: 3px 9px;
  min-width: 112px;
  padding: 4px 16px;
  border-left: 1px solid var(--workflow-border);
}

.summary-progress {
  min-width: 154px;
}

.summary-progress > span,
.summary-metric > span {
  color: var(--workflow-muted);
  font-size: 11px;
  font-weight: 650;
  white-space: nowrap;
}

.summary-progress > strong,
.summary-metric > strong {
  color: var(--workflow-text);
  font-size: 17px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.summary-metric small {
  margin-left: 2px;
  color: var(--workflow-faint);
  font-size: 11px;
}

.summary-progress-track {
  grid-column: 1 / -1;
  height: 4px;
  margin-top: 5px;
  overflow: hidden;
  border-radius: 99px;
  background: #e8edf3;
}

.summary-progress-track i {
  display: block;
  width: 100%;
  height: 100%;
  transform-origin: left;
  border-radius: inherit;
  background: linear-gradient(
      90deg,
      #4f73e8,
      #32b4a2
  );
  transition: transform 320ms ease;
}

.summary-log-button {
  display: inline-flex;
  height: 36px;
  align-items: center;
  gap: 7px;
  margin-left: 11px;
  padding: 0 14px;
  border: 1px solid #cbd6e4;
  border-radius: 8px;
  color: #40536e;
  background: #ffffff;
  font: inherit;
  font-size: 12px;
  font-weight: 750;
  cursor: pointer;
  transition:
      border-color 180ms ease,
      color 180ms ease,
      background-color 180ms ease;
}

.summary-log-button:hover {
  border-color: #9fb2ca;
  color: #244e8f;
  background: #f8fbff;
}

.workflow-main {
  width: 100%;
  min-width: 0;
  margin-top: 14px;
}

.workflow-workbench {
  width: 100%;
  min-width: 0;
  padding: 20px;
  border: 1px solid var(--workflow-border);
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 9px 30px rgba(22, 35, 57, 0.055);
}

.workbench-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 22px;
  margin-bottom: 17px;
}

.workbench-header h3 {
  margin: 5px 0 0;
  color: var(--workflow-text);
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.workbench-header p {
  margin: 6px 0 0;
  color: var(--workflow-muted);
  font-size: 13px;
  line-height: 1.55;
}

.workbench-controls {
  display: flex;
  align-items: center;
  gap: 9px;
}

.live-control,
.plan-control {
  display: inline-flex;
  height: 32px;
  align-items: center;
  gap: 7px;
  padding: 0 11px;
  border: 1px solid #dce3ec;
  border-radius: 7px;
  color: #667489;
  background: #f8fafc;
  font-size: 11px;
  font-weight: 750;
  white-space: nowrap;
}

.live-control {
  border-color: #bfd2ff;
  color: #355ba9;
  background: #f5f8ff;
}

.live-control i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4f73e8;
  box-shadow: 0 0 0 4px rgba(79, 115, 232, 0.12);
  animation: live-pulse 1.6s ease-in-out infinite;
}

.workflow-error-status {
  display: inline-flex;
  height: 32px;
  align-items: center;
  gap: 7px;
  padding: 0 11px;
  border: 1px solid #f0b9b9;
  border-radius: 7px;
  color: #a43a3a;
  background: #fff6f6;
  font: inherit;
  cursor: pointer;
}

.workflow-error-status > span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #dc5050;
}

.workflow-error-status strong {
  font-size: 11px;
}

.workflow-error-status em {
  color: #bb6969;
  font-size: 10px;
  font-style: normal;
}

.workflow-canvas {
  position: relative;
  display: flex;
  width: 100%;
  min-width: 0;
  flex-direction: column;
  overflow: hidden;
  isolation: isolate;
  padding: clamp(26px, 2.8vw, 46px);
  border: 1px solid #d8e5f4;
  border-radius: 17px;
  background:
      radial-gradient(
          circle at 50% 1%,
          rgba(79, 115, 232, 0.105),
          transparent 28%
      ),
      radial-gradient(
          circle at 8% 48%,
          rgba(44, 180, 161, 0.065),
          transparent 25%
      ),
      linear-gradient(
          180deg,
          #fcfdff 0%,
          #f7faff 100%
      );
}

.canvas-grid {
  position: absolute;
  inset: 0;
  z-index: -3;
  opacity: 0.42;
  background-image:
      linear-gradient(
          rgba(135, 151, 174, 0.085) 1px,
          transparent 1px
      ),
      linear-gradient(
          90deg,
          rgba(135, 151, 174, 0.085) 1px,
          transparent 1px
      );
  background-size: 30px 30px;
  mask-image: radial-gradient(
      ellipse at center,
      #000 20%,
      transparent 82%
  );
}

.canvas-glow {
  position: absolute;
  z-index: -2;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(10px);
}

.canvas-glow-one {
  top: 90px;
  left: 43%;
  width: 220px;
  height: 220px;
  background: rgba(79, 115, 232, 0.065);
}

.canvas-glow-two {
  right: 5%;
  bottom: 10%;
  width: 280px;
  height: 280px;
  background: rgba(45, 181, 163, 0.055);
}

.workflow-stage {
  position: relative;
  z-index: 4;
}

.stage-heading {
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr) auto;
  gap: 13px;
  width: 100%;
  align-items: center;
  margin-bottom: 17px;
}

.stage-index {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border: 1px solid #cad6e5;
  border-radius: 9px;
  color: #51657f;
  background: rgba(255, 255, 255, 0.94);
  font-size: 11px;
  font-weight: 850;
}

.stage-heading strong {
  display: block;
  color: #1f2b3e;
  font-size: 15px;
  font-weight: 800;
}

.stage-heading p {
  margin: 4px 0 0;
  color: #748196;
  font-size: 12px;
  line-height: 1.5;
}

.stage-heading > em {
  padding: 5px 9px;
  border: 1px solid #d8e0ea;
  border-radius: 6px;
  color: #7d8999;
  background: #ffffff;
  font-size: 11px;
  font-style: normal;
  font-weight: 750;
}

.stage-heading > em.status-running {
  border-color: #bfd1ff;
  color: #355cac;
  background: #f4f7ff;
}

.stage-heading > em.status-success {
  border-color: #bce2d4;
  color: #157258;
  background: #f2fbf7;
}

.stage-heading > em.status-failed {
  border-color: #f0bebe;
  color: #ae4141;
  background: #fff5f5;
}

.stage-live-summary {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stage-live-summary span {
  display: inline-flex;
  height: 28px;
  align-items: center;
  gap: 6px;
  padding: 0 9px;
  border: 1px solid #dce4ee;
  border-radius: 6px;
  color: #657388;
  background: #ffffff;
  font-size: 11px;
  font-weight: 700;
}

.running-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #4f73e8;
  animation: live-pulse 1.6s ease-in-out infinite;
}

.planning-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.delivery-icon,
.detail-agent-icon {
  display: grid;
  place-items: center;
  color: #3d61b3;
  background: #edf3ff;
  border: 1px solid #cbdafa;
}

.delivery-copy > span {
  display: block;
  color: #6e83af;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.1em;
}

.delivery-copy strong {
  display: block;
  margin-top: 3px;
  color: #1e2b41;
  font-size: 14px;
  font-weight: 850;
}

.node-status-badge {
  display: inline-flex;
  height: 28px;
  align-items: center;
  gap: 6px;
  padding: 0 9px;
  border: 1px solid #dce3ec;
  border-radius: 6px;
  color: #6f7c90;
  background: #ffffff;
  font-size: 11px;
  font-weight: 750;
  white-space: nowrap;
}

.node-status-badge.compact {
  height: 26px;
  padding: 0 8px;
  font-size: 10px;
}

.node-status-badge i,
.detail-status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #a5afbc;
}

.node-status-badge.status-running,
.detail-status.status-running {
  border-color: #bfd1ff;
  color: #3159a7;
  background: #f5f8ff;
}

.node-status-badge.status-running i,
.detail-status.status-running i {
  background: #4f73e8;
  box-shadow: 0 0 0 4px rgba(79, 115, 232, 0.13);
  animation: live-pulse 1.5s ease-in-out infinite;
}

.node-status-badge.status-success,
.detail-status.status-success {
  border-color: #bce2d4;
  color: #157158;
  background: #f3fbf7;
}

.node-status-badge.status-success i,
.detail-status.status-success i {
  background: #24a47c;
}

.node-status-badge.status-failed,
.detail-status.status-failed {
  border-color: #f0bdbd;
  color: #ae4141;
  background: #fff5f5;
}

.node-status-badge.status-failed i,
.detail-status.status-failed i {
  background: #d65050;
}

.agent-current-task > span,
.agent-event-preview > span,
.detail-io-grid span,
.detail-metric-section > span {
  display: block;
  color: #748298;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.agent-card-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 9px;
}

.agent-card-footer > span {
  color: #2f8b70;
  font-size: 11px;
  font-weight: 750;
  white-space: nowrap;
}

.agent-card-footer > b {
  min-width: 33px;
  color: #66758a;
  font-size: 11px;
  font-weight: 800;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.node-progress-track {
  height: 5px;
  flex: 1;
  overflow: hidden;
  border-radius: 99px;
  background: #e7ebf1;
}

.node-progress-track i {
  display: block;
  width: 100%;
  height: 100%;
  transform-origin: left;
  border-radius: inherit;
  background: linear-gradient(
      90deg,
      #4f73e8,
      #33b6a2
  );
  transition: transform 350ms ease;
}

.status-running .node-progress-track i {
  background-size: 180% 100%;
  animation: progress-flow 1.8s linear infinite;
}

.dispatch-bus {
  position: relative;
  z-index: 5;
  width: min(760px, 94%);
  height: 70px;
  margin: 0 auto;
}

.dispatch-bus::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  width: 2px;
  height: 29px;
  border-radius: 99px;
  background: linear-gradient(
      180deg,
      #7796e4,
      #43ac9d
  );
  transform: translateX(-50%);
}

.dispatch-command {
  position: absolute;
  top: 25px;
  left: 50%;
  display: flex;
  height: 31px;
  align-items: center;
  gap: 8px;
  padding: 0 11px;
  border: 1px solid #bfd0f2;
  border-radius: 7px;
  color: #3e5f9e;
  background: #ffffff;
  box-shadow: 0 6px 18px rgba(44, 69, 117, 0.09);
  transform: translateX(-50%);
}

.dispatch-command > span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4f73e8;
  box-shadow: 0 0 0 4px rgba(79, 115, 232, 0.11);
}

.dispatch-command strong {
  font-size: 11px;
  font-weight: 800;
}

.dispatch-command em {
  color: #7d899b;
  font-size: 10px;
  font-style: normal;
  font-weight: 650;
}

.agent-link-svg {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
  pointer-events: none;
}

.agent-link-path {
  fill: none;
  stroke: url(#agentLinkGradient);
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-dasharray: 6 7;
  opacity: 0.48;
  vector-effect: non-scaling-stroke;
}

.agent-link-path.status-running {
  stroke-width: 2.3;
  opacity: 0.96;
  animation: link-flow 1.4s linear infinite;
}

.agent-link-path.status-success {
  stroke: #55ae91;
  stroke-dasharray: 0;
  opacity: 0.78;
}

.agent-link-path.status-failed {
  stroke: #d46161;
  stroke-dasharray: 4 6;
  opacity: 0.75;
}

.agent-data-packet {
  fill: #5079ec;
  filter: url(#agentPacketGlow);
}

.agent-data-packet.packet-secondary {
  fill: #35b4a1;
}

.agent-link-terminal {
  fill: #91a1b6;
  opacity: 0.85;
}

.agent-link-terminal.status-running {
  fill: #4f73e8;
  animation: terminal-pulse 1.5s ease-in-out infinite;
}

.agent-link-terminal.status-success {
  fill: #35a780;
}

.parallel-stage {
  margin-top: 8px;
}

.parallel-agent-grid {
  position: relative;
  z-index: 4;
  display: grid;
  grid-template-columns: repeat(
    auto-fit,
    minmax(260px, 320px)
  );
  grid-auto-rows: 250px;
  justify-content: center;
  gap: 15px;
  width: 100%;
}

.agent-card {
  --agent-accent: #4f73e8;
  --agent-accent-soft: rgba(79, 115, 232, 0.08);
  --agent-accent-border: rgba(79, 115, 232, 0.28);
  --agent-accent-glow: rgba(79, 115, 232, 0.13);

  position: relative;
  display: flex;
  width: 100%;
  min-height: 0;
  height: 100%;
  flex-direction: column;
  padding: 12px;
  overflow: hidden;
  border: 1px solid #d6dee9;
  border-radius: 14px;
  background:
      linear-gradient(
          145deg,
          rgba(255, 255, 255, 0.98),
          rgba(249, 251, 254, 0.96)
      );
  box-shadow: none;
  cursor: pointer;
  transition:
      transform 190ms ease,
      border-color 190ms ease,
      box-shadow 190ms ease,
      background-color 190ms ease;
}

.planning-agent-card {
  width: min(320px, 100%);
  height: 250px;
  flex: 0 0 250px;
}

.planning-agent-card.status-running {
  animation: none;
}

.agent-card.tone-blue,
.agent-detail-panel.tone-blue {
  --agent-accent: #3676d8;
  --agent-accent-soft: rgba(54, 118, 216, 0.085);
  --agent-accent-border: rgba(54, 118, 216, 0.3);
  --agent-accent-glow: rgba(54, 118, 216, 0.14);
}

.agent-card.tone-violet,
.agent-detail-panel.tone-violet {
  --agent-accent: #7a5bd6;
  --agent-accent-soft: rgba(122, 91, 214, 0.085);
  --agent-accent-border: rgba(122, 91, 214, 0.3);
  --agent-accent-glow: rgba(122, 91, 214, 0.14);
}

.agent-card.tone-rose,
.agent-detail-panel.tone-rose {
  --agent-accent: #cf5f7d;
  --agent-accent-soft: rgba(207, 95, 125, 0.085);
  --agent-accent-border: rgba(207, 95, 125, 0.3);
  --agent-accent-glow: rgba(207, 95, 125, 0.14);
}

.agent-card.tone-amber,
.agent-detail-panel.tone-amber {
  --agent-accent: #b67731;
  --agent-accent-soft: rgba(182, 119, 49, 0.085);
  --agent-accent-border: rgba(182, 119, 49, 0.3);
  --agent-accent-glow: rgba(182, 119, 49, 0.14);
}

.agent-card.tone-emerald,
.agent-detail-panel.tone-emerald {
  --agent-accent: #25896c;
  --agent-accent-soft: rgba(37, 137, 108, 0.085);
  --agent-accent-border: rgba(37, 137, 108, 0.3);
  --agent-accent-glow: rgba(37, 137, 108, 0.14);
}

.agent-card.tone-indigo,
.agent-detail-panel.tone-indigo {
  --agent-accent: #5866c9;
  --agent-accent-soft: rgba(88, 102, 201, 0.085);
  --agent-accent-border: rgba(88, 102, 201, 0.3);
  --agent-accent-glow: rgba(88, 102, 201, 0.14);
}

.agent-card.tone-pink,
.agent-detail-panel.tone-pink {
  --agent-accent: #c6539d;
  --agent-accent-soft: rgba(198, 83, 157, 0.085);
  --agent-accent-border: rgba(198, 83, 157, 0.3);
  --agent-accent-glow: rgba(198, 83, 157, 0.14);
}

.agent-detail-panel.tone-cyan {
  --agent-accent: #258d9b;
  --agent-accent-soft: rgba(37, 141, 155, 0.085);
  --agent-accent-border: rgba(37, 141, 155, 0.28);
  --agent-accent-glow: rgba(37, 141, 155, 0.14);
}

.agent-card:hover,
.agent-card.is-selected {
  transform: translateY(-4px);
  border-color: var(--agent-accent-border);
  box-shadow: 0 0 0 2px var(--agent-accent-soft);
}

.agent-card.status-running {
  border-color: var(--agent-accent-border);
  background:
      linear-gradient(
          145deg,
          #ffffff,
          var(--agent-accent-soft)
      );
  box-shadow: inset 0 2px 0 var(--agent-accent);
}

.agent-card.status-success,
.agent-card.has-artifact {
  border-color: #b7dece;
  background:
      linear-gradient(
          145deg,
          #ffffff,
          #f4fbf8
      );
}

.agent-card.status-failed {
  border-color: #e8bcbc;
  background:
      linear-gradient(
          145deg,
          #ffffff,
          #fff5f5
      );
}

.agent-card-running-line {
  position: absolute;
  top: 0;
  right: 100%;
  left: -40%;
  height: 2px;
  opacity: 0;
  background: linear-gradient(
      90deg,
      transparent,
      var(--agent-accent),
      transparent
  );
}

.agent-card.status-running .agent-card-running-line {
  opacity: 1;
  animation: card-line-flow 2s linear infinite;
}

.agent-card-header {
  display: grid;
  grid-template-columns: 39px minmax(0, 1fr) auto;
  gap: 9px;
  align-items: center;
}

.agent-icon {
  display: grid;
  width: 39px;
  height: 39px;
  place-items: center;
  border: 1px solid var(--agent-accent-border);
  border-radius: 10px;
  color: var(--agent-accent);
  background: var(--agent-accent-soft);
}

.agent-identity {
  min-width: 0;
}

.agent-identity strong {
  display: block;
  overflow: hidden;
  color: #28364b;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-identity span {
  display: block;
  margin-top: 3px;
  overflow: hidden;
  color: #7e8a9b;
  font-size: 10px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-current-task {
  min-height: 48px;
  margin-top: 8px;
  padding: 7px 9px;
  border: 1px solid #e1e7ef;
  border-radius: 9px;
  background: #f8fafc;
}

.agent-current-task > span {
  color: var(--agent-accent);
}

.agent-current-task p {
  display: -webkit-box;
  margin: 3px 0 0;
  overflow: hidden;
  color: #4e5e77;
  font-size: 11px;
  font-weight: 650;
  line-height: 1.5;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
}

.agent-execution-chain {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  margin-top: 8px;
}

.execution-step {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  text-align: center;
}

.execution-step > i {
  width: 9px;
  height: 9px;
  border: 2px solid #ffffff;
  border-radius: 50%;
  background: #ccd4df;
  box-shadow: 0 0 0 1px #cfd8e4;
}

.execution-step > span {
  overflow: hidden;
  color: #8995a6;
  font-size: 9px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.execution-step.running > i {
  background: var(--agent-accent);
  box-shadow:
      0 0 0 1px var(--agent-accent-border),
      0 0 0 4px var(--agent-accent-soft);
  animation: execution-pulse 1.4s ease-in-out infinite;
}

.execution-step.running > span {
  color: var(--agent-accent);
}

.execution-step.success > i {
  background: #2da47d;
  box-shadow: 0 0 0 1px #72c5a8;
}

.execution-step.success > span {
  color: #278467;
}

.execution-step.failed > i {
  background: #d55454;
  box-shadow: 0 0 0 1px #e49a9a;
}

.execution-step.failed > span {
  color: #b54343;
}

.agent-execution-chain > b {
  width: 16px;
  height: 1px;
  margin-top: -14px;
  background: #dce2ea;
}

.agent-event-preview {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  min-height: 31px;
  margin-top: 7px;
  padding: 7px 0 0;
  border-top: 1px solid #e6eaf0;
}

.agent-event-preview p {
  margin: 0 8px;
  overflow: hidden;
  color: #5f6e84;
  font-size: 10px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-event-preview em {
  position: static;
  color: #8995a6;
  font-size: 9px;
  font-style: normal;
  font-weight: 700;
}

.agent-card-footer {
  margin-top: 7px;
  padding-top: 7px;
}

.agent-card-footer > span {
  color: var(--agent-accent);
}

.handoff-rail {
  position: relative;
  z-index: 4;
  width: min(900px, 92%);
  margin: 20px auto;
}

.handoff-return-rail {
  height: 76px;
}

.handoff-return-rail::before,
.handoff-return-rail::after {
  content: '';
  position: absolute;
  left: 50%;
  width: 1px;
  background: #b9c6d7;
  transform: translateX(-50%);
}

.handoff-return-rail::before {
  top: 0;
  height: 25px;
}

.handoff-return-rail::after {
  bottom: 0;
  height: 25px;
}

.handoff-return-rail > strong {
  position: absolute;
  top: 50%;
  left: 50%;
  display: inline-flex;
  height: 29px;
  align-items: center;
  padding: 0 11px;
  border: 1px solid #cbd7e5;
  border-radius: 7px;
  color: #52657f;
  background: #ffffff;
  box-shadow: 0 6px 16px rgba(33, 50, 76, 0.07);
  font-size: 10px;
  font-weight: 800;
  transform: translate(-50%, -50%);
}

.handoff-packet {
  position: absolute;
  top: 50%;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #64748b;
  font-size: 9px;
  font-weight: 700;
  opacity: 0;
}

.handoff-packet i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #4f73e8;
  box-shadow: 0 0 0 4px rgba(79, 115, 232, 0.1);
}

.workflow-canvas.is-running .handoff-packet {
  animation: handoff-return 3.2s linear infinite;
}

.handoff-packet.packet-one {
  left: 8%;
  animation-delay: 0s !important;
}

.handoff-packet.packet-two {
  left: 20%;
  animation-delay: 1s !important;
}

.handoff-packet.packet-three {
  left: 32%;
  animation-delay: 2s !important;
}

.coordination-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.coordination-flow {
  width: min(920px, 100%);
  padding: 0 18px;
}

.coordination-flow-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.coordination-flow-header > div:first-child > strong {
  display: block;
  margin-top: 0;
  color: #34465b;
  font-size: 13px;
  font-weight: 750;
}

.coordination-progress-copy {
  display: flex;
  align-items: center;
  gap: 9px;
}

.coordination-progress-copy span {
  color: #617286;
  font-size: 11px;
  font-weight: 700;
}

.coordination-progress-copy b {
  color: #2f8190;
  font-size: 13px;
  font-weight: 850;
}

.coordination-steps {
  display: flex;
  align-items: stretch;
  gap: 12px;
  margin-top: 12px;
}

.coordination-step {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto;
  gap: 9px;
  min-width: 0;
  flex: 1;
  align-items: center;
  min-height: 40px;
  padding: 0;
}

.coordination-step > span {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 50%;
  color: #7c8999;
  background: #e8edf3;
  font-size: 10px;
  font-weight: 800;
}

.coordination-step strong {
  display: block;
  color: #47586e;
  font-size: 11px;
  font-weight: 800;
}

.coordination-step p {
  margin: 3px 0 0;
  overflow: hidden;
  color: #7e8a9a;
  font-size: 10px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.coordination-step > em {
  color: #8995a6;
  font-size: 10px;
  font-style: normal;
  font-weight: 700;
  white-space: nowrap;
}

.coordination-step.running {
  background: transparent;
}

.coordination-step.running > span {
  color: #ffffff;
  background: #2c909e;
  box-shadow: 0 0 0 4px rgba(44, 144, 158, 0.1);
  animation: live-pulse 1.5s ease-in-out infinite;
}

.coordination-step.running strong,
.coordination-step.running > em {
  color: #257985;
}

.coordination-step.success {
  background: transparent;
}

.coordination-step.success > span {
  color: #ffffff;
  background: #2ba17a;
}

.coordination-step.success strong,
.coordination-step.success > em {
  color: #277b62;
}

.coordination-step.failed {
  background: transparent;
}

.coordination-step.failed > span {
  color: #ffffff;
  background: #d65353;
}

.coordination-step.failed strong,
.coordination-step.failed > em {
  color: #ae4141;
}

.coordination-step-line {
  width: 24px;
  height: 1px;
  align-self: center;
  background: #d4dde7;
}

.coordination-step-line.running {
  background: #79b5bf;
}

.coordination-step-line.success {
  background: #68ba9b;
}

.coordination-progress-track {
  height: 4px;
  margin-top: 12px;
  overflow: hidden;
  border-radius: 99px;
  background: #e5ebf1;
}

.coordination-progress-track i {
  display: block;
  width: 100%;
  height: 100%;
  transform-origin: left;
  background: linear-gradient(
      90deg,
      #3195a3,
      #4f73e8
  );
  transition: transform 350ms ease;
}

.context-handoff-line,
.delivery-merge-line {
  position: relative;
  z-index: 4;
  width: min(760px, 92%);
  height: 84px;
  margin: 2px auto;
}

.context-handoff-line > span,
.delivery-merge-line > span {
  position: absolute;
  top: 0;
  left: 50%;
  width: 1px;
  height: 29px;
  background: #aebdd0;
}

.context-handoff-line::after,
.delivery-merge-line::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 1px;
  height: 29px;
  background: #aebdd0;
}

.context-handoff-line > div,
.delivery-merge-line > div {
  position: absolute;
  top: 50%;
  left: 50%;
  display: grid;
  grid-template-columns: 9px auto;
  gap: 2px 8px;
  align-items: center;
  padding: 8px 11px;
  border: 1px solid #cbd7e5;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 6px 16px rgba(30, 46, 70, 0.07);
  transform: translate(-50%, -50%);
}

.context-handoff-line i {
  grid-row: 1 / 3;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #4f73e8;
  box-shadow: 0 0 0 4px rgba(79, 115, 232, 0.1);
}

.delivery-merge-line i {
  grid-row: 1 / 3;
  width: 9px;
  height: 9px;
  border-radius: 2px;
  background: #4f73e8;
  transform: rotate(45deg);
}

.context-handoff-line p,
.delivery-merge-line p {
  margin: 0;
}

.context-handoff-line strong,
.delivery-merge-line strong {
  display: block;
  color: #4c607c;
  font-size: 10px;
  font-weight: 800;
}

.context-handoff-line em,
.delivery-merge-line em {
  display: block;
  margin-top: 2px;
  color: #7e8a9b;
  font-size: 9px;
  font-style: normal;
}

.aggregation-agent-grid {
  display: grid;
  grid-template-columns: repeat(
    auto-fit,
    minmax(260px, 320px)
  );
  grid-auto-rows: 250px;
  justify-content: center;
  gap: 15px;
  width: 100%;
  margin: 0 auto;
}

.delivery-stage {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.delivery-summary {
  display: grid;
  grid-template-columns: 50px minmax(0, 1fr) auto auto;
  gap: 14px;
  width: min(800px, 100%);
  align-items: center;
  padding: 17px 18px;
  border: 1px solid #cad8e9;
  border-radius: 14px;
  background:
      radial-gradient(
          circle at 78% 0%,
          rgba(79, 115, 232, 0.08),
          transparent 36%
      ),
      linear-gradient(
          145deg,
          #ffffff,
          #f8fbff
      );
  box-shadow: 0 10px 28px rgba(30, 51, 82, 0.065);
}

.delivery-summary.status-running {
  border-color: #8da6dd;
  box-shadow:
      0 13px 32px rgba(44, 68, 119, 0.11),
      inset 3px 0 0 #4f73e8;
}

.delivery-summary.status-success {
  border-color: #b7dece;
  background:
      radial-gradient(
          circle at 78% 0%,
          rgba(36, 164, 124, 0.08),
          transparent 36%
      ),
      linear-gradient(
          145deg,
          #ffffff,
          #f3fbf7
      );
}

.delivery-icon {
  width: 50px;
  height: 50px;
  border-radius: 13px;
}

.delivery-copy {
  min-width: 0;
}

.delivery-copy p {
  margin: 5px 0 0;
  overflow: hidden;
  color: #64748b;
  font-size: 11px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delivery-count {
  padding: 8px 16px;
  border-right: 1px solid #e0e6ed;
  border-left: 1px solid #e0e6ed;
  text-align: center;
}

.delivery-count span {
  display: block;
  color: #7f8b9d;
  font-size: 10px;
  font-weight: 700;
}

.delivery-count strong {
  display: block;
  margin-top: 3px;
  color: #2f4058;
  font-size: 20px;
  font-weight: 850;
}

.delivery-progress {
  grid-column: 2 / 5;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 9px;
  align-items: center;
}

.delivery-progress span {
  color: #62728a;
  font-size: 10px;
  font-weight: 700;
}

.delivery-progress b {
  color: #40516a;
  font-size: 11px;
  font-weight: 800;
}

.agent-station-enter-active,
.agent-station-leave-active {
  transition:
      opacity 280ms ease,
      transform 280ms ease;
}

.agent-station-enter-from,
.agent-station-leave-to {
  opacity: 0;
  transform: translateY(16px) scale(0.97);
}

/* Agent 完整流程弹窗 */
.detail-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 26px;
  background: rgba(18, 28, 45, 0.38);
  backdrop-filter: blur(5px);
}

.agent-detail-panel {
  --agent-accent: #4f73e8;
  --agent-accent-soft: rgba(79, 115, 232, 0.08);
  --agent-accent-border: rgba(79, 115, 232, 0.26);
  --agent-accent-glow: rgba(79, 115, 232, 0.14);

  width: min(1040px, calc(100vw - 36px));
  max-height: min(860px, 90vh);
  overflow: hidden;
  border: 1px solid #d8e1ec;
  border-radius: 18px;
  background: #ffffff;
  box-shadow: 0 32px 86px rgba(14, 24, 40, 0.22);
}

.detail-header {
  display: grid;
  grid-template-columns: 48px minmax(0, 1fr) auto 34px;
  gap: 13px;
  align-items: center;
  min-height: 78px;
  padding: 15px 18px;
  border-bottom: 1px solid #e1e7ef;
  background:
      linear-gradient(
          90deg,
          var(--agent-accent-soft),
          rgba(255, 255, 255, 0.98) 35%
      );
}

.detail-agent-icon {
  width: 48px;
  height: 48px;
  border-color: var(--agent-accent-border);
  border-radius: 12px;
  color: var(--agent-accent);
  background: var(--agent-accent-soft);
}

.detail-agent-title {
  min-width: 0;
}

.detail-agent-title > span {
  display: block;
  color: var(--agent-accent);
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.1em;
}

.detail-agent-title h3 {
  margin: 3px 0 0;
  overflow: hidden;
  color: #263449;
  font-size: 18px;
  font-weight: 850;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-agent-title p {
  margin: 2px 0 0;
  color: #718096;
  font-size: 12px;
  font-weight: 650;
}

.detail-status {
  display: inline-flex;
  height: 29px;
  align-items: center;
  gap: 7px;
  padding: 0 9px;
  border: 1px solid #dce3eb;
  border-radius: 7px;
  color: #6f7c90;
  background: #ffffff;
  font-size: 11px;
  font-weight: 750;
  white-space: nowrap;
}

.detail-header button {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 1px solid #d8e0e9;
  border-radius: 8px;
  color: #64748b;
  background: #ffffff;
  font: inherit;
  font-size: 20px;
  cursor: pointer;
  transition:
      border-color 180ms ease,
      color 180ms ease,
      background-color 180ms ease;
}

.detail-header button:hover {
  border-color: var(--agent-accent-border);
  color: var(--agent-accent);
  background: var(--agent-accent-soft);
}

.detail-body {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(340px, 0.92fr);
  min-height: 0;
  max-height: calc(90vh - 78px);
}

.detail-overview,
.detail-history {
  min-height: 0;
  overflow-y: auto;
}

/* 自定义滚轮样式方便长日志查看 */
.detail-overview::-webkit-scrollbar,
.detail-history::-webkit-scrollbar {
  width: 6px;
}

.detail-overview::-webkit-scrollbar-track,
.detail-history::-webkit-scrollbar-track {
  background: transparent;
}

.detail-overview::-webkit-scrollbar-thumb,
.detail-history::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: 4px;
}

.detail-overview::-webkit-scrollbar-thumb:hover,
.detail-history::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.22);
}

.detail-overview {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  border-right: 1px solid #e2e8f0;
}

.detail-current-task {
  padding: 14px;
  border: 1px solid var(--agent-accent-border);
  border-radius: 11px;
  background: var(--agent-accent-soft);
}

.detail-section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.detail-section-heading > div > span {
  display: block;
  color: var(--agent-accent);
  font-size: 10px;
  font-weight: 800;
}

.detail-section-heading > div > strong {
  display: block;
  margin-top: 4px;
  color: #34465d;
  font-size: 14px;
  font-weight: 800;
}

.detail-section-heading > b {
  color: var(--agent-accent);
  font-size: 18px;
  font-weight: 850;
}

.detail-current-task > p {
  margin: 10px 0 0;
  color: #47586f;
  font-size: 12px;
  font-weight: 650;
  line-height: 1.6;
}

.detail-progress-row {
  margin-top: 12px;
}

.detail-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin: 0;
}

.detail-metrics > div {
  padding: 11px;
  border: 1px solid #e0e7ef;
  border-radius: 9px;
  background: #f8fafc;
}

.detail-metrics dt {
  color: #7f8b9d;
  font-size: 10px;
  font-weight: 700;
}

.detail-metrics dd {
  margin: 5px 0 0;
  overflow: hidden;
  color: #3f5068;
  font-size: 11px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-full-process {
  padding: 14px;
  border: 1px solid #e0e7ef;
  border-radius: 11px;
  background: #ffffff;
}

.detail-section-title {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.detail-section-title span {
  display: block;
  color: #35465d;
  font-size: 13px;
  font-weight: 850;
}

.detail-section-title p {
  margin: 4px 0 0;
  color: #7b8798;
  font-size: 10px;
  line-height: 1.45;
}

.detail-section-title > em {
  padding: 4px 8px;
  border: 1px solid var(--agent-accent-border);
  border-radius: 6px;
  color: var(--agent-accent);
  background: var(--agent-accent-soft);
  font-size: 10px;
  font-style: normal;
  font-weight: 800;
}

.detail-process-list {
  position: relative;
  display: flex;
  flex-direction: column;
  margin-top: 14px;
}

.detail-process-step {
  position: relative;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 11px;
  min-height: 70px;
}

.detail-process-index {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: center;
}

.detail-process-index > span {
  position: relative;
  z-index: 2;
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 2px solid #ffffff;
  border-radius: 50%;
  color: #7c899a;
  background: #e7ecf2;
  box-shadow: 0 0 0 1px #d2dbe5;
  font-size: 10px;
  font-weight: 850;
}

.detail-process-index > i {
  position: absolute;
  top: 28px;
  bottom: 0;
  left: 50%;
  width: 1px;
  background: #dce3eb;
  transform: translateX(-50%);
}

.detail-process-step:last-child .detail-process-index > i {
  display: none;
}

.detail-process-copy {
  padding: 2px 0 15px;
}

.detail-process-copy > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.detail-process-copy strong {
  color: #43536a;
  font-size: 12px;
  font-weight: 800;
}

.detail-process-copy em {
  color: #8995a6;
  font-size: 10px;
  font-style: normal;
  font-weight: 700;
}

.detail-process-copy p {
  margin: 6px 0 0;
  color: #718096;
  font-size: 11px;
  line-height: 1.55;
}

.detail-process-step.running .detail-process-index > span {
  color: #ffffff;
  background: var(--agent-accent);
  box-shadow:
      0 0 0 1px var(--agent-accent-border),
      0 0 0 5px var(--agent-accent-soft);
  animation: execution-pulse 1.5s ease-in-out infinite;
}

.detail-process-step.running .detail-process-copy strong,
.detail-process-step.running .detail-process-copy em {
  color: var(--agent-accent);
}

.detail-process-step.success .detail-process-index > span {
  color: #ffffff;
  background: #2ca27b;
  box-shadow: 0 0 0 1px #76c5aa;
}

.detail-process-step.success .detail-process-index > i {
  background: #8acbb4;
}

.detail-process-step.success .detail-process-copy strong,
.detail-process-step.success .detail-process-copy em {
  color: #277b62;
}

.detail-process-step.failed .detail-process-index > span {
  color: #ffffff;
  background: #d65050;
  box-shadow: 0 0 0 1px #e39898;
}

.detail-process-step.failed .detail-process-copy strong,
.detail-process-step.failed .detail-process-copy em {
  color: #ae4141;
}

.detail-io-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
}

.detail-io-grid article {
  padding: 12px;
  border: 1px solid #e0e7ef;
  border-radius: 10px;
  background: #f8fafc;
}

.detail-io-grid span {
  color: var(--agent-accent);
}

.detail-io-grid p {
  margin: 6px 0 0;
  color: #5e6d83;
  font-size: 11px;
  line-height: 1.55;
}

.detail-metric-section {
  padding: 12px;
  border: 1px solid #e0e7ef;
  border-radius: 10px;
  background: #ffffff;
}

.detail-metric-section > span {
  color: #52627a;
}

.detail-metric-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 8px;
}

.detail-metric-chips em {
  padding: 5px 8px;
  border: 1px solid var(--agent-accent-border);
  border-radius: 6px;
  color: var(--agent-accent);
  background: var(--agent-accent-soft);
  font-size: 10px;
  font-style: normal;
  font-weight: 700;
}

.detail-history {
  padding: 18px;
  background: #f8fafc;
}

.detail-history-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e0e7ef;
}

.detail-history-header span {
  display: block;
  color: var(--agent-accent);
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.08em;
}

.detail-history-header h4 {
  margin: 4px 0 0;
  color: #2d3c51;
  font-size: 15px;
  font-weight: 850;
}

.detail-history-header p {
  margin: 5px 0 0;
  color: #7b8798;
  font-size: 10px;
  line-height: 1.45;
}

.detail-history-header > em {
  padding: 5px 8px;
  border: 1px solid #d5dee8;
  border-radius: 6px;
  color: #68778b;
  background: #ffffff;
  font-size: 10px;
  font-style: normal;
  font-weight: 750;
  white-space: nowrap;
}

.timeline-stream {
  position: relative;
  display: flex;
  flex-direction: column;
  margin-top: 15px;
}

.timeline-item {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 10px;
  min-height: 92px;
}

.timeline-axis {
  position: relative;
  display: flex;
  justify-content: center;
}

.timeline-axis > span {
  position: relative;
  z-index: 2;
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 2px solid #f8fafc;
  border-radius: 50%;
  color: #738095;
  background: #e3e9f0;
  box-shadow: 0 0 0 1px #ced8e3;
  font-size: 10px;
  font-weight: 850;
}

.timeline-axis > i {
  position: absolute;
  top: 28px;
  bottom: 0;
  left: 50%;
  width: 1px;
  background: #d4dde7;
  transform: translateX(-50%);
}

.timeline-item:last-child .timeline-axis > i {
  display: none;
}

.timeline-card {
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid #dfe6ee;
  border-radius: 10px;
  background: #ffffff;
}

.timeline-card > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.timeline-card > header > div {
  display: flex;
  align-items: center;
  gap: 7px;
}

.timeline-card strong {
  color: #43536a;
  font-size: 11px;
  font-weight: 800;
}

.timeline-card header span {
  padding: 3px 6px;
  border-radius: 5px;
  color: #718096;
  background: #eef2f6;
  font-size: 9px;
  font-weight: 700;
}

.timeline-card header > em {
  color: #8793a4;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 9px;
  font-style: normal;
  white-space: nowrap;
}

.timeline-card p {
  margin: 8px 0 0;
  color: #617086;
  font-size: 11px;
  line-height: 1.55;
}

.timeline-item.is-running .timeline-axis > span {
  color: #ffffff;
  background: var(--agent-accent);
  box-shadow:
      0 0 0 1px var(--agent-accent-border),
      0 0 0 5px var(--agent-accent-soft);
}

.timeline-item.is-running .timeline-card {
  border-color: var(--agent-accent-border);
}

.timeline-item.is-running .timeline-card strong {
  color: var(--agent-accent);
}

.timeline-item.is-success .timeline-axis > span {
  color: #ffffff;
  background: #2ca27b;
  box-shadow: 0 0 0 1px #78c6ac;
}

.timeline-item.is-success .timeline-axis > i {
  background: #89cbb3;
}

.timeline-item.is-success .timeline-card {
  border-color: #bfe0d4;
}

.timeline-item.is-failed .timeline-axis > span {
  color: #ffffff;
  background: #d65050;
  box-shadow: 0 0 0 1px #e49b9b;
}

.timeline-item.is-failed .timeline-card {
  border-color: #edc0c0;
  background: #fffafa;
}

.timeline-item.is-failed .timeline-card strong {
  color: #ae4141;
}

.timeline-empty {
  display: flex;
  min-height: 260px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-top: 15px;
  border: 1px dashed #d6dfe9;
  border-radius: 11px;
  background: #ffffff;
  text-align: center;
}

.timeline-empty > span {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: #b7c1cd;
  box-shadow: 0 0 0 6px rgba(148, 163, 184, 0.12);
}

.timeline-empty strong {
  margin-top: 14px;
  color: #52627a;
  font-size: 13px;
  font-weight: 800;
}

.timeline-empty p {
  margin: 5px 0 0;
  color: #8793a4;
  font-size: 11px;
}

/* 日志抽屉 */
.drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: 1300;
  background: rgba(17, 27, 43, 0.31);
}

.log-drawer {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  width: min(450px, 100%);
  height: 100%;
  flex-direction: column;
  background: #ffffff;
  box-shadow: -20px 0 55px rgba(12, 22, 38, 0.16);
}

.log-drawer > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 21px 22px 17px;
  border-bottom: 1px solid #e2e7ee;
}

.log-drawer > header span {
  display: block;
  color: #8793a4;
  font-size: 10px;
  font-weight: 850;
  letter-spacing: 0.1em;
}

.log-drawer > header h3 {
  margin: 4px 0 0;
  color: #28364a;
  font-size: 16px;
  font-weight: 850;
}

.log-drawer > header button {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 1px solid #dce3eb;
  border-radius: 7px;
  color: #7a8799;
  background: #ffffff;
  font: inherit;
  font-size: 20px;
  cursor: pointer;
}

.drawer-log-list {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0;
  overflow-y: auto;
  padding: 9px 22px 22px;
}

.drawer-log-item {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr);
  gap: 11px;
  padding: 14px 0;
  border-bottom: 1px solid #edf0f4;
}

.drawer-log-dot {
  width: 8px;
  height: 8px;
  margin-top: 5px;
  border-radius: 50%;
  background: #a7b1bf;
}

.drawer-log-item.is-running .drawer-log-dot {
  background: #4f73e8;
  box-shadow: 0 0 0 4px rgba(79, 115, 232, 0.1);
}

.drawer-log-item.is-success .drawer-log-dot {
  background: #28a07a;
}

.drawer-log-item.is-failed .drawer-log-dot {
  background: #d45050;
}

.drawer-log-item strong {
  display: block;
  color: #405068;
  font-size: 12px;
  font-weight: 800;
}

.drawer-log-item p,
.empty-log {
  margin: 5px 0 0;
  color: #718096;
  font-size: 11px;
  line-height: 1.55;
}

.detail-fade-enter-active,
.detail-fade-leave-active {
  transition: opacity 220ms ease;
}

.detail-fade-enter-from,
.detail-fade-leave-to {
  opacity: 0;
}

.detail-fade-enter-active .agent-detail-panel,
.detail-fade-leave-active .agent-detail-panel {
  transition:
      opacity 220ms ease,
      transform 260ms cubic-bezier(0.16, 1, 0.3, 1);
}

.detail-fade-enter-from .agent-detail-panel,
.detail-fade-leave-to .agent-detail-panel {
  opacity: 0;
  transform: translateY(12px) scale(0.97);
}

.slide-over-enter-active,
.slide-over-leave-active {
  transition: opacity 210ms ease;
}

.slide-over-enter-from,
.slide-over-leave-to {
  opacity: 0;
}

.slide-over-enter-active .log-drawer,
.slide-over-leave-active .log-drawer {
  transition: transform 260ms cubic-bezier(0.16, 1, 0.3, 1);
}

.slide-over-enter-from .log-drawer,
.slide-over-leave-to .log-drawer {
  transform: translateX(100%);
}

@keyframes live-pulse {
  0%,
  100% {
    opacity: 0.72;
    transform: scale(0.94);
  }

  50% {
    opacity: 1;
    transform: scale(1.12);
  }
}

@keyframes planning-running {
  0%,
  100% {
    box-shadow:
        0 18px 44px rgba(59, 91, 170, 0.13),
        0 0 0 5px rgba(79, 115, 232, 0.045);
  }

  50% {
    box-shadow:
        0 23px 52px rgba(59, 91, 170, 0.19),
        0 0 0 7px rgba(79, 115, 232, 0.08);
  }
}

@keyframes planning-ring {
  0% {
    opacity: 0.42;
    transform: scale(0.94);
  }

  100% {
    opacity: 0;
    transform: scale(1.08);
  }
}

@keyframes progress-flow {
  to {
    background-position: -180% 0;
  }
}

@keyframes link-flow {
  to {
    stroke-dashoffset: -26;
  }
}

@keyframes terminal-pulse {
  0%,
  100% {
    opacity: 0.7;
    r: 4;
  }

  50% {
    opacity: 1;
    r: 6;
  }
}

@keyframes card-line-flow {
  to {
    right: -40%;
    left: 100%;
  }
}

@keyframes execution-pulse {
  50% {
    transform: scale(1.2);
  }
}

@keyframes handoff-return {
  0% {
    left: 5%;
    opacity: 0;
  }

  12% {
    opacity: 1;
  }

  75% {
    opacity: 1;
  }

  100% {
    left: 46%;
    opacity: 0;
  }
}

@media (max-width: 1320px) {
  .workflow-summary {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .summary-metrics {
    justify-content: flex-start;
  }

  .summary-progress:first-child {
    padding-left: 0;
    border-left: 0;
  }
}

@media (max-width: 1100px) {
  .summary-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 11px;
  }

  .route-progress {
    max-width: 100%;
    overflow-x: auto;
    padding-bottom: 4px;
  }

  .workbench-header {
    flex-direction: column;
  }

  .workbench-controls {
    justify-content: flex-start;
  }

  .coordination-steps {
    flex-direction: column;
  }

  .coordination-step-line {
    width: 1px;
    height: 14px;
    margin-left: 14px;
  }

  .detail-body {
    grid-template-columns: minmax(0, 1fr);
    overflow-y: auto;
  }

  .detail-overview,
  .detail-history {
    overflow: visible;
  }

  .detail-overview {
    border-right: 0;
    border-bottom: 1px solid #e2e8f0;
  }

  .agent-detail-panel {
    overflow-y: auto;
  }

  .detail-body {
    max-height: none;
  }
}

@media (max-width: 760px) {
  .workflow-page {
    padding: 13px 10px 38px;
  }

  .workflow-workbench {
    padding: 13px;
    border-radius: 14px;
  }

  .workflow-canvas {
    padding: 19px 14px;
  }

  .summary-metrics {
    display: grid;
    grid-template-columns: repeat(
      3,
      minmax(0, 1fr)
    );
    width: 100%;
  }

  .summary-progress,
  .summary-metric {
    display: flex;
    min-width: 0;
    flex-direction: column;
    align-items: flex-start;
    padding: 5px 9px;
  }

  .summary-progress {
    border-left: 0;
  }

  .summary-progress-track {
    width: 100%;
  }

  .summary-log-button {
    grid-column: 1 / -1;
    width: 100%;
    justify-content: center;
    margin: 9px 0 0;
  }

  .stage-heading {
    grid-template-columns: 36px minmax(0, 1fr);
  }

  .stage-heading > em,
  .stage-live-summary {
    grid-column: 2;
    justify-self: start;
  }

  .parallel-agent-grid,
  .aggregation-agent-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .parallel-agent-grid {
    grid-auto-rows: 296px;
  }

  .aggregation-agent-grid {
    grid-auto-rows: 296px;
  }

  .planning-agent-card {
    width: 100%;
    height: 296px;
    flex-basis: 296px;
  }

  .agent-link-svg {
    display: none;
  }

  .agent-card-header {
    grid-template-columns: 42px minmax(0, 1fr);
  }

  .agent-card-header > .node-status-badge {
    grid-column: 2;
    justify-self: start;
  }

  .agent-card {
    min-height: 0;
  }

  .coordination-flow-header {
    flex-direction: column;
  }

  .delivery-summary {
    grid-template-columns: 48px minmax(0, 1fr);
  }

  .delivery-count {
    grid-column: 2;
    border: 0;
    padding: 5px 0;
    text-align: left;
  }

  .delivery-summary > .node-status-badge {
    grid-column: 2;
    justify-self: start;
  }

  .delivery-progress {
    grid-column: 1 / -1;
  }

  .detail-overlay {
    padding: 10px;
  }

  .agent-detail-panel {
    width: calc(100vw - 20px);
    max-height: 94vh;
  }

  .detail-header {
    grid-template-columns: 44px minmax(0, 1fr) 32px;
  }

  .detail-status {
    grid-column: 2;
    justify-self: start;
  }

  .detail-header button {
    grid-column: 3;
    grid-row: 1;
  }

  .detail-metrics,
  .detail-io-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .handoff-packet span {
    display: none;
  }
}

@media (max-width: 520px) {
  .summary-metrics {
    grid-template-columns: repeat(
      2,
      minmax(0, 1fr)
    );
  }

  .summary-progress,
  .summary-metric {
    border-left: 0;
  }

  .summary-progress {
    grid-column: 1 / -1;
  }

  .route-connector {
    min-width: 10px;
  }

  .workbench-controls {
    flex-wrap: wrap;
  }

  .detail-metrics,
  .detail-io-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .detail-overview,
  .detail-history {
    padding: 14px;
  }

  .timeline-item {
    grid-template-columns: 32px minmax(0, 1fr);
  }

  .timeline-card > header {
    flex-direction: column;
  }
}

@media (prefers-reduced-motion: reduce) {
  .workflow-page *,
  .workflow-page *::before,
  .workflow-page *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }

  .agent-data-packet {
    display: none;
  }
}
</style>
