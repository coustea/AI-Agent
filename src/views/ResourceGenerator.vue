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
    <section class="dag-hero-bar" aria-live="polite">
      <div class="dag-hero-left">
        <el-tag class="dag-hero-kicker" effect="plain" round>
          <span class="ping-dot"></span> STREAMING
        </el-tag>
        <h2 class="dag-hero-title">{{ dagHeroMessage }}</h2>
      </div>
      <div class="dag-hero-right">
        <span class="dag-progress-summary">{{ dagCompletedCount }}/{{ dagTotalCount }} 完成</span>
      </div>
    </section>

    <el-alert v-if="generationError" class="generation-error" type="error" :closable="false" show-icon :title="generationError" />

    <main class="dag-canvas-card">
      <div class="dag-canvas">
        <svg class="dag-lines" :viewBox="`0 0 ${dagCanvasWidthV2} ${dagCanvasHeightV2}`" preserveAspectRatio="xMidYMid meet">
          <line v-for="edge in dagEdges" :key="`${edge.from}-${edge.to}`"
            :x1="dagNodePositionsV2[edge.from]?.x" :y1="dagNodePositionsV2[edge.from]?.y"
            :x2="dagNodePositionsV2[edge.to]?.x" :y2="dagNodePositionsV2[edge.to]?.y"
            :class="['dag-edge', edge.statusClass]" />
        </svg>
        <div v-for="node in dagNodesV2" :key="node.id"
          class="dag-node" :class="[`dag-${node.status}`, { 'dag-expanded': dagExpandedNodes[node.id], 'dag-sys': node.isSystem }]"
          :style="dagNodeStyle(node)" @click="toggleDagNodeExpand(node.id)">
          <div class="dag-node-compact">
            <div class="dag-node-head">
              <span class="dag-node-icon">{{ node.icon }}</span>
              <span class="dag-node-name">{{ node.label }}</span>
              <span v-if="node.status === 'success'" class="dag-node-check">✓</span>
              <span v-if="node.status === 'failed'" class="dag-node-x">✗</span>
            </div>
            <div v-if="node.status === 'running'" class="dag-node-running">
              <p class="dag-node-msg">{{ node.currentMessage }}</p>
              <div class="dag-bar"><div class="dag-bar-fill" :style="{ width: `${node.progress}%` }"></div></div>
              <span class="dag-bar-text">{{ node.progress }}%</span>
            </div>
            <div v-if="node.status === 'waiting'" class="dag-node-info">等待中</div>
            <div v-if="node.status === 'success'" class="dag-node-info dag-info-ok">已完成</div>
            <div v-if="node.status === 'failed'" class="dag-node-info dag-info-err">生成失败</div>
          </div>
          <transition name="dag-expand">
            <div v-if="dagExpandedNodes[node.id]" class="dag-node-expanded">
              <div v-for="(step, i) in node.stepHistory" :key="i"
                class="dag-step" :class="{ 'dag-step-cur': i === node.stepHistory.length - 1 && node.status === 'running' }">
                <span class="dag-step-mk">{{ i < node.stepHistory.length - 1 ? '✓' : (node.status === 'running' ? '→' : node.status === 'success' ? '✓' : '✗') }}</span>
                <span class="dag-step-txt">{{ step }}</span>
              </div>
            </div>
          </transition>
        </div>
      </div>
    </main>

    <section class="dag-res-row">
      <div class="dag-res-hdr">
        <el-icon><Collection /></el-icon>
        <span>已生成资源</span>
        <el-tag size="small" effect="plain" round v-if="generatedResources.length">{{ generatedResources.length }} 项</el-tag>
      </div>
      <div v-if="generatedResources.length" class="dag-res-cards">
        <article v-for="resource in sortedGeneratedResources" :key="resource.id || resource.type"
          class="dag-res-card" :class="getResourceToneClass(resource.type)" @click="previewGeneratedResource(resource)">
          <span class="dag-rc-icon">{{ getDagNodeIcon(resource.type) }}</span>
          <span class="dag-rc-title">{{ resource.title || getResourceTypeLabel(resource.type) }}</span>
        </article>
      </div>
      <div v-else class="dag-res-empty"><span class="loading-dots">等待资源生成中...</span></div>
    </section>
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

