<template>
  <div class="elegant-generator-layout">
    <transition name="page-slide" mode="out-in">

      <div v-if="currentPhase === 'input'" class="phase-view omni-input-view" key="input">
        <div class="omni-ambient-bg">
          <div class="ambient-glow glow-blue"></div>
          <div class="ambient-glow glow-indigo"></div>
          <div class="omni-pattern-bg"></div>
        </div>
        
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
                        <el-radio-button label="both">中英双语</el-radio-button>
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
                <h3>多智能体 OPRE 执行拓扑</h3>
              </div>
              <div class="stage-control-pills">
                <span class="control-pill active"><span class="live-dot"></span> SSE 实时流追踪</span>
              </div>
            </div>

            <div class="dispatch-stage dag-flow-wrapper">
              <transition-group name="dag-col-anim" tag="div" class="dag-flow-container">
                <div class="dag-col" v-for="(col, colIndex) in dagColumns" :key="'col-'+colIndex">
                  <transition-group name="dag-node-anim" tag="div" class="dag-col-inner">
                    <div
                      v-for="(node, nodeIdx) in col"
                      :key="node.id"
                      class="dag-node-card"
                      :class="['status-' + node.status, { 'is-selected': selectedDagNodeId === node.id }]"
                      :style="{ transitionDelay: `${nodeIdx * 0.1}s` }"
                      @click="selectedDagNodeId = node.id"
                    >
                      <div class="node-indicator"></div>
                      
                      <div class="node-inner">
                        <div class="node-head">
                          <div class="node-icon">
                            <span>{{ node.icon }}</span> 
                          </div>
                          <div class="node-title-group">
                            <strong>{{ node.label }}</strong>
                            <span class="node-sub">
                              {{ node.status === 'success' ? '已就绪' : node.status === 'running' ? '执行指令中' : '挂起等待' }}
                            </span>
                          </div>
                          <div class="node-status-pill">
                            {{ node.status === 'success' ? '100%' : (node.progress + '%') }}
                          </div>
                        </div>
                        
                        <div class="node-divider"></div>
                        
                        <div class="node-body">
                          <div class="meta-row">
                            <span class="meta-label">
                              {{ node.status === 'running' ? '当前动作' : node.status === 'success' ? '最终状态' : '依赖事件' }}
                            </span>
                            <span class="meta-time" v-if="node.status !== 'waiting'">
                              {{ getCurrentTimeStr() }}
                            </span>
                            <span class="meta-time" v-else>等待上游</span>
                          </div>
                          <p class="node-message" :class="{'is-error': node.status === 'failed'}">
                            {{ node.status === 'failed' ? '执行失败，请检查审核日志' : (node.currentMessage || '等待前置任务就绪') }}
                          </p>
                        </div>
                      </div>

                      <transition name="fade-edge">
                        <div class="dag-edge-out" v-if="colIndex < dagColumns.length - 1 && node.status !== 'waiting'"></div>
                      </transition>
                    </div>
                  </transition-group>
                </div>
              </transition-group>
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
  ArrowRight, RefreshLeft,
  Clock, Odometer, Top, StarFilled,
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
const generatedResources = ref<GeneratedResourceItem[]>([])
const finalBundle = ref<any | null>(null)
const isGenerating = ref(false)
const generationError = ref<string | null>(null)
const resultWarning = ref('')
const overallProgress = ref(0)
const latestWorkflowMessage = ref('')
const pollingInterval = ref<ReturnType<typeof setInterval> | null>(null)
const resourceStreamController = ref<EventSource | null>(null)
const generationFinalized = ref(false)

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
  nodes.push(dagNodeStates.value['bundle'] || {
    id: 'bundle', label: '资源组装', icon: '📦',
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

// ===================== DAG 拓扑视图列分组 (严丝合缝对齐后端架构) =====================
const dagColumns = computed(() => {
  const nodes = visibleWorkflowNodes.value;
  
  // 1. 顶层规划 (Stage 1: Planning Agent)
  const col1 = nodes.filter(n => n.id === 'planning');
  
  // 2. 基础资源并行层 (Stage 2: Parallel Worker Agents)
  const col2 = nodes.filter(n => ['content', 'mindmap', 'quiz', 'code', 'reading'].includes(n.id));
  
  // 3. 前置事实与安全审核 (Stage 3: Pre Review)
  const col3 = nodes.filter(n => n.id === PRE_REVIEW_AGENT_ID);
  
  // 4. 演示文稿生成 (Stage 3 延伸: 严格依赖预审通过的内容)
  const col4 = nodes.filter(n => n.id === PPT_AGENT_ID);
  
  // 5. 演示文稿专项审核 (Stage 3 延伸: PPT Review)
  const col5 = nodes.filter(n => n.id === PPT_REVIEW_AGENT_ID);
  
  // 6. 数据打包与组装落库 (Stage 4: Assembler / Save)
  const col6 = nodes.filter(n => n.id === 'bundle');

  // 过滤掉空列
  return [col1, col2, col3, col4, col5, col6].filter(col => col.length > 0);
});

const getCurrentTimeStr = () => {
  const d = new Date();
  return `${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}:${d.getSeconds().toString().padStart(2,'0')}`;
};

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
    [PRE_REVIEW_AGENT_ID]: createDagNode(PRE_REVIEW_AGENT_ID, true),
    bundle: createDagNode('bundle', true),
  }
  if (enabledAgentIds.value.includes(PPT_AGENT_ID as ResourceAgentId)) {
    nodes[PPT_REVIEW_AGENT_ID] = createDagNode(PPT_REVIEW_AGENT_ID, true)
  }
  enabledAgentIds.value.forEach((agentId) => {
    nodes[agentId] = createDagNode(agentId, false)
  })
  dagNodeStates.value = nodes
  selectedDagNodeId.value = 'planning'
}

