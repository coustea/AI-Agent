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
              placeholder="例如：我是软件工程大二学生，明天考《操作系统》。我搞不懂死锁的四个必要条件，我喜欢看图解，请帮我生成复习资料和几道自测题..."
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
        <div class="personalize-container">
          <div class="view-header">
            <h2>多智能体参数定制中心</h2>
            <p>请为即将出场的 AI 智能体配置加工参数，您的输入指令将作为最高优先级要求贯穿全局。</p>
          </div>

          <div class="scenario-selector">
            <label>学习场景</label>
            <el-select v-model="learningScenario" @change="applyScenarioDefaults" size="small">
              <el-option label="🎯 考试备考" value="exam_prep" />
              <el-option label="📚 日常学习" value="daily_review" />
              <el-option label="💻 项目实践" value="project_practice" />
              <el-option label="📖 预习自学" value="self_study" />
            </el-select>
            <span class="hint">切换场景会自动调整下方配置，您仍可手动修改</span>
          </div>

          <div class="config-section">
            <div class="agent-configs-grid">
              
              <div class="config-card">
                <div class="cc-header">
                  <el-icon class="text-blue"><Document /></el-icon> 核心知识讲解
                </div>
                <div class="cc-body">
                  <div class="ctrl-group">
                    <label>讲解结构</label>
                    <el-select v-model="agentConfigs.content.structure" size="small" class="w-full">
                      <el-option label="渐进式引导 (Progressive)" value="progressive" />
                      <el-option label="先总后分 (Summary First)" value="summary_first" />
                      <el-option label="考点驱动 (Exam Points)" value="exam_points" />
                      <el-option label="案例驱动 (Case Driven)" value="case_driven" />
                    </el-select>
                  </div>
                  <div class="ctrl-group ctrl-switch-group">
                    <div class="ctrl-switch"><label>涵盖易错点解析</label><el-switch v-model="agentConfigs.content.include_common_mistakes" /></div>
                    <div class="ctrl-switch"><label>丰富生活化示例</label><el-switch v-model="agentConfigs.content.include_examples" /></div>
                  </div>
                </div>
              </div>

              <div class="config-card">
                <div class="cc-header">
                  <el-icon class="text-orange"><Monitor /></el-icon> 原理可视化图解
                </div>
                <div class="cc-body">
                  <div class="ctrl-group">
                    <label>图解渲染范式</label>
                    <el-select v-model="agentConfigs.diagram.diagram_type" size="small" class="w-full">
                      <el-option label="💡 智能自动判断 (Auto)" value="auto" />
                      <el-option-group label="通用基础图解">
                        <el-option label="层级结构图 (Hierarchy)" value="hierarchy" />
                        <el-option label="顺序流程图 (Flow)" value="flow" />
                        <el-option label="对比结构图 (Compare)" value="compare" />
                        <el-option label="因果关系图 (Relation)" value="relation" />
                        <el-option label="状态转移图 (State)" value="state" />
                      </el-option-group>
                      <el-option-group label="计算机学科专用">
                        <el-option label="类继承图 (Class)" value="class" />
                        <el-option label="系统方块图 (Block)" value="block" />
                        <el-option label="网络包格式图 (Packet)" value="packet" />
                      </el-option-group>
                      <el-option-group label="软件工程图表">
                        <el-option label="交互时序图 (Sequence)" value="sequence" />
                        <el-option label="活动图 (Activity)" value="activity" />
                        <el-option label="组件图 (Component)" value="component" />
                      </el-option-group>
                    </el-select>
                  </div>
                  <div class="ctrl-group">
                    <label>视觉呈现风格</label>
                    <el-radio-group v-model="agentConfigs.diagram.visual_style" size="small" class="w-full-radios">
                      <el-radio-button label="minimal">极简纯净</el-radio-button>
                      <el-radio-button label="exam">严肃应试</el-radio-button>
                    </el-radio-group>
                  </div>
                </div>
              </div>

              <div class="config-card">
                <div class="cc-header">
                  <el-icon class="text-purple"><Share /></el-icon> 知识结构图谱
                </div>
                <div class="cc-body">
                  <div class="ctrl-group">
                    <label>导图生成策略</label>
                    <el-select v-model="agentConfigs.mindmap.map_type" size="small" class="w-full">
                      <el-option label="核心知识树 (Knowledge Tree)" value="knowledge_tree" />
                      <el-option label="高频考点图 (Exam Map)" value="exam_map" />
                      <el-option label="对比复习图 (Comparison)" value="comparison_map" />
                    </el-select>
                  </div>
                  <div class="ctrl-group">
                    <label>节点发散层级: <b>{{ agentConfigs.mindmap.max_depth }} 层</b></label>
                    <el-slider v-model="agentConfigs.mindmap.max_depth" :min="2" :max="5" :step="1" class="custom-slider" show-stops />
                  </div>
                </div>
              </div>

              <div class="config-card">
                <div class="cc-header">
                  <el-icon class="text-red"><Cpu /></el-icon> 实战代码沙箱
                </div>
                <div class="cc-body">
                  <div class="ctrl-group">
                    <label>编程语言目标</label>
                    <el-select v-model="agentConfigs.code.programming_language" size="small" class="w-full">
                      <el-option label="Python" value="python" />
                      <el-option label="C++" value="cpp" />
                      <el-option label="Java" value="java" />
                      <el-option label="Go" value="go" />
                      <el-option label="JavaScript" value="javascript" />
                    </el-select>
                  </div>
                  <div class="ctrl-group">
                    <label>案例交付形态</label>
                    <el-radio-group v-model="agentConfigs.code.case_type" size="small" class="w-full-radios">
                      <el-radio-button label="basic_demo">基础教学</el-radio-button>
                      <el-radio-button label="algorithm_template">算法模板</el-radio-button>
                      <el-radio-button label="debug_demo">调试排错</el-radio-button>
                    </el-radio-group>
                  </div>
                </div>
              </div>

              <div class="config-card">
                <div class="cc-header">
                  <el-icon class="text-emerald"><Edit /></el-icon> 自适应强化题库
                </div>
                <div class="cc-body">
                  <div class="ctrl-group">
                    <label>测验难度引擎</label>
                    <el-radio-group v-model="agentConfigs.quiz.difficulty_mode" size="small" class="w-full-radios">
                      <el-radio-button label="basic">基础巩固</el-radio-button>
                      <el-radio-button label="adaptive">动态自适应</el-radio-button>
                      <el-radio-button label="exam">硬核考研</el-radio-button>
                    </el-radio-group>
                  </div>
                  <div class="ctrl-group">
                    <label>生成题目数量: <b>{{ agentConfigs.quiz.question_count }} 道</b></label>
                    <el-slider v-model="agentConfigs.quiz.question_count" :min="1" :max="20" :step="1" class="custom-slider" />
                  </div>
                </div>
              </div>

              <div class="config-card">
                <div class="cc-header">
                  <el-icon class="text-indigo"><Collection /></el-icon> 前沿学术延展
                </div>
                <div class="cc-body">
                  <div class="ctrl-group">
                    <label>阅读文献深度</label>
                    <el-select v-model="agentConfigs.reading.reading_depth" size="small" class="w-full">
                      <el-option label="课程内延展 (Course Extended)" value="course_extended" />
                      <el-option label="工程化实践 (Engineering)" value="engineering" />
                      <el-option label="前沿学术论文 (Frontier)" value="frontier" />
                    </el-select>
                  </div>
                  <div class="ctrl-group">
                    <label>文献推送数量: <b>{{ agentConfigs.reading.max_items }} 篇</b></label>
                    <el-slider v-model="agentConfigs.reading.max_items" :min="1" :max="10" :step="1" class="custom-slider" />
                  </div>
                </div>
              </div>

            </div>
          </div>

          <div class="personalize-footer">
            <el-button plain round size="large" @click="currentPhase = 'input'">返回修改需求</el-button>
            <el-button type="primary" round size="large" class="launch-btn" @click="startGeneration">
              确认配置，启动多智能体加工 <el-icon class="el-icon--right"><VideoPlay /></el-icon>
            </el-button>
          </div>
        </div>
      </div>

      <div v-else-if="currentPhase === 'generating'" class="phase-view generating-view" key="generating">
        <div class="working-container">
          <div class="working-header">
            <h2>AI 矩阵正在执行生成任务</h2>
            <p class="status-text">{{ currentStatusMessage }}</p>
          </div>
          <div class="collaboration-stage">
            <AgentCollaborationUniverse 
              :worker-agents="enabledAgentIds"
              :states="workflow.states"
              :messages="workflow.messages"
              :payloads="workflow.payloads"
              :orchestrator-message="currentStatusMessage"
              :get-agent-meta="getAgentMeta"
              :results="generatedResourcesMap"
            />
          </div>
        </div>
      </div>

      <div v-else-if="currentPhase === 'results'" class="phase-view results-view" key="results">
        <header class="results-header glass-nav">
          <div class="nav-brand">
            <el-icon class="success-icon"><CircleCheckFilled /></el-icon>
            <div class="nav-titles">
              <h2>个性化学习包已就绪</h2>
              <p>智能体团队已按照您的个性化配置生成了 {{ generatedResources.length }} 项定制资料</p>
            </div>
          </div>
          <div class="nav-actions">
            <el-button plain round @click="resetGenerator" class="back-btn">
              <el-icon><RefreshLeft /></el-icon> 新建任务
            </el-button>
            <el-button type="primary" round @click="pushToLearningPath" class="path-btn">
              加入学习路线 <el-icon class="el-icon--right"><Position /></el-icon>
            </el-button>
          </div>
        </header>

        <div class="results-body">
          <div class="bento-grid-container">
            <ResourceCard 
              v-for="res in sortedResources" 
              :key="res.id"
              :agent-id="res.type"
              :meta="getAgentMeta(res.type)"
              topic="个性化生成"
              :result-data="res.content"
              :class="getBentoClass(res.type)"
              @preview="handlePreview"
            />
          </div>
        </div>
      </div>

    </transition>

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

