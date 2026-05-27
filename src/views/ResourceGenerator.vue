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
                placeholder="例如：我是软件工程大二学生，明天考《操作系统》。我搞不懂死锁的四个必要条件，请帮我生成复习资料和几道自测题…"
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
        <div class="workflow-shell">
          <!-- Topbar: Title + Stats + Stage Steps -->
          <section class="workflow-topbar" aria-live="polite">
            <div class="workflow-topbar-main">
              <div class="workflow-title-block">
                <el-tag class="workflow-kicker" effect="plain" round>
                  <span class="ping-dot"></span> 多智能体工作流运行中
                </el-tag>
                <h2>{{ dagHeroMessage }}</h2>
              </div>
              <div class="workflow-summary-panel">
                <div class="summary-item">
                  <span>总进度</span>
                  <strong>{{ overallProgress }}%</strong>
                </div>
                <div class="summary-divider"></div>
                <div class="summary-item">
                  <span>完成节点</span>
                  <strong>{{ dagCompletedCount }}<small>/{{ dagTotalCount }}</small></strong>
                </div>
                <el-progress
                    class="workflow-total-progress"
                    :percentage="overallProgress"
                    :stroke-width="8"
                    :show-text="false"
                />
              </div>
            </div>

            <!-- Stage steps horizontal strip -->
            <div class="stage-steps-strip">
              <div
                  v-for="(stage, index) in workflowStages"
                  :key="stage.id"
                  class="stage-step"
                  :class="`is-${stage.status}`"
              >
                <div class="step-dot">
                  <span v-if="stage.status === 'success'">&#10003;</span>
                  <span v-else>{{ index + 1 }}</span>
                </div>
                <div class="step-label">
                  <strong>{{ stage.title }}</strong>
                </div>
                <div class="step-connector" v-if="index < workflowStages.length - 1"></div>
              </div>
            </div>
          </section>

          <el-alert v-if="generationError" class="generation-error" type="error" :closable="false" show-icon :title="generationError" />

          <!-- Full-width DAG canvas -->
          <section class="workflow-canvas-panel workflow-card">
            <div class="panel-header canvas-header">
              <div>
                <span class="panel-eyebrow">AGENT ORCHESTRATION</span>
                <h3>智能体协作流程</h3>
              </div>
              <el-tag size="small" effect="plain" round>{{ dagSelectedAgentIds.length }} 个资源智能体</el-tag>
            </div>

            <div class="workflow-canvas">
              <div class="parallel-layer-label">并行资源生成层</div>
              <svg class="workflow-lines" :viewBox="`0 0 ${dagCanvasWidthV2} ${dagCanvasHeightV2}`" preserveAspectRatio="xMidYMid meet">
                <defs>
                  <linearGradient id="workflow-active-line" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#2563EB" />
                    <stop offset="100%" stop-color="#06B6D4" />
                  </linearGradient>
                </defs>
                <line
                    v-for="edge in dagEdges"
                    :key="`${edge.from}-${edge.to}`"
                    :x1="dagNodePositionsV2[edge.from]?.x"
                    :y1="dagNodePositionsV2[edge.from]?.y"
                    :x2="dagNodePositionsV2[edge.to]?.x"
                    :y2="dagNodePositionsV2[edge.to]?.y"
                    :class="['workflow-edge', edge.statusClass]"
                />
              </svg>

              <button
                  v-for="node in dagNodesV2"
                  :key="node.id"
                  class="workflow-agent-node"
                  :class="[`is-${node.status}`, { 'is-system-node': node.isSystem, 'is-selected': selectedDagNodeId === node.id }]"
                  :style="dagNodeStyle(node)"
                  type="button"
                  @click="selectedDagNodeId = node.id"
              >
                <div class="agent-node-topline">
                  <span class="agent-icon-bubble">{{ node.icon }}</span>
                  <span class="agent-node-name">{{ node.label }}</span>
                  <span class="agent-status-dot"></span>
                </div>

                <p class="agent-node-message">
                  {{ node.currentMessage || getNodeFallbackMessage(node) }}
                </p>

                <div class="agent-node-footer">
                  <span>{{ getStatusText(node.status) }}</span>
                  <strong>{{ node.progress }}%</strong>
                </div>

                <div class="agent-mini-progress">
                  <span :style="{ width: `${node.progress}%` }"></span>
                </div>
              </button>
            </div>

            <!-- Inline agent detail panel below canvas -->
            <transition name="detail-slide">
              <div v-if="selectedDagNode" class="inline-agent-detail">
                <div class="iad-header">
                  <div class="iad-agent-info">
                    <span class="iad-icon">{{ selectedDagNode.icon }}</span>
                    <div>
                      <h4>{{ selectedDagNode.label }}</h4>
                      <span :class="['detail-status-pill', `is-${selectedDagNode.status}`]">
                        {{ getStatusText(selectedDagNode.status) }}
                      </span>
                    </div>
                  </div>
                  <div class="iad-progress-wrap">
                    <el-progress
                        :percentage="selectedDagNode.progress"
                        :stroke-width="8"
                        :status="selectedDagNode.status === 'failed' ? 'exception' : selectedDagNode.status === 'success' ? 'success' : undefined"
                        style="width: 180px"
                    />
                  </div>
                  <div class="iad-action">
                    <span class="iad-action-text">{{ selectedDagNode.currentMessage || getNodeFallbackMessage(selectedDagNode) }}</span>
                  </div>
                  <button type="button" class="iad-close" @click="selectedDagNodeId = ''">×</button>
                </div>
                <div class="iad-logs" v-if="selectedDagNode.stepHistory?.length">
                  <div
                      v-for="(step, index) in selectedDagNode.stepHistory"
                      :key="index"
                      class="agent-log-item"
                      :class="{ active: index === selectedDagNode.stepHistory.length - 1 && selectedDagNode.status === 'running' }"
                  >
                    <span class="log-dot"></span>
                    <span>{{ step }}</span>
                  </div>
                </div>
                <div class="iad-logs-empty" v-else>等待工作流推送实时日志。</div>
              </div>
            </transition>
          </section>

          <section class="workflow-resource-strip workflow-card">
            <div class="resource-strip-header">
              <div>
                <span class="panel-eyebrow">DELIVERABLES</span>
                <h3>阶段性产物实时接收区</h3>
              </div>
              <transition name="scale-fade">
                <el-tag size="small" effect="plain" round v-if="generatedResources.length" class="res-count-badge">
                  已接收 {{ generatedResources.length }} 项
                </el-tag>
              </transition>
            </div>

            <div v-if="generatedResources.length" class="resource-strip-list">
              <article
                  v-for="resource in sortedGeneratedResources"
                  :key="resource.id || resource.type"
                  class="resource-chip-card"
                  :class="getResourceToneClass(resource.type)"
                  @click="previewGeneratedResource(resource)"
              >
                <span class="resource-chip-icon">{{ getDagNodeIcon(resource.type) }}</span>
                <div class="resource-chip-meta">
                  <span>{{ getResourceTypeLabel(resource.type) }}</span>
                  <strong :title="resource.title">{{ resource.title || '未命名数据片段' }}</strong>
                </div>
                <el-icon><ArrowRight /></el-icon>
              </article>
            </div>

            <div v-else class="resource-empty-state">
              <div class="empty-wave-loader">
                <span></span><span></span><span></span>
              </div>
              <span>多个智能体正在并行加工，资源产物生成后会在这里实时出现。</span>
            </div>
          </section>
        </div>
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

    <el-dialog v-model="previewVisible" :title="previewData?.title || '资源预览'" width="78%" top="6vh" destroy-on-close class="elegant-dialog">
      <div v-if="previewData" class="preview-dialog-body">
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
  MagicStick, ArrowRight, Cpu,
  CircleCheckFilled, RefreshLeft, Position, VideoPlay,
  Document, Share, Edit, Collection,
  Clock, Odometer, DataBoard
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
  video: { script_style: string; estimated_duration: number }
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