// Use ResourceGenerateEvent from api/resource.ts - local type not needed


type GeneratedResourceItem = Record<string, any> & {
  generatedAt?: string
  displayOrder?: number
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
const generatedResources = ref<GeneratedResourceItem[]>([])
const reviewResult = ref<any | null>(null)
const finalBundle = ref<any | null>(null)
const profileSummary = ref<Record<string, any> | null>(null)
const isGenerating = ref(false)
const generationError = ref<string | null>(null)
const streamController = ref<AbortController | null>(null)
const resourceDisplayCounter = ref(0)
const USE_FIXED_RESULT_PAGE = false

// ===================== DAG layout =====================

const RESOURCE_TYPE_ORDER = ['content', 'mindmap', 'knowledge_graph', 'code', 'quiz', 'reading', 'ppt', 'video']

// ===================== New DAG Generating Phase State =====================

const AGENT_DISPLAY: Record<string, { label: string; icon: string }> = {
  planning: { label: '规划', icon: '🎯' },
  content: { label: '课程讲解', icon: '📝' },
  mindmap: { label: '思维导图', icon: '🧠' },
  knowledge_graph: { label: '知识图谱', icon: '🔗' },
  quiz: { label: '练习题', icon: '📋' },
  code: { label: '代码案例', icon: '💻' },
  reading: { label: '拓展阅读', icon: '📚' },
  ppt: { label: '演示文稿', icon: '📊' },
  review: { label: '质量审查', icon: '🔍' },
  bundle: { label: '打包', icon: '📦' },
}

interface DagNodeState {
  id: string
  label: string
  icon: string
  status: 'waiting' | 'running' | 'success' | 'failed'
  progress: number
  currentMessage: string
  stepHistory: string[]
  isSystem: boolean
}

const dagNodeStates = ref<Record<string, DagNodeState>>({})
const dagExpandedNodes = ref<Record<string, boolean>>({})

// Which agents are selected in personalize phase
const dagSelectedAgentIds = computed(() => {
  return enabledAgentIds.value.filter(id => !['master', 'reviewer', 'assembler'].includes(id))
})

// DAG Nodes (dynamic based on selected agents)
const dagNodesV2 = computed<DagNodeState[]>(() => {
  const selected = dagSelectedAgentIds.value
  const nodes: DagNodeState[] = []

  // Planning
  nodes.push(dagNodeStates.value['planning'] || {
    id: 'planning', label: '规划', icon: '🎯',
    status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: true,
  })

  // Selected sub-agents
  for (const agentId of selected) {
    const display = AGENT_DISPLAY[agentId]
    if (!display) continue
    nodes.push(dagNodeStates.value[agentId] || {
      id: agentId, label: display.label, icon: display.icon,
      status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: false,
    })
  }

  // Review
  nodes.push(dagNodeStates.value['review'] || {
    id: 'review', label: '质量审查', icon: '🔍',
    status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: true,
  })

  // Bundle
  nodes.push(dagNodeStates.value['bundle'] || {
    id: 'bundle', label: '打包', icon: '📦',
    status: 'waiting', progress: 0, currentMessage: '', stepHistory: [], isSystem: true,
  })

  return nodes
})

// DAG node positions (4-layer layout)
const dagCanvasWidthV2 = 960
const dagCanvasHeightV2 = 520
const dagLayerY: [number, number, number, number] = [60, 200, 340, 460]

const dagNodePositionsV2 = computed<Record<string, { x: number; y: number }>>(() => {
  const positions: Record<string, { x: number; y: number }> = {}
  const selected = dagSelectedAgentIds.value
  const cx = dagCanvasWidthV2 / 2

  // Layer 0: Planning
  positions['planning'] = { x: cx, y: dagLayerY[0] }

  // Layer 1: Sub-agents (evenly distributed)
  if (selected.length > 0) {
    const spacing = dagCanvasWidthV2 / (selected.length + 1)
    selected.forEach((id, i) => {
      positions[id] = { x: spacing * (i + 1), y: dagLayerY[1] }
    })
  }

  // Layer 2: Review
  positions['review'] = { x: cx, y: dagLayerY[2] }

  // Layer 3: Bundle
  positions['bundle'] = { x: cx, y: dagLayerY[3] }

  return positions
})

// DAG edges
const dagEdges = computed<{ from: string; to: string; statusClass: string }[]>(() => {
  const edges: { from: string; to: string; statusClass: string }[] = []
  const selected = dagSelectedAgentIds.value
  const states = dagNodeStates.value

  for (const agentId of selected) {
    // Planning → Agent
    const fromDone = states['planning']?.status === 'success'
    edges.push({
      from: 'planning', to: agentId,
      statusClass: fromDone ? (states[agentId]?.status === 'success' ? 'completed' : 'active') : 'pending',
    })

    // Agent → Review
    const agentDone = states[agentId]?.status === 'success'
    edges.push({
      from: agentId, to: 'review',
      statusClass: agentDone ? (states['review']?.status === 'success' ? 'completed' : 'active') : 'pending',
    })
  }

  // Review → Bundle
  const reviewDone = states['review']?.status === 'success'
  edges.push({
    from: 'review', to: 'bundle',
    statusClass: reviewDone ? (states['bundle']?.status === 'success' ? 'completed' : 'active') : 'pending',
  })

  return edges
})

// Hero message and progress summary
const dagHeroMessage = computed(() => {
  const running = Object.values(dagNodeStates.value).find(n => n.status === 'running')
  if (running) return running.currentMessage || `${running.label}处理中...`
  const allDone = Object.values(dagNodeStates.value).every(n => n.status === 'success')
  if (allDone) return '所有资源生成完成'
  return '多智能体协同生成中'
})

const dagTotalCount = computed(() => dagNodesV2.value.length)
const dagCompletedCount = computed(() => dagNodesV2.value.filter(n => n.status === 'success').length)

// Node style function
function dagNodeStyle(node: DagNodeState): Record<string, string> {
  const pos = dagNodePositionsV2.value[node.id]
  if (!pos) return {}
  const expanded = dagExpandedNodes.value[node.id]
  const width = expanded ? 220 : 160
  const height = expanded ? (80 + node.stepHistory.length * 24) : (node.status === 'running' ? 90 : 56)
  return {
    left: `${pos.x - width / 2}px`,
    top: `${pos.y - height / 2}px`,
    width: `${width}px`,
    minHeight: `${height}px`,
  }
}

// Toggle expand function
function toggleDagNodeExpand(nodeId: string) {
  dagExpandedNodes.value[nodeId] = !dagExpandedNodes.value[nodeId]
}

// Helper functions
function getDagNodeIcon(type: string): string {
  return AGENT_DISPLAY[type]?.icon || '📄'
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

// 预览运行中已生成的单个资源
const previewGeneratedResource = (resource: any) => {
  handlePreview({
    agentId: resource.type,
    resultData: resource.content,
    title: resource.title || getResourceTypeLabel(resource.type)
  })
}

const startGeneration = async () => {
  dagNodeStates.value = {}
  dagExpandedNodes.value = {}
  if (USE_FIXED_RESULT_PAGE) {
    applyFixedResultPage()
    return
  }
  currentPhase.value = 'generating'
  resetGenerationState()
  isGenerating.value = true

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
        currentPhase.value = 'result'
      }
    },
    (err: any) => {
      generationError.value = err.message || '生成中断，请稍后重试'
      isGenerating.value = false
      ElMessage.error(generationError.value || '生成中断，请稍后重试')
    }
  )
}