import ResourceCard from '@/components/resource/ResourceCard.vue'
import MindmapResourceView from '@/components/resource/MindmapResourceView.vue'
import MarkdownResourceView from '@/components/resource/MarkdownResourceView.vue'
import QuizResourceView from '@/components/resource/QuizResourceView.vue'
import DiagramResourceView from '@/components/resource/DiagramResourceView.vue'
import CodeResourceView from '@/components/resource/CodeResourceView.vue'
import ReadingResourceView from '@/components/resource/ReadingResourceView.vue'
import AgentCollaborationUniverse from '@/components/resource/AgentCollaborationUniverse.vue'

import { generateResources, type ResourceAgentId, type LearningScenario } from '@/api/resource'

const router = useRouter()

// ===================== 场景默认配置 =====================
// 定义宽松类型以支持不同场景的配置值
type AnyAgentConfigs = {
  content: {
    structure: string
    include_common_mistakes: boolean
    include_examples: boolean
    focus_mode: string
    depth_level: string
  }
  mindmap: {
    map_type: string
    max_depth: number
    highlight_weak: boolean
    expand_weak_points: boolean
    include_prerequisites: boolean
  }
  diagram: {
    diagram_type: string
    visual_style: string
    highlight_mode: string
    detail_level: string
  }
  quiz: {
    question_count: number
    difficulty_mode: string
    weak_point_weight: number
    exam_style: string
    include_analysis: boolean
  }
  code: {
    programming_language: string
    case_type: string
    comment_level: string
    include_test: boolean
    difficulty: string
  }
  reading: {
    reading_depth: string
    max_items: number
    resource_quality: string
    include_practice: boolean
    language_preference: string
  }
}