const quickPrompts = [
  "复习《计算机网络》TCP三次握手，我喜欢看时序图，请多出几道难题",
  "零基础学习 Python 多线程，需要底层原理和带详细注释的代码",
  "考研冲刺《数据结构》二叉树，帮我精简思维导图，重点标注高频考点"
]

const agentMetaList = [
  { id: 'master', name: '多智能体调度', icon: Cpu, colorClass: 'text-blue' },
  { id: 'reviewer', name: '资源审查', icon: CircleCheckFilled, colorClass: 'text-emerald' },
  { id: 'assembler', name: '资源组装', icon: Position, colorClass: 'text-indigo' },
  { id: 'content', name: '核心知识讲解', icon: Document, colorClass: 'text-blue' },
  { id: 'mindmap', name: '知识结构图谱', icon: Share, colorClass: 'text-purple' },
  { id: 'code', name: '实战代码沙箱', icon: Cpu, colorClass: 'text-red' },
  { id: 'quiz', name: '自测题训练', icon: Edit, colorClass: 'text-emerald' },
  { id: 'reading', name: '拓展阅读推荐', icon: Collection, colorClass: 'text-indigo' },
  { id: 'ppt', name: 'PPT文稿生成', icon: DataBoard, colorClass: 'text-pink' },
  { id: 'video', name: '视频动画脚本', icon: VideoPlay, colorClass: 'text-slate', disabled: true }
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

const RESOURCE_TYPE_ORDER = ['content', 'diagram', 'mindmap', 'code', 'quiz', 'reading', 'ppt', 'video']

const AGENT_DISPLAY: Record<string, { label: string; icon: string }> = {
  planning: { label: '规划任务', icon: '🎯' },
  content: { label: '课程讲解', icon: '📝' },
  mindmap: { label: '思维导图', icon: '🧠' },
  quiz: { label: '自测题库', icon: '📋' },
  code: { label: '代码案例', icon: '💻' },
  reading: { label: '拓展阅读', icon: '📚' },
  ppt: { label: '演示文稿', icon: '📊' },
  review: { label: '质量审查', icon: '🔍' },
  bundle: { label: '资源组装', icon: '📦' },
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

const selectedDagNode = computed(() => {
  return dagNodesV2.value.find(node => node.id === selectedDagNodeId.value) || dagNodesV2.value[0]
})

const workflowStages = computed(() => {
  const states = dagNodeStates.value
  const businessNodes = dagSelectedAgentIds.value.map(id => states[id]).filter(Boolean)
  const hasRunningBusiness = businessNodes.some(node => node?.status === 'running')
  const hasFailedBusiness = businessNodes.some(node => node?.status === 'failed')
  const allBusinessDone = businessNodes.length > 0 && businessNodes.every(node => ['success', 'skipped'].includes(node?.status || ''))

  return [
    {
      id: 'planning',
      title: '需求解析与任务规划',
      desc: 'MasterAgent 解析学习目标并生成调度计划',
      status: states.planning?.status || 'waiting',
    },
    {
      id: 'parallel',
      title: '资源智能体并行生成',
      desc: '讲解、导图、代码、题库、阅读等智能体协同工作',
      status: hasFailedBusiness ? 'failed' : hasRunningBusiness ? 'running' : allBusinessDone ? 'success' : 'waiting',
    },
    {
      id: 'review',
      title: '质量审查',
      desc: 'ReviewerAgent 检查资源完整性、质量与可用性',
      status: states.review?.status || 'waiting',
    },
    {
      id: 'bundle',
      title: '资源组装交付',
      desc: 'AssemblerAgent 统一打包并输出学习资源包',
      status: states.bundle?.status || 'waiting',
    },
  ]
})


// 定位参数定义：采用“上中下 + 并行区两行网格”布局，避免多个智能体挤在一条横线上
const dagCanvasWidthV2 = 820
const dagCanvasHeightV2 = 660
const dagLayerY: [number, number, number, number, number] = [68, 220, 350, 505, 600]

const dagNodePositionsV2 = computed<Record<string, { x: number; y: number }>>(() => {
  const positions: Record<string, { x: number; y: number }> = {}
  const selected = dagSelectedAgentIds.value
  const cx = dagCanvasWidthV2 / 2

  positions['planning'] = { x: cx, y: dagLayerY[0] }

  if (selected.length > 0) {
    const firstRowCount = selected.length <= 3 ? selected.length : Math.ceil(selected.length / 2)
    const secondRowCount = Math.max(0, selected.length - firstRowCount)
    const firstRow = selected.slice(0, firstRowCount)
    const secondRow = selected.slice(firstRowCount)

    firstRow.forEach((id, i) => {
      const spacing = dagCanvasWidthV2 / (firstRowCount + 1)
      positions[id] = { x: spacing * (i + 1), y: dagLayerY[1] }
    })

    secondRow.forEach((id, i) => {
      const spacing = dagCanvasWidthV2 / (secondRowCount + 1)
      positions[id] = { x: spacing * (i + 1), y: dagLayerY[2] }
    })
  }

  positions['review'] = { x: cx, y: dagLayerY[3] }
  positions['bundle'] = { x: cx, y: dagLayerY[4] }

  return positions
})

const dagEdges = computed<{ from: string; to: string; statusClass: string }[]>(() => {
  const edges: { from: string; to: string; statusClass: string }[] = []
  const selected = dagSelectedAgentIds.value
  const states = dagNodeStates.value

  for (const agentId of selected) {
    const fromDone = states['planning']?.status === 'success'
    edges.push({
      from: 'planning', to: agentId,
      statusClass: fromDone ? (states[agentId]?.status === 'success' ? 'completed' : 'active') : 'pending',
    })

    const agentDone = states[agentId]?.status === 'success'
    edges.push({
      from: agentId, to: 'review',
      statusClass: agentDone ? (states['review']?.status === 'success' ? 'completed' : 'active') : 'pending',
    })
  }

  const reviewDone = states['review']?.status === 'success'
  edges.push({
    from: 'review', to: 'bundle',
    statusClass: reviewDone ? (states['bundle']?.status === 'success' ? 'completed' : 'active') : 'pending',
  })

  return edges
})

const dagHeroMessage = computed(() => {
  const running = Object.values(dagNodeStates.value).find(n => n.status === 'running')
  if (running) return running.currentMessage || `${running.label}处理中...`
  const allDone = Object.values(dagNodeStates.value).every(n => n.status === 'success')
  if (allDone) return '所有资源生成完成'
  return latestWorkflowMessage.value || '多智能体协同生成中'
})

const dagTotalCount = computed(() => dagNodesV2.value.length)
const dagCompletedCount = computed(() => dagNodesV2.value.filter(n => n.status === 'success').length)

// 动态高度和宽度自适应适配
function dagNodeStyle(node: DagNodeState): Record<string, string> {
  const pos = dagNodePositionsV2.value[node.id]
  if (!pos) return {}

  const width = node.isSystem ? 190 : 162
  const height = node.isSystem ? 84 : 78

  return {
    left: `${pos.x - width / 2}px`,
    top: `${pos.y - height / 2}px`,
    width: `${width}px`,
    minHeight: `${height}px`,
    transition: 'left 0.25s ease, top 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease',
  }
}

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
    video: '视频脚本',
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
    video: '可作为后续视频或动画讲解的脚本基础。',
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
    video: 'Script',
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
    code: 'tone-rose',
    quiz: 'tone-emerald',
    reading: 'tone-indigo',
    ppt: 'tone-pink',
    video: 'tone-slate',
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

    const checkStatus = async () => {
      try {
        const taskStatus = await pollResourceStatus(resource_id)
        applyProgressSnapshot(taskStatus.progress)
        if (taskStatus.status === 'completed' || taskStatus.status === 'partial_completed') {
          stopPolling()
          const bundle = await getResourceBundle(resource_id)
          finalBundle.value = bundle
          generatedResources.value = bundle.resources || []
          resultWarning.value = taskStatus.status === 'partial_completed'
              ? '部分资源生成失败或质量审查未通过，以下已完成内容仍可查看。'
              : ''
          isGenerating.value = false
          currentPhase.value = 'result'
        } else if (taskStatus.status === 'failed') {
          stopPolling()
          generationError.value = taskStatus.progress.latest_message || '资源生成失败，暂无可展示内容'
          isGenerating.value = false
          ElMessage.error(generationError.value || '资源生成失败，暂无可展示内容')
        }
      } catch (err: any) {
        stopPolling()
        generationError.value = err.message || '生成中断，请稍后重试'
        isGenerating.value = false
        ElMessage.error(generationError.value || '生成中断，请稍后重试')
      }
    }

    await checkStatus()
    if (isGenerating.value) {
      pollingInterval.value = setInterval(() => {
        void checkStatus()
      }, 3000)
    }
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
  dagNodeStates.value = {}
  selectedDagNodeId.value = 'planning'
}

const stopPolling = () => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value)
    pollingInterval.value = null
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