const applyFixedResultPage = () => {
  const now = new Date().toISOString()
  resetGenerationState()
  currentPhase.value = 'result'
  dagNodeStates.value['planning'] = { id: 'planning', label: '规划', icon: '🎯', status: 'success', progress: 100, currentMessage: '已完成', stepHistory: [], isSystem: true }
  dagNodeStates.value['review'] = { id: 'review', label: '质量审查', icon: '🔍', status: 'success', progress: 100, currentMessage: '已完成', stepHistory: [], isSystem: true }
  dagNodeStates.value['bundle'] = { id: 'bundle', label: '打包', icon: '📦', status: 'success', progress: 100, currentMessage: '已完成', stepHistory: [], isSystem: true }

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
  generatedResources.value = []
  reviewResult.value = null
  finalBundle.value = null
  profileSummary.value = null
  generationError.value = null
  resourceDisplayCounter.value = 0
  isGenerating.value = false
  // Reset DAG state
  dagNodeStates.value = {}
  dagExpandedNodes.value = {}
}

const handleSseEvent = (event: ResourceGenerateEvent) => {
  if (!event?.event_type) return

  // --- Update DAG node state from SSE events ---
  // Backend event type mapping:
  //   PlanningAgent → emit_agent("planning") → event_type="agent", agent="planning"
  //   SubAgents    → emit_agent_action()     → event_type="agent_step"
  //   SubAgents    → emit_agent()            → event_type="agent"
  //   ReviewAgent  → emit_agent("review")    → event_type="agent", agent="review"
  //   Bundle       → emit_bundle()           → event_type="bundle"
  //   Workflow     → emit_workflow()         → event_type="workflow"
  //   Resource     → emit_resource()         → event_type="resource"

  const systemNodeIds = new Set(['planning', 'review', 'bundle'])
  const agentId = event.agent || ''

  // Helper: ensure a dagNodeState exists
  function ensureDagNode(id: string): DagNodeState {
    if (!dagNodeStates.value[id]) {
      const display = AGENT_DISPLAY[id]
      dagNodeStates.value[id] = {
        id, label: display?.label || id, icon: display?.icon || '📄',
        status: 'waiting', progress: 0, currentMessage: '', stepHistory: [],
        isSystem: systemNodeIds.has(id),
      }
    }
    return dagNodeStates.value[id]
  }

  // agent_step: sub-agent is running a step
  if (event.event_type === 'agent_step') {
    const node = ensureDagNode(agentId)
    node.status = 'running'
    node.progress = event.progress ?? node.progress
    node.currentMessage = event.message || node.currentMessage
    if (event.message) node.stepHistory.push(event.message)
  }

  // agent: status update (running/success/failed) for any agent including planning & review
  if (event.event_type === 'agent') {
    const node = ensureDagNode(agentId)
    node.status = event.status === 'skipped' ? 'failed' : (event.status as 'running' | 'success' | 'failed')
    if (event.status === 'success') {
      node.progress = 100
      node.currentMessage = event.message || '已完成'
    } else if (event.status === 'failed') {
      node.currentMessage = event.message || '生成失败'
    } else if (event.status === 'running') {
      node.currentMessage = event.message || node.currentMessage
      if (event.progress) node.progress = event.progress
    }
    if (event.message && node.status !== 'success') node.stepHistory.push(event.message)
  }

  // bundle event
  if (event.event_type === 'bundle') {
    const node = ensureDagNode('bundle')
    node.status = event.status === 'pending' ? 'waiting' : (event.status as 'running' | 'success' | 'failed')
    node.currentMessage = event.message || node.currentMessage
    if (event.message) node.stepHistory.push(event.message)
    if (event.progress) node.progress = event.progress
    if (event.status === 'success') node.progress = 100
    if (event.payload?.bundle) {
      finalBundle.value = event.payload.bundle
    }
  }

  // workflow event
  if (event.event_type === 'workflow') {
    if (event.payload?.profile_summary) {
      profileSummary.value = event.payload.profile_summary
    }
  }

  // resource event: a sub-agent completed its output
  if (event.event_type === 'resource') {
    const resource = event.payload?.resource
    if (resource) {
      const eventTime = event.timestamp || new Date().toISOString()
      upsertResource(resource, eventTime)
      // Mark the agent node as success
      const resAgentId = (resource.type as string) || agentId
      if (resAgentId) {
        const node = ensureDagNode(resAgentId)
        node.status = 'success'
        node.progress = 100
        node.currentMessage = '资源已生成'
      }
    }
  }

  // review event (from emit_review, which has event_type="review")
  if (event.event_type === 'review') {
    const node = ensureDagNode('review')
    node.status = event.status === 'pending' ? 'waiting' : (event.status as 'running' | 'success' | 'failed')
    node.currentMessage = event.message || node.currentMessage
    if (event.message) node.stepHistory.push(event.message)
    if (event.progress) node.progress = event.progress
    if (event.payload?.review_result) {
      reviewResult.value = event.payload.review_result
    }
    if (event.status === 'success') node.progress = 100
  }

  // done event
  if (event.event_type === 'done') {
    finalBundle.value = event.payload?.bundle || finalBundle.value
    // Mark all system nodes as success
    ensureDagNode('planning').status = 'success'
    ensureDagNode('planning').progress = 100
    ensureDagNode('review').status = 'success'
    ensureDagNode('review').progress = 100
    ensureDagNode('bundle').status = 'success'
    ensureDagNode('bundle').progress = 100
    isGenerating.value = false
    closeSseConnection()
    currentPhase.value = 'result'
  }

  // error event
  if (event.event_type === 'error') {
    generationError.value = event.message
    isGenerating.value = false
    // Mark all running nodes as failed
    Object.values(dagNodeStates.value).forEach(node => {
      if (node.status === 'running') node.status = 'failed'
    })
    closeSseConnection()
  }
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
.generation-error { border-radius: var(--radius-xl); }
.generation-workbench { flex: 1 0 auto !important; min-height: min-content !important; }

/* ================= DAG Canvas ================= */
.dag-canvas-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-2xl); box-shadow: var(--shadow-md); padding: var(--space-6); }
.dag-canvas { position: relative; overflow: auto; border-radius: var(--radius-2xl); background: var(--color-bg); border: 1px solid rgba(226, 232, 240, 0.6); min-height: 480px; }