const SCENARIO_DEFAULTS: Record<string, Partial<AnyAgentConfigs>> = {
  exam_prep: {
    content: { structure: 'exam_points', include_common_mistakes: true, include_examples: true, focus_mode: 'weak_points', depth_level: 'standard' },
    quiz: { question_count: 5, difficulty_mode: 'exam', weak_point_weight: 70, exam_style: '考研', include_analysis: true },
    diagram: { diagram_type: 'auto', visual_style: 'exam', highlight_mode: 'weak_points', detail_level: 'standard' },
    mindmap: { map_type: 'exam_map', max_depth: 3, highlight_weak: true, expand_weak_points: true, include_prerequisites: false },
    code: { programming_language: 'python', case_type: 'algorithm_template', comment_level: 'standard', include_test: false, difficulty: 'intermediate' },
    reading: { reading_depth: 'course_extended', max_items: 3, resource_quality: 'classic', include_practice: false, language_preference: 'chinese' },
  },
  daily_review: {
    content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'weak_points', depth_level: 'quick' },
    quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 50, exam_style: 'school', include_analysis: true },
    diagram: { diagram_type: 'auto', visual_style: 'minimal', highlight_mode: 'key_points', detail_level: 'concise' },
    mindmap: { map_type: 'knowledge_tree', max_depth: 3, highlight_weak: true, expand_weak_points: true, include_prerequisites: false },
    code: { programming_language: 'python', case_type: 'basic_demo', comment_level: 'standard', include_test: false, difficulty: 'beginner' },
    reading: { reading_depth: 'course_extended', max_items: 3, resource_quality: 'balanced', include_practice: false, language_preference: 'chinese' },
  },
  project_practice: {
    content: { structure: 'case_driven', include_common_mistakes: true, include_examples: true, focus_mode: 'full_coverage', depth_level: 'deep' },
    quiz: { question_count: 5, difficulty_mode: 'adaptive', weak_point_weight: 30, exam_style: 'school', include_analysis: true },
    diagram: { diagram_type: 'auto', visual_style: 'minimal', highlight_mode: 'all', detail_level: 'detailed' },
    mindmap: { map_type: 'knowledge_tree', max_depth: 4, highlight_weak: false, expand_weak_points: false, include_prerequisites: true },
    code: { programming_language: 'python', case_type: 'basic_demo', comment_level: 'standard', include_test: true, difficulty: 'intermediate' },
    reading: { reading_depth: 'engineering', max_items: 5, resource_quality: 'latest', include_practice: true, language_preference: 'chinese' },
  },
  self_study: {
    content: { structure: 'progressive', include_common_mistakes: true, include_examples: true, focus_mode: 'key_concepts', depth_level: 'deep' },
    quiz: { question_count: 5, difficulty_mode: 'basic', weak_point_weight: 40, exam_style: 'school', include_analysis: true },
    diagram: { diagram_type: 'auto', visual_style: 'minimal', highlight_mode: 'key_points', detail_level: 'standard' },
    mindmap: { map_type: 'knowledge_tree', max_depth: 4, highlight_weak: false, expand_weak_points: false, include_prerequisites: true },
    code: { programming_language: 'python', case_type: 'basic_demo', comment_level: 'verbose', include_test: false, difficulty: 'beginner' },
    reading: { reading_depth: 'course_extended', max_items: 3, resource_quality: 'balanced', include_practice: false, language_preference: 'chinese' },
  },
}