onMounted(() => {
  const prompt = route.query.prompt
  if (prompt) {
    naturalInput.value = String(prompt)
  }
})

onBeforeUnmount(() => {
  stopPolling()
})

const resetGenerator = () => {
  stopPolling()
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
.elegant-generator-layout { width: 100%; height: calc(100vh - 64px); background: var(--color-bg); font-family: var(--font-sans); overflow-x: hidden; position: relative; padding-top: var(--space-5); }
.phase-view { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; flex-direction: column; background: transparent; }
.page-slide-enter-active, .page-slide-leave-active { transition: opacity 0.4s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.page-slide-enter-from { opacity: 0; transform: translateY(30px) scale(0.98); }
.page-slide-leave-to { opacity: 0; transform: translateY(-30px) scale(1.02); }

/* ================= Phase 1: 输入需求控制 ================= */
.input-view {
  align-items: center;
  justify-content: center;
  padding: 2.4rem 2rem;
  background: #F9FAFB;
}
.input-container { width: 100%; max-width: 800px; display: flex; flex-direction: column; align-items: center; margin-top: -8vh; }
.welcome-header { text-align: center; margin-bottom: 2.75rem; }
.sparkle-icon {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  width: 56px;
  height: 56px;
  background: #FFFFFF;
  color: #111827;
  font-size: 1.6rem;
  border-radius: 16px;
  margin-bottom: 1.25rem;
  border: 1px solid #E5E7EB;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.greeting-title { font-size: clamp(2.1rem, 4.2vw, 3.15rem); font-weight: var(--weight-extrabold); color: var(--color-text); margin: 0 0 0.9rem; letter-spacing: -0.03em; }
.greeting-subtitle { font-size: 1.08rem; color: var(--color-text-muted); line-height: 1.75; max-width: 680px; margin: 0 auto; }
.search-box-wrapper {
  width: 100%;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  border-radius: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
  padding: var(--space-2);
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}
.search-box-wrapper.is-focused {
  border-color: #D1D5DB;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
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

/* ================= Phase 2: 参数定制配置 ================= */
.personalize-view { background: #F9FAFB; align-items: center; overflow-y: auto; padding: 60px var(--space-5); position: relative; }
.aurora-background { display: none; }
.personalize-container { width: 100%; max-width: 1160px; display: flex; flex-direction: column; gap: var(--space-12); position: relative; z-index: 1; }
.view-header { text-align: center; margin-bottom: 0; }
.header-badge { margin-bottom: var(--space-4); font-weight: var(--weight-bold); letter-spacing: 0.05em; background: var(--color-text) !important; border: none; }
.view-header h2 { font-family: var(--font-sans); font-size: 2.5rem; font-weight: var(--weight-extrabold); color: var(--color-text); margin: 0 0 var(--space-4); letter-spacing: -0.02em; }
.view-header p { font-size: 1.1rem; color: var(--color-text-muted); margin: 0; max-width: 600px; margin: 0 auto; line-height: 1.6; }
.scenario-selector-v2 { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-5); }
.scenario-card { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 16px; padding: var(--space-5); display: flex; align-items: center; gap: var(--space-4); cursor: pointer; transition: all 0.2s ease; position: relative; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04); }
.scenario-card:hover { transform: translateY(-2px); border-color: #D1D5DB; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06); }
.scenario-card.active { border-color: #111827; box-shadow: 0 4px 12px rgba(17, 24, 39, 0.08); border-width: 1.5px; }
.scenario-icon-box { width: 44px; height: 44px; background: #F3F4F6; border: 1px solid #E5E7EB; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; color: #4B5563; transition: background-color 0.2s, transform 0.2s; }
.scenario-card.active .scenario-icon-box { background: #111827; color: #FFFFFF; }
.scenario-info { display: flex; flex-direction: column; gap: var(--space-1); flex: 1; }
.s-name { font-weight: var(--weight-bold); font-size: 1rem; color: var(--color-text); }
.s-desc { font-size: 0.75rem; color: var(--color-text-muted); line-height: 1.4; }
.active-dot { position: absolute; top: 12px; right: 12px; width: 8px; height: 8px; background: var(--color-text); border-radius: 50%; }
.config-section-v2 { margin-top: var(--space-2); }
.agent-configs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-6); }
.config-card-v2 { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 16px; overflow: hidden; display: flex; flex-direction: column; transition: all 0.2s ease; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04); }
.config-card-v2:hover { transform: translateY(-2px); border-color: #D1D5DB; box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06); }
.cc-header-v2 { padding: var(--space-5) var(--space-5) 12px; display: flex; align-items: center; gap: var(--space-3); }
.cc-icon-wrap { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; background: #F3F4F6; border: 1px solid #E5E7EB; color: #4B5563; }
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
.slider-value { font-size: 0.9rem; color: var(--color-info); font-weight: var(--weight-bold); }
.custom-slider-v2 { padding: 0 var(--space-2); }
.personalize-footer-v2 { display: flex; flex-direction: column; align-items: center; gap: var(--space-5); margin-top: var(--space-4); padding-bottom: 40px; }
.footer-btns { display: flex; justify-content: center; gap: var(--space-6); }
.selected-agents-bar { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; justify-content: center; background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 16px; padding: var(--space-3) var(--space-5); max-width: 860px; box-shadow: 0 1px 3px rgba(0,0,0,0.03); }
.sab-label { font-size: 0.85rem; color: #6B7280; font-weight: var(--weight-bold); white-space: nowrap; }
.sab-pills { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.sab-pill { display: inline-flex; align-items: center; gap: var(--space-1); font-size: 0.82rem; font-weight: var(--weight-semibold); cursor: default; }
.sab-hint { font-size: 0.78rem; color: #6B7280; font-weight: var(--weight-bold); }
.footer-back-btn { font-weight: var(--weight-semibold); color: #4B5563; border: 1px solid #D1D5DB; }
.launch-btn-v2 { font-weight: var(--weight-bold); padding: 0 var(--space-10); background: #111827 !important; color: #FFFFFF !important; border: none; box-shadow: 0 2px 6px rgba(17, 24, 39, 0.1); transition: transform 0.2s, box-shadow 0.2s; }
.launch-btn-v2:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(17, 24, 39, 0.15); }

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
.workflow-canvas-panel { padding: var(--space-5); }
.canvas-header { margin-bottom: var(--space-4); }
.workflow-canvas {
  position: relative;
  width: 100%;
  max-width: 100%;
  height: 720px;
  margin: 0 auto;
  background-color: #FAFAFA;
  background-image:
    linear-gradient(#F0F0F0 1px, transparent 1px),
    linear-gradient(90deg, #F0F0F0 1px, transparent 1px);
  background-size: 32px 32px;
  border: 1px solid #E5E7EB;
  border-radius: 16px;
  overflow: hidden;
}
.parallel-layer-label {
  position: absolute;
  left: 24px;
  right: 24px;
  top: 145px;
  height: 280px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 10px;
  background: rgba(249, 250, 251, 0.7);
  border: 1px dashed #D1D5DB;
  border-radius: 14px;
  color: #9CA3AF;
  font-size: 0.72rem;
  font-weight: var(--weight-semibold);
  letter-spacing: 0.06em;
  pointer-events: none;
}
.workflow-lines { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1; }
.workflow-edge { stroke-width: 1.2; transition: stroke 0.3s ease, stroke-width 0.3s ease, opacity 0.3s ease; }
.workflow-edge.pending { stroke: #D1D5DB; stroke-dasharray: 5 5; opacity: 0.5; }
.workflow-edge.active { stroke: #374151; stroke-width: 1.8; stroke-dasharray: 8 6; animation: dagFlowMoving 1.2s linear infinite; }
.workflow-edge.completed { stroke: #059669; stroke-width: 1.6; opacity: 0.8; }
@keyframes dagFlowMoving { from { stroke-dashoffset: 28; } to { stroke-dashoffset: 0; } }
.workflow-agent-node {
  position: absolute;
  z-index: 5;
  appearance: none;
  border: 1px solid #E5E7EB;
  background: #FFFFFF;
  border-radius: 14px;
  padding: 10px;
  text-align: left;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  gap: 7px;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.workflow-agent-node:hover, .workflow-agent-node.is-selected { transform: translateY(-2px); border-color: #9CA3AF; box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1); }
.workflow-agent-node.is-waiting { opacity: 0.65; }
.workflow-agent-node.is-running { border-color: #6B7280; box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1); animation: workflowNodePulse 2s ease-in-out infinite; }
.workflow-agent-node.is-success { border-color: #A7F3D0; background: #FAFFFE; }
.workflow-agent-node.is-failed { border-color: #FECACA; background: #FFFBFB; }
.workflow-agent-node.is-system-node { background: #FFFFFF; border-color: #E5E7EB; }
@keyframes workflowNodePulse { 0%, 100% { box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08); } 50% { box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14); } }
.agent-node-topline { display: flex; align-items: center; gap: 8px; min-width: 0; }
.agent-icon-bubble { width: 28px; height: 28px; border-radius: 8px; background: #F3F4F6; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.agent-node-name { font-size: 0.8rem; color: #111827; font-weight: var(--weight-bold); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.agent-status-dot { width: 7px; height: 7px; border-radius: 999px; background: #D1D5DB; margin-left: auto; }
.workflow-agent-node.is-running .agent-status-dot { background: #10B981; box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.15); }
.workflow-agent-node.is-success .agent-status-dot { background: #10B981; }
.workflow-agent-node.is-failed .agent-status-dot { background: #EF4444; }
.agent-node-message { margin: 0; min-height: 20px; font-size: 0.7rem; line-height: 1.45; color: #6B7280; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.agent-node-footer { display: flex; justify-content: space-between; align-items: center; color: #9CA3AF; font-size: 0.68rem; font-weight: var(--weight-semibold); }
.agent-node-footer strong { color: #374151; font-family: var(--font-mono); }
.agent-mini-progress { height: 3px; border-radius: 999px; overflow: hidden; background: #F3F4F6; }
.agent-mini-progress span { display: block; height: 100%; border-radius: inherit; background: #374151; transition: width 0.35s ease; }
.workflow-canvas::before,
.workflow-canvas::after {
  content: '↓';
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
  width: 24px;
  height: 24px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #FFFFFF;
  border: 1px solid #E5E7EB;
  color: #9CA3AF;
  font-weight: var(--weight-semibold);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
}
.workflow-canvas::before { top: 118px; }
.workflow-canvas::after { top: 443px; }

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

h1, h2, h3, h4, .greeting-title, .cc-title { letter-spacing: -0.025em; color: var(--color-text); font-weight: var(--weight-bold); }
p, .card-summary, .s-desc, .greeting-subtitle { line-height: 1.65; letter-spacing: 0.01em; color: var(--color-text-secondary); }
@media (max-width: 1280px) {
  .workflow-canvas {
    height: 520px;
  }
}

</style>