/* DAG SVG lines */
.dag-lines { position: absolute; inset: 0; z-index: 1; width: 100%; height: 100%; pointer-events: none; }
.dag-edge { stroke: var(--color-border-hover); stroke-width: 2; stroke-linecap: round; opacity: 0.5; }
.dag-edge.dashed { stroke-dasharray: 6 4; opacity: 0.4; }
.dag-edge.flowing { stroke: var(--color-info); stroke-width: 2.5; stroke-dasharray: 8 6; animation: dagFlowDash 1s linear infinite; opacity: 1; }
.dag-edge.completed { stroke: var(--color-success); stroke-width: 2; opacity: 0.7; }
@keyframes dagFlowDash { to { stroke-dashoffset: -14; } }

/* DAG Node base */
.dag-node {
  position: absolute;
  z-index: 5;
  width: 160px;
  border: 2px solid rgba(203, 213, 225, 0.6);
  border-radius: var(--radius-xl);
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  cursor: pointer;
  color: var(--color-text-secondary);
  box-shadow: var(--shadow-sm);
  padding: var(--space-3) var(--space-4);
  text-align: left;
  transition: border-color 0.3s ease, box-shadow 0.3s ease, transform 0.2s ease;
}
.dag-node:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* DAG Node head */
.dag-node-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.dag-node-emoji { font-size: 1.25rem; line-height: 1; flex-shrink: 0; }
.dag-node-label { font-weight: var(--weight-extrabold); font-size: 0.9rem; color: var(--color-text-strong); line-height: 1.2; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dag-node-check { color: var(--color-success); font-weight: var(--weight-extrabold); font-size: 0.9rem; margin-left: auto; flex-shrink: 0; }
.dag-node-x { color: var(--color-danger); font-weight: var(--weight-extrabold); font-size: 0.9rem; margin-left: auto; flex-shrink: 0; }

/* Node status-specific text */
.dag-node-status-text { font-size: 0.78rem; color: var(--color-text-faint); font-weight: var(--weight-semibold); }
.dag-node-failed-text { color: var(--color-danger); }

/* Running state */
.dag-node-running { display: flex; flex-direction: column; gap: var(--space-1); }
.dag-node-step-msg { margin: 0; font-size: 0.78rem; color: var(--color-text-secondary); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.dag-node-progress-bar { height: 4px; background: var(--color-border); border-radius: var(--radius-pill); overflow: hidden; }
.dag-node-progress-fill { height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--color-info), var(--color-primary)); transition: width 0.3s ease; }
.dag-node-progress-text { font-size: 0.7rem; color: var(--color-info); font-weight: var(--weight-extrabold); font-variant-numeric: tabular-nums; }