// ===================== 1. 核心状态 =====================
type Phase = 'input' | 'personalize' | 'generating' | 'results'
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
  { id: 'content', name: '核心知识讲解', icon: Document },
  { id: 'mindmap', name: '知识结构图谱', icon: Share },
  { id: 'diagram', name: '原理解析图解', icon: Monitor },
  { id: 'code', name: '实战代码沙箱', icon: Cpu },
  { id: 'quiz', name: '自适应强化题库', icon: Edit },
  { id: 'reading', name: '前沿学术延展', icon: Collection }
]

const getAgentMeta = (id: string) => agentMetaList.find(a => a.id === id) || { name: id, icon: Document }
const enabledAgentIds = computed(() => ['content', 'mindmap', 'diagram', 'code', 'quiz', 'reading'])

// ===================== 2. 参数配置状态 =====================
const agentConfigs = reactive({
  content: {
    structure: 'progressive' as const,
    include_common_mistakes: true,
    include_examples: true,
    focus_mode: 'full_coverage' as const,
    depth_level: 'standard' as const,
  },
  mindmap: {
    map_type: 'knowledge_tree' as const,
    max_depth: 3,
    highlight_weak: true,
    expand_weak_points: false,
    include_prerequisites: false,
  },
  diagram: {
    diagram_type: 'auto' as const,
    visual_style: 'minimal' as const,
    highlight_mode: 'key_points' as const,
    detail_level: 'standard' as const,
  },
  quiz: {
    question_count: 5,
    difficulty_mode: 'adaptive' as const,
    weak_point_weight: 50,
    exam_style: 'school' as const,
    include_analysis: true,
  },
  code: {
    programming_language: 'python' as const,
    case_type: 'basic_demo' as const,
    comment_level: 'standard' as const,
    include_test: false,
    difficulty: 'beginner' as const,
  },
  reading: {
    reading_depth: 'course_extended' as const,
    max_items: 3,
    resource_quality: 'balanced' as const,
    include_practice: false,
    language_preference: 'chinese' as const,
  },
})