function applyAgentEvent(event: ResourceStreamEvent) {
  if (!event.agent_id) return
  const node = dagNodeStates.value[event.agent_id] || createDagNode(
    event.agent_id,
    SYSTEM_AGENT_IDS.includes(event.agent_id),
  )
  if (event.status) node.status = event.status === 'finished' ? 'success' : event.status
  node.currentMessage = event.message || ''
  dagNodeStates.value[event.agent_id] = node

  if (event.status === 'running') {
    selectedDagNodeId.value = event.agent_id
  }
}

function applyTaskStatus(taskStatus: ResourceTaskStatus) {
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

function startResourceStream(resourceId: number) {
  stopResourceStream()
  resourceStreamController.value = streamResourceEvents(
    resourceId,
    (event) => {
      applyAgentEvent(event)
      if (event.message) {
        latestWorkflowMessage.value = event.message
      }
    },
    (event) => {
      if (isGenerating.value && !generationFinalized.value) {
        void completeGeneration(resourceId, { resource_id: resourceId, status: event.success ? 'completed' : 'failed' })
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
    resourceStreamController.value.close()
    resourceStreamController.value = null
  }
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
.agent-stage-canvas {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(18px);
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

/* ================= 严格后面对齐的 DAG 画布样式 ================= */
.dag-flow-wrapper {
  position: relative;
  min-height: 580px;
  background: #F8FAFC;
  border-radius: 16px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 40px;
  /* 科技感背景暗网格 */
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.1) 1px, transparent 1px);
  background-size: 24px 24px;
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
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 14px;
  border: 1px solid #E2E8F0;
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
  background: #CBD5E1; 
}
.status-success .node-indicator { background: #10B981; }
.status-running .node-indicator { background: #3B82F6; box-shadow: 0 0 8px rgba(59, 130, 246, 0.6); }
.status-failed .node-indicator { background: #EF4444; }

.node-inner { padding: 14px 16px 14px 20px; }

/* 头部排版 */
.node-head { display: flex; align-items: center; gap: 12px; }
.node-icon {
  width: 38px; height: 38px; border-radius: 10px;
  background: #F1F5F9; color: #64748B;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.15rem; border: 1px solid rgba(0,0,0,0.03);
}
.status-success .node-icon { background: #D1FAE5; color: #10B981; }
.status-running .node-icon { background: #DBEAFE; color: #3B82F6; }
.status-failed .node-icon { background: #FEE2E2; color: #EF4444; }

.node-title-group { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.node-title-group strong { color: #0F172A; font-size: 0.92rem; font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.node-title-group .node-sub { color: #94A3B8; font-size: 0.72rem; }

.node-status-pill {
  font-family: var(--font-mono, monospace);
  font-size: 0.72rem; font-weight: 800;
  background: #F8FAFC; padding: 3px 8px; border-radius: 6px;
  color: #64748B;
}
.status-running .node-status-pill { background: #EFF6FF; color: #2563EB; }
.status-success .node-status-pill { background: #ECFDF5; color: #10B981; }

.node-divider { margin: 12px 0; border-top: 1px dashed #E2E8F0; }

/* 底部状态消息区 */
.meta-row { display: flex; justify-content: space-between; margin-bottom: 6px; }
.meta-label { font-size: 0.75rem; font-weight: 700; color: #3B82F6; }
.status-waiting .meta-label { color: #94A3B8; }
.status-success .meta-label { color: #10B981; }
.meta-time { font-size: 0.75rem; color: #94A3B8; font-family: var(--font-mono, monospace); }

.node-message {
  margin: 0; font-size: 0.78rem; color: #475569;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; height: 34px; line-height: 1.45;
}
.status-running .node-message { color: #1E293B; }
.node-message.is-error { color: #EF4444; font-weight: 600; }

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
.status-waiting .dag-edge-out { background-image: linear-gradient(90deg, #CBD5E1 50%, transparent 50%); animation: none; }
/* 成功态：虚线静止并变绿 */
.status-success .dag-edge-out { background-image: linear-gradient(90deg, #10B981 50%, transparent 50%); animation: none; }
/* 失败态：虚线静止并变红 */
.status-failed .dag-edge-out { background-image: linear-gradient(90deg, #EF4444 50%, transparent 50%); animation: none; }

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
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.96);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(18px);
}
.output-dock-heading { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.output-dock-heading > div { display: flex; flex-direction: column; gap: 4px; }
.output-dock-heading strong { color: #0F172A; font-size: 0.98rem; font-weight: 900; line-height: 1.2; }
.output-dock-heading p { margin: 0; color: #64748B; font-size: 0.74rem; line-height: 1.5; }
.output-dock-list { display: grid; grid-template-columns: repeat(6, minmax(130px, 1fr)); gap: 10px; min-width: 0; }
.output-dock-item { display: flex; gap: 8px; align-items: center; padding: 8px 10px; border: 1px solid #E2E8F0; border-radius: 16px; background: #F8FAFC; opacity: 0.72; transition: opacity 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease; cursor: default; }
.output-dock-item.ready { opacity: 1; background: #F0FDF4; border-color: #A7F3D0; cursor: pointer; }
.output-dock-item.ready:hover { transform: translateY(-2px); box-shadow: 0 14px 28px rgba(16, 185, 129, 0.10); }
.output-dock-item > span { width: 26px; height: 26px; border-radius: 8px; background: #FFFFFF; display: grid; place-items: center; flex-shrink: 0; font-size: 0.9rem; }
.output-dock-item strong { display: block; color: #0F172A; font-size: 0.72rem; font-weight: 900; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.output-dock-item p { margin: 1px 0 0; color: #64748B; font-size: 0.65rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.output-dock-empty { min-height: 40px; display: flex; align-items: center; justify-content: center; border: 1px dashed #CBD5E1; border-radius: 12px; color: #64748B; background: #F8FAFC; font-size: 0.78rem; font-weight: 800; }

.workflow-log-drawer :deep(.el-drawer__header) { margin-bottom: 0; padding: 20px 22px; border-bottom: 1px solid #E2E8F0; font-weight: 900; color: #0F172A; }
.drawer-log-list { display: flex; flex-direction: column; gap: 14px; padding: 4px; }
.drawer-log-item { display: flex; gap: 12px; align-items: flex-start; padding: 12px; border-radius: 16px; background: #F8FAFC; border: 1px solid #E2E8F0; }
.drawer-log-dot { width: 10px; height: 10px; border-radius: 999px; background: #CBD5E1; margin-top: 5px; flex-shrink: 0; }
.drawer-log-item.is-running .drawer-log-dot { background: #F97316; box-shadow: 0 0 0 5px rgba(249, 115, 22, 0.12); }
.drawer-log-item.is-success .drawer-log-dot { background: #10B981; }
.drawer-log-item.is-failed .drawer-log-dot { background: #EF4444; }
.drawer-log-item strong { color: #0F172A; font-size: 0.86rem; font-weight: 900; }
.drawer-log-item p { margin: 4px 0 0; color: #64748B; font-size: 0.78rem; line-height: 1.45; }


/* ================= Phase 4: 交付中心看板 (Bento Layout) ================= */
.results-view { background: #F9FAFB; overflow-y: auto; padding-bottom: 80px; position: relative; }
.result-hero-compact { display: flex; justify-content: space-between; align-items: center; padding: var(--space-4) var(--space-8); background: #FFFFFF; border-bottom: 1px solid #E5E7EB; margin-bottom: var(--space-6); border-radius: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); position: sticky; top: 0; z-index: 100; }
.hero-content-left { display: flex; flex-direction: column; gap: var(--space-1); }
.hero-status-tag-mini { display: inline-flex; align-items: center; gap: var(--space-1); color: var(--color-success); font-size: 0.75rem; font-weight: var(--weight-extrabold); }
.hero-title-compact { margin: 0; font-size: 1.25rem; font-weight: var(--weight-extrabold); color: var(--color-text-strong); }
.hero-subtitle-compact { margin: 0; font-size: 0.85rem; color: var(--color-text-muted); }
.hero-actions-right { display: flex; gap: var(--space-3); align-items: center; }
.results-body-bento { max-width: 1440px; margin: 0 auto; padding: var(--space-10) 60px; display: flex; flex-direction: column; gap: var(--space-10); position: relative; z-index: 1; }
.premium-resource-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 24px; align-items: stretch; }
.premium-res-card { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 16px; padding: 24px; display: flex; flex-direction: column; gap: 20px; position: relative; overflow: hidden; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03); cursor: pointer; animation: fadeSlideUp 0.6s ease-out backwards; }
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
}
@media (max-width: 900px) {
  .workflow-stage-page { overflow: auto; }
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
.is-ppt-dialog :deep(.el-dialog__body) { padding: 0 !important; background: #F8FAFC !important; }
.preview-dialog-body.is-ppt-preview { padding: 0 !important; background: transparent !important; border: none !important; box-shadow: none !important; }
.preview-dialog-body.is-ppt-preview :deep(.player-wrapper) { margin-top: 0 !important; border: none !important; border-radius: 0 !important; }

h1, h2, h3, h4, .cc-title { letter-spacing: -0.025em; color: var(--color-text); font-weight: var(--weight-bold); }
p, .card-summary, .s-desc { line-height: 1.65; letter-spacing: 0.01em; color: var(--color-text-secondary); }

</style>