/* Node visual states */
.dag-node.is-waiting { border-color: rgba(203, 213, 225, 0.6); }
.dag-node.is-waiting .dag-node-emoji { opacity: 0.5; }
.dag-node.is-waiting .dag-node-label { color: var(--color-text-faint); }

.dag-node.is-running {
  border-color: #7C9CF5;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08), var(--shadow-md);
  animation: dagNodePulse 2s ease-in-out infinite;
}
.dag-node.is-running .dag-node-emoji { opacity: 1; }
.dag-node.is-running .dag-node-label { color: var(--color-text); }
@keyframes dagNodePulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08), var(--shadow-md); }
  50% { box-shadow: 0 0 0 5px rgba(99, 102, 241, 0.12), 0 8px 24px rgba(15, 23, 42, 0.08); }
}

.dag-node.is-success { border-color: #86EFAC; }
.dag-node.is-success .dag-node-emoji { opacity: 1; }
.dag-node.is-success .dag-node-label { color: var(--color-text); }

.dag-node.is-failed { border-color: #FCA5A5; }
.dag-node.is-failed .dag-node-emoji { opacity: 1; }
.dag-node.is-failed .dag-node-label { color: var(--color-text); }

/* Expanded node: step history */
.dag-node.expanded {
  box-shadow: var(--shadow-lg);
  z-index: 10;
}
.dag-node-steps {
  margin-top: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  max-height: 200px;
  overflow-y: auto;
}
.dag-step-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-1);
  font-size: 0.75rem;
  line-height: 1.4;
}
.dag-step-marker { flex-shrink: 0; font-size: 0.7rem; }
.dag-step-item.is-done .dag-step-marker { color: var(--color-success); }
.dag-step-item.is-current .dag-step-marker { color: var(--color-info); }
.dag-step-text { color: var(--color-text-secondary); word-break: break-word; }
.dag-step-item.is-done .dag-step-text { color: var(--color-text-faint); }
.dag-step-item.is-current .dag-step-text { color: var(--color-text); font-weight: var(--weight-semibold); }