// 场景切换函数
const applyScenarioDefaults = (scenario: LearningScenario) => {
  const defaults = SCENARIO_DEFAULTS[scenario]
  if (!defaults) return

  // 深度合并，保留用户可能已修改的其他字段
  Object.keys(defaults).forEach((key) => {
    const agentKey = key as keyof typeof agentConfigs
    const agentDefaults = defaults[agentKey]
    if (agentDefaults) {
      Object.assign(agentConfigs[agentKey], agentDefaults)
    }
  })
}

// 无解析，直接切换页面
const goToPersonalize = () => {
  if (!naturalInput.value.trim()) return
  currentPhase.value = 'personalize'
}

// ===================== 3. 工作流与生成逻辑 =====================
const currentStatusMessage = ref('')
const workflow = reactive({ 
  states: {} as Record<string, string>,
  messages: {} as Record<string, string>,
  payloads: {} as Record<string, any>
})
const generatedResources = ref<any[]>([])

const generatedResourcesMap = computed(() => {
  const map: Record<string, any> = {}
  generatedResources.value.forEach(r => map[r.type] = r.content)
  return map
})

const sortedResources = computed(() => {
  const order = ['content', 'diagram', 'mindmap', 'code', 'quiz', 'reading']
  return [...generatedResources.value].sort((a, b) => order.indexOf(a.type) - order.indexOf(b.type))
})

const getBentoClass = (type: string) => {
  if (type === 'content') return 'bento-main'
  if (['diagram', 'mindmap'].includes(type)) return 'bento-side'
  return 'bento-small'
}

const friendlyMessageMap: Record<string, string> = {
  'content': '正在应用选定的【讲解结构】策略撰写核心图文...',
  'mindmap': '正在严格按照【层级深度限制】构建知识网络...',
  'diagram': '正在调用专业渲染引擎绘制指定类型的图表...',
  'code': '正在构建对应语言环境的带注释实操沙箱...',
  'quiz': '正在调取题库引擎，自适应装配试卷...',
  'reading': '正在跨学术库匹配契合该深度的拓展资料...'
}

const startGeneration = async () => {
  currentPhase.value = 'generating'
  generatedResources.value = []
  currentStatusMessage.value = '正在将配置参数打包并发送至后端集群...'
  
  enabledAgentIds.value.forEach(id => {
    workflow.states[id] = 'pending'
    workflow.messages[id] = ''
  })

  // 调用 API
  generateResources(
    {
      learning_need: naturalInput.value,
      learning_scenario: learningScenario.value,
      selected_agents: enabledAgentIds.value.map(id => ({ agent_id: id as ResourceAgentId, enabled: true, priority: 1 })),
      agent_configs: agentConfigs,
      output_options: { output_format: 'json' }
    },
    (event: any) => {
      const type = event.event_type || event.type
      const agent = event.agent
      
      if ((type === 'agent' || type === 'agent_status') && agent) {
        workflow.states[agent] = event.status || 'running'
        if (event.status === 'running') {
          currentStatusMessage.value = friendlyMessageMap[agent] || 'AI 导师正在高速生成资料...'
        }
      }
      
      if ((type === 'resource' || type === 'artifact_ready') && agent) {
        workflow.states[agent] = 'success'
        const res = event.payload?.resource || event.payload || event.artifact
        if (res) {
          generatedResources.value.push({ 
            id: Date.now() + '_' + agent, 
            type: agent, 
            title: res.title || getAgentMeta(agent).name, 
            content: res.content || res 
          })
        }
      }
    },
    () => { 
      currentStatusMessage.value = '全部指令执行完毕，排版引擎介入中...'
      setTimeout(() => { currentPhase.value = 'results' }, 1500) 
    },
    (err: any) => { 
      currentPhase.value = 'personalize'
      ElMessage.error(err.message || '生成中断，请稍后重试') 
    }
  )
}

// ===================== 4. UI 交互 =====================
const resetGenerator = () => {
  naturalInput.value = ''
  currentPhase.value = 'input'
}

const pushToLearningPath = () => {
  ElMessage.success('已无缝衔接至学习路线图！')
  router.push('/path-planner')
}

const previewVisible = ref(false)
const previewData = ref<any>(null)
const handlePreview = (data: any) => {
  previewData.value = data
  previewVisible.value = true
}
</script>

<style scoped>
.elegant-generator-layout {
  width: 100%;
  height: calc(100vh - 64px);
  background: #FCFDFE;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  overflow-x: hidden;
  position: relative;
}

.phase-view {
  position: absolute;
  top: 0; left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #FCFDFE;
}

/* 滑动转场动画 */
.page-slide-enter-active, .page-slide-leave-active {
  transition: opacity 0.4s ease, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.page-slide-enter-from { opacity: 0; transform: translateY(30px) scale(0.98); }
.page-slide-leave-to { opacity: 0; transform: translateY(-30px) scale(1.02); }

/* ================= Phase 1: Input View ================= */
.input-view {
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background-image: radial-gradient(circle at 50% 0%, rgba(59, 130, 246, 0.03) 0%, transparent 60%);
}

.input-container { width: 100%; max-width: 800px; display: flex; flex-direction: column; align-items: center; margin-top: -8vh; }
.welcome-header { text-align: center; margin-bottom: 2.5rem; }
.sparkle-icon {
  display: inline-flex; justify-content: center; align-items: center;
  width: 56px; height: 56px; background: #EFF6FF; color: #3B82F6; font-size: 1.8rem;
  border-radius: 20px; margin-bottom: 1.5rem; box-shadow: 0 8px 20px rgba(59, 130, 246, 0.15);
}
.greeting-title { font-size: 2.5rem; font-weight: 800; color: #0F172A; margin: 0 0 1rem; letter-spacing: -0.02em; }
.greeting-subtitle { font-size: 1.05rem; color: #64748B; line-height: 1.7; max-width: 660px; margin: 0 auto; }

.search-box-wrapper {
  width: 100%; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 28px;
  box-shadow: 0 10px 40px rgba(15, 23, 42, 0.05); padding: 8px; transition: all 0.3s ease;
}
.search-box-wrapper.is-focused { border-color: #3B82F6; box-shadow: 0 15px 50px rgba(59, 130, 246, 0.1); transform: translateY(-2px); }

.elegant-textarea :deep(.el-textarea__inner) {
  border: none; background: transparent; box-shadow: none !important;
  font-size: 1.15rem; color: #1E293B; padding: 20px 24px; line-height: 1.6; resize: none;
}
.elegant-textarea :deep(.el-textarea__inner)::placeholder { color: #94A3B8; font-weight: 400; }

.search-actions { display: flex; justify-content: space-between; align-items: center; padding: 8px 16px 8px 24px; }
.ai-hint { font-size: 0.85rem; color: #94A3B8; display: flex; align-items: center; gap: 6px; }
.ai-hint .el-icon { color: #3B82F6; font-size: 1rem; }

.generate-btn {
  padding: 12px 28px; font-size: 1.05rem; font-weight: 700; border-radius: 999px;
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.25); transition: transform 0.2s ease;
}
.generate-btn:hover:not(:disabled) { transform: scale(1.03); }

.suggestion-area { margin-top: 2.5rem; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.suggestion-label { font-size: 0.85rem; color: #94A3B8; font-weight: 600; }
.suggestion-tags { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; }
.s-tag {
  cursor: pointer; background: #F8FAFC !important; border-color: #E2E8F0 !important;
  color: #475569 !important; padding: 8px 16px; height: auto; font-size: 0.9rem; transition: all 0.2s ease;
}
.s-tag:hover { background: #EFF6FF !important; border-color: #BFDBFE !important; color: #3B82F6 !important; }

/* ================= Phase 2: Personalize View ================= */
.personalize-view { background: #FCFDFE; align-items: center; overflow-y: auto; padding: 40px 20px; }
.personalize-container { width: 100%; max-width: 1100px; display: flex; flex-direction: column; gap: 32px; }

.view-header { text-align: center; margin-bottom: 10px; }
.view-header h2 { font-size: 2rem; font-weight: 800; color: #0F172A; margin: 0 0 12px; }
.view-header p { font-size: 1.05rem; color: #64748B; margin: 0; }

.scenario-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: #F0F9FF;
  border-radius: 12px;
  border: 1px solid #BAE6FD;
}
.scenario-selector label {
  font-weight: 700;
  color: #0369A1;
  font-size: 0.95rem;
}
.scenario-selector .hint {
  font-size: 0.85rem;
  color: #64748B;
  margin-left: auto;
}

.config-section { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 24px; padding: 32px; box-shadow: 0 4px 20px rgba(0,0,0,0.02); }
.agent-configs-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
.config-card { border: 1px solid #F1F5F9; border-radius: 16px; background: #F8FAFC; overflow: hidden; display: flex; flex-direction: column; }
.cc-header { padding: 16px 20px; font-weight: 800; font-size: 0.95rem; color: #0F172A; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #F1F5F9; background: #FFFFFF; }

.text-blue { color: #3B82F6; } .text-emerald { color: #10B981; } .text-purple { color: #8B5CF6; } 
.text-orange { color: #F59E0B; } .text-red { color: #EF4444; } .text-indigo { color: #6366F1; }

.cc-body { padding: 20px; display: flex; flex-direction: column; gap: 20px; flex: 1; }
.ctrl-group { display: flex; flex-direction: column; gap: 10px; }
.ctrl-switch-group { gap: 12px; }
.ctrl-switch { display: flex; justify-content: space-between; align-items: center; }
.ctrl-group label { font-size: 0.85rem; color: #64748B; font-weight: 600; }
.ctrl-group label b { color: #3B82F6; }
.custom-slider { margin-top: -6px; padding: 0 10px; }

:deep(.w-full) { width: 100%; }
:deep(.w-full-radios) { display: flex; width: 100%; }
:deep(.w-full-radios .el-radio-button) { flex: 1; }
:deep(.w-full-radios .el-radio-button__inner) { width: 100%; padding: 8px 0; }

:deep(.el-radio-button__inner) { border-radius: 8px !important; border: 1px solid #E2E8F0 !important; margin-right: 6px; background: #FFFFFF; box-shadow: none !important; color: #64748B; font-size: 0.8rem; }
:deep(.el-radio-button:last-child .el-radio-button__inner) { margin-right: 0; }
:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) { background-color: #EEF2FF !important; color: #3B82F6 !important; border-color: #BFDBFE !important; font-weight: 700; }

.personalize-footer { display: flex; justify-content: center; gap: 20px; margin-top: 10px; padding-bottom: 20px; }
.launch-btn { font-weight: 800; box-shadow: 0 8px 20px rgba(59, 130, 246, 0.3); transition: transform 0.2s; }
.launch-btn:hover { transform: translateY(-2px); }

/* ================= Phase 3: Generating View ================= */
.generating-view { justify-content: flex-start; align-items: center; padding-top: 60px; overflow-y: auto; }
.working-header { text-align: center; display: flex; flex-direction: column; align-items: center; margin-bottom: 30px; }
.working-header h2 { font-size: 1.8rem; font-weight: 800; color: #0F172A; margin: 0 0 0.8rem; }
.status-text { font-size: 1.1rem; color: #3B82F6; margin: 0; font-weight: 600; }
.collaboration-stage { width: 100%; max-width: 1200px; background: #FFFFFF; border-radius: 32px; padding: 40px; box-shadow: 0 0 0 1px #F1F5F9, 0 20px 40px rgba(0,0,0,0.02); }

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

.results-body { padding: 40px; }
.bento-grid-container { display: grid; grid-template-columns: repeat(4, 1fr); grid-auto-rows: minmax(180px, auto); gap: 24px; max-width: 1600px; margin: 0 auto; }
:deep(.bento-main) { grid-column: span 2; grid-row: span 2; }
:deep(.bento-side) { grid-column: span 2; grid-row: span 1; }
:deep(.bento-small) { grid-column: span 1; grid-row: span 1; }

@media (max-width: 1200px) {
  .bento-grid-container { grid-template-columns: repeat(2, 1fr); }
  :deep(.bento-main), :deep(.bento-side) { grid-column: span 2; }
  :deep(.bento-small) { grid-column: span 1; }
  .agent-configs-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .agent-configs-grid { grid-template-columns: 1fr; }
}

.elegant-dialog :deep(.el-dialog) { border-radius: 24px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); }
.elegant-dialog :deep(.el-dialog__header) { padding: 24px 32px 20px; margin-right: 0; border-bottom: 1px solid #F1F5F9; }
.elegant-dialog :deep(.el-dialog__title) { font-weight: 800; font-size: 1.2rem; color: #0F172A; }
.elegant-dialog :deep(.el-dialog__body) { padding: 32px; background: #F8FAFC; }
</style>