/* Expand transition */
.dag-expand-enter-active, .dag-expand-leave-active { transition: all 0.25s ease; overflow: hidden; }
.dag-expand-enter-from, .dag-expand-leave-to { opacity: 0; max-height: 0; margin-top: 0; padding-top: 0; }
.dag-expand-enter-to, .dag-expand-leave-from { opacity: 1; max-height: 200px; }

/* Resource panel below DAG */
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
.side-empty.minimal { display: flex; align-items: center; justify-content: center; height: 100px; color: var(--color-text-faint); font-size: 0.9rem; font-weight: var(--weight-semibold); }

.interactive-resources-panel { min-height: 0; height: auto; padding-top: var(--space-1); padding-bottom: var(--space-1); }

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
  .resource-side-panel { grid-column: 1 / -1; position: static; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .agent-configs-grid { grid-template-columns: repeat(2, 1fr); }
  .bento-stats-row { grid-template-columns: repeat(2, 1fr); }
  .bento-resource-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); }
  .bento-res-card { grid-column: span 2 !important; }
  .resource-metric-stack { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .results-body-bento { padding: var(--space-6) var(--space-8); }
  .generated-resource-card { grid-column: span 4; }
  .interactive-resources-panel { min-height: 0; height: auto; }
  .dag-canvas { min-height: 380px; }
  .dag-node { width: 140px; }
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
  .resource-side-panel { grid-template-columns: 1fr; }
  .resource-status-item { grid-template-columns: 1fr; }
  .generated-resource-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .generated-resource-card { grid-column: span 1; grid-template-columns: auto minmax(0, 1fr); min-height: 0; }
  .interactive-resources-panel { min-height: 0; }
  .resource-card-action { grid-column: 1 / -1; width: 100%; }
  .resource-side-panel { position: static; }
  .results-body-bento { padding: var(--space-4); }
  .result-hero-minimal { padding: var(--space-5); }
  .bento-stats-row { grid-template-columns: 1fr; }
  .bento-resource-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .bento-res-card { grid-column: span 1 !important; }
  .compact-hero-bar { flex-direction: column; align-items: flex-start; gap: var(--space-4); }
  .dag-canvas { min-height: 360px; }
  .dag-node { width: 120px; padding: var(--space-2) var(--space-3); }
  .dag-node-label { font-size: 0.78rem; }
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

/* ================= 极简明亮模式：生成中顶部面板 ================= */
.compact-hero-bar { background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(226, 232, 240, 0.8); border-radius: var(--radius-xl); padding: var(--space-4) var(--space-6); display: flex; justify-content: space-between; align-items: center; box-shadow: var(--shadow-sm); transition: all var(--transition-slow); }
.hero-bar-left { display: flex; align-items: center; gap: var(--space-5); }
.hero-kicker { display: flex; align-items: center; gap: var(--space-1); color: #0369A1 !important; border-color: #BAE6FD !important; background: #F0F9FF !important; font-weight: var(--weight-extrabold); padding: 0 var(--space-3); }
.ping-dot { width: 8px; height: 8px; border-radius: 50%; background-color: var(--color-success); animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite; }
@keyframes ping { 75%, 100% { transform: scale(2); opacity: 0; } }
.hero-bar-title { margin: 0 0 var(--space-1); font-size: 1.25rem; font-weight: var(--weight-extrabold); color: var(--color-text); }
.hero-bar-message { margin: 0; color: var(--color-text-muted); font-size: 0.9rem; }
.hero-bar-right { display: flex; align-items: center; gap: var(--space-6); }
.mini-progress { position: relative; display: flex; justify-content: center; align-items: center; }
.mini-progress-text { position: absolute; font-size: 0.75rem; font-weight: var(--weight-extrabold); color: #0369A1; }

/* DAG Generating Phase */
.dag-hero-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: linear-gradient(135deg, #0c4a6e 0%, #164e63 100%);
  border-radius: 12px;
  margin-bottom: 16px;
}
.dag-hero-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.dag-hero-kicker {
  color: #7dd3fc !important;
  border-color: rgba(125, 211, 252, 0.3) !important;
  background: rgba(125, 211, 252, 0.08) !important;
}
.dag-hero-title {
  color: #f0f9ff;
  font-size: 15px;
  font-weight: 500;
  margin: 0;
}
.dag-hero-right {
  display: flex;
  align-items: center;
}
.dag-progress-summary {
  color: #7dd3fc;
  font-size: 13px;
  font-weight: 600;
}

.dag-canvas-card {
  background: #0f172a;
  border-radius: 12px;
  border: 1px solid #1e293b;
  padding: 20px;
  margin-bottom: 16px;
  overflow: hidden;
}
.dag-canvas {
  position: relative;
  width: 960px;
  max-width: 100%;
  margin: 0 auto;
  height: 520px;
}

/* SVG edges */
.dag-lines {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.dag-edge {
  stroke-width: 2;
  transition: stroke 0.3s, stroke-dasharray 0.3s;
}
.dag-edge.pending {
  stroke: #334155;
  stroke-dasharray: 6 4;
}
.dag-edge.active {
  stroke: #38bdf8;
  stroke-dasharray: none;
  animation: dag-edge-flow 1.5s linear infinite;
}
.dag-edge.completed {
  stroke: #22c55e;
  stroke-dasharray: none;
}
@keyframes dag-edge-flow {
  from { stroke-dashoffset: 10; }
  to { stroke-dashoffset: 0; }
}

/* DAG nodes */
.dag-node {
  position: absolute;
  background: #1e293b;
  border: 2px solid #334155;
  border-radius: 10px;
  padding: 8px 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  z-index: 1;
}
.dag-node:hover {
  border-color: #475569;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
.dag-node.dag-waiting {
  border-color: #334155;
  opacity: 0.6;
}
.dag-node.dag-running {
  border-color: #38bdf8;
  box-shadow: 0 0 16px rgba(56, 189, 248, 0.25);
  animation: dag-pulse 2s ease-in-out infinite;
}
.dag-node.dag-success {
  border-color: #22c55e;
  opacity: 0.9;
}
.dag-node.dag-failed {
  border-color: #ef4444;
  opacity: 0.9;
}
.dag-node.dag-system {
  background: #1a2332;
}
@keyframes dag-pulse {
  0%, 100% { box-shadow: 0 0 8px rgba(56, 189, 248, 0.15); }
  50% { box-shadow: 0 0 20px rgba(56, 189, 248, 0.35); }
}

.dag-node-compact {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.dag-node-head {
  display: flex;
  align-items: center;
  gap: 6px;
}
.dag-node-icon {
  font-size: 16px;
}
.dag-node-name {
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 600;
}
.dag-node-check {
  color: #22c55e;
  font-weight: bold;
  margin-left: auto;
}
.dag-node-x {
  color: #ef4444;
  font-weight: bold;
  margin-left: auto;
}

.dag-node-running-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.dag-node-message {
  color: #94a3b8;
  font-size: 11px;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dag-node-progress-bar {
  height: 4px;
  background: #334155;
  border-radius: 2px;
  overflow: hidden;
}
.dag-node-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #0ea5e9, #38bdf8);
  border-radius: 2px;
  transition: width 0.5s ease;
}
.dag-node-progress-text {
  color: #7dd3fc;
  font-size: 10px;
}
.dag-node-waiting-info,
.dag-node-success-info,
.dag-node-failed-info {
  color: #64748b;
  font-size: 11px;
}
.dag-node-success-info {
  color: #4ade80;
}
.dag-node-failed-info {
  color: #f87171;
}

/* Expanded step history */
.dag-node-expanded {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid #334155;
}
.dag-step-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 2px 0;
  font-size: 11px;
  color: #94a3b8;
}
.dag-step-row.dag-step-current {
  color: #38bdf8;
}
.dag-step-marker {
  flex-shrink: 0;
  width: 14px;
  text-align: center;
}
.dag-step-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dag-expand-enter-active,
.dag-expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.dag-expand-enter-from,
.dag-expand-leave-to {
  opacity: 0;
  max-height: 0;
}

/* Resource row */
.dag-resource-row {
  background: #0f172a;
  border-radius: 12px;
  border: 1px solid #1e293b;
  padding: 12px 16px;
}
.dag-resource-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: #94a3b8;
  font-size: 13px;
}
.dag-resource-cards {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.dag-resource-card {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.dag-resource-card:hover {
  border-color: #475569;
  background: #263348;
}
.dag-rc-icon {
  font-size: 14px;
}
.dag-rc-title {
  color: #e2e8f0;
  font-size: 12px;
}
.dag-resource-empty {
  color: #64748b;
  font-size: 13px;
}
</style